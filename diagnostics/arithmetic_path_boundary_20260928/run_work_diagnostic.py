#!/usr/bin/env python3
"""Measure exact work counters in separate non-timed diagnostic processes."""
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
    candidate = {(r["dataset"], r["radius_name"], r["mode"], r["query_id"]): int(r["candidate_objects"])
                 for r in csv.DictReader((ROOT / "work.csv").open())}
    report = ROOT / "work_diagnostic.jsonl"
    recorded = {json.loads(line)["label"] for line in report.read_text().splitlines()} if report.exists() else set()
    for kind in ("normal", "half", "all"):
        for ds in ("GIST", "Deep", "Tloc"):
            bits = manifest["datasets"][ds]["radii_f32_bits"][kind]
            radius = struct.unpack("<f", struct.pack("<I", int(bits, 16)))[0]
            modes = ("FR", "FF", f"CR{DEPTH[ds]}", f"CF{DEPTH[ds]}", "TR", "TF")
            root = ROOT / "data" / ds / "1000000"
            for mode in modes:
                label = f"work_v3_{kind}_{ds}_{mode}"
                run = root / "runs" / label
                detail = run / "work_detailed.csv"
                if not run.exists():
                    env = {**os.environ, "GTS_WORK_OUTPUT": str(detail)}
                    subprocess.run([sys.executable, str(ROOT / "run.py"), str(root),
                                    "--gpu", GPU, "--label", label, "--mode", mode,
                                    "--radius", repr(radius), "--repeats", "1", "--warmup", "0",
                                    "--qfile", "final_v3.qid", "--binary", "graph_bench_work"],
                                   env=env, check=True, stdout=subprocess.DEVNULL)
                audited_label = f"finalcheck_{ds}_{mode}" if kind == "normal" else f"finalcheck_v3_{kind}_{ds}_{mode}"
                expected = list(csv.DictReader((root / "runs" / audited_label / "result.csv").open()))
                actual = list(csv.DictReader((run / "result.csv").open()))
                assert len(expected) == len(actual) == 64
                assert [(r["qid"],r["count"],r["ordered_hash"]) for r in actual] == [
                    (r["qid"],r["count"],r["ordered_hash"]) for r in expected]
                counters = list(csv.DictReader(detail.open()))
                assert len(counters) == 64
                for result, row in zip(actual, counters):
                    qid = result["qid"]
                    assert row["qid"] == qid
                    p = int(row["point_pairs"])
                    reject = int(row["point_fast_rejected"])
                    ref = int(row["point_ref_calls"])
                    assert p == candidate[ds,kind,mode,qid]
                    assert p == reject + ref and ref >= int(result["count"])
                    assert int(row["pivot_pairs"]) >= int(row["pivot_ref_calls"])
                    if mode[0] == "F": assert int(row["pivot_pairs"]) == 0
                    if kind == "all": assert p == ref == 1000000 and reject == 0
                record = {"label": label, "dataset": ds, "radius_name": kind, "mode": mode,
                          "queries": 64, "output_matches_audited_run": True,
                          "detail": str(detail)}
                if label not in recorded:
                    with report.open("a") as f:f.write(json.dumps(record, sort_keys=True) + "\n")
                    recorded.add(label)
                print(kind, ds, mode, "work pass", flush=True)


if __name__ == "__main__":
    main()
