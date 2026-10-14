// CPU-only sector certificate; the immutable parent supplies numerical guards.
#include "../proof_per_byte_512_gate5_20261013/probe.cpp"

extern "C" int sector_oracle(const float* x, const float* q, size_t n, int d,
    int k, double* b0, double* best, double* full) {
    if (d % 8 || !admissible(x,q,n,d,k*8) || !b0 || !best || !full) return 1;
    const int sectors = d/8;
    int bad = 0;
    #pragma omp parallel for schedule(static) reduction(max:bad)
    for (size_t i = 0; i < n; ++i) {
        double terms[960], scores[120], partition[120], sum = 0, first = 0;
        bool selected[120] = {}, invalid = false;
        for (int s = 0; s < sectors; ++s) {
            double group = 0;
            for (int h = 0; h < 8; ++h) {
                const int j = 8*s+h;
                const float coordinate = x[i*size_t(d)+j];
                if (!std::isfinite(coordinate)) { bad = 2; invalid = true; break; }
                const double delta = double(coordinate)-double(q[j]);
                const double term = delta*delta;
                terms[j] = term; group = group+term; sum = sum+term;
                if (j < k*8) first = first+term;
            }
            if (invalid) break;
            scores[s] = partition[s] = group;
        }
        if (invalid) continue;
        if (k < sectors) std::nth_element(partition,partition+k,partition+sectors,std::greater<double>());
        const double cut = *std::min_element(partition,partition+k);
        int greater = 0;
        for (int s = 0; s < sectors; ++s) greater += scores[s] > cut;
        int ties = k-greater, count = 0;
        for (int s = 0; s < sectors; ++s) {
            bool take = scores[s] > cut;
            if (scores[s] == cut && ties > 0) { take = true; --ties; }
            selected[s] = take; count += take;
        }
        // Sector sums rank only. The certificate adds original coordinate terms.
        double partial = 0;
        for (int j = 0; j < d; ++j) if (selected[j/8]) partial = partial+terms[j];
        b0[i] = first; best[i] = partial; full[i] = sum;
        if (count != k || ties || !std::isfinite(sum) || first > sum || partial > sum) bad = 3;
    }
    return bad;
}

extern "C" int sector_subset(const float* x, const float* q, size_t n, int d,
    const uint16_t* sectors, int k, double* partial) {
    if (d % 8 || !admissible(x,q,n,d,k*8) || !sectors || !partial) return 1;
    for (int h = 0; h < k; ++h)
        if (sectors[h] >= d/8 || (h && sectors[h] <= sectors[h-1])) return 2;
    int bad = 0;
    #pragma omp parallel for schedule(static) reduction(max:bad)
    for (size_t i = 0; i < n; ++i) {
        double sum = 0;
        for (int s = 0; s < k; ++s) for (int h = 0; h < 8; ++h) {
            const int j = 8*sectors[s]+h;
            const float coordinate = x[i*size_t(d)+j];
            if (!std::isfinite(coordinate)) bad = 2;
            const double delta = double(coordinate)-double(q[j]);
            const double term = delta*delta;
            sum = sum+term;
        }
        partial[i] = sum;
        if (!std::isfinite(sum)) bad = 3;
    }
    return bad;
}
