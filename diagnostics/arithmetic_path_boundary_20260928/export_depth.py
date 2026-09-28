#!/usr/bin/env python3
"""Preserve the development-only cutoff selection evidence."""
import csv
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOP = {"GIST": (5, 4), "Deep": (1, 2), "Tloc": (5, 4)}
CHOSEN = {"GIST": 4, "Deep": 1, "Tloc": 4}


def main():
    manifest = json.loads((ROOT / "frozen_v3/PREFLIGHT.json").read_text())
    development = manifest["development_ids"]
    rows = []
    decisions = {"split": "24 seen development query IDs only", "near_tie_rule": "choose shallower if paired median difference is below 5%",
                 "final_manifest_sha256": hashlib.sha256((ROOT / "frozen_v3/PREFLIGHT.json").read_bytes()).hexdigest(),
                 "datasets": {}}
    for ds in ("GIST", "Deep", "Tloc"):
        def add(label, stage, mode, rd):
            run = ROOT / "data" / ds / "1000000" / "runs" / label
            if stage == "screen": assert json.loads((run / "audit.json").read_text())["pass"]
            samples = list(csv.DictReader((run / "result.csv").open()))
            assert [int(s["qid"]) for s in samples] == development
            for s in samples:
                rows.append({"dataset": ds, "stage": stage, "round": rd, "mode": mode,
                             "query_id": s["qid"], "host_ready_us": s["query_us"],
                             "result_count": s["count"], "ordered_hash": s["ordered_hash"]})
            return statistics.mean(float(s["query_us"]) for s in samples)
        screen = {d: add(f"select_{ds}_CF{d}", "screen", f"CF{d}", 0) for d in range(1, 6)}
        assert list(sorted(screen, key=lambda d: (screen[d], d)))[:2] == list(TOP[ds])
        a, b = TOP[ds]
        pairs = []
        for rd in (1, 2, 3):
            x = add(f"confirm_{ds}_r{rd}_CF{a}", "confirm", f"CF{a}", rd)
            y = add(f"confirm_{ds}_r{rd}_CF{b}", "confirm", f"CF{b}", rd)
            pairs.append({"round": rd, f"CF{a}_mean_us": x, f"CF{b}_mean_us": y,
                          "b_over_a": y/x})
        median = statistics.median(p["b_over_a"] for p in pairs)
        chosen = min(a,b) if abs(median-1) < 0.05 else (a if median>1 else b)
        assert chosen == CHOSEN[ds]
        decisions["datasets"][ds] = {"screen_mean_us": screen, "top_two": [a,b],
                                      "confirmation": pairs, "median_b_over_a": median,
                                      "chosen_depth": chosen}
    assert len(rows) == 792
    with (ROOT / "development_depth.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (ROOT / "DECISIONS.json").write_text(json.dumps(decisions, indent=2, sort_keys=True) + "\n")
    print({ds: item["chosen_depth"] for ds,item in decisions["datasets"].items()})


if __name__ == "__main__":
    main()
