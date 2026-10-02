#!/usr/bin/env python3
"""P6 development grid under the frozen GPU admission policy."""
import csv
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
P5 = Path("/home/data/wangxuran/tmp/gts_p5_external_mask_20261002")
GPU = "GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603"
CAGRA_PYTHON = P5 / "venv/bin/python"
FAISS_PYTHON = ROOT / "faiss_source_venv/bin/python"


def run(label, command):
    folder = ROOT / "runs" / label
    if not folder.exists():
        subprocess.run([sys.executable, str(P5 / "run_p4.py"), "--gpu", GPU,
                        "--output", str(folder), "--", *map(str, command)],
                       check=True, stdout=subprocess.DEVNULL)
    receipt = json.loads((folder / "receipt.json").read_text())
    assert receipt["runtime_valid"], label
    return json.loads((folder / "stdout.log").read_text())


def main():
    entries = []
    for k in (128, 512, 1024):
        label = f"dev_cagra_gist_half_b32_k{k}"
        payload = run(label, [CAGRA_PYTHON, ROOT / "cagra_dev_curve.py",
                              "--k", k, "--rounds", 3])
        entries.append((label, "CAGRA_RANGE_ADAPTER", payload))
        print("PASS", label, payload["quality"]["range_recall_micro"], flush=True)
    for nlist, probes in ((1024, (1, 4, 16, 64, 256, 1024)),
                          (4096, (1, 4, 16, 64, 256, 1024, 2048))):
        for nprobe in probes:
            for k in (128, 512, 2048):
                label = f"dev_faiss_gist_half_b32_n{nlist}_p{nprobe}_k{k}"
                payload = run(label, [FAISS_PYTHON, ROOT / "faiss_dev_curve.py",
                                      "--nlist", nlist, "--nprobe", nprobe,
                                      "--k", k, "--rounds", 3])
                entries.append((label, "FAISS_GPU_IVFFLAT_RANGE_ADAPTER", payload))
                print("PASS", label, payload["quality"]["range_recall_micro"], flush=True)
    with (ROOT / "development_raw.json").open("w") as f:
        json.dump({"runs": [{"label": label, "method": method, "result": payload}
                            for label, method, payload in entries]}, f, indent=2)
        f.write("\n")
    native = []
    refined = []
    quality = []
    builds = []
    for label, method, payload in entries:
        key = {"phase": "dev", "label": label, "method": method,
               "dataset": "GIST", "radius": "half", "B": 32,
               "nlist": payload.get("nlist", ""),
               "nprobe": payload.get("nprobe", ""), "K": payload["k"]}
        for row in payload["timing"]:
            target = refined if row["mode"] == "common_refined" else native
            target.append({**key, "round": row["round"],
                           "host_ready_ms": row["host_ready_ms"],
                           "batch_p50_ms": row["batch_p50_ms"],
                           "batch_p95_ms": row["batch_p95_ms"]})
        quality.append({**key, **payload["quality"]})
        builds.append({**key, "data_layout_s": payload.get("layout_s", payload.get("verifier_layout_s")),
                       "index_train_s": payload.get("train_s", ""),
                       "index_add_s": payload.get("add_s", ""),
                       "graph_build_s": payload.get("graph_build_s", ""),
                       "training_seed": payload.get("train_sample_seed", ""),
                       "training_samples": payload.get("train_sample_count", "")})
    for name, rows in (("native_latency.csv", native), ("refined_latency.csv", refined),
                       ("range_quality.csv", quality), ("BUILD_COST.csv", builds)):
        with (ROOT / name).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0])
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
