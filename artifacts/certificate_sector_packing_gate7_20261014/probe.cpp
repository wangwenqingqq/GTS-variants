// CPU-only packed subset and original-order parity audit; no fallback execution.
#include "../proof_per_byte_512_gate5_20261013/probe.cpp"

static bool permutation(const uint16_t* pi, int d, uint16_t* inverse) {
    if (!pi) return false;
    bool seen[960] = {};
    for (int p = 0; p < d; ++p) {
        if (pi[p] >= d || seen[pi[p]]) return false;
        seen[pi[p]] = true; inverse[pi[p]] = p;
    }
    return true;
}

extern "C" int packed_subset(const float* x, const float* q, size_t n, int d,
    const uint16_t* pi, const uint16_t* sectors, int k, double* partial) {
    if (d%8 || !admissible(x,q,n,d,k*8) || !sectors || !partial) return 1;
    uint16_t inverse[960]; bool selected[960] = {};
    if (!permutation(pi,d,inverse)) return 2;
    for (int h = 0; h < k; ++h) {
        if (sectors[h] >= d/8 || (h && sectors[h] <= sectors[h-1])) return 2;
        for (int t = 0; t < 8; ++t) selected[pi[8*sectors[h]+t]] = true;
    }
    uint16_t positions[960]; int count = 0;
    for (int j = 0; j < d; ++j) if (selected[j]) positions[count++] = inverse[j];
    if (count != k*8) return 2;
    int bad = 0;
    #pragma omp parallel for schedule(static) reduction(max:bad)
    for (size_t i = 0; i < n; ++i) {
        double sum = 0;
        for (int h = 0; h < count; ++h) {
            const int p = positions[h]; const float v = x[i*size_t(d)+p];
            if (!std::isfinite(v)) bad = 3;
            const double delta = double(v)-double(q[p]);
            const double square = delta*delta; sum = sum+square;
        }
        partial[i] = sum;
        if (!std::isfinite(sum)) bad = 3;
    }
    return bad;
}

extern "C" int packed_full_audit(const float* x, const float* q, size_t n, int d,
    const uint16_t* pi, double* full) {
    if (d%8 || !admissible(x,q,n,d,d) || !full) return 1;
    uint16_t inverse[960]; if (!permutation(pi,d,inverse)) return 2;
    int bad = 0;
    #pragma omp parallel for schedule(static) reduction(max:bad)
    for (size_t i = 0; i < n; ++i) {
        double sum = 0;
        for (int j = 0; j < d; ++j) {
            const int p = inverse[j]; const float v = x[i*size_t(d)+p];
            if (!std::isfinite(v)) bad = 3;
            const double delta = double(v)-double(q[p]);
            const double square = delta*delta; sum = sum+square;
        }
        full[i] = sum;
        if (!std::isfinite(sum)) bad = 3;
    }
    return bad;
}
