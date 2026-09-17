// GTS++ Gate 1 prototype: containment-only admission + exact GPU delta.
//
// This program deliberately does NOT modify a GTS source tree.  It copies the
// archived headers into a scratch directory, builds a GTS index over an active
// prefix of SIFT, and treats the following IDs as genuinely withheld arrivals.
// An arrival is placed directly only when it is contained by every unchanged
// ancestor/leaf radial interval on one root-to-leaf path AND the target leaf
// remains within MAX_SIZE.  Otherwise it lives in an explicit fallback buffer
// that is scanned by the query path.  The range-query oracle is a brute-force
// scan of the full active set.

#include <cuda_runtime.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <numeric>
#include <random>
#include <sstream>
#include <string>
#include <vector>

// update.cuh brings in the archived GTS tree/query data structures.  Include
// standard-library headers first: config.cuh defines `short` as `float`.
#include "update.cuh"

namespace {

using Clock = std::chrono::steady_clock;

// One thread owns one delta object. The initial Gate-1 contract is range
// search over L2/SIFT, so a direct atomic append is sufficient and avoids
// conflating correctness with a separate prefix-scan implementation. A later
// performance candidate may replace the append path after this keeper passes.
__global__ void exact_delta_range_l2(const short* data, int dim, int query_id,
                                     const int* delta_ids, int delta_size,
                                     float radius, int* result_ids,
                                     int* result_count) {
    const int tid = blockIdx.x * blockDim.x + threadIdx.x;
    const int stride = blockDim.x * gridDim.x;
    for (int pos = tid; pos < delta_size; pos += stride) {
        const int object_id = delta_ids[pos];
        float distance_squared = 0.0f;
        const short* object = data + static_cast<size_t>(object_id) * dim;
        const short* query = data + static_cast<size_t>(query_id) * dim;
        for (int col = 0; col < dim; ++col) {
            const float diff = static_cast<float>(object[col]) -
                               static_cast<float>(query[col]);
            distance_squared += diff * diff;
        }
        // Match the archived/CPU contract: form the L2 norm, then compare to r.
        if (sqrtf(distance_squared) <= radius) {
            const int out = atomicAdd(result_count, 1);
            result_ids[out] = object_id;
        }
    }
}

void cuda_ok(cudaError_t status, const char* where) {
    if (status != cudaSuccess) {
        std::fprintf(stderr, "CUDA failure at %s: %s\\n", where,
                     cudaGetErrorString(status));
        std::exit(2);
    }
}

[[noreturn]] void fail(const char* msg) {
    std::fprintf(stderr, "FAIL: %s\\n", msg);
    std::exit(2);
}

double micros(Clock::time_point begin, Clock::time_point end) {
    return std::chrono::duration<double, std::micro>(end - begin).count();
}

double percentile(std::vector<double> values, double q) {
    if (values.empty()) return 0.0;
    std::sort(values.begin(), values.end());
    const size_t pos = static_cast<size_t>(q * static_cast<double>(values.size() - 1));
    return values[pos];
}

double mean(const std::vector<double>& values) {
    if (values.empty()) return 0.0;
    return std::accumulate(values.begin(), values.end(), 0.0) /
           static_cast<double>(values.size());
}

bool load_sift_prefix(const char* path, int wanted, int expected_dim,
                      std::vector<float>& out) {
    std::ifstream input(path);
    if (!input) {
        std::fprintf(stderr, "cannot open SIFT input: %s\\n", path);
        return false;
    }
    std::string line;
    if (!std::getline(input, line)) return false;
    std::istringstream header(line);
    int dim = 0, rows = 0, metric = -1;
    header >> dim >> rows >> metric;
    if (dim != expected_dim || metric != 2 || rows < wanted) {
        std::fprintf(stderr,
                     "unexpected SIFT header dim=%d rows=%d metric=%d wanted=%d\\n",
                     dim, rows, metric, wanted);
        return false;
    }
    out.assign(static_cast<size_t>(wanted) * dim, 0.0f);
    for (int row = 0; row < wanted; ++row) {
        if (!std::getline(input, line)) {
            std::fprintf(stderr, "truncated SIFT input at row %d\\n", row);
            return false;
        }
        char* p = line.data();
        for (int col = 0; col < dim; ++col) {
            char* end = nullptr;
            const float v = std::strtof(p, &end);
            if (end == p) {
                std::fprintf(stderr, "parse failure at row=%d col=%d\\n", row, col);
                return false;
            }
            out[static_cast<size_t>(row) * dim + col] = v;
            p = end;
        }
    }
    return true;
}

inline float l2(const std::vector<float>& values, int a, int b, int dim) {
    float total = 0.0f;
    const float* pa = values.data() + static_cast<size_t>(a) * dim;
    const float* pb = values.data() + static_cast<size_t>(b) * dim;
    for (int j = 0; j < dim; ++j) {
        const float diff = pa[j] - pb[j];
        total += diff * diff;
    }
    return std::sqrt(total);
}

struct RouteResult {
    int leaf = -1;
    bool saw_containment = false;
    bool saw_full_leaf = false;
};

struct QueryStats {
    int leaves = 0;
    int tree_candidates = 0;
};

struct SafeContainmentIndex {
    int dim = 0;
    int max_nodes = 0;
    int max_size = 0;
    int id_capacity = 0;
    const std::vector<float>* values = nullptr;
    TN* d_nodes = nullptr;
    int* d_ids = nullptr;

    std::vector<TN> nodes;
    std::vector<int> empty;
    std::vector<float> max_dis;
    std::vector<int> ids;
    std::vector<int> fallback;
    std::vector<int> direct;

    float distance(int a, int b) const {
        return l2(*values, a, b, dim);
    }

    RouteResult find_leaf_rec(int parent, int incoming) const {
        RouteResult aggregate;
        for (int c = 0; c < TREE_ORDER; ++c) {
            const int child = parent * TREE_ORDER + c + 1;
            if (child >= max_nodes || empty[child] != 0) continue;
            const TN& n = nodes[child];
            const float d = distance(incoming, n.pid);

            // Exact containment only.  We intentionally do not add epsilon:
            // a borderline numerical case falls back rather than expanding an
            // interval whose unchanged query semantics are being audited.
            if (d < n.min_dis || d > max_dis[child]) continue;
            aggregate.saw_containment = true;

            if (n.is_leaf == 1) {
                if (n.size < max_size) {
                    aggregate.leaf = child;
                    return aggregate;
                }
                aggregate.saw_full_leaf = true;
                continue;
            }

            const RouteResult below = find_leaf_rec(child, incoming);
            if (below.leaf >= 0) return below;
            aggregate.saw_containment = aggregate.saw_containment || below.saw_containment;
            aggregate.saw_full_leaf = aggregate.saw_full_leaf || below.saw_full_leaf;
        }
        return aggregate;
    }

    RouteResult find_leaf(int incoming) const {
        if (max_nodes <= 0 || empty[0] != 0) return RouteResult{};
        if (nodes[0].is_leaf == 1) {
            RouteResult result;
            result.saw_containment = true;
            if (nodes[0].size < max_size) result.leaf = 0;
            else result.saw_full_leaf = true;
            return result;
        }
        return find_leaf_rec(0, incoming);
    }

    bool direct_insert(int incoming, const RouteResult& route) {
        if (route.leaf < 0) return false;
        TN& leaf = nodes[route.leaf];
        if (leaf.size >= max_size) return false;  // query layout invariant
        const int write_pos = leaf.lid + leaf.size;
        if (write_pos < 0 || write_pos >= id_capacity) {
            fail("direct write would exceed padded id_list capacity");
        }
        if (ids[write_pos] != -1) {
            fail("direct write target is not an unused padded slot");
        }

        // The only device mutations on the direct path.  Crucially no
        // ancestor min/max envelope is modified because containment makes the
        // old envelope valid for the new object.
        cuda_ok(cudaMemcpy(d_ids + write_pos, &incoming, sizeof(int),
                           cudaMemcpyHostToDevice),
                "direct id slot write");
        ids[write_pos] = incoming;
        leaf.size += 1;
        cuda_ok(cudaMemcpy(d_nodes + route.leaf, &leaf, sizeof(TN),
                           cudaMemcpyHostToDevice),
                "direct leaf-size write");
        direct.push_back(incoming);
        return true;
    }

    void scan_leaf(int node_id, int query, float radius,
                   std::vector<int>& results, QueryStats& stats) const {
        const TN& leaf = nodes[node_id];
        stats.leaves++;
        for (int i = 0; i < leaf.size; ++i) {
            const int candidate = ids[leaf.lid + i];
            if (candidate < 0) fail("negative candidate in used leaf slot");
            stats.tree_candidates++;
            if (distance(candidate, query) <= radius) results.push_back(candidate);
        }
    }

    void range_rec(int parent, int query, float radius,
                   std::vector<int>& results, QueryStats& stats) const {
        if (nodes[parent].is_leaf == 1) {
            scan_leaf(parent, query, radius, results, stats);
            return;
        }
        for (int c = 0; c < TREE_ORDER; ++c) {
            const int child = parent * TREE_ORDER + c + 1;
            if (child >= max_nodes || empty[child] != 0) continue;
            const TN& n = nodes[child];
            const float d = distance(query, n.pid);
            float lower_bound = 0.0f;
            if (d < n.min_dis) lower_bound = n.min_dis - d;
            else if (d > max_dis[child]) lower_bound = d - max_dis[child];
            if (lower_bound > radius) continue;
            if (n.is_leaf == 1) scan_leaf(child, query, radius, results, stats);
            else range_rec(child, query, radius, results, stats);
        }
    }

    std::vector<int> range_query(int query, float radius, QueryStats& stats) const {
        std::vector<int> result;
        range_rec(0, query, radius, result, stats);
        // Explicit active-set semantics: every fallback arrival is scanned.
        for (int candidate : fallback) {
            if (distance(candidate, query) <= radius) result.push_back(candidate);
        }
        std::sort(result.begin(), result.end());
        result.erase(std::unique(result.begin(), result.end()), result.end());
        return result;
    }
};

std::vector<int> brute_range(const std::vector<float>& values, int active_total,
                             int query, float radius, int dim) {
    std::vector<int> result;
    result.reserve(64);
    for (int candidate = 0; candidate < active_total; ++candidate) {
        if (l2(values, candidate, query, dim) <= radius) result.push_back(candidate);
    }
    return result;
}

bool contains(const int* values, int count, int wanted) {
    for (int i = 0; i < count; ++i) {
        if (values[i] == wanted) return true;
    }
    return false;
}

void write_summary(const char* path, int prefix, int arrivals, int tree_h,
                   int leaves, int initial_leaf_min, int initial_leaf_max,
                   int direct, int fallback, int containment_fail,
                   int capacity_fail, const std::vector<double>& direct_us,
                   const std::vector<double>& fallback_us,
                   int oracle_queries, int oracle_failures,
                   double safe_q_mean, double safe_q_p50, double safe_q_p95,
                   double brute_q_mean, double direct_tree_candidates,
                   int direct_structural_missing,
                   double direct_gpu_query_mean, int direct_gpu_samples,
                   int direct_gpu_visible, unsigned gpu_sample_seed) {
    std::FILE* out = std::fopen(path, "w");
    if (!out) fail("cannot write summary");
    std::fprintf(out, "{\n");
    std::fprintf(out, "  \"design\": \"containment_only_no_interval_mutation\",\n");
    std::fprintf(out, "  \"dataset\": \"SIFT1M deterministic prefix/tail holdout\",\n");
    std::fprintf(out, "  \"prefix_active_initial\": %d,\n", prefix);
    std::fprintf(out, "  \"genuine_withheld_arrivals\": %d,\n", arrivals);
    std::fprintf(out, "  \"tree_height\": %d,\n", tree_h);
    std::fprintf(out, "  \"leaves\": %d,\n", leaves);
    std::fprintf(out, "  \"MAX_SIZE_legal_capacity\": 20,\n");
    std::fprintf(out, "  \"initial_leaf_size_min_max\": [%d, %d],\n", initial_leaf_min, initial_leaf_max);
    std::fprintf(out, "  \"direct_admitted\": %d,\n", direct);
    std::fprintf(out, "  \"fallback_total\": %d,\n", fallback);
    std::fprintf(out, "  \"fallback_no_containment\": %d,\n", containment_fail);
    std::fprintf(out, "  \"fallback_capacity_full\": %d,\n", capacity_fail);
    std::fprintf(out, "  \"direct_insert_us_mean_p50_p95\": [%.3f, %.3f, %.3f],\n",
                 mean(direct_us), percentile(direct_us, 0.50), percentile(direct_us, 0.95));
    std::fprintf(out, "  \"fallback_enqueue_us_mean_p50_p95\": [%.3f, %.3f, %.3f],\n",
                 mean(fallback_us), percentile(fallback_us, 0.50), percentile(fallback_us, 0.95));
    std::fprintf(out, "  \"range_oracle_queries\": %d,\n", oracle_queries);
    std::fprintf(out, "  \"range_oracle_failures\": %d,\n", oracle_failures);
    std::fprintf(out, "  \"safe_tree_plus_fallback_query_us_mean_p50_p95\": [%.3f, %.3f, %.3f],\n",
                 safe_q_mean, safe_q_p50, safe_q_p95);
    std::fprintf(out, "  \"bruteforce_query_us_mean\": %.3f,\n", brute_q_mean);
    std::fprintf(out, "  \"mean_tree_candidates_per_safe_query\": %.3f,\n", direct_tree_candidates);
    std::fprintf(out, "  \"all_direct_structural_missing\": %d,\n", direct_structural_missing);
    std::fprintf(out, "  \"gpu_tree_r0_visibility_scope\": \"all_direct_admitted\",\n");
    std::fprintf(out, "  \"gpu_tree_r0_fixed_random_seed\": %u,\n", gpu_sample_seed);
    std::fprintf(out, "  \"gpu_tree_r0_direct_visibility_samples\": %d,\n", direct_gpu_samples);
    std::fprintf(out, "  \"gpu_tree_r0_direct_visibility_hits\": %d,\n", direct_gpu_visible);
    std::fprintf(out, "  \"gpu_tree_r0_query_us_mean\": %.3f\n", direct_gpu_query_mean);
    std::fprintf(out, "}\n");
    std::fclose(out);
}

}  // namespace

int main(int argc, char** argv) {
    const char* sift_path = argc > 1 ? argv[1] :
        "data/sift_base.txt";
    const int prefix = argc > 2 ? std::atoi(argv[2]) : 100000;
    const int arrivals = argc > 3 ? std::atoi(argv[3]) : 10000;
    const char* summary_path = argc > 4 ? argv[4] : "containment_summary.json";
    const char* mode = argc > 5 ? argv[5] : "safe_admit";
    const bool safe_admit = std::strcmp(mode, "safe_admit") == 0;
    const bool all_delta = std::strcmp(mode, "all_delta") == 0;
    constexpr int dim = 128;
    const float range_radius = argc > 6 ? std::atof(argv[6]) : 442.0f;
    const int oracle_qnum = argc > 7 ? std::atoi(argv[7]) : 64;
    // For this 10K arrival audit this bound is above the entire direct set,
    // so every admitted ID receives a GPU r=0 visibility check.  Keeping the
    // deterministic shuffle/seed makes a capped future run reproducible.
    const int gpu_visibility_samples_target = argc > 8 ? std::atoi(argv[8]) : 1000000;
    constexpr unsigned gpu_visibility_seed = 20260717U;
    const int total = prefix + arrivals;
    if (prefix <= MAX_SIZE || arrivals <= 0 || range_radius < 0.0f ||
        oracle_qnum <= 0 || gpu_visibility_samples_target < 0)
        fail("invalid prefix/arrival/query configuration");
    if (!safe_admit && !all_delta) fail("mode must be safe_admit or all_delta");

    cuda_ok(cudaSetDevice(0), "cudaSetDevice(0)");
    std::printf("GTSPP_GATE1_BEGIN mode=%s prefix=%d arrivals=%d dim=%d radius=%.1f\\n",
                mode, prefix, arrivals, dim, range_radius);
    std::printf("ACTIVE_SET_SEMANTICS initial=[0,%d), arrivals=[%d,%d); direct in tree, fallback explicitly scanned.\\n",
                prefix, prefix, total);

    std::vector<float> host_data;
    const auto load_begin = Clock::now();
    if (!load_sift_prefix(sift_path, total, dim, host_data)) return 2;
    std::printf("LOAD_US=%.3f\\n", micros(load_begin, Clock::now()));

    short* data_d = nullptr;
    int* data_info = nullptr;
    int* id_list = nullptr;
    TN* node_list = nullptr;
    int* max_node_num = nullptr;
    int* empty_list = nullptr;
    int tree_h = 0;
    cuda_ok(cudaMallocManaged(&data_d, static_cast<size_t>(total) * dim * sizeof(short)),
            "allocate full raw store");
    cuda_ok(cudaMallocManaged(&data_info, 3 * sizeof(int)), "allocate data_info");
    cuda_ok(cudaMemcpy(data_d, host_data.data(),
                       static_cast<size_t>(total) * dim * sizeof(short),
                       cudaMemcpyHostToDevice),
            "upload full raw store");
    data_info[0] = dim;
    data_info[1] = prefix;  // index construction sees only the active prefix.
    data_info[2] = 2;
    cuda_ok(cudaDeviceSynchronize(), "raw-store upload sync");

    const auto build_begin = Clock::now();
    indexConstru(data_d, nullptr, nullptr, data_info, id_list, node_list,
                 max_node_num, tree_h, empty_list);
    cuda_ok(cudaDeviceSynchronize(), "index construction");
    const double build_us = micros(build_begin, Clock::now());
    std::printf("INDEX_BUILD_US=%.3f tree_h=%d nodes=%d MAX_SIZE=%d\\n",
                build_us, tree_h, max_node_num[0], MAX_SIZE);

    SafeContainmentIndex index;
    index.dim = dim;
    index.max_nodes = max_node_num[0];
    index.max_size = MAX_SIZE;
    index.values = &host_data;
    index.d_nodes = node_list;
    index.d_ids = id_list;
    index.nodes.resize(index.max_nodes);
    index.empty.resize(index.max_nodes);
    index.max_dis.resize(index.max_nodes);
    cuda_ok(cudaMemcpy(index.nodes.data(), node_list,
                       index.max_nodes * sizeof(TN), cudaMemcpyDeviceToHost),
            "copy nodes for containment router");
    cuda_ok(cudaMemcpy(index.empty.data(), empty_list,
                       index.max_nodes * sizeof(int), cudaMemcpyDeviceToHost),
            "copy empty flags for containment router");
    cuda_ok(cudaMemcpy(index.max_dis.data(), max_dis_d,
                       index.max_nodes * sizeof(float), cudaMemcpyDeviceToHost),
            "copy max intervals for containment router");

    int leaves = 0;
    int leaf_min = MAX_SIZE;
    int leaf_max = 0;
    int id_capacity = 0;
    for (int i = 0; i < index.max_nodes; ++i) {
        if (index.empty[i] == 0 && index.nodes[i].is_leaf == 1) {
            ++leaves;
            leaf_min = std::min(leaf_min, index.nodes[i].size);
            leaf_max = std::max(leaf_max, index.nodes[i].size);
            if (index.nodes[i].size > MAX_SIZE) fail("initial leaf exceeds MAX_SIZE");
            id_capacity = std::max(id_capacity,
                                   index.nodes[i].lid + index.nodes[i].size + LEAF_PAD_SLOTS);
        }
    }
    if (leaves == 0 || id_capacity <= prefix) fail("could not infer padded id_list capacity");
    index.id_capacity = id_capacity;
    index.ids.resize(id_capacity);
    cuda_ok(cudaMemcpy(index.ids.data(), id_list, id_capacity * sizeof(int), cudaMemcpyDeviceToHost),
            "copy padded ids for structural oracle");
    std::printf("TREE_SHAPE leaves=%d initial_leaf_size=[%d,%d] padded_id_capacity=%d\\n",
                leaves, leaf_min, leaf_max, id_capacity);

    std::vector<double> direct_us;
    std::vector<double> fallback_us;
    int containment_fallback = 0;
    int capacity_fallback = 0;
    for (int incoming = prefix; incoming < total; ++incoming) {
        const auto begin = Clock::now();
        const RouteResult route = safe_admit ? index.find_leaf(incoming) : RouteResult{};
        bool admitted = false;
        if (safe_admit && route.leaf >= 0) admitted = index.direct_insert(incoming, route);
        if (admitted) {
            direct_us.push_back(micros(begin, Clock::now()));
        } else {
            index.fallback.push_back(incoming);
            fallback_us.push_back(micros(begin, Clock::now()));
            if (route.saw_full_leaf) ++capacity_fallback;
            else ++containment_fallback;
        }
    }
    cuda_ok(cudaDeviceSynchronize(), "direct insert synchronization");
    std::printf("ADMISSION direct=%zu fallback=%zu no_containment=%d capacity=%d direct_rate=%.4f\\n",
                index.direct.size(), index.fallback.size(), containment_fallback, capacity_fallback,
                static_cast<double>(index.direct.size()) / static_cast<double>(arrivals));
    std::printf("INSERT_US direct mean/p50/p95=%.3f/%.3f/%.3f fallback mean/p50/p95=%.3f/%.3f/%.3f\\n",
                mean(direct_us), percentile(direct_us, 0.5), percentile(direct_us, 0.95),
                mean(fallback_us), percentile(fallback_us, 0.5), percentile(fallback_us, 0.95));

    // All directly admitted IDs must occur exactly once in an in-bounds leaf
    // slot before any query is run.  This checks the MAX_SIZE=20 layout
    // invariant over the complete direct set, not merely a sampled query set.
    std::vector<unsigned char> direct_seen(total, 0);
    for (int nid = 0; nid < index.max_nodes; ++nid) {
        if (index.empty[nid] != 0 || index.nodes[nid].is_leaf != 1) continue;
        const TN& leaf = index.nodes[nid];
        if (leaf.size > MAX_SIZE) fail("post-insert leaf exceeds MAX_SIZE");
        for (int pos = 0; pos < leaf.size; ++pos) {
            const int id = index.ids[leaf.lid + pos];
            if (id >= prefix && id < total) ++direct_seen[id];
        }
    }
    int direct_structural_missing = 0;
    for (int id : index.direct) {
        if (direct_seen[id] != 1) ++direct_structural_missing;
    }
    std::printf("ALL_DIRECT_STRUCTURAL_VISIBILITY direct=%zu missing_or_duplicate=%d\\n",
                index.direct.size(), direct_structural_missing);

    // Exact active-set audit: each query sees prefix + every arrival.  Tree
    // hits are supplemented by the explicit fallback buffer, then compared
    // byte-for-byte as an ID set with brute force.
    std::vector<double> safe_query_us;
    std::vector<double> brute_query_us;
    std::vector<double> tree_candidates;
    int oracle_failures = 0;
    int direct_self_queries = 0;
    int direct_self_hits = 0;
    for (int qi = 0; qi < oracle_qnum; ++qi) {
        const int query = prefix + (qi * arrivals) / oracle_qnum;
        QueryStats stats;
        const auto safe_begin = Clock::now();
        const std::vector<int> safe = index.range_query(query, range_radius, stats);
        safe_query_us.push_back(micros(safe_begin, Clock::now()));
        const auto brute_begin = Clock::now();
        const std::vector<int> brute = brute_range(host_data, total, query, range_radius, dim);
        brute_query_us.push_back(micros(brute_begin, Clock::now()));
        tree_candidates.push_back(static_cast<double>(stats.tree_candidates));
        if (safe != brute) {
            ++oracle_failures;
            std::printf("ORACLE_MISMATCH query=%d safe=%zu brute=%zu\\n",
                        query, safe.size(), brute.size());
        }
        if (std::binary_search(index.direct.begin(), index.direct.end(), query)) {
            ++direct_self_queries;
            if (std::binary_search(safe.begin(), safe.end(), query)) ++direct_self_hits;
        }
    }
    std::printf("RANGE_ORACLE queries=%d failures=%d safe_us mean/p50/p95=%.3f/%.3f/%.3f brute_us_mean=%.3f tree_candidates_mean=%.1f direct_self=%d/%d\\n",
                oracle_qnum, oracle_failures,
                mean(safe_query_us), percentile(safe_query_us, 0.5), percentile(safe_query_us, 0.95),
                mean(brute_query_us), mean(tree_candidates), direct_self_hits, direct_self_queries);

    // A second, GPU-resident visibility check uses the archived range-query
    // implementation only for directly admitted IDs at r=0.  It is not used
    // as the active-set oracle (the fallback buffer is intentionally outside
    // that archived query function); it simply verifies that unchanged tree
    // intervals expose each newly admitted object to the existing query path.
    int gpu_visible = 0;
    int gpu_samples = 0;
    std::vector<double> gpu_query_us;
    int* qid_list = nullptr;
    int* qresult_count = nullptr;
    int* qresult_count_prefix = nullptr;
    int* result_id = nullptr;
    float* result_dis = nullptr;
    cuda_ok(cudaMallocManaged(&is_delete, total * sizeof(int)), "allocate deletion bitmap");
    cuda_ok(cudaMemset(is_delete, 0, total * sizeof(int)), "clear deletion bitmap");
    cuda_ok(cudaMallocManaged(&qid_list, sizeof(int)), "allocate GPU query id");

    // End-to-end safe GPU path: archived GPU tree traversal over the unchanged
    // tree-resident set plus an exact GPU scan of every delta-resident object.
    // The same active snapshot is then checked against a CPU brute-force
    // oracle. Timing includes both GPU paths, synchronization, result transfer,
    // and host merge because all of them are required by this prototype's
    // immediate-visibility contract.
    int* delta_ids_d = nullptr;
    int* delta_result_ids_d = nullptr;
    int* delta_result_count_d = nullptr;
    if (!index.fallback.empty()) {
        cuda_ok(cudaMalloc(&delta_ids_d, index.fallback.size() * sizeof(int)),
                "allocate exact delta ids");
        cuda_ok(cudaMalloc(&delta_result_ids_d, index.fallback.size() * sizeof(int)),
                "allocate exact delta results");
        cuda_ok(cudaMemcpy(delta_ids_d, index.fallback.data(),
                           index.fallback.size() * sizeof(int), cudaMemcpyHostToDevice),
                "upload exact delta ids");
    }
    cuda_ok(cudaMalloc(&delta_result_count_d, sizeof(int)),
            "allocate exact delta result count");

    std::vector<double> gpu_safe_query_us;
    int gpu_safe_oracle_failures = 0;
    for (int qi = 0; qi < oracle_qnum; ++qi) {
        const int query = prefix + (qi * arrivals) / oracle_qnum;
        qid_list[0] = query;
        const auto begin = Clock::now();

        searchIndexRnnUpdate(data_d, node_list, id_list, max_node_num, qid_list,
                             1, range_radius, tree_h, data_info, empty_list,
                             qresult_count, qresult_count_prefix, result_id,
                             result_dis, nullptr, nullptr);
        cuda_ok(cudaMemset(delta_result_count_d, 0, sizeof(int)),
                "clear exact delta result count");
        if (!index.fallback.empty()) {
            const int threads = 256;
            const int blocks = std::min(4096, static_cast<int>(
                (index.fallback.size() + threads - 1) / threads));
            exact_delta_range_l2<<<blocks, threads>>>(
                data_d, dim, query, delta_ids_d,
                static_cast<int>(index.fallback.size()),
                range_radius, delta_result_ids_d,
                delta_result_count_d);
        }
        cuda_ok(cudaDeviceSynchronize(), "safe GPU tree+delta query");

        int delta_result_count = 0;
        cuda_ok(cudaMemcpy(&delta_result_count, delta_result_count_d, sizeof(int),
                           cudaMemcpyDeviceToHost),
                "copy exact delta result count");
        std::vector<int> safe;
        safe.reserve(static_cast<size_t>(qresult_count[0]) + delta_result_count);
        bool tree_contains_query = false;
        bool delta_contains_query = false;
        if (qresult_count[0] > 0) {
            const size_t old_size = safe.size();
            safe.resize(old_size + qresult_count[0]);
            cuda_ok(cudaMemcpy(safe.data() + old_size, result_id,
                               qresult_count[0] * sizeof(int),
                               cudaMemcpyDeviceToHost),
                    "copy GPU tree results");
            tree_contains_query =
                std::find(safe.begin() + old_size, safe.end(), query) != safe.end();
        }
        if (delta_result_count > 0) {
            const size_t old_size = safe.size();
            safe.resize(old_size + delta_result_count);
            cuda_ok(cudaMemcpy(safe.data() + old_size, delta_result_ids_d,
                               delta_result_count * sizeof(int),
                               cudaMemcpyDeviceToHost),
                    "copy exact delta results");
            delta_contains_query =
                std::find(safe.begin() + old_size, safe.end(), query) != safe.end();
        }
        std::sort(safe.begin(), safe.end());
        safe.erase(std::unique(safe.begin(), safe.end()), safe.end());
        gpu_safe_query_us.push_back(micros(begin, Clock::now()));

        const std::vector<int> brute =
            brute_range(host_data, total, query, range_radius, dim);
        if (safe != brute) {
            ++gpu_safe_oracle_failures;
            std::vector<int> missing;
            std::vector<int> extra;
            std::set_difference(brute.begin(), brute.end(), safe.begin(), safe.end(),
                                std::back_inserter(missing));
            std::set_difference(safe.begin(), safe.end(), brute.begin(), brute.end(),
                                std::back_inserter(extra));
            std::printf("GPU_SAFE_ORACLE_MISMATCH mode=%s query=%d safe=%zu brute=%zu tree=%d delta=%d\\n",
                        mode, query, safe.size(), brute.size(), qresult_count[0],
                        delta_result_count);
            std::printf("GPU_SAFE_ORACLE_DIFF query=%d query_direct=%d query_delta=%d tree_has_query=%d delta_has_query=%d missing=%zu extra=%zu",
                        query,
                        std::binary_search(index.direct.begin(), index.direct.end(), query) ? 1 : 0,
                        std::binary_search(index.fallback.begin(), index.fallback.end(), query) ? 1 : 0,
                        tree_contains_query ? 1 : 0, delta_contains_query ? 1 : 0,
                        missing.size(), extra.size());
            for (size_t mi = 0; mi < std::min<size_t>(missing.size(), 8); ++mi)
                std::printf(" missing_id=%d missing_d=%.6f", missing[mi],
                            l2(host_data, missing[mi], query, dim));
            for (size_t ei = 0; ei < std::min<size_t>(extra.size(), 8); ++ei)
                std::printf(" extra_id=%d extra_d=%.6f", extra[ei],
                            l2(host_data, extra[ei], query, dim));
            std::printf("\\n");
        }
    }
    std::printf("GPU_SAFE_ORACLE mode=%s queries=%d failures=%d mean/p50/p95_us=%.3f/%.3f/%.3f delta=%zu\\n",
                mode, oracle_qnum, gpu_safe_oracle_failures,
                mean(gpu_safe_query_us), percentile(gpu_safe_query_us, 0.50),
                percentile(gpu_safe_query_us, 0.95), index.fallback.size());
    if (!index.direct.empty()) {
        std::vector<int> sample_positions(index.direct.size());
        std::iota(sample_positions.begin(), sample_positions.end(), 0);
        std::mt19937 rng(gpu_visibility_seed);
        std::shuffle(sample_positions.begin(), sample_positions.end(), rng);
        const int target = std::min(gpu_visibility_samples_target,
                                    static_cast<int>(sample_positions.size()));
        for (int si = 0; si < target; ++si) {
            const int query = index.direct[sample_positions[si]];
            qid_list[0] = query;
            const auto begin = Clock::now();
            searchIndexRnnUpdate(data_d, node_list, id_list, max_node_num, qid_list,
                                 1, 0.0f, tree_h, data_info, empty_list,
                                 qresult_count, qresult_count_prefix, result_id,
                                 result_dis, nullptr, nullptr);
            cuda_ok(cudaDeviceSynchronize(), "GPU r=0 direct visibility query");
            gpu_query_us.push_back(micros(begin, Clock::now()));
            if (contains(result_id, qresult_count[0], query)) ++gpu_visible;
            ++gpu_samples;
        }
    }
    std::printf("GPU_TREE_R0_VISIBILITY seed=%u hits=%d samples=%d mean_us=%.3f\\n",
                gpu_visibility_seed, gpu_visible, gpu_samples, mean(gpu_query_us));

    write_summary(summary_path, prefix, arrivals, tree_h, leaves, leaf_min, leaf_max,
                  static_cast<int>(index.direct.size()), static_cast<int>(index.fallback.size()),
                  containment_fallback, capacity_fallback, direct_us, fallback_us,
                  oracle_qnum, oracle_failures, mean(safe_query_us),
                  percentile(safe_query_us, 0.5), percentile(safe_query_us, 0.95),
                  mean(brute_query_us), mean(tree_candidates), direct_structural_missing,
                  mean(gpu_query_us), gpu_samples, gpu_visible, gpu_visibility_seed);

    const bool pass = oracle_failures == 0 &&
                      gpu_safe_oracle_failures == 0 &&
                      direct_self_hits == direct_self_queries &&
                      direct_structural_missing == 0 &&
                      gpu_visible == gpu_samples;
    if (delta_ids_d) cudaFree(delta_ids_d);
    if (delta_result_ids_d) cudaFree(delta_result_ids_d);
    cudaFree(delta_result_count_d);
    std::printf("GTSPP_GATE1_RESULT mode=%s result=%s\\n", mode,
                pass ? "PASS" : "FAIL");
    return pass ? 0 : 1;
}
