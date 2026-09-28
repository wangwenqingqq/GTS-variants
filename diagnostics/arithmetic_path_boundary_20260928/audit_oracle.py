#!/usr/bin/env python3
"""Check independently generated squared distances against frozen radii."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument("preflight", type=Path)
    p.add_argument("reference_dir", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    manifest = json.loads(a.preflight.read_text())
    report = {"contract": "FP64 sequential squared L2, inclusive radius", "datasets": {}}
    for name, spec in manifest["datasets"].items():
        path = a.reference_dir / f"{name}_final.sq64"
        n, d = spec["n"], spec["dimension"]
        with path.open("rb") as f:
            actual_d, actual_n, nq = struct.unpack("<iii", f.read(12))
        assert (actual_d, actual_n, nq) == (d, n, len(manifest["final_ids"]))
        assert path.stat().st_size == 12 + nq * (4 + 8 * n)
        rows = np.memmap(path, dtype=np.dtype([("qid", "<i4"), ("sums", "<f8", (n,))]),
                         mode="r", offset=12, shape=(nq,))
        radii = {}
        for label, bits in spec["radii_f32_bits"].items():
            radius = struct.unpack("<f", struct.pack("<I", int(bits, 16)))[0]
            assert radius >= 0
            radii[label] = (bits, float(radius) ** 2)
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(8 << 20), b""):
                digest.update(block)
        summary = {"reference_sha256": digest.hexdigest(), "queries": []}
        for i, qid in enumerate(manifest["final_ids"]):
            assert rows[i]["qid"] == qid
            sums = rows[i]["sums"]
            assert bool(np.isfinite(sums).all()) and bool((sums >= 0).all())
            assert sums[qid] == 0.0
            entry = {"query_id": qid, "radii": {}}
            prev_count = -1
            for label in ("half", "normal", "all"):
                bits, cutoff = radii[label]
                ids = np.flatnonzero(sums <= cutoff).astype("<i4")
                count = len(ids)
                assert count >= prev_count
                prev_count = count
                assert qid in ids
                if label == "all":
                    assert count == n, (name, qid, count)
                entry["radii"][label] = {"bits": bits, "count": count,
                                            "id_sha256": hashlib.sha256(ids.tobytes()).hexdigest()}
            summary["queries"].append(entry)
        report["datasets"][name] = summary
        print(name, "queries", nq, "all-hit validated", flush=True)
    assert not a.output.exists()
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
