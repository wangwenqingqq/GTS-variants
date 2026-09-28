#!/usr/bin/env python3
"""Summarize the 216 validated half/all timing processes."""
import csv
import json
import statistics
from pathlib import Path

import numpy as np
from analyze_g2 import interval

ROOT = Path(__file__).resolve().parent
DEPTH = {"GIST": 4, "Deep": 1, "Tloc": 4}


def main():
    records = [json.loads(line) for line in (ROOT / "formal_g3.jsonl").read_text().splitlines()]
    assert len(records) == 216 and len({r["label"] for r in records}) == 216
    by_condition = {(r["kind"], r["dataset"], r["mode"], r["round"]): r for r in records}
    assert len(by_condition) == 216
    rows, setup = [], []
    report = {"conditions": 36, "processes": 216, "queries_per_process": 64, "radii": {}}
    for kind in ("half", "all"):
        report["radii"][kind] = {}
        for ds in ("GIST", "Deep", "Tloc"):
            modes = ("FR", "FF", f"CR{DEPTH[ds]}", f"CF{DEPTH[ds]}", "TR", "TF")
            means, per_query, identities = {}, {}, set()
            for mode in modes:
                means[mode], per_query[mode] = [], {}
                for rd in range(1, 7):
                    rec = by_condition[kind, ds, mode, rd]
                    run = Path(rec["run"])
                    summary = json.loads((run / "result.json").read_text())
                    identities.add((summary["idlist_hash"], summary["bounds_hash"]))
                    samples = list(csv.DictReader((run / "result.csv").open()))
                    assert len(samples) == 64
                    values = [float(s["query_us"]) for s in samples]
                    mean = statistics.mean(values)
                    assert abs(mean - rec["mean_us"]) < 1e-6
                    means[mode].append(mean)
                    peak_mib = max(int(line.split(",")[1].strip())
                                   for line in (run / "gpu.csv").read_text().splitlines() if line.strip())
                    setup.append({"dataset": ds, "radius_name": kind, "mode": mode, "round": rd,
                                  "refit_s": summary["refit_s"], "driver_setup_s": summary["setup_s"],
                                  "capture_instantiate_s": summary["capture_instantiate_s"],
                                  "before_cleanup_process_s": summary["before_cleanup_process_s"],
                                  "sampled_peak_gpu_memory_mib": peak_mib})
                    for sample in samples:
                        q = int(sample["qid"])
                        per_query[mode].setdefault(q, []).append(float(sample["query_us"]))
                        rows.append({"dataset": ds, "radius_name": kind, "mode": mode, "round": rd,
                                     "query_id": q, "host_ready_us": sample["query_us"],
                                     "result_count": sample["count"], "ordered_hash": sample["ordered_hash"],
                                     "radius_bits": rec["radius_bits"]})
            assert len(identities) == 1
            fast = ("FF", f"CF{DEPTH[ds]}", "TF")
            pairs = {}
            for baseline, candidate in (("FF", fast[1]), ("FF", "TF"), (fast[1], "TF")):
                ratios = [means[baseline][i] / means[candidate][i] for i in range(6)]
                pairs[f"{baseline}_over_{candidate}"] = {
                    "round_ratios": ratios, "median_speedup": statistics.median(ratios),
                    "candidate_wins": sum(x > 1 for x in ratios),
                    "paired_bootstrap_95": interval(ratios)}
            qids = sorted(per_query["FF"])
            assert len(qids) == 64 and all(len(per_query[m][q]) == 6 for m in modes for q in qids)
            qmed = {m: {q: statistics.median(per_query[m][q]) for q in qids} for m in fast}
            best_fixed = min(statistics.mean(qmed[m].values()) for m in fast)
            ideal = statistics.mean(min(qmed[m][q] for m in fast) for q in qids)
            report["radii"][kind][ds] = {
                "identity_hashes": list(next(iter(identities))),
                "modes": {m: {"round_mean_us": means[m],
                               "median_round_mean_us": statistics.median(means[m]),
                               "median_query_p50_us": statistics.median(
                                   float(np.percentile([per_query[m][q][i] for q in qids], 50)) for i in range(6)),
                               "median_query_p95_us": statistics.median(
                                   float(np.percentile([per_query[m][q][i] for q in qids], 95)) for i in range(6))}
                          for m in modes},
                "pairs": pairs, "ideal_per_query_speedup_over_best_fixed": best_fixed / ideal}
    assert len(rows) == 216 * 64 and len(setup) == 216
    for filename, table in (("latency_g3.csv", rows), ("setup_g3.csv", setup)):
        with (ROOT / filename).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(table[0]))
            writer.writeheader();writer.writerows(table)
    (ROOT / "G3_SUMMARY.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    for kind, datasets in report["radii"].items():
        for ds, item in datasets.items():
            print(kind, ds,
                  {m: round(item["modes"][m]["median_round_mean_us"], 1)
                   for m in ("FF", f"CF{DEPTH[ds]}", "TF")})


if __name__ == "__main__":
    main()
