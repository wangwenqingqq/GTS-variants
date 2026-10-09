#!/usr/bin/env python3
"""Bind complete CPU answers to registered inputs and successful original receipts."""
import argparse
import csv
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cpu

SUFFIXES = ('.queries.csv', '.ids.i32', '.dist.f32', '.native_squared.f64', '.native.json')


def check_receipt(receipt, source_hash, registration_hash, output_hashes):
    assert receipt['exit_code'] == 0 and receipt['runtime_valid'] and not receipt['timed_out']
    assert math.isfinite(receipt['wall_s']) and receipt['wall_s'] > 0
    assert receipt['script_sha256'] == source_hash
    assert receipt['registration_sha256'] == registration_hash
    assert receipt['output_hashes'] == output_hashes, 'changed/incomplete original outputs'


def check_rows(rows, spec):
    assert len(rows) == 64 and len(spec['queries']) == 32
    offset = 0
    for i, r in enumerate(rows):
        qi = i % 32
        assert r['task'] == ('knn' if i < 32 else 'range') and int(r['query']) == qi
        assert int(r['qid']) == spec['queries'][qi]['physical_qid'], 'changed query coordinate'
        assert int(r['offset']) == offset and 0 <= int(r['count']) <= spec['N']
        if i < 32: assert int(r['count']) == 8
        assert math.isfinite(float(r['ack_ms'])) and float(r['ack_ms']) >= 0
        offset += int(r['count'])
    return offset


def qualify(a):
    registered = json.loads((a.work / 'CPU_REGISTERED.json').read_text())
    contract = json.loads((HERE / 'CONTRACT.json').read_text())
    assert registered['contract_sha256'] == cpu.sha(HERE / 'CONTRACT.json')
    assert registered['script_sha256'] == cpu.sha(a.executed_source)
    assert [j['label'] for j in registered['jobs']] == contract['baseline_diagnostic']['job_order']
    bindings = []
    # All timing receipts must exist before any exhaustive validation work starts.
    for job in registered['jobs']:
        label = job['label']; prefix = a.work / 'cpu_outputs' / label
        snapshot = Path(job['snapshot']); data = Path(job['data'])
        spec = json.loads((snapshot / 'SNAPSHOT.json').read_text())
        assert cpu.sha(snapshot / 'SNAPSHOT.json') == job['snapshot_sha256']
        assert (spec['N'], spec['D'], spec['Q']) == (1000000, 960, 32)
        assert spec['data_sha256'] == job['data_sha256'] == cpu.sha(data)
        hashes = {label+s: cpu.sha(Path(str(prefix)+s)) for s in SUFFIXES}
        receipt_path = a.work / 'cpu_guards' / label / 'receipt.json'
        receipt = json.loads(receipt_path.read_text())
        check_receipt(receipt, registered['script_sha256'], cpu.sha(a.work / 'CPU_REGISTERED.json'), hashes)
        with Path(str(prefix)+'.queries.csv').open() as f: rows = list(csv.DictReader(f))
        total = check_rows(rows, spec)
        for suffix, size in (('.ids.i32', 4), ('.dist.f32', 4), ('.native_squared.f64', 8)):
            assert Path(str(prefix)+suffix).stat().st_size == total*size, 'incomplete payload'
        native = json.loads(Path(str(prefix)+'.native.json').read_text())
        assert native['method'] == job['method'] and native['requested_native_threads'] == 1
        assert native['source_sha256'] == registered['script_sha256']
        assert native['snapshot_sha256'] == job['snapshot_sha256']
        assert native['radius'] == contract['scope']['radius']
        assert not Path(str(prefix)+'.quality.json').exists(), 'never replace a quality run'
        bindings.append(dict(label=label, receipt_sha256=cpu.sha(receipt_path),
            data_sha256=job['data_sha256'], snapshot_sha256=job['snapshot_sha256'], output_hashes=hashes))
    for job, binding in zip(registered['jobs'], bindings):
        prefix = a.work / 'cpu_outputs' / job['label']
        assert np.isfinite(cpu.validate.load(Path(job['data']))).all()
        cpu.check(SimpleNamespace(data=Path(job['data']), output=prefix, library=a.library))
        proof = json.loads(Path(str(prefix)+'.quality.json').read_text())
        assert proof['output_hashes'] == binding['output_hashes']
        binding.update(quality_sha256=cpu.sha(Path(str(prefix)+'.quality.json')), passed=proof['passed'])
    destination = a.work / 'CPU_QUALITY_BINDING.json'; assert not destination.exists()
    cpu.save(destination, dict(passed=all(x['passed'] for x in bindings), jobs=bindings,
        registration_sha256=cpu.sha(a.work / 'CPU_REGISTERED.json'),
        analyst_sha256=cpu.sha(Path(__file__)), executed_source_sha256=cpu.sha(a.executed_source),
        contract_sha256=cpu.sha(HERE / 'CONTRACT.json'),
        scope='six fresh static diagnostics; all registered coordinates, members and fields; native times preserved on failure'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('work', 'library', 'executed-source'): p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); assert __debug__
    assert HERE.parents[1] not in a.work.resolve().parents
    qualify(a)
