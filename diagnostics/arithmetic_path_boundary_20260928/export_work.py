#!/usr/bin/env python3
"""Export candidate and full-coordinate work from audited diagnostic runs."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEPTH = {"GIST": 4, "Deep": 1, "Tloc": 4}
N = 1000000


def main():
    manifest = json.loads((ROOT / "frozen_v3/PREFLIGHT.json").read_text())
    rows = []
    for kind in ("half", "normal", "all"):
        for ds in ("GIST", "Deep", "Tloc"):
            dimension = manifest["datasets"][ds]["dimension"]
            modes = ("FR", "FF", f"CR{DEPTH[ds]}", f"CF{DEPTH[ds]}", "TR", "TF")
            for mode in modes:
                label = f"finalcheck_{ds}_{mode}" if kind == "normal" else f"finalcheck_v3_{kind}_{ds}_{mode}"
                run = ROOT / "data" / ds / "1000000" / "runs" / label
                assert json.loads((run / "audit.json").read_text())["pass"]
                results = list(csv.DictReader((run / "result.csv").open()))
                work = list(csv.DictReader((run / "result.work.csv").open()))
                assert len(results) == len(work) == 64
                for result, measurement in zip(results, work):
                    assert result["qid"] == measurement["qid"]
                    raw = int(measurement["candidates"])
                    # Every leaf has exactly ten objects in these three 1M trees.
                    candidates = N if mode[0] == "F" else raw * (10 if mode[0] == "T" else 1)
                    assert 0 <= candidates <= N
                    count = int(result["count"])
                    assert 0 <= count <= candidates
                    rows.append({"dataset": ds, "radius_name": kind, "mode": mode,
                                 "query_id": result["qid"], "dimension": dimension,
                                 "candidate_objects": candidates, "candidate_ratio": candidates/N,
                                 "object_coordinate_evaluations": candidates * dimension,
                                 "result_count": count,
                                 "leaf_nodes": raw if mode[0] == "T" else ""})
    assert len(rows) == 54 * 64
    with (ROOT / "work.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("exported", len(rows), "work rows")


if __name__ == "__main__":
    main()
