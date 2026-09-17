// ============================================================
// Incremental Insert Module for GTS++ (v3: Global Pool + Per-Leaf Index)
// O(log n) per insert, linked-list index for fast per-leaf search
// ============================================================

#pragma once

// Global overflow pool capacity
#define OVERFLOW_POOL_CAP 128

// Global pool storage
int *overflow_pool_data = nullptr;   // data IDs
int *overflow_pool_leaf = nullptr;   // which leaf each entry belongs to
int *overflow_pool_next = nullptr;   // linked list: next pointer (-1 = end)
int *overflow_leaf_head = nullptr;   // per-leaf: head index into pool (-1 = empty)
int overflow_pool_size = 0;          // current entries in pool
int overflow_pool_generation = 0;
int overflow_max_nodes = 0;

// ============================================================
// CPU-side: Find which leaf node a new data point belongs to
// ============================================================

int findTargetLeaf(short *data_d, TN *node_list, int *empty_list,
                   int data_id, int tree_h, int *data_info, int *id_list,
                   char *data_s, int *size_s)
{
    static TN *h_node_list = nullptr;
    static int *h_empty_list = nullptr;
    static int h_generation = -1;

    if (h_generation != overflow_pool_generation) {
        if (h_node_list) free(h_node_list);
        if (h_empty_list) free(h_empty_list);
        h_node_list = (TN *)malloc(overflow_max_nodes * sizeof(TN));
        h_empty_list = (int *)malloc(overflow_max_nodes * sizeof(int));
        cudaMemcpy(h_node_list, node_list, overflow_max_nodes * sizeof(TN), cudaMemcpyDeviceToHost);
        cudaMemcpy(h_empty_list, empty_list, overflow_max_nodes * sizeof(int), cudaMemcpyDeviceToHost);
        h_generation = overflow_pool_generation;
    }

    int current_node = 0;
    for (int level = 0; level < tree_h - 1; level++)
    {
        float best_dist = 1e30f;
        int best_child = -1;

        for (int c = 0; c < TREE_ORDER; c++)
        {
            int child_id = current_node * TREE_ORDER + c + 1;
            if (child_id >= overflow_max_nodes) continue;
            if (h_empty_list[child_id] != 0) continue;

            TN child = h_node_list[child_id];
            int pivot = child.pid;

            float dist = 0;
            if (data_info[2] == 2) {  // L2
                for (int j = 0; j < data_info[0]; j++) {
                    float diff = (float)data_d[data_id * data_info[0] + j] -
                                 (float)data_d[pivot * data_info[0] + j];
                    dist += diff * diff;
                }
                dist = sqrtf(dist);
            } else if (data_info[2] == 1) {  // L1
                for (int j = 0; j < data_info[0]; j++) {
                    dist += fabsf((float)data_d[data_id * data_info[0] + j] -
                                  (float)data_d[pivot * data_info[0] + j]);
                }
            } else if (data_info[2] == 0) {  // Linf
                for (int j = 0; j < data_info[0]; j++) {
                    float d = fabsf((float)data_d[data_id * data_info[0] + j] -
                                    (float)data_d[pivot * data_info[0] + j]);
                    if (d > dist) dist = d;
                }
            } else if (data_info[2] == 5) {  // Cosine
                float sa1 = 0, sa2 = 0, sa3 = 0;
                for (int j = 0; j < data_info[0]; j++) {
                    sa1 += data_d[data_id * data_info[0] + j] * data_d[data_id * data_info[0] + j];
                    sa2 += data_d[pivot * data_info[0] + j] * data_d[pivot * data_info[0] + j];
                    sa3 += data_d[data_id * data_info[0] + j] * data_d[pivot * data_info[0] + j];
                }
                sa1 = sqrtf(sa1); sa2 = sqrtf(sa2);
                if (sa1 * sa2 > 0) {
                    float cos_val = sa3 / (sa1 * sa2);
                    if (cos_val > 1) cos_val = 0.99999999f;
                    dist = fabsf(acosf(cos_val) * 180.0f / 3.1415926f);
                }
            } else if (data_info[2] == 6) {  // Edit distance
                int n = size_s[data_id];
                int m = size_s[pivot];
                if (n == 0) dist = m;
                else if (m == 0) dist = n;
                else {
                    int table[110][110];
                    for (int j = 0; j <= n; j++) table[j][0] = j;
                    for (int k = 0; k <= m; k++) table[0][k] = k;
                    for (int j = 1; j <= n; j++)
                        for (int k = 1; k <= m; k++) {
                            int cost = (data_s[data_id * M + j - 1] == data_s[pivot * M + k - 1]) ? 0 : 1;
                            table[j][k] = 1 + std::min(table[j-1][k], table[j][k-1]);
                            table[j][k] = std::min(table[j-1][k-1] + cost, table[j][k]);
                        }
                    dist = table[n][m];
                }
            }

            if (dist < best_dist) {
                best_dist = dist;
                best_child = child_id;
            }
        }

        if (best_child < 0) break;
        if (h_node_list[best_child].is_leaf == 1) return best_child;
        current_node = best_child;
    }

    for (int c = 0; c < TREE_ORDER; c++) {
        int child_id = current_node * TREE_ORDER + c + 1;
        if (child_id >= overflow_max_nodes) continue;
        if (h_empty_list[child_id] != 0) continue;
        if (h_node_list[child_id].is_leaf == 1) return child_id;
    }
    return current_node;
}

// ============================================================
// Initialize global overflow pool with per-leaf linked list index
// ============================================================

void initOverflowPool(int max_nodes)
{
    if (overflow_pool_data) { free(overflow_pool_data); }
    if (overflow_pool_leaf) { free(overflow_pool_leaf); }
    if (overflow_pool_next) { free(overflow_pool_next); }
    if (overflow_leaf_head) { cudaFree(overflow_leaf_head); }

    overflow_max_nodes = max_nodes;
    overflow_pool_generation++;

    overflow_pool_data = (int*)malloc(OVERFLOW_POOL_CAP * sizeof(int));
    overflow_pool_leaf = (int*)malloc(OVERFLOW_POOL_CAP * sizeof(int));
    overflow_pool_next = (int*)malloc(OVERFLOW_POOL_CAP * sizeof(int));
    overflow_leaf_head = (int*)malloc(max_nodes * sizeof(int));

    memset(overflow_leaf_head, 0xFF, max_nodes * sizeof(int)); // -1

    overflow_pool_size = 0;
    cudaDeviceSynchronize();
    cudaGetLastError(); // clear any stale errors
}

// ============================================================
// Incremental insert: O(log n) tree traversal + O(1) pool append
// Returns: 0 = success, 1 = pool full
// ============================================================

int incrementalInsert(short *data_d, TN *node_list, int *empty_list,
                      int data_id, int tree_h, int *data_info, int *id_list,
                      char *data_s, int *size_s)
{
    if (overflow_pool_size >= OVERFLOW_POOL_CAP) {
        return 1;  // pool full
    }

    int leaf_id = findTargetLeaf(data_d, node_list, empty_list,
                                  data_id, tree_h, data_info, id_list,
                                  data_s, size_s);

    int idx = overflow_pool_size;
    overflow_pool_data[idx] = data_id;
    overflow_pool_leaf[idx] = leaf_id;

    // Insert at head of leaf linked list
    overflow_pool_next[idx] = overflow_leaf_head[leaf_id];
    overflow_leaf_head[leaf_id] = idx;

    overflow_pool_size++;
    return 0;
}

// ============================================================
// Get overflow entries for a specific leaf (for search integration)
// Returns count of entries written to out_ids[]
// ============================================================

int getLeafOverflowEntries(int leaf_id, int *out_ids, int max_out)
{
    int count = 0;
    int idx = overflow_leaf_head[leaf_id];
    while (idx >= 0 && count < max_out) {
        out_ids[count++] = overflow_pool_data[idx];
        idx = overflow_pool_next[idx];
    }
    return count;
}

// ============================================================
// Collect ALL overflow data IDs into a flat array (for naive scan fallback)
// ============================================================

int collectAllOverflow(int *out_ids, int max_out)
{
    int count = (overflow_pool_size < max_out) ? overflow_pool_size : max_out;
    for (int i = 0; i < count; i++) {
        out_ids[i] = overflow_pool_data[i];
    }
    return count;
}

// ============================================================
// Free overflow pool
// ============================================================

void freeOverflowPool()
{
    if (overflow_pool_data) { free(overflow_pool_data); overflow_pool_data = nullptr; }
    if (overflow_pool_leaf) { free(overflow_pool_leaf); overflow_pool_leaf = nullptr; }
    if (overflow_pool_next) { free(overflow_pool_next); overflow_pool_next = nullptr; }
    if (overflow_leaf_head) { free(overflow_leaf_head); overflow_leaf_head = nullptr; }
    overflow_max_nodes = 0;
    overflow_pool_size = 0;
}
