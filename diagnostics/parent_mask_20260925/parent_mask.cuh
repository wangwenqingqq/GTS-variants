#pragma once

// One thread owns one parent and its ten children. Siblings share one pivot.
// The 10-bit register mask keeps the original radial-shell test; child flags
// are expanded to int because the unchanged downstream selector consumes ints.
template<int Group>
__global__ void parentMaskWalk(int* flags, int start, const TN* nodes, float radius,
                               const float* data, const int* query_id, int dim,
                               const int* empty, int parent_count) {
    const int parent_pos = blockIdx.x * Group + threadIdx.x;
    if (parent_pos >= parent_count) return;
    const int first = start + parent_pos * TREE_ORDER;
    const int parent = (first - 1) / TREE_ORDER;
    if (flags[parent] != 1) return;

    int pivot = -1;
    for (int child = 0; child < TREE_ORDER; ++child) {
        if (empty[first + child] == 0) {
            pivot = nodes[first + child].pid;
            break;
        }
    }
    if (pivot < 0) return;

    float distance = 0.0f;
    const int query = query_id[0];
    for (int j = 0; j < dim; ++j) {
        distance += pow(data[pivot * dim + j] - data[query * dim + j], 2);
    }
    distance = pow(distance, 0.5);

    unsigned int mask = 0;
    for (int child = 0; child < TREE_ORDER; ++child) {
        const int nid = first + child;
        if (empty[nid] != 0) continue;
        float lower = max(nodes[nid].min_dis - distance, 0.0f);
        if (child != TREE_ORDER - 1)
            lower = max(lower, distance - nodes[nid + 1].min_dis);
        if (lower <= radius) mask |= 1u << child;
    }
    for (int child = 0; child < TREE_ORDER; ++child)
        flags[first + child] = (mask >> child) & 1u;
}
