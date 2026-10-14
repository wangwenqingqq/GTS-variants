"""Frozen synthetic admission model, not a GPU/server performance simulator."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import csv
from decimal import Decimal, localcontext
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import random

RATES = (100, 500, 1000, 5000)
N = 100_000
WINDOW_PS = 500_000_000
DB_BYTES = 3_840_000_000
KEEPER_BYTES = 1_014_828_776


def batches(arrivals):
    """No service backlog: dispatch at the eighth arrival or oldest + 500us."""
    i = 0
    while i < len(arrivals):
        j, deadline = i + 1, arrivals[i] + WINDOW_PS
        while j < len(arrivals) and j - i < 8 and arrivals[j] <= deadline:
            j += 1
        dispatch = arrivals[j - 1] if j - i == 8 else deadline
        yield i, j, dispatch
        i = j


def analytic(rate):
    with localcontext() as ctx:
        ctx.prec = 60
        m = Decimal(rate) / 2000
        p = (-m).exp()
        probabilities = []
        for k in range(7):
            probabilities.append(p)
            p *= m / (k + 1)
        probabilities.append(1 - sum(probabilities))
        mean = sum((b + 1) * p for b, p in enumerate(probabilities))
        var = sum((b + 1) ** 2 * p for b, p in enumerate(probabilities)) - mean ** 2
        return {
            "formula": "B=min(1+Poisson(lambda*0.0005),8)",
            "batch_probabilities": [float(p) for p in probabilities],
            "mean_B": float(mean), "variance_B": float(var),
            "query_weighted_bytes": float(Decimal(DB_BYTES) / mean),
            "batch_weighted_E_bytes_over_B": float(sum(
                Decimal(DB_BYTES) / (b + 1) * p for b, p in enumerate(probabilities))),
            "exact_mean_upper_bound": {"numerator": 2000 + rate, "denominator": 2000},
            "source_model_lower_bound_fraction": {
                "numerator": DB_BYTES * 2000, "denominator": 2000 + rate},
        }


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def classify(query_count, batch_count, max_wait_ps):
    reasons = []
    if 2 * query_count < 5 * batch_count:
        reasons.append("mean_B<2.5")
    if DB_BYTES * batch_count > 1_000_000_000 * query_count:
        reasons.append("query_weighted_source_bytes>1.0GB")
    if max_wait_ps > WINDOW_PS:
        reasons.append("collection_wait>500us")
    if reasons:
        return {"label": "NO_GO_CROSS_QUERY_REUSE", "reasons": reasons}
    mean, cost = query_count / batch_count, DB_BYTES * batch_count / query_count
    if 2.5 <= mean < 4 or 750_000_000 < cost <= 1_000_000_000:
        return {"label": "CONDITIONAL", "reasons": []}
    return {"label": "UNCLASSIFIED", "reasons": ["global GO gates still required"]}


def simulate(rate, out):
    seed = 2026101400 + rate
    rng, clock = random.Random(seed), 0
    arrivals = []
    for _ in range(N):
        # Explicit 1ps discretization: <=0.5ps rounding per exponential gap.
        clock += round(-math.log1p(-rng.random()) / rate * 10**12)
        arrivals.append(clock)
    kinds = ["range"] * (N // 2) + ["knn"] * (N // 2)
    random.Random(seed + 10_000_000).shuffle(kinds)
    counts, waits, sizes, mixed = [0] * 8, [], [], 0
    raw = out / (str(rate) + "qps.csv.gz")
    with raw.open("wb") as binary, gzip.GzipFile(fileobj=binary, mode="wb", mtime=0,
                                               filename="") as zipped:
        with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text:
            writer = csv.writer(text, lineterminator="\n")
            writer.writerow(["query_id", "arrival_ps", "kind", "batch_id", "dispatch_ps", "wait_ps"])
            for bid, (i, j, dispatch) in enumerate(batches(arrivals)):
                size = j - i
                sizes.append(size)
                counts[size - 1] += 1
                mixed += len(set(kinds[i:j])) == 2
                for qid in range(i, j):
                    wait = dispatch - arrivals[qid]
                    assert 0 <= wait <= WINDOW_PS
                    waits.append(wait)
                    writer.writerow([qid, arrivals[qid], kinds[qid], bid, dispatch, wait])
    nb = len(sizes)
    theory = analytic(rate)
    # Eight-sigma consistency check, not a CI or empirical latency gate.
    assert abs(N / nb - theory["mean_B"]) <= 8 * math.sqrt(theory["variance_B"] / nb) + 8 / nb
    for b, count in enumerate(counts):
        p = theory["batch_probabilities"][b]
        assert abs(count - nb * p) <= 8 * math.sqrt(nb * p * (1 - p)) + 8
    return {
        "rate_qps": rate, "seed": seed, "queries": N, "batches": nb,
        "arrival_horizon_ps": arrivals[-1], "mix_counts": {"range": N // 2, "knn": N // 2},
        "batch_counts_B1_to_B8": counts, "mean_B_batch_weighted": N / nb,
        "mean_B_query_experienced": sum((b + 1)**2 * c for b, c in enumerate(counts)) / N,
        "p50_B_batch_weighted": percentile(sizes, .5), "p90_B_batch_weighted": percentile(sizes, .9),
        "fraction_batches_B_ge_2": (nb - counts[0]) / nb,
        "fraction_batches_B_ge_4": sum(counts[3:]) / nb,
        "fraction_batches_B_eq_8": counts[7] / nb,
        "fraction_queries_B_ge_2": (N - counts[0]) / N,
        "fraction_queries_B_ge_4": sum((b + 1) * c for b, c in enumerate(counts) if b >= 3) / N,
        "fraction_queries_B_eq_8": 8 * counts[7] / N,
        "mixed_type_batches": mixed,
        "query_wait_ps": {"mean": sum(waits) / N, "p50": percentile(waits, .5),
                          "p90": percentile(waits, .9), "p99": percentile(waits, .99), "max": max(waits)},
        "query_weighted_source_bytes": DB_BYTES * nb / N,
        "batch_weighted_E_source_bytes_over_B": sum(DB_BYTES / (b + 1) * c for b, c in enumerate(counts)) / nb,
        "query_weighted_over_keeper": DB_BYTES * nb / (N * KEEPER_BYTES),
        "point_decision": classify(N, nb, max(waits)), "analytic": theory,
        "raw_trace": {"file": raw.name, "bytes": raw.stat().st_size,
                      "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    artifact = Path(__file__).resolve().parent
    contract = json.loads((artifact / "CONTRACT.json").read_text())
    assert contract["bounded_CPU_exception"]["human_confirmed"] is True
    assert contract["novelty_admission"] == "NOT_ADMITTED"
    assert contract["scheduler"] == {"name": "window-or-cap", "Bmax": 8, "window_ps": WINDOW_PS}
    assert contract["rates_qps"] == list(RATES) and contract["queries_per_rate"] == N
    for path, digest in contract["parent_input_sha256"].items():
        assert hashlib.sha256((args.repo / path).read_bytes()).hexdigest() == digest, path
    args.out.mkdir(parents=True, exist_ok=False)
    rows = [simulate(rate, args.out) for rate in RATES]
    result = {"scope": "one synthetic trace/rate; ideal admission only, no device service or update arrivals",
              "contract_sha256": hashlib.sha256((artifact / "CONTRACT.json").read_bytes()).hexdigest(),
              "rows": rows, "final": "NO_GO_CROSS_QUERY_REUSE", "GPU_starts": 0,
              "query_state_bytes": "UNKNOWN", "output_bytes": "UNKNOWN", "control_bytes": "UNKNOWN",
              "actual_DRAM": "NOT_RUN", "Host_ready_latency": "NOT_RUN", "exactness": "NOT_RUN"}
    assert all(row["point_decision"]["label"] == result["final"] for row in rows)
    (args.out / "RESULTS.json").write_text(json.dumps(result, indent=2) + "\n")
    for row in rows:
        print(row["rate_qps"], "qps mean_B=", round(row["mean_B_batch_weighted"], 6),
              "ideal_GB/query=", round(row["query_weighted_source_bytes"] / 1e9, 6), row["point_decision"]["label"])


if __name__ == "__main__":
    main()
