// CPU certificate diagnostic; no layout change and no GPU code.
#include <algorithm>
#include <cfenv>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <limits>

static_assert(std::numeric_limits<float>::is_iec559 &&
              std::numeric_limits<float>::digits == 24, "IEEE FP32 required");
static_assert(std::numeric_limits<double>::is_iec559 &&
              std::numeric_limits<double>::digits == 53, "IEEE FP64 required");

static bool admissible(const float* x, const float* q, size_t n, int d, int k) {
    if (!x || !q || !n || d < 1 || d > 960 || k < 1 || k > d ||
        std::fegetround() != FE_TONEAREST) return false;
    for (int j = 0; j < d; ++j) if (!std::isfinite(q[j])) return false;
    return true;
}

extern "C" int oracle_scores(const float* x, const float* q, size_t n, int d,
    int k, double* b0, double* top, double* full) {
    if (!admissible(x,q,n,d,k) || !b0 || !top || !full) return 1;
    int bad = 0;
    #pragma omp parallel for schedule(static) reduction(max:bad)
    for (size_t i = 0; i < n; ++i) {
        double terms[960], partition[960], sum = 0, first = 0;
        bool invalid = false;
        for (int j = 0; j < d; ++j) {
            const float coordinate = x[i*size_t(d)+j];
            if (!std::isfinite(coordinate)) { bad = 2; invalid = true; break; }
            const double delta = double(coordinate)-double(q[j]);
            const double square = delta*delta;
            terms[j] = partition[j] = square;
            sum = sum+square;
            if (j < k) first = first+square;
        }
        if (invalid) continue;
        // Native nth_element replaces a full per-pair sort; no routing heuristic.
        if (k < d) std::nth_element(partition,partition+k,partition+d,std::greater<double>());
        const double cut = *std::min_element(partition,partition+k);
        int greater = 0;
        for (int j = 0; j < d; ++j) greater += terms[j] > cut;
        int ties = k-greater, selected = 0;
        double partial = 0;
        for (int j = 0; j < d; ++j) {
            bool take = terms[j] > cut;
            if (terms[j] == cut && ties > 0) { take = true; --ties; }
            if (take) { partial = partial+terms[j]; ++selected; }
        }
        b0[i] = first; top[i] = partial; full[i] = sum;
        if (selected != k || ties || !std::isfinite(sum) ||
            first > sum || partial > sum) bad = 3;
    }
    return bad;
}

extern "C" int subset_scores(const float* x, const float* q, size_t n, int d,
    const uint16_t* indices, int k, double* partial) {
    if (!admissible(x,q,n,d,k) || !indices || !partial) return 1;
    for (int h = 0; h < k; ++h)
        if (indices[h] >= d || (h && indices[h] <= indices[h-1])) return 2;
    int bad = 0;
    #pragma omp parallel for schedule(static) reduction(max:bad)
    for (size_t i = 0; i < n; ++i) {
        double sum = 0;
        for (int h = 0; h < k; ++h) {
            const int j = indices[h];
            const float coordinate = x[i*size_t(d)+j];
            if (!std::isfinite(coordinate)) bad = 2;
            const double delta = double(coordinate)-double(q[j]);
            const double square = delta*delta;
            sum = sum+square;
        }
        partial[i] = sum;
        if (!std::isfinite(sum)) bad = 3;
    }
    return bad;
}
