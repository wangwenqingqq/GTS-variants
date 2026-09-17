#pragma once

#include <cuda_runtime_api.h>
#include <device_launch_parameters.h>
#include <math.h>
#include <string>
#include "tree.cuh"

// 极简神经网络剪枝模块的常量配置
constexpr int PRUNE_INPUT_DIM = 4;
constexpr int PRUNE_H1 = 16;
constexpr int PRUNE_H2 = 8;

struct LearnedPruneWeights
{
    float distance_norm;
    float level_norm;
    float threshold;
    float w1[PRUNE_H1 * PRUNE_INPUT_DIM];
    float b1[PRUNE_H1];
    float w2[PRUNE_H2 * PRUNE_H1];
    float b2[PRUNE_H2];
    float w3[PRUNE_H2];
    float b3;
};

struct LearnedPruneDeviceConfig
{
    int enabled;
    float distance_norm;
    float level_norm;
    float threshold;
};

__device__ __managed__ LearnedPruneDeviceConfig g_prune_cfg = {0, 1.0f, 1.0f, 0.5f};
__constant__ float g_prune_w1[PRUNE_H1 * PRUNE_INPUT_DIM] = {0.0f};
__constant__ float g_prune_b1[PRUNE_H1] = {0.0f};
__constant__ float g_prune_w2[PRUNE_H2 * PRUNE_H1] = {0.0f};
__constant__ float g_prune_b2[PRUNE_H2] = {0.0f};
__constant__ float g_prune_w3[PRUNE_H2] = {0.0f};
__constant__ float g_prune_b3 = 0.0f;

__host__ bool loadLearnedPruneWeights(const std::string &path, LearnedPruneWeights &weights);
__host__ bool uploadLearnedPruneWeights(const LearnedPruneWeights &weights);
__host__ void disableLearnedPrune();
__host__ void configureLearnedPruneRuntime(int tree_height);
__host__ bool exportLearnedPruneDataset(const std::string &path, int sample_queries, int max_nodes_per_query,
                                        short *data_d, char *data_s, int *size_s, int *data_info, int *qid_list,
                                        int qnum, int k, float r, int process_type, int *id_list, TN *node_list,
                                        int *empty_list, int max_node_count);

__host__ inline bool learnedPruneEnabledHost()
{
    return g_prune_cfg.enabled != 0;
}

__device__ inline void normalize_features(float &f0, float &f1, float &level)
{
    float dist_norm = g_prune_cfg.distance_norm > 1e-6f ? g_prune_cfg.distance_norm : 1.0f;
    float level_norm = g_prune_cfg.level_norm > 0.0f ? g_prune_cfg.level_norm : 1.0f;
    f0 = f0 / dist_norm;
    f1 = f1 / dist_norm;
    level = level / level_norm;
}

__device__ inline float runLearnedPruneMLP(const float features[PRUNE_INPUT_DIM])
{
    float hidden1[PRUNE_H1];
    float hidden2[PRUNE_H2];

    #pragma unroll
    for (int i = 0; i < PRUNE_H1; ++i)
    {
        float acc = g_prune_b1[i];
        #pragma unroll
        for (int j = 0; j < PRUNE_INPUT_DIM; ++j)
        {
            acc += g_prune_w1[i * PRUNE_INPUT_DIM + j] * features[j];
        }
        hidden1[i] = fmaxf(0.0f, acc);
    }

    #pragma unroll
    for (int i = 0; i < PRUNE_H2; ++i)
    {
        float acc = g_prune_b2[i];
        #pragma unroll
        for (int j = 0; j < PRUNE_H1; ++j)
        {
            acc += g_prune_w2[i * PRUNE_H1 + j] * hidden1[j];
        }
        hidden2[i] = fmaxf(0.0f, acc);
    }

    float acc = g_prune_b3;
    #pragma unroll
    for (int j = 0; j < PRUNE_H2; ++j)
    {
        acc += g_prune_w3[j] * hidden2[j];
    }

    return 1.0f / (1.0f + expf(-acc));
}

__device__ inline bool learnedPruneAllowsNode(float dis_q, const TN &node, float current_radius)
{
    if (g_prune_cfg.enabled == 0)
    {
        return true;
    }

    float features[PRUNE_INPUT_DIM];
    features[0] = fabsf(dis_q - node.min_dis);
    features[1] = current_radius;
    features[2] = fminf(1.0f, static_cast<float>(node.size) / fmaxf(1.0f, static_cast<float>(MAX_SIZE)));
    features[3] = static_cast<float>(node.level);

    normalize_features(features[0], features[1], features[3]);

    float prob = runLearnedPruneMLP(features);
    return prob >= g_prune_cfg.threshold;
}
