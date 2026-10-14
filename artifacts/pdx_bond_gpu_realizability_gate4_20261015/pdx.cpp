// Fixed32 contract adaptation of the published PDX zone criterion; no new score.
#include "../exact_gpu_limits_gate1_20261014/oracles.cpp"
#include <cstring>
#include <numeric>

extern "C" int pdx_zone_order(const float* q, const float* means, int* order,
    float* ranks, int* zone_ids, int* cutoff_tie) {
    if (!q || !means || !order || !ranks || !zone_ids || !cutoff_tie ||
        std::fegetround() != FE_TONEAREST) return 1;
    for (int z = 0; z < 30; ++z) {
        float sum = 0;
        for (int j = 32*z; j < 32*(z+1); ++j) {
            if (!std::isfinite(q[j]) || !std::isfinite(means[j])) return 2;
            const float delta = q[j] - means[j];
            sum = sum + std::abs(delta);
        }
        ranks[z] = float(double(sum) / 32.0);
        if (!std::isfinite(ranks[z])) return 2;
    }
    std::iota(zone_ids, zone_ids + 30, 0);
    std::partial_sort(zone_ids, zone_ids + 3, zone_ids + 30,
        [ranks](int a, int b) { return ranks[a] > ranks[b]; });
    *cutoff_tie = 0;
    for (int k = 3; k < 30; ++k)
        *cutoff_tie += ranks[zone_ids[k]] == ranks[zone_ids[2]];
    std::sort(zone_ids, zone_ids + 3);
    std::sort(zone_ids + 3, zone_ids + 30);
    for (int k = 0; k < 960; ++k) order[k] = zone_ids[k/32]*32 + k%32;
    return 0;
}

extern "C" int validate_ordered_scores(const float* x, const float* q,
    const double* reference, size_t n, uint64_t* mismatches) {
    if (!x || !q || !reference || !n || !mismatches ||
        std::fegetround() != FE_TONEAREST) return 1;
    *mismatches = 0;
    for (int j = 0; j < 960; ++j) if (!std::isfinite(q[j])) return 2;
    for (size_t i = 0; i < n; ++i) {
        double score = 0;
        for (int j = 0; j < 960; ++j) {
            if (!std::isfinite(x[i*960+j])) return 2;
            const double delta = double(x[i*960+j]) - double(q[j]);
            const double term = delta * delta;
            score = score + term;
        }
        uint64_t got, expected;
        std::memcpy(&got, &score, sizeof(got));
        std::memcpy(&expected, reference+i, sizeof(expected));
        *mismatches += got != expected;
    }
    return *mismatches ? 3 : 0;
}
