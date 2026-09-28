#!/usr/bin/env python3
"""Full-output oracle gate for the half and all-hit radii."""
import json
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GPU = "GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603"
DEPTH = {"GIST": 4, "Deep": 1, "Tloc": 4}


def main():
    manifest = json.loads((ROOT / "frozen_v3/PREFLIGHT.json").read_text())
    report = ROOT / "verify_g3.jsonl"
    done = {json.loads(line)["label"] for line in report.read_text().splitlines()} if report.exists() else set()
    for kind in ("half", "all"):
        for ds in ("Tloc", "Deep", "GIST"):
            bits = manifest["datasets"][ds]["radii_f32_bits"][kind]
            radius = struct.unpack("<f", struct.pack("<I", int(bits, 16)))[0]
            modes = ("FR", "FF", f"CR{DEPTH[ds]}", f"CF{DEPTH[ds]}", "TR", "TF")
            root = ROOT / "data" / ds / "1000000"
            order = ROOT / "reference_v2" / f"{ds}_idlist.i32"
            reference = ROOT / "reference_v3" / f"{ds}_final.sq64"
            for mode in modes:
                label = f"finalcheck_v3_{kind}_{ds}_{mode}"
                run = root / "runs" / label
                if not run.exists():
                    subprocess.run([sys.executable, str(ROOT / "run.py"), str(root),
                                    "--gpu", GPU, "--label", label, "--mode", mode,
                                    "--radius", repr(radius), "--repeats", "1", "--warmup", "8",
                                    "--dump", "--qfile", "final_v3.qid", "--binary", "graph_bench_strict"],
                                   check=True, stdout=subprocess.DEVNULL)
                audit_path = run / "audit.json"
                if not audit_path.exists():
                    subprocess.run([sys.executable, str(ROOT / "audit_strict_run.py"),
                                    str(reference), str(order), str(run / "result.bin"),
                                    bits, str(audit_path)], check=True, stdout=subprocess.DEVNULL)
                audit = json.loads(audit_path.read_text())
                assert audit["pass"] and len(audit["queries"]) == 64
                summary = json.loads((run / "result.json").read_text())
                baseline = json.loads((root / "runs" / f"finalcheck_{ds}_{mode}" / "result.json").read_text())
                assert (summary["idlist_hash"], summary["bounds_hash"]) == (baseline["idlist_hash"], baseline["bounds_hash"])
                record = {"label": label, "dataset": ds, "kind": kind, "mode": mode,
                          "radius_bits": bits, "queries": 64,
                          "all_counts_equal_n": all(q["count"] == 1000000 for q in audit["queries"]) if kind == "all" else None,
                          "audit": str(audit_path)}
                if kind == "all": assert record["all_counts_equal_n"]
                if label not in done:
                    with report.open("a") as f:f.write(json.dumps(record, sort_keys=True) + "\n")
                    done.add(label)
                print(kind, ds, mode, "pass", flush=True)


if __name__ == "__main__":
    main()
