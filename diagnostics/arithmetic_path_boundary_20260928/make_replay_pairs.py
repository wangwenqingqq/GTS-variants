#!/usr/bin/env python3
"""Freeze real object and index-pivot IDs for equal-work arithmetic replay."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument("index_dump", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    assert not a.output.exists()
    a.output.mkdir(parents=True)
    with a.index_dump.open("rb") as f:
        d, n, nodes = struct.unpack("<iii", f.read(12))
    node_type = np.dtype([("pid", "<i4"), ("min_dis", "<f4"), ("size", "<i4"),
                          ("lid", "<i4"), ("is_leaf", "<i4")])
    tree = np.memmap(a.index_dump, dtype=node_type, mode="r", offset=12, shape=(nodes,))
    empty = np.memmap(a.index_dump, dtype="<i4", mode="r", offset=12 + nodes * node_type.itemsize, shape=(nodes,))
    ids = np.memmap(a.index_dump, dtype="<i4", mode="r",
                    offset=12 + nodes * (node_type.itemsize + 4), shape=(n,))
    assert a.index_dump.stat().st_size == 12 + nodes * (node_type.itemsize + 4) + n * 4
    assert np.array_equal(np.sort(ids), np.arange(n, dtype=np.int32))
    points = np.asarray(ids[np.linspace(0, n - 1, 8192, dtype=np.int64)], dtype="<i4")
    actual_pivots = tree["pid"][empty == 0]
    pivots = np.unique(actual_pivots[(actual_pivots >= 0) & (actual_pivots < n)])
    assert len(pivots) >= 8192
    rng = np.random.default_rng(20260928)
    selected = np.asarray(rng.choice(pivots, size=8192, replace=False), dtype="<i4")
    manifest = {"dimension": d, "n": n, "node_count": nodes,
                "index_dump_sha256": hashlib.sha256(a.index_dump.read_bytes()).hexdigest(),
                "point_count": len(points), "pivot_count": len(selected)}
    for label, values in (("points", points), ("pivots", selected)):
        path = a.output / f"{label}.i32"
        values.tofile(path)
        manifest[label + "_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (a.output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
