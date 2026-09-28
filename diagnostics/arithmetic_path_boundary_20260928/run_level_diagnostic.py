#!/usr/bin/env python3
"""Count surviving nodes at each level in separate non-timed tree runs."""
import csv
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GPU = "GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603"
DEPTH = {"GIST": 4, "Deep": 1, "Tloc": 4}


def main():
    manifest = json.loads((ROOT / "frozen_v3/PREFLIGHT.json").read_text())
    counts = {(r["dataset"], r["radius_name"], r["mode"], r["query_id"]): r
              for r in csv.DictReader((ROOT / "work.csv").open())}
    report = ROOT / "work_level_diagnostic.jsonl"
    recorded = {json.loads(line)["label"] for line in report.read_text().splitlines()} if report.exists() else set()
    rows = []
    for kind in ("normal", "half", "all"):
        for ds in ("GIST", "Deep", "Tloc"):
            bits = manifest["datasets"][ds]["radii_f32_bits"][kind]
            radius = struct.unpack("<f", struct.pack("<I", int(bits, 16)))[0]
            root = ROOT / "data" / ds / "1000000"
            for mode in (f"CR{DEPTH[ds]}", f"CF{DEPTH[ds]}", "TR", "TF"):
                label = f"level_v3_{kind}_{ds}_{mode}"
                run = root / "runs" / label
                detail = run / "work_detailed.csv"
                if not run.exists():
                    env = {**os.environ, "GTS_WORK_OUTPUT": str(detail)}
                    subprocess.run([sys.executable, str(ROOT / "run.py"), str(root),
                                    "--gpu", GPU, "--label", label, "--mode", mode,
                                    "--radius", repr(radius), "--repeats", "1", "--warmup", "0",
                                    "--qfile", "final_v3.qid", "--binary", "graph_bench_work_level"],
                                   env=env, check=True, stdout=subprocess.DEVNULL)
                receipt = json.loads((run / "receipt.json").read_text())
                assert receipt["exit_code"] == 0 and receipt["stop_reason"] is None
                assert not receipt["runtime_errors"] and receipt["post_gpu_clear"]
                audit_label = f"finalcheck_{ds}_{mode}" if kind == "normal" else f"finalcheck_v3_{kind}_{ds}_{mode}"
                expected = list(csv.DictReader((root / "runs" / audit_label / "result.csv").open()))
                actual = list(csv.DictReader((run / "result.csv").open()))
                detailed = list(csv.DictReader(detail.open()))
                assert len(expected) == len(actual) == len(detailed) == 64
                assert [(r["qid"], r["count"], r["ordered_hash"]) for r in actual] == [
                    (r["qid"], r["count"], r["ordered_hash"]) for r in expected]
                for result, row in zip(actual, detailed):
                    qid = result["qid"]
                    old = counts[ds, kind, mode, qid]
                    assert row["qid"] == qid
                    for field in ("point_pairs", "point_fast_rejected", "point_ref_calls", "point_abnormal",
                                  "pivot_pairs", "pivot_ref_calls", "pivot_abnormal"):
                        assert row[field] == old[field], (label, qid, field)
                    nodes_in = [int(row[f"level{level}_in"]) for level in range(1, 6)]
                    nodes_out = [int(row[f"level{level}_out"]) for level in range(1, 6)]
                    assert sum(nodes_in) == int(old["pivot_pairs"])
                    assert all(0 <= o <= i for i, o in zip(nodes_in, nodes_out))
                    assert all(nodes_in[i] <= 10 * nodes_out[i - 1] for i in range(1, 5))
                    assert all(nodes_in[i] == nodes_out[i] == 0 for i in range(DEPTH[ds] if mode[0] == "C" else 5, 5))
                    for level, (n_in, n_out) in enumerate(zip(nodes_in, nodes_out), 1):
                        rows.append({"dataset": ds, "radius_name": kind, "mode": mode,
                                     "query_id": qid, "level": level, "nodes_in": n_in, "nodes_out": n_out})
                if label not in recorded:
                    with report.open("a") as f:
                        f.write(json.dumps({"label": label, "queries": 64, "output_matches_audited_run": True,
                                            "counters_match_prior_run": True, "detail": str(detail)}, sort_keys=True) + "\n")
                    recorded.add(label)
                print(kind, ds, mode, "level pass", flush=True)
    with (ROOT / "work_levels.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print("exported", len(rows), "level rows")


if __name__ == "__main__":
    main()
