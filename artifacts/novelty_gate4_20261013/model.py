"""One sector-accounting kill test; not a new GPU measurement."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''):
            h.update(b)
    return h.hexdigest()


def save(path, value):
    with Path(path).open('x') as f:
        f.write(json.dumps(value, indent=2) + '\n')


def warp_sectors(row, start, iteration, stride=960, base=0):
    return len({(base + 4 * (row * stride + start + lane + 32 * iteration)) // 32
                for lane in range(32)})


def sector_model():
    c = read(HERE / 'CONTRACT.json')
    for path, digest in c['parent_files'].items():
        assert sha(ROOT / path) == digest, path
    p = ROOT / 'artifacts/progressive_gpu_gate2_20261013'
    cost = read(p / 'cost/PRE_GPU_COST.json')
    replay = read(p / 'cost/REPLAY_SCREEN.json')
    ncu = read(p / 'traffic/DRAM_ACCOUNTING.json')['modes']['P1']
    rows, coordinate, transactions = [], 0, 0
    period = 32 // math.gcd(960 * 4, 32)
    for r in cost['rows']:
        widths = [warp_sectors(row, r['start'], it)
                  for row in range(period)
                  for it in range((r['end'] - r['start']) // 32)]
        per_row = sum(widths) * 32 // period
        useful = (r['end'] - r['start']) * 4
        actual = per_row * r['input_pairs']
        assert useful * r['input_pairs'] == r['coordinate_bytes']
        coordinate += r['coordinate_bytes']
        transactions += actual
        rows.append(dict(stage=r['stage'], start=r['start'], end=r['end'],
                         input_pairs=r['input_pairs'], row_alignment_period=period,
                         sectors_per_warp_instruction=sorted(set(widths)),
                         useful_bytes_per_row=useful, sector_bytes_per_row=per_row,
                         modeled_sector_bytes=actual))
    useful = coordinate / cost['queries']
    payload = cost['including_padding_flags'] + replay['replay_upper_coordinate_bytes_per_query']
    physical = ncu['means']['DRAM_bytes']
    headroom = 1 - coordinate / transactions
    return dict(complete=True, experiment='M1_SECTOR_MODEL', GPU_starts=0,
                evidence_state='theoretical', queries=cost['queries'], rows=rows,
                useful_coordinate_bytes_per_query=useful,
                modeled_coordinate_sector_bytes_per_query=transactions / cost['queries'],
                coordinate_sector_headroom_fraction=headroom,
                generous_all_noncoordinate_payload_removal_fraction=1 - useful / payload,
                modeled_total_with_refinement_bytes_per_query=payload,
                historical_NCU_total_bytes_per_query=physical,
                historical_difference_fraction=1 - useful / physical,
                historical_difference_is_universal_DRAM_floor=False,
                numeric_pass=headroom >= .20, decision='KILL_M1' if headroom < .20 else 'HEADROOM_ONLY',
                reason='Aligned full-warp128B loads consume every requested32B sector; gaps between rows do not overfetch within a warp',
                source_hashes={str(x.relative_to(ROOT)): sha(x) for x in
                               (HERE / 'CONTRACT.json', HERE / 'model.py')})


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    save(a.output, sector_model())
    print('M1 model saved', a.output)
