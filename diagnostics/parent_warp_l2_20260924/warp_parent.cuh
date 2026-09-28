#pragma once

// Batch-one L2: one warp owns a parent. Lane 0 retains the original scalar
// accumulation order; its one pivot distance is broadcast to child lanes.
__global__ void warpParentL2(int *flags, int start_idx, TN *node_list,
                             float radius, float *data_d, int *qid_list,
                             int node_num, int *data_info, int *empty_list) {
    const int lane = threadIdx.x & 31;
    const int group = (blockIdx.x * blockDim.x + threadIdx.x) >> 5;
    const int groups = node_num / TREE_ORDER;
    if (group >= groups) return;
    const int first = start_idx + group * TREE_ORDER;
    const int parent = (first - 1) / TREE_ORDER;
    if (flags[parent] != 1) return;

    int first_live = TREE_ORDER;
    if (lane == 0) {
        for (int k = 0; k < TREE_ORDER; ++k) {
            if (empty_list[first + k] == 0) { first_live = k; break; }
        }
    }
    first_live = __shfl_sync(0xffffffffu, first_live, 0);
    if (first_live == TREE_ORDER) return;

    float dis_q = 0;
    if (lane == 0) {
        const int pid = node_list[first + first_live].pid;
        for (int j = 0; j < data_info[0]; j++) {
            dis_q += pow(data_d[pid * data_info[0] + j] -
                         data_d[qid_list[0] * data_info[0] + j], 2);
        }
        dis_q = pow(dis_q, 0.5);
    }
    dis_q = __shfl_sync(0xffffffffu, dis_q, 0);

    if (lane < TREE_ORDER) {
        const int nid = first + lane;
        if (empty_list[nid] == 0) {
            TN node = node_list[nid];
            float dis_lb = node.min_dis - dis_q;
            dis_lb = max(dis_lb, 0.0);
            if (nid % TREE_ORDER != 0) {
                float dis_lb2 = dis_q - node_list[nid + 1].min_dis;
                dis_lb = max(dis_lb, dis_lb2);
            }
            if (dis_lb <= radius) flags[nid] = 1;
        }
    }
}
