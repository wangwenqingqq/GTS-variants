#!/usr/bin/env python3
"""Source groups, predication, relative PCs and raw-unit rows remain distinct."""
import csv
from pathlib import Path
import tempfile
import analyze

with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp) / 'source.csv'
    with p.open('w', newline='') as f:
        w = csv.writer(f)
        for name in ['helper', 'kernel', 'helper']:
            w.writerow(['Kernel Name', name]); w.writerow(['Address', 'Source'] + list(analyze.COUNTS.values()))
            w.writerow(['0x1000', 'ISETP P0, PT, R0, R1, PT', 10, 40, 30, 2])
            w.writerow(['0x1010', '@P0 CALL.ABS.NOINC 0xDEADBEEF', 10, 40, 20, 5])
    groups = analyze.source_groups(p); assert len(groups) == 3
    assert [g['function'] for g in groups] == ['helper', 'kernel', 'helper']
    s = analyze.summarize_group(groups[0])
    assert s['totals'] == {'warp_instructions': 20, 'thread_instructions': 80, 'predicated_thread_instructions': 50, 'stall_samples': 7}
    assert s['entry']['relative_pc'] == 0 and s['executed_calls'][0]['relative_pc'] == 16
    assert s['top_stall_sites'][0]['predicated_thread_instructions'] == 20
    assert 'DEADBEEF' not in str(s) and '0x1000' not in str(s)
    p.write_text('"ID","Kernel Name","gpu__time_duration.sum"\n"","","nsecond"\n"0","kernel","123"\n')
    units, rows = analyze.raw_metrics(p)
    assert len(rows) == 1 and units['gpu__time_duration.sum'] == 'nsecond' and rows[0]['gpu__time_duration.sum'] == '123'
print('PASS: repeated function groups, warp/thread/predicated counts, relative sites, units, no raw instruction publication')
