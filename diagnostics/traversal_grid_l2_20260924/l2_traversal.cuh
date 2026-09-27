#pragma once

// Batch-one L2 path. The predicate and arithmetic are kept in the original
// order; only metric dispatch and assignment of children to CTAs change.
template<bool Grid>
__global__ void l2Walk(int *query_node_list, int start_idx, TN *node_list,
                       float r, float *data_d, int *qid_list, int node_num,
                       int *max_node_num, int *data_info, int *empty_list) {
    int i = Grid ? blockIdx.x * blockDim.x + threadIdx.x : threadIdx.x;
    const int stride = Grid ? blockDim.x * gridDim.x : blockDim.x;
    for (; i < node_num; i += stride) {
        int nid = start_idx + i;
        int nid_parent = (nid - 1) / TREE_ORDER;
        if ((query_node_list[nid_parent] == 1) && (empty_list[nid] == 0)) {
            TN node = node_list[nid];
            float dis_q = 0;
            for (int j = 0; j < data_info[0]; j++) {
                dis_q += pow(data_d[node.pid * data_info[0] + j] -
                             data_d[qid_list[0] * data_info[0] + j], 2);
            }
            dis_q = pow(dis_q, 0.5);
            float dis_lb = node.min_dis - dis_q;
            dis_lb = max(dis_lb, 0.0);
            if (nid % TREE_ORDER != 0) {
                float dis_lb2 = dis_q - node_list[nid + 1].min_dis;
                dis_lb = max(dis_lb, dis_lb2);
            }
            if (dis_lb <= r) query_node_list[nid] = 1;
        }
    }
}
