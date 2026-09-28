#!/usr/bin/env python3
"""Validate query-only Nsight traces and export non-timed stage breakdowns."""
import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEPTH = {"GIST": 4, "Deep": 1, "Tloc": 4}


def stage(name):
    if name == "strict_walk":
        return "pivot_walk"
    if name in ("strict_flat", "strict_compact", "strict_leaf"):
        return "object_distance"
    if "ResultSelect" in name:
        return "result_select"
    if "Scan" in name:
        return "result_scan"
    return "candidate_or_setup"


def main():
    specs = [(ds, "normal", mode, f"profile_{ds}_{mode}")
             for ds in ("GIST", "Deep", "Tloc")
             for mode in ("FF", f"CF{DEPTH[ds]}", "TF")]
    specs += [(ds, radius, mode, f"profile_{ds}_{radius}_{mode}")
              for ds, radius, mode in (("GIST", "normal", "FR"), ("GIST", "normal", "CR4"),
                                       ("GIST", "all", "FF"), ("GIST", "all", "FR"),
                                       ("Deep", "normal", "FR"))]
    specs += [("GIST", "normal", mode, f"profile_GIST_sparse_{mode}") for mode in ("FF", "TF")]
    summaries, kernels = [], []
    for ds, radius_name, mode, label in specs:
        run = ROOT / "data" / ds / "1000000" / "runs" / label
        receipt = json.loads((run / "receipt.json").read_text())
        assert receipt["exit_code"] == 0 and receipt["stop_reason"] is None
        assert not receipt["runtime_errors"] and receipt["post_gpu_clear"]
        actual = list(csv.DictReader((run / "result.csv").open()))
        assert len(actual) == 1
        audit_label = f"finalcheck_{ds}_{mode}" if radius_name == "normal" else f"finalcheck_v3_{radius_name}_{ds}_{mode}"
        expected = {r["qid"]: r for r in csv.DictReader((ROOT / "data" / ds / "1000000" / "runs" / audit_label / "result.csv").open())}
        got = actual[0]
        assert (got["count"], got["ordered_hash"]) == (expected[got["qid"]]["count"], expected[got["qid"]]["ordered_hash"])
        with sqlite3.connect(run / "trace.sqlite") as conn:
            names = dict(conn.execute("SELECT id,value FROM StringIds"))
            kr = list(conn.execute("SELECT start,end,shortName FROM CUPTI_ACTIVITY_KIND_KERNEL"))
            mr = list(conn.execute("SELECT start,end,bytes,copyKind FROM CUPTI_ACTIVITY_KIND_MEMCPY"))
            ar = list(conn.execute("SELECT start,end,nameId FROM CUPTI_ACTIVITY_KIND_RUNTIME"))
        assert kr and mr and ar
        categories = {k: 0 for k in ("pivot_walk", "object_distance", "result_select", "result_scan", "candidate_or_setup")}
        for start, end, name_id in kr:
            name = names[name_id]
            ms = (end - start) / 1e6
            categories[stage(name)] += ms
            kernels.append({"dataset": ds, "radius_name": radius_name, "mode": mode,
                            "query_id": got["qid"], "kernel": name, "stage": stage(name), "duration_ms": ms})
        h2d = sum((e - s) / 1e6 for s, e, _, kind in mr if kind == 1)
        d2h = sum((e - s) / 1e6 for s, e, _, kind in mr if kind == 2)
        d2h_bytes = sum(size for _, _, size, kind in mr if kind == 2)
        graph = sum((e - s) / 1e6 for s, e, name in ar if "GraphLaunch" in names[name])
        sync = sum((e - s) / 1e6 for s, e, name in ar if "StreamSynchronize" in names[name])
        assert graph > 0 and sync > 0 and d2h_bytes == 17777764
        first = min([s for s, _, _ in kr] + [s for s, _, _, _ in mr])
        last = max([e for _, e, _ in kr] + [e for _, e, _, _ in mr])
        summary = {"dataset": ds, "radius_name": radius_name, "mode": mode,
                   "query_id": got["qid"], "result_count": got["count"],
                   "profiled_host_ready_ms": float(got["query_us"]) / 1000,
                   **{k + "_ms": v for k, v in categories.items()},
                   "h2d_ms": h2d, "d2h_ms": d2h, "d2h_bytes": d2h_bytes,
                   "gpu_activity_span_ms": (last - first) / 1e6,
                   "cuda_graph_launch_api_ms": graph, "cuda_stream_sync_api_ms": sync,
                   "kernel_count": len(kr), "memcpy_count": len(mr),
                   "trace": str(run / "trace.sqlite"), "output_matches_oracle_audit": True}
        summaries.append(summary)
    for name, rows in (("profile_summary.csv", summaries), ("profile_kernels.csv", kernels)):
        with (ROOT / name).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print("validated", len(summaries), "profiled queries and", len(kernels), "kernels")


if __name__ == "__main__":
    main()
