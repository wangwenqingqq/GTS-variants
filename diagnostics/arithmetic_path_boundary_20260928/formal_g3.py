#!/usr/bin/env python3
"""Six rotated process rounds for audited half and all-hit conditions."""
import csv
import hashlib
import json
import statistics
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GPU = "GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603"
DEPTH = {"GIST": 4, "Deep": 1, "Tloc": 4}
DATASETS = ("GIST", "Deep", "Tloc")
KINDS = ("half", "all")


def main():
    manifest = json.loads((ROOT / "frozen_v3/PREFLIGHT.json").read_text())
    binary_hash = hashlib.sha256((ROOT / "graph_bench_strict").read_bytes()).hexdigest()
    assert binary_hash == "ae4887df0a24ab25b1d44c33603704181b14abbc8520d751dffcb6837f7b4a99"
    references, identities = {}, {}
    for kind in KINDS:
        for ds in DATASETS:
            modes = ("FR", "FF", f"CR{DEPTH[ds]}", f"CF{DEPTH[ds]}", "TR", "TF")
            for mode in modes:
                run = ROOT / "data" / ds / "1000000" / "runs" / f"finalcheck_v3_{kind}_{ds}_{mode}"
                assert json.loads((run / "audit.json").read_text())["pass"]
                rows = list(csv.DictReader((run / "result.csv").open()))
                assert len(rows) == 64
                references[kind, ds, mode] = [(r["qid"], r["count"], r["ordered_hash"]) for r in rows]
                s = json.loads((run / "result.json").read_text())
                identities[kind, ds, mode] = (s["idlist_hash"], s["bounds_hash"])
    report = ROOT / "formal_g3.jsonl"
    recorded = {json.loads(line)["label"] for line in report.read_text().splitlines()} if report.exists() else set()
    for rd in range(6):
        ds_order = list(DATASETS[rd % 3:] + DATASETS[:rd % 3])
        if rd % 2: ds_order.reverse()
        kind_order = KINDS if rd % 2 == 0 else KINDS[::-1]
        for kind in kind_order:
            for ds in ds_order:
                modes = ["FR", "FF", f"CR{DEPTH[ds]}", f"CF{DEPTH[ds]}", "TR", "TF"]
                modes = modes[rd:] + modes[:rd]
                bits = manifest["datasets"][ds]["radii_f32_bits"][kind]
                radius = struct.unpack("<f", struct.pack("<I", int(bits, 16)))[0]
                root = ROOT / "data" / ds / "1000000"
                for position, mode in enumerate(modes):
                    label = f"formal_v3_{kind}_r{rd+1}_{ds}_{mode}"
                    run = root / "runs" / label
                    if not run.exists():
                        cmd = [sys.executable, str(ROOT / "run.py"), str(root),
                               "--gpu", GPU, "--label", label, "--mode", mode,
                               "--radius", repr(radius), "--repeats", "1", "--warmup", "8",
                               "--qfile", "final_v3.qid", "--binary", "graph_bench_strict"]
                        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
                    receipt = json.loads((run / "receipt.json").read_text())
                    assert receipt["exit_code"] == 0 and receipt["stop_reason"] is None
                    assert receipt["post_gpu_clear"] and not receipt["runtime_errors"]
                    assert receipt["binary_sha256"] == binary_hash
                    rows = list(csv.DictReader((run / "result.csv").open()))
                    actual = [(r["qid"], r["count"], r["ordered_hash"]) for r in rows]
                    assert actual == references[kind, ds, mode], (label, "output changed")
                    s = json.loads((run / "result.json").read_text())
                    assert (s["idlist_hash"], s["bounds_hash"]) == identities[kind, ds, mode]
                    us = [float(r["query_us"]) for r in rows]
                    record = {"label": label, "dataset": ds, "kind": kind, "mode": mode,
                              "round": rd+1, "position": position, "radius_bits": bits,
                              "mean_us": statistics.mean(us), "median_us": statistics.median(us),
                              "run": str(run), "binary_sha256": binary_hash,
                              "output_matches_audited_run": True}
                    if label not in recorded:
                        with report.open("a") as f:f.write(json.dumps(record, sort_keys=True) + "\n")
                        recorded.add(label)
                    print(f"{rd+1}/6 {kind} {ds} {mode} mean_us={record['mean_us']:.1f}", flush=True)


if __name__ == "__main__":
    main()
