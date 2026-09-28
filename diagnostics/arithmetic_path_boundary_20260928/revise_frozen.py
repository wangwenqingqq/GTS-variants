#!/usr/bin/env python3
"""Replace exposed final IDs after correcting the all-hit radius from data bounds."""
import argparse
import hashlib
import json
import math
import random
import struct
from pathlib import Path

import numpy as np

DEFAULT_SEED = 2026092802


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("prior", type=Path)
    p.add_argument("data_root", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--exclude-qid", type=Path, action="append", default=[])
    p.add_argument("--reason", default="Prior Tloc all radius missed 658 objects for a held-out query; prior final split was inspected and retired")
    a = p.parse_args()
    assert not a.output.exists()
    a.output.mkdir(parents=True)
    prior = json.loads((a.prior / "PREFLIGHT.json").read_text())
    excluded = set(prior["historical_ids"] + prior["development_ids"] + prior["final_ids"])
    for path in a.exclude_qid:
        ids = list(map(int, path.read_text().split()))
        assert ids[0] == len(ids) - 1
        excluded.update(ids[1:])
    rng = random.Random(a.seed)
    final = []
    while len(final) < 64:
        q = rng.randrange(1_000_000)
        if q not in excluded and q not in final:
            final.append(q)
    assert not set(final) & excluded
    manifest = json.loads(json.dumps(prior))
    manifest.update(seed=a.seed, final_ids=final, excluded_count=len(excluded),
                    supersedes_preflight_sha256=sha256(a.prior / "PREFLIGHT.json"),
                    revision_reason=a.reason)
    for label in ("historical", "development"):
        (a.output / f"{label}.qid").write_bytes((a.prior / f"{label}.qid").read_bytes())
    (a.output / "final.qid").write_text("64\n" + "\n".join(map(str, final)) + "\n")
    rows = []
    for name, spec in manifest["datasets"].items():
        path = a.data_root / name / "1000000" / "fixtures" / "data.f32bin"
        assert sha256(path) == spec["data_sha256"]
        n, d = spec["n"], spec["dimension"]
        data = np.memmap(path, dtype="<f4", mode="r", offset=12, shape=(n, d))
        lo = np.full(d, np.inf)
        hi = np.full(d, -np.inf)
        for start in range(0, n, 16_384):
            block = data[start:start + 16_384]
            assert bool(np.isfinite(block).all())
            lo = np.minimum(lo, block.min(axis=0).astype(np.float64))
            hi = np.maximum(hi, block.max(axis=0).astype(np.float64))
        # Every coordinate difference is at most hi-lo. The generous margin
        # covers FP64 accumulation rounding; nextafter rounds the radius up.
        upper = math.sqrt(math.fsum((hi - lo) ** 2)) * (1 + 1e-10)
        radius = np.nextafter(np.float32(upper), np.float32(np.inf))
        assert math.isfinite(radius) and float(radius) >= upper
        bits = f"0x{struct.unpack('<I', struct.pack('<f', float(radius)))[0]:08x}"
        spec["old_all_bits"] = spec["radii_f32_bits"]["all"]
        spec["radii_f32_bits"]["all"] = bits
        spec["all_radius_bound"] = {"method": "coordinate bounding box with 1e-10 relative margin and one float32 ULP upward",
                                    "bound_before_f32": upper, "radius_f32": float(radius)}
        for split, ids in (("historical", manifest["historical_ids"]),
                           ("development", manifest["development_ids"]), ("final", final)):
            for q in ids:
                vector_hash = hashlib.sha256(data[q].tobytes()).hexdigest()
                for kind, radius_bits in spec["radii_f32_bits"].items():
                    rows.append({"dataset": name, "split": split, "query_id": q,
                                 "vector_sha256": vector_hash, "radius_name": kind,
                                 "radius_f32_bits": radius_bits})
    (a.output / "workloads.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    manifest["workloads_sha256"] = sha256(a.output / "workloads.jsonl")
    (a.output / "PREFLIGHT.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(a.output), "sha256": sha256(a.output / "PREFLIGHT.json"),
                      "all_radius_bits": {n: s["radii_f32_bits"]["all"] for n, s in manifest["datasets"].items()}}))


if __name__ == "__main__":
    main()
