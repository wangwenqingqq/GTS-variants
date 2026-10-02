"""Shared P6 strict candidate verifier and range quality metrics."""
import struct
import numpy as np

KERNEL = r"""
extern "C" __global__ void refine(const float* x, const int* qids,
    const long long* candidates, int n, int d, int k, int batch, double cutoff,
    unsigned char* keep, float* distance) {
  int pos = blockIdx.x * blockDim.x + threadIdx.x;
  if (pos >= batch * k) return;
  long long id = candidates[pos];
  if (id < 0 || id >= n) { keep[pos] = 0; return; }
  int qid = qids[pos / k];
  double sum = 0.0;
  for (int j = 0; j < d; ++j) {
    double delta = __dsub_rn(double(x[id * d + j]), double(x[(long long)qid * d + j]));
    sum = __dadd_rn(sum, __dmul_rn(delta, delta));
  }
  unsigned char hit = sum <= cutoff;
  keep[pos] = hit;
  if (hit) distance[pos] = float(sqrt(sum));
}
"""


def oracle(path):
    result = []
    with open(path, "rb") as f:
        while header := f.read(8):
            if len(header) != 8:
                raise ValueError("short oracle header")
            qid, count = struct.unpack("<ii", header)
            ids = np.frombuffer(f.read(count * 4), dtype="<i4").copy()
            fields = np.frombuffer(f.read(count * 4), dtype="<f4").copy()
            if len(ids) != count or len(fields) != count:
                raise ValueError("short oracle payload")
            result.append((qid, ids, fields))
    return result


def quality(qids, truth, results, k):
    recalls, ceilings, self_recalls = [], [], []
    false_negatives = false_positives = duplicates = field_errors = 0
    complete = empty_errors = 0
    truth_total = got_true_total = 0
    for qid, (expect_qid, expected, expected_fields), (got, fields, raw_dup) in zip(qids, truth, results):
        assert int(qid) == expect_qid
        expected_set = set(map(int, expected))
        got_set = set(map(int, got))
        hit_set = expected_set & got_set
        truth_total += len(expected_set)
        got_true_total += len(hit_set)
        duplicates += raw_dup
        false_negatives += len(expected_set - got_set)
        false_positives += len(got_set - expected_set)
        complete += expected_set == got_set
        empty_errors += not expected_set and bool(got_set)
        if expected_set:
            recalls.append(len(hit_set) / len(expected_set))
            ceilings.append(min(k, len(expected_set)) / len(expected_set))
        without_self = expected_set - {int(qid)}
        if without_self:
            self_recalls.append(len(without_self & (got_set - {int(qid)})) / len(without_self))
        ref_fields = dict(zip(map(int, expected), expected_fields))
        field_errors += sum(np.float32(ref_fields[int(i)]).view("<u4") !=
                            np.float32(v).view("<u4") for i, v in zip(got, fields)
                            if int(i) in ref_fields)
    arr = np.asarray(recalls)
    return {"queries": len(qids), "nonempty_queries": len(recalls),
            "truth_hits": truth_total, "true_positive_hits": got_true_total,
            "range_recall_macro_nonempty": float(arr.mean()),
            "range_recall_micro": got_true_total / truth_total,
            "recall_p05": float(np.quantile(arr, .05)),
            "recall_p50": float(np.median(arr)), "recall_min": float(arr.min()),
            "complete_query_fraction": complete / len(qids),
            "false_negatives": false_negatives, "false_positives": false_positives,
            "duplicate_candidate_ids": duplicates, "empty_query_errors": empty_errors,
            "bitwise_field_errors_on_returned_true_ids": int(field_errors),
            "capacity_ceiling_macro": float(np.mean(ceilings)),
            "capacity_ceiling_micro": sum(min(k, len(x[1])) for x in truth) / truth_total,
            "without_self_nonempty_queries": len(self_recalls),
            "without_self_macro_recall": float(np.mean(self_recalls)) if self_recalls else None}


def collect_ordered(ids_host, keep_host, fields_host, rank):
    """Restore common id_list order and remove duplicates after device refinement."""
    results = []
    for row in range(len(ids_host)):
        valid = keep_host[row].astype(bool)
        hits = ids_host[row, valid].astype(np.int32)
        values = fields_host[row, valid]
        order = np.argsort(rank[hits], kind="stable")
        hits, values = hits[order], values[order]
        unique = np.r_[True, hits[1:] != hits[:-1]] if len(hits) else np.zeros(0, bool)
        results.append((hits[unique], values[unique], len(hits) - int(unique.sum())))
    return results
