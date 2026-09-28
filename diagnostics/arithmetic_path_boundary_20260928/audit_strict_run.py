#!/usr/bin/env python3
"""Validate every strict-query result against the independent FP64 scan."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument("reference", type=Path)
    p.add_argument("idlist", type=Path)
    p.add_argument("result_binary", type=Path)
    p.add_argument("radius_bits")
    p.add_argument("output", type=Path)
    a = p.parse_args()
    assert not a.output.exists()
    with a.reference.open("rb") as f:
        d, n, nq = struct.unpack("<iii", f.read(12))
    rows = np.memmap(a.reference, dtype=np.dtype([("qid", "<i4"), ("sums", "<f8", (n,))]),
                     mode="r", offset=12, shape=(nq,))
    by_qid = {int(rows[i]["qid"]): i for i in range(nq)}
    order = np.fromfile(a.idlist, dtype="<i4")
    assert len(order) == n and np.array_equal(np.sort(order), np.arange(n, dtype=np.int32))
    radius = struct.unpack("<f", struct.pack("<I", int(a.radius_bits, 16)))[0]
    records = []
    with a.result_binary.open("rb") as f:
        while True:
            head = f.read(8)
            if not head:
                break
            assert len(head) == 8
            qid, count = struct.unpack("<ii", head)
            assert qid in by_qid and 0 <= count <= n
            ids = np.frombuffer(f.read(count * 4), dtype="<i4")
            distances = np.frombuffer(f.read(count * 4), dtype="<f4")
            assert len(ids) == len(distances) == count
            sums = rows[by_qid[qid]]["sums"]
            expected = order[sums[order] <= float(radius) ** 2] if radius >= 0 else order[:0]
            assert np.array_equal(ids, expected), (qid, count, len(expected))
            reference_distances = np.sqrt(sums[ids])
            errors = np.abs(distances.astype(np.float64) - reference_distances)
            tolerance = 1e-7 + 1e-5 * reference_distances
            assert bool((errors <= tolerance).all()), (qid, int((errors > tolerance).sum()))
            records.append({"query_id": qid, "count": count,
                            "ordered_id_sha256": hashlib.sha256(ids.tobytes()).hexdigest(),
                            "max_distance_error": float(errors.max(initial=0))})
    assert records
    report = {"pass": True, "dimension": d, "n": n, "radius_bits": a.radius_bits,
              "idlist_sha256": hashlib.sha256(a.idlist.read_bytes()).hexdigest(),
              "queries": records}
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"pass": True, "queries": len(records), "counts": [r["count"] for r in records[:3]],
                      "idlist_sha256": report["idlist_sha256"]}))


if __name__ == "__main__":
    main()
