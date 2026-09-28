#!/usr/bin/env python3
"""Summarize only the 108 validated normal-radius timing processes."""
import csv
import itertools
import json
import statistics
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
DEPTH = {"GIST": 4, "Deep": 1, "Tloc": 4}


def interval(values):
    boot = sorted(statistics.median(values[i] for i in draw)
                  for draw in itertools.product(range(6), repeat=6))
    return [boot[int(0.025 * len(boot))], boot[int(0.975 * len(boot))]]


def main():
    records = [json.loads(line) for line in (ROOT / "formal_g2.jsonl").read_text().splitlines()]
    assert len(records) == 108 and len({r["label"] for r in records}) == 108
    by_condition = {(r["dataset"], r["mode"], r["round"]): r for r in records}
    assert len(by_condition) == 108
    rows = []
    setup = []
    output = {"conditions": 108, "processes": 108, "queries_per_process": 64, "datasets": {}}
    for ds in ("GIST", "Deep", "Tloc"):
        modes = ("FR", "FF", f"CR{DEPTH[ds]}", f"CF{DEPTH[ds]}", "TR", "TF")
        for rd in range(1, 7):
            assert all((ds, mode, rd) in by_condition for mode in modes)
        means = {}
        per_query = {}
        identities = set()
        for mode in modes:
            means[mode] = []
            per_query[mode] = {}
            for rd in range(1, 7):
                rec = by_condition[ds, mode, rd]
                run = Path(rec["run"])
                result = json.loads((run / "result.json").read_text())
                identities.add((result["idlist_hash"], result["bounds_hash"]))
                samples = list(csv.DictReader((run / "result.csv").open()))
                assert len(samples) == 64
                us = [float(s["query_us"]) for s in samples]
                mean = statistics.mean(us)
                assert abs(mean - rec["mean_us"]) < 1e-6
                means[mode].append(mean)
                peak_mib = max(int(line.split(",")[1].strip())
                               for line in (run / "gpu.csv").read_text().splitlines() if line.strip())
                setup.append({"dataset": ds, "mode": mode, "round": rd,
                              "refit_s": result["refit_s"], "driver_setup_s": result["setup_s"],
                              "capture_instantiate_s": result["capture_instantiate_s"],
                              "before_cleanup_process_s": result["before_cleanup_process_s"],
                              "sampled_peak_gpu_memory_mib": peak_mib})
                for sample in samples:
                    q = int(sample["qid"])
                    per_query[mode].setdefault(q, []).append(float(sample["query_us"]))
                    rows.append({"dataset": ds, "mode": mode, "round": rd, "query_id": q,
                                 "host_ready_us": sample["query_us"], "result_count": sample["count"],
                                 "ordered_hash": sample["ordered_hash"], "radius_bits": rec["radius_bits"]})
        assert len(identities) == 1
        fast = ("FF", f"CF{DEPTH[ds]}", "TF")
        pairs = {}
        for baseline, candidate in (("FF", fast[1]), ("FF", "TF"), (fast[1], "TF")):
            ratios = [means[baseline][i] / means[candidate][i] for i in range(6)]
            pairs[f"{baseline}_over_{candidate}"] = {
                "round_ratios": ratios, "median_speedup": statistics.median(ratios),
                "candidate_wins": sum(x > 1 for x in ratios), "paired_bootstrap_95": interval(ratios)}
        qids = sorted(per_query["FF"])
        assert len(qids) == 64 and all(len(per_query[mode][q]) == 6 for mode in modes for q in qids)
        qmeans = {mode: {q: statistics.median(per_query[mode][q]) for q in qids} for mode in fast}
        fixed = min(statistics.mean(qmeans[mode].values()) for mode in fast)
        ideal = statistics.mean(min(qmeans[mode][q] for mode in fast) for q in qids)
        output["datasets"][ds] = {
            "identity_hashes": list(next(iter(identities))),
            "modes": {mode: {"round_mean_us": means[mode],
                              "median_round_mean_us": statistics.median(means[mode]),
                              "median_query_p50_us": statistics.median(
                                  float(np.percentile([per_query[mode][q][i] for q in qids], 50))
                                  for i in range(6)),
                              "median_query_p95_us": statistics.median(
                                  float(np.percentile([per_query[mode][q][i] for q in qids], 95))
                                  for i in range(6))}
                      for mode in modes},
            "pairs": pairs,
            "ideal_per_query_speedup_over_best_fixed": fixed / ideal,
        }
    assert len(rows) == 6912 and len(setup) == 108
    for filename, table in (("latency_g2.csv", rows), ("setup_g2.csv", setup)):
        with (ROOT / filename).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
    (ROOT / "G2_SUMMARY.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    for ds, data in output["datasets"].items():
        print(ds, {m: round(x["median_round_mean_us"], 1) for m, x in data["modes"].items()},
              {k: round(v["median_speedup"], 3) for k, v in data["pairs"].items()})


if __name__ == "__main__":
    main()
