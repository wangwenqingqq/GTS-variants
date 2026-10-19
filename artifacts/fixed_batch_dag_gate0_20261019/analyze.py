"""Independently check every case/witness and sum fixed-batch source costs."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import csv
import struct
from pathlib import Path
from prepare import load, save, sha
from test_solver import witness

HERE = Path(__file__).resolve().parent


def cases(path):
    data = path.read_bytes()
    magic,b,z,n = struct.unpack_from('<8sIII',data)
    assert magic == b'BQSI001\n'
    orders = [list(data[20+q*z:20+(q+1)*z]) for q in range(b)]
    at = 20+b*z
    assert len(data) == at+12*n
    return orders,dict(struct.unpack_from('<QI',data,at+12*i) for i in range(n))


def analyze(inputs, runs, out):
    c = load(HERE/'CONTRACT.json')
    prep = load(inputs/'PREPARE.json')
    assert prep['passed'] and prep['contract_sha256'] == sha(HERE/'CONTRACT.json')
    execution = load(runs/'RUNS.json')
    assert execution['passed'] and execution['CPU_processes'] == 28 and execution['GPU_starts'] == 0
    records = {r['label']:r for r in execution['records']}
    assert set(records) == {b['label'] for b in prep['batches']}
    assert {f.stem for f in (runs/'runs').glob('*.csv')} == set(records)
    out.mkdir()
    batches = []
    for batch in prep['batches']:
        name = batch['label']
        inp,path = inputs/(name+'.bin'),runs/'runs'/(name+'.csv')
        assert sha(inp) == batch['input_sha256'] == records[name]['input_sha256']
        receipt = load(runs/'receipts'/(name+'.result.json'))
        assert receipt == records[name] and receipt['returncode'] == 0 and receipt['GPU_starts'] == 0
        assert sha(path) == receipt['output_sha256']
        orders,expected = cases(inp)
        assert orders == batch['orders'] and len(expected) == batch['contexts']
        sums = dict.fromkeys(('independent','trie','fanout','lookahead','lower','upper'),0)
        exact_sectors = expansions = seen = 0
        with path.open() as f:
            for row in csv.DictReader(f):
                key,freq = int(row['key']),int(row['frequency'])
                assert freq == expected.pop(key)
                depth = [(key >> (5*q)) & 31 for q in range(batch['B'])]
                assert int(row['independent']) == sum(depth)
                union = {t for order,n in zip(orders,depth) for t in order[:n]}
                lo,hi = int(row['lower']),int(row['upper'])
                assert len(union) <= lo <= hi <= min(int(row[k]) for k in ('trie','fanout','lookahead'))
                assert max(depth) <= hi <= sum(depth)
                witness(orders,depth,row['witness'])
                assert len(row['witness'])//4 == hi
                expanded = int(row['expanded'])
                assert 0 <= expanded <= c['oracle']['max_expansions_per_context']
                expansions += expanded
                exact_sectors += freq*int(lo == hi)
                for k in sums:
                    sums[k] += freq*int(row[k])
                seen += freq
        assert not expected and seen == batch['sectors']
        assert expansions <= c['oracle']['max_expansions_per_batch']
        inputs_source = batch['B']*(960*4+30*4)
        shared_terminal = batch['terminal_shared_sectors']*960*32
        independent_terminal = batch['terminal_independent_sectors']*960*32
        source = {k:v*1024+shared_terminal+inputs_source for k,v in sums.items()}
        source['independent'] = sums['independent']*1024+independent_terminal+inputs_source
        source['full_scan'] = c['N']*c['D']*4+inputs_source
        source['simple_envelope'] = min(source[k] for k in ('trie','fanout','lookahead'))
        assert source['lower'] <= source['upper'] <= source['simple_envelope']
        batches.append(dict(label=name,B=batch['B'],query_indices=batch['query_indices'],contexts=batch['contexts'],
                            exact_sectors=exact_sectors,sectors=seen,expansions=expansions,
                            tile_reads=sums,source_bytes=source,query_inputs_source_bytes=inputs_source,
                            shared_terminal_source_bytes=shared_terminal,independent_terminal_source_bytes=independent_terminal,
                            filter_dimension_operations=batch['filter_dimension_operations'],
                            terminal_dimension_operations=batch['terminal_query_points']*960,
                            full_scan_dimension_operations=batch['B']*c['N']*960,
                            live_partial_bytes=8*batch['B']*8,live_mask_bytes=batch['B'],tile_buffer_bytes=1024,
                            raw_output_sha256=receipt['output_sha256']))
    groups = []
    for b in c['batch_sizes']:
        cells = [r for r in batches if r['B'] == b]
        source = {k:sum(r['source_bytes'][k] for r in cells) for k in cells[0]['source_bytes']}
        simple,low,upper = source['lookahead'],source['lower'],source['upper']
        label = ('SIMPLE_WITHIN_10_PERCENT' if 10*(simple-low) < simple else
                 'MATERIAL_REMAINING_SPACE' if 10*(simple-upper) >= simple else
                 'UNRESOLVED_AT_10_PERCENT')
        envelope = source['simple_envelope']
        groups.append(dict(B=b,batches=len(cells),queries=32,source_bytes=source,
                           source_bytes_per_query={k:v/32 for k,v in source.items()},
                           remaining_read_ratio=simple/source['independent'],
                           headroom_proven=(simple-upper)/simple,headroom_maximum=(simple-low)/simple,
                           envelope_headroom_proven=(envelope-upper)/envelope,
                           envelope_headroom_maximum=(envelope-low)/envelope,
                           filter_headroom_proven=(sum(r['tile_reads']['lookahead']-r['tile_reads']['upper'] for r in cells))/sum(r['tile_reads']['lookahead'] for r in cells),
                           filter_headroom_maximum=(sum(r['tile_reads']['lookahead']-r['tile_reads']['lower'] for r in cells))/sum(r['tile_reads']['lookahead'] for r in cells),
                           exact_sectors=sum(r['exact_sectors'] for r in cells),sectors=sum(r['sectors'] for r in cells),
                           solver_expansions=sum(r['expansions'] for r in cells),decision=label))
    summary = dict(passed=True,contract_sha256=sha(HERE/'CONTRACT.json'),prepare_sha256=sha(inputs/'PREPARE.json'),
                   execution_sha256=sha(runs/'RUNS.json'),batch_results=batches,groups=groups,
                   primary='GREEDY_LOOKAHEAD;envelope is a stronger posthoc nondeployable control',
                   scope='Finite fixed-query-chain source model;not actual DRAM,online planning or Host-ready latency',
                   all_contexts_and_feasible_witnesses_checked=True,new_distance_evaluations=0,GPU_starts=0)
    save(out/'RESULTS.json',summary)
    rows = []
    for r in groups:
        for mode,bytes_ in r['source_bytes_per_query'].items():
            rows.append(dict(B=r['B'],strategy=mode,source_bytes_per_query=bytes_,
                             headroom_proven=r['headroom_proven'] if mode == 'lookahead' else '',
                             headroom_maximum=r['headroom_maximum'] if mode == 'lookahead' else ''))
    with (out/'summary.csv').open('x',newline='') as f:
        w = csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    print('ANALYSIS_PASS',len(batches),'batches;all witnesses checked;0 GPU targets')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--runs',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    analyze(a.inputs,a.runs,a.out)
