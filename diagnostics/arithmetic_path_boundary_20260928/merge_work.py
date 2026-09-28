#!/usr/bin/env python3
"""Join candidate counts and independent work counters into work.csv."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEPTH = {"GIST": 4, "Deep": 1, "Tloc": 4}
CAPACITY_D2H_BYTES = 2222220 * 8 + 4


def main():
    rows = list(csv.DictReader((ROOT / "work.csv").open()))
    assert len(rows) == 3456 and "pivot_pairs" not in rows[0]
    full = {}
    for kind in ("normal", "half", "all"):
        for ds in ("GIST", "Deep", "Tloc"):
            for mode in ("FR", "FF", f"CR{DEPTH[ds]}", f"CF{DEPTH[ds]}", "TR", "TF"):
                run = ROOT / "data" / ds / "1000000" / "runs" / f"work_v3_{kind}_{ds}_{mode}"
                receipt = json.loads((run / "receipt.json").read_text())
                assert receipt["exit_code"] == 0 and receipt["stop_reason"] is None
                assert not receipt["runtime_errors"] and receipt["post_gpu_clear"]
                for row in csv.DictReader((run / "work_detailed.csv").open()):
                    key = (ds, kind, mode, row["qid"])
                    assert key not in full
                    full[key] = row
    assert len(full) == len(rows)
    merged = []
    for row in rows:
        key = (row["dataset"], row["radius_name"], row["mode"], row["query_id"])
        c = full[key]
        point = int(c["point_pairs"])
        pivot = int(c["pivot_pairs"])
        ref = int(c["point_ref_calls"])
        reject = int(c["point_fast_rejected"])
        d = int(row["dimension"])
        assert point == int(row["candidate_objects"]) and point == ref + reject
        assert ref >= int(row["result_count"])
        assert int(c["pivot_ref_calls"]) <= pivot
        row.update({k: c[k] for k in c if k != "qid"})
        row["pivot_coordinate_evaluations"] = pivot * d
        row["total_coordinate_evaluations"] = (point + pivot) * d
        row["logical_vector_read_bytes"] = (point + pivot) * d * 8
        row["valid_output_bytes"] = int(row["result_count"]) * 8 + 4
        row["fixed_D2H_bytes"] = CAPACITY_D2H_BYTES
        merged.append(row)
    temp = ROOT / "work.tmp.csv"
    with temp.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(merged[0]))
        writer.writeheader();writer.writerows(merged)
    temp.replace(ROOT / "work.csv")
    print("merged",len(merged),"work rows")


if __name__ == "__main__":
    main()
