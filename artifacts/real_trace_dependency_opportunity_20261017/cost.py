"""Prepare and verify CPU-only planning diagnostics; never launch a GPU."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import csv
import hashlib
import json
import statistics
import struct
from pathlib import Path
from replay import quantile, save

BOOKS = ('wikipedia-1M_expiration_time_runbook',
         'wikipedia-1M_expiration_time_replace_delete_runbook')


def digest(path):
    b = path.read_bytes()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


def prepare(replays, out):
    out.mkdir()
    entries = {}
    for book in BOOKS:
        result = json.loads((replays/book/'RESULT.json').read_text())
        assert result['passed'] and result['scopes']['within_call_512']['eliminated'] == 0
        cases = [c for c in json.loads((replays/book/'cpu_cases.json').read_text())
                 if c['scope'] == 'within_call_512']
        assert len(cases) == result['scopes']['within_call_512']['batches']
        f = out/(book+'.bin')
        with f.open('xb') as stream:
            stream.write(struct.pack('<8sI', b'GTSTRC1\n', len(cases)))
            for c in cases:
                assert 1 <= c['deleted'] <= 512 and len(c['commands']) <= c['deleted']
                stream.write(struct.pack('<4i', c['request_step'], c['n'], c['deleted'], len(c['commands'])))
                for src, dst in c['commands']:
                    stream.write(struct.pack('<2i', src, dst))
        entries[f.name] = dict(**digest(f), cases=len(cases),
                               M=sum(len(c['commands']) for c in cases),
                               replay_result_sha256=digest(replays/book/'RESULT.json')['sha256'])
    save(out/'INPUTS.json', dict(passed=True, files=entries, GPU_starts=0))


def inputs(folder):
    receipt = json.loads((folder/'INPUTS.json').read_text())
    result = {}
    for book in BOOKS:
        f = folder/(book+'.bin')
        identity = receipt['files'][f.name]
        assert all(digest(f)[k] == identity[k] for k in ('bytes', 'sha256'))
        body, at, cases = f.read_bytes(), 12, []
        magic, n = struct.unpack_from('<8sI', body)
        assert magic == b'GTSTRC1\n' and n == identity['cases']
        for _ in range(n):
            step, live, rows, moves = struct.unpack_from('<4i', body, at)
            at += 16
            commands = [struct.unpack_from('<2i', body, at+8*j) for j in range(moves)]
            at += 8*moves
            signature = 1469598103934665603
            assert len({dst for src, dst in commands}) == moves
            assert not {src for src, dst in commands}.intersection(dst for src, dst in commands)
            for src, dst in sorted(commands, key=lambda x: x[1]):
                for byte in struct.pack('<2i', src, dst):
                    signature = ((signature ^ byte)*1099511628211) & ((1 << 64)-1)
            cases.append(dict(step=step, n=live, rows=rows, M=moves, signature=signature))
        assert at == len(body) and sum(c['M'] for c in cases) == identity['M']
        result[book] = cases
    return result


def analyze(folder, runs, out):
    cases = inputs(folder)
    expected = {f'{book}_r{r}.csv' for book in BOOKS for r in range(6)}
    assert {f.name for f in runs.glob('*.csv')} == expected
    processes = []
    for book in BOOKS:
        for r in range(6):
            path = runs/f'{book}_r{r}.csv'
            records = list(csv.DictReader(path.open()))
            assert len(records) == 2*len(cases[book])
            parsed = []
            for i, record in enumerate(records):
                c = cases[book][i//2]
                variant = ('GENERIC_WAVES', 'GENERIC_DSE')[(r+i%2)%2]
                for field, wanted in (('case', i//2), ('request_step', c['step']),
                                      ('rows', c['rows']), ('M', c['M']), ('F', c['M']),
                                      ('signature', c['signature']), ('levels', int(c['M'] > 0))):
                    assert int(record[field]) == wanted, (path.name, i, field)
                assert record['variant'] == variant
                build, release, total = (int(record[k]) for k in ('build_ns', 'release_ns', 'total_ns'))
                assert build >= 0 and release >= 0 and total == build+release
                parsed.append(dict(variant=variant, build=build, release=release, total=total))
            for variant in ('GENERIC_WAVES', 'GENERIC_DSE'):
                values = [v for v in parsed if v['variant'] == variant]
                processes.append(dict(book=book, round=r, variant=variant, plans=len(values),
                                      build_ms=sum(v['build'] for v in values)/1e6,
                                      release_ms=sum(v['release'] for v in values)/1e6,
                                      total_ms=sum(v['total'] for v in values)/1e6,
                                      mean_plan_us=statistics.mean(v['total'] for v in values)/1000,
                                      p50_plan_us=quantile([v['total']/1000 for v in values], .5),
                                      p95_plan_us=quantile([v['total']/1000 for v in values], .95),
                                      input_run=digest(path)))
    cells = []
    for book in BOOKS:
        for variant in ('GENERIC_WAVES', 'GENERIC_DSE'):
            rr = [r for r in processes if r['book'] == book and r['variant'] == variant]
            cells.append(dict(book=book, variant=variant, process_rounds=6,
                              total_planning_median_ms=statistics.median(r['total_ms'] for r in rr),
                              total_planning_min_ms=min(r['total_ms'] for r in rr),
                              total_planning_max_ms=max(r['total_ms'] for r in rr),
                              per_plan_mean_median_us=statistics.median(r['mean_plan_us'] for r in rr),
                              per_plan_p50_median_us=statistics.median(r['p50_plan_us'] for r in rr),
                              per_plan_p95_median_us=statistics.median(r['p95_plan_us'] for r in rr)))
    save(out, dict(passed=True, CPU_processes=12, GPU_starts=0, processes=processes, cells=cells,
                   scope='Isolated planning build+destruction;signature/replay/input I/O excluded;not ACK or events+release',
                   scratch_allocator_peak_bytes='UNKNOWN', device_and_service_costs='UNKNOWN',
                   raw_order='Per-batch forward/reverse variant order balanced over six independent processes'))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='mode', required=True)
    pp = sub.add_parser('prepare')
    pp.add_argument('--replays', type=Path, required=True)
    pp.add_argument('--out', type=Path, required=True)
    aa = sub.add_parser('analyze')
    aa.add_argument('--inputs', type=Path, required=True)
    aa.add_argument('--runs', type=Path, required=True)
    aa.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.mode == 'prepare':
        prepare(a.replays, a.out)
    else:
        analyze(a.inputs, a.runs, a.out)
    print('CPU_COST_'+a.mode.upper()+'_PASS;GPU starts 0')
