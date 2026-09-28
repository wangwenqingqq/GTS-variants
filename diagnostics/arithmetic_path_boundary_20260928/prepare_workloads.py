#!/usr/bin/env python3
"""Freeze disjoint GTS query splits and exact float32 radius bits."""
import argparse
import hashlib
import json
import random
import struct
from pathlib import Path

import numpy as np

DATASETS = ("GIST", "Deep", "Tloc")
SEED = 20260928


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def qids(path):
    values = list(map(int, path.read_text().split()))
    assert values and values[0] == len(values) - 1, path
    return values[1:]


def f32bits(value):
    return f"0x{struct.unpack('<I', struct.pack('<f', float(value)))[0]:08x}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("fixture_root", type=Path)
    p.add_argument("holdout_root", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    assert not a.output.exists(), "workloads are frozen; use a new output directory"
    a.output.mkdir(parents=True)
    fixtures = {name: a.fixture_root / "data" / name / "1000000" / "fixtures"
                for name in DATASETS}
    holdouts = {name: a.holdout_root / "data" / name / "1000000" / "fixtures"
                for name in DATASETS}
    historical = qids(fixtures["GIST"] / "queries.qid")
    development = qids(holdouts["GIST"] / "queries.qid")
    assert len(historical) == 8 and len(development) == 24
    excluded = set()
    for name in DATASETS:
        assert qids(fixtures[name] / "queries.qid") == historical
        assert qids(holdouts[name] / "queries.qid") == development
        for directory in (fixtures[name], holdouts[name]):
            for path in directory.glob("*.qid"):
                excluded.update(qids(path))
    rng = random.Random(SEED)
    final = []
    while len(final) < 64:
        candidate = rng.randrange(1_000_000)
        if candidate not in excluded and candidate not in final:
            final.append(candidate)
    assert len(set(historical) | set(development) | set(final)) == 96
    for label, ids in (("historical", historical), ("development", development),
                       ("final", final)):
        (a.output / f"{label}.qid").write_text(
            str(len(ids)) + "\n" + "\n".join(map(str, ids)) + "\n")
    manifest = {"seed": SEED, "excluded_count": len(excluded),
                "historical_ids": historical, "development_ids": development,
                "final_ids": final, "datasets": {}}
    rows = []
    for name in DATASETS:
        directory = fixtures[name]
        oracle = json.loads((directory / "oracle.json").read_text())
        path = directory / "data.f32bin"
        with path.open("rb") as f:
            dimension, count, metric = struct.unpack("<iii", f.read(12))
        assert count == 1_000_000 and dimension == oracle["dimension"]
        assert path.stat().st_size == 12 + count * dimension * 4
        digest = sha256(path)
        assert digest == oracle["sha256"]["data.f32bin"]
        data = np.memmap(path, dtype="<f4", mode="r", offset=12,
                         shape=(count, dimension))
        for start in range(0, count, 16_384):
            assert bool(np.isfinite(data[start:start + 16_384]).all()), (name, start)
        r0 = np.float32(oracle["radii"]["normal"])
        rall = np.float32(oracle["radii"]["all"])
        assert float(r0) == oracle["radii"]["normal"]
        assert float(rall) == oracle["radii"]["all"]
        radii = {"half": f32bits(np.float32(r0 * np.float32(0.5))),
                 "normal": f32bits(r0), "all": f32bits(rall)}
        manifest["datasets"][name] = {
            "n": count, "dimension": dimension, "metric_code": metric,
            "data_sha256": digest, "source_sha256": oracle["source_sha256"],
            "radii_f32_bits": radii}
        for split, ids in (("historical", historical), ("development", development),
                           ("final", final)):
            for query_id in ids:
                vector_digest = hashlib.sha256(data[query_id].tobytes()).hexdigest()
                for radius_name, bits in radii.items():
                    rows.append({"dataset": name, "split": split, "query_id": query_id,
                                 "vector_sha256": vector_digest,
                                 "radius_name": radius_name, "radius_f32_bits": bits})
    (a.output / "workloads.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    manifest["workloads_sha256"] = sha256(a.output / "workloads.jsonl")
    (a.output / "PREFLIGHT.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(a.output), "rows": len(rows),
                      "preflight_sha256": sha256(a.output / "PREFLIGHT.json"),
                      "workloads_sha256": manifest["workloads_sha256"]}))


if __name__ == "__main__":
    main()
