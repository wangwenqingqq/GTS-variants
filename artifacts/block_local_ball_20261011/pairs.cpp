// CPU-only ordered FP64 pair distances. No reassociation or contraction admitted.
#include <cmath>
#include <cstdint>
#include <limits>
extern "C" int pair_distances(const float* x, int64_t n, int d,
    const int64_t* left, const int64_t* right, int64_t count, double* out) {
    if (!x || !left || !right || !out || n <= 0 || d <= 0 || d > 4096 || count <= 0 ||
        n > std::numeric_limits<int64_t>::max() / d) return 1;
    int invalid = 0;
    #pragma omp parallel for schedule(static) reduction(|:invalid) num_threads(4)
    for (int64_t i = 0; i < count; ++i) {
        int64_t a = left[i], b = right[i];
        if (a < 0 || a >= n || b < 0 || b >= n) { invalid = 1; continue; }
        double s = 0;
        for (int j = 0; j < d; ++j) {
            double u = x[a*d+j], v = x[b*d+j];
            if (!std::isfinite(u) || !std::isfinite(v)) invalid = 1;
            double delta = u-v;
            s += delta*delta;
        }
        out[i] = s;
    }
    return invalid;
}
