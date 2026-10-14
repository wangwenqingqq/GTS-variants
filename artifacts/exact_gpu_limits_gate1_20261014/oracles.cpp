// CPU diagnostic only: all ordering construction and full-score reads are free in the oracle model.
#include <algorithm>
#include <cfenv>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <limits>
static_assert(std::numeric_limits<double>::is_iec559 && std::numeric_limits<double>::digits == 53, "IEEE FP64 required");
static_assert(std::numeric_limits<float>::is_iec559 && std::numeric_limits<float>::digits == 24, "IEEE FP32 required");

static bool valid(int d, double threshold, double guard) {
    return d > 0 && d <= 960 && std::isfinite(threshold) && threshold >= 0 &&
        std::isfinite(guard) && guard > threshold && std::fegetround() == FE_TONEAREST;
}

extern "C" int pair_oracle(const float* x, const float* q, size_t n, int d,
    double threshold, double guard, double* full, uint16_t* original,
    uint16_t* nominal, uint16_t* safe, double* nonhit_dim_sums, uint64_t* audit) {
    if (!valid(d, threshold, guard) || !n || !x || !q || !full || !original ||
        !nominal || !safe || !nonhit_dim_sums || !audit) return 1;
    for (int j = 0; j < d; ++j) if (!std::isfinite(q[j])) return 2;
    double contributions[960];
    for (size_t i = 0; i < n; ++i) {
        double total = 0;
        int first = 0;
        for (int j = 0; j < d; ++j) {
            if (!std::isfinite(x[i * size_t(d) + j])) return 2;
            const double delta = double(x[i * size_t(d) + j]) - double(q[j]);
            const double square = delta * delta;
            contributions[j] = square;
            const double previous = total;
            total = total + square;
            if (!std::isfinite(total) || total < previous) return 3;
            if (!first && total > threshold) first = j + 1;
        }
        full[i] = total;
        original[i] = uint16_t(first ? first : d);
        const bool hit = total <= threshold;
        if (!hit) for (int j = 0; j < d; ++j) {
            nonhit_dim_sums[j] = nonhit_dim_sums[j] + contributions[j];
            if (!std::isfinite(nonhit_dim_sums[j])) return 3;
        }
        std::sort(contributions, contributions + d, std::greater<double>());
        double prefix = 0;
        int plain = 0, guarded = 0;
        for (int j = 0; j < d; ++j) {
            prefix = prefix + contributions[j];
            if (!plain && prefix > threshold) plain = j + 1;
            if (prefix > guard) { guarded = j + 1; break; }
        }
        if (hit && plain) ++audit[0];
        if (hit && guarded) return 4;
        if (!hit && !guarded) ++audit[1];
        nominal[i] = uint16_t(hit ? d : (plain ? plain : d));
        safe[i] = uint16_t(hit ? d : (guarded ? guarded : d));
        if (nominal[i] != safe[i]) ++audit[2];
    }
    return 0;
}

extern "C" int global_oracle(const float* x, const float* q, const double* reference,
    size_t n, int d, double threshold, double guard, const int* order,
    uint16_t* nominal, uint16_t* safe, uint64_t* audit) {
    if (!valid(d, threshold, guard) || !n || !x || !q || !reference || !order ||
        !nominal || !safe || !audit) return 1;
    bool seen[960] = {};
    for (int j = 0; j < d; ++j) {
        if (order[j] < 0 || order[j] >= d || seen[order[j]] || !std::isfinite(q[j])) return 2;
        seen[order[j]] = true;
    }
    for (size_t i = 0; i < n; ++i) {
        if (!std::isfinite(reference[i]) || reference[i] < 0) return 2;
        const bool hit = reference[i] <= threshold;
        double prefix = 0;
        int plain = 0, guarded = 0;
        for (int k = 0; k < d; ++k) {
            const int j = order[k];
            if (!std::isfinite(x[i * size_t(d) + j])) return 2;
            const double delta = double(x[i * size_t(d) + j]) - double(q[j]);
            const double square = delta * delta;
            prefix = prefix + square;
            if (!plain && prefix > threshold) plain = k + 1;
            if (prefix > guard) { guarded = k + 1; break; }
        }
        if (hit && plain) ++audit[0];
        if (hit && guarded) return 4;
        if (!hit && !guarded) ++audit[1];
        nominal[i] = uint16_t(hit ? d : (plain ? plain : d));
        safe[i] = uint16_t(hit ? d : (guarded ? guarded : d));
        if (nominal[i] != safe[i]) ++audit[2];
    }
    return 0;
}
