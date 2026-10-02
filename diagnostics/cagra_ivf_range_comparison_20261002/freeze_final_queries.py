#!/usr/bin/env python3
"""Freeze P6 final qids after choosing configurations on development data."""
import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent
DIAG = ROOT.parent
P5 = DIAG / "external_mask_validation_20261002"


def read_qids(path):
    values = list(map(int, path.read_text().split()))
    assert values[0] == len(values) - 1
    return values[1:]


def main():
    assert (ROOT / "FROZEN_CONFIG.json").exists()
    previous = json.loads((P5 / "QUERY_SETS.json").read_text())
    config_sha256 = hashlib.sha256((ROOT / "FROZEN_CONFIG.json").read_bytes()).hexdigest()
    output = {}
    for dataset, seed in (("GIST", 2026100210), ("Deep", 2026100211)):
        paths = [DIAG / name for name in previous[dataset]["excluded_files"]]
        paths.append(P5 / "fixtures" / f"{dataset}_p5_final1024.qid")
        forbidden = {q for path in paths for q in read_qids(path)}
        rng = random.Random(seed)
        chosen = []
        while len(chosen) < 1024:
            q = rng.randrange(1_000_000)
            if q not in forbidden:
                chosen.append(q)
                forbidden.add(q)
        target = ROOT / "fixtures" / f"{dataset}_p6_final1024.qid"
        target.parent.mkdir(exist_ok=True)
        assert not target.exists()
        target.write_text("1024\n" + "".join(f"{q}\n" for q in chosen))
        output[dataset] = {
            "seed": seed,
            "frozen_config_sha256": config_sha256,
            "query_file": str(target.relative_to(ROOT)),
            "query_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "excluded_count": len(forbidden) - 1024,
            "intersection_count": 0,
            "excluded_files": {str(path.relative_to(DIAG)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in paths},
        }
    (ROOT / "QUERY_SETS.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
