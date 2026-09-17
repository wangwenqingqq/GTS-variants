#ifndef MLP_TUNER_CUH
#define MLP_TUNER_CUH

#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <cuda_runtime.h>
#include <cstdio>
#include "config.cuh"
#include "tree.cuh"
#include "mlp_constant.cuh"

// ================== 补齐缺失的数据结构 ==================

struct TrainingSample {
    float features[3]; // [d_qp/Rk, r/Rk, lb/Rk]
    float label;       
};

struct MLPWeightsHost {
    float W1[3][8];
    float b1[8];
    float W2[8][1];
    float b2[1];
};

// ================== 补齐缺失的辅助函数 ==================

inline float compute_dist_cpu(const short* data, int idx1, int idx2, int dim, int metric_type) {
    float result = 0.0f;
    if (metric_type == 2) { // L2
        for (int j = 0; j < dim; j++) {
            float diff = (float)data[idx1 * dim + j] - (float)data[idx2 * dim + j];
            result += diff * diff;
        }
        result = sqrtf(result);
    } else {
        // 简写，实际生产中请保留你原来的多度量支持
        for (int j = 0; j < dim; j++) {
            float diff = (float)data[idx1 * dim + j] - (float)data[idx2 * dim + j];
            result += diff * diff;
        }
        result = sqrtf(result);
    }
    return result;
}

// ================== 核心类: MLPTuner ==================

class MLPTuner {
private:
    const int hidden_size = 8;
    const float learning_rate = 0.05f; 
    const int epochs = 100;

    // 模拟搜索获取真实阈值 Rk
    float get_ground_truth_rk(int q_idx, short* data_h, int n, int dim, int metric_type, int k) {
        std::vector<float> dists;
        std::mt19937 rng(q_idx);
        std::uniform_int_distribution<int> dist_gen(0, n - 1);
        for (int i = 0; i < 500; ++i) {
            dists.push_back(compute_dist_cpu(data_h, q_idx, dist_gen(rng), dim, metric_type));
        }
        std::sort(dists.begin(), dists.end());
        // 取第 k 小的距离作为 Rk 的估计
        return dists[k < dists.size() ? k : dists.size() - 1];
    }

public:
    void AutoTuneAndUpload(TN* node_list, int num_nodes, short* data_h, int* id_list_h, int dim, int n, int metric_type) {
        std::printf("\n[AutoTune] Starting Optimized Tuning (H100 Target)...\n");

        std::vector<TrainingSample> train_data;
        std::mt19937 rng(1337);
        
        // 1. 选取更有代表性的 Queries
        std::vector<int> pilot_queries;
        for (int i = num_nodes - 1; i >= 0 && pilot_queries.size() < 100; --i) {
            if (node_list[i].is_leaf && node_list[i].pid >= 0) pilot_queries.push_back(node_list[i].pid);
        }

        // 2. 生成高质量标签
        for (int q_idx : pilot_queries) {
            float Rk = get_ground_truth_rk(q_idx, data_h, n, dim, metric_type, 8);
            if (Rk < 1e-6) Rk = 1.0f;

            // 只采样部分节点，防止训练集过大减慢索引构建速度
            for (int i = 0; i < num_nodes && i < 1000; i += 2) {
                if (node_list[i].pid < 0) continue;

                float d_qp = compute_dist_cpu(data_h, q_idx, node_list[i].pid, dim, metric_type);
                float r = node_list[i].min_dis;
                float lb = fmaxf(0.0f, d_qp - r);

                // 使用相对距离特征
                float f1 = d_qp / Rk;
                float f2 = r / Rk;
                float f3 = lb / Rk;

                if (f3 < 3.0f) { // 困难样本：LB在Rk附近的
                    float label = (lb <= Rk) ? 1.0f : 0.0f;
                    train_data.push_back({{f1, f2, f3}, label});
                }
            }
        }

        // 3. 训练逻辑
        MLPWeightsHost w;
        std::uniform_real_distribution<float> init_dist(-0.2f, 0.2f);
        for(int i=0; i<3; i++) for(int j=0; j<8; j++) w.W1[i][j] = init_dist(rng);
        for(int i=0; i<8; i++) w.b1[i] = 0.0f;
        for(int i=0; i<8; i++) w.W2[i][0] = init_dist(rng);
        
        // 关键改进：默认大幅度剪枝
        w.b2[0] = -1.5f; 

        for (int e = 0; e < epochs; ++e) {
            for (const auto& s : train_data) {
                float h[8];
                for(int j=0; j<8; ++j) {
                    float sum = w.b1[j] + s.features[0]*w.W1[0][j] + s.features[1]*w.W1[1][j] + s.features[2]*w.W1[2][j];
                    h[j] = fmaxf(0.0f, sum); 
                }

                float out = w.b2[0];
                for(int j=0; j<8; ++j) out += h[j] * w.W2[j][0];
                float pred = 1.0f / (1.0f + expf(-out));

                float beta = (s.label > 0.5f) ? 2.5f : 1.0f; // 降低 Recall 惩罚，追求加速
                float error = beta * (pred - s.label);
                
                float d_out = error * pred * (1.0f - pred);
                w.b2[0] -= learning_rate * d_out;
                for(int j=0; j<8; ++j) {
                    w.W2[j][0] -= learning_rate * d_out * h[j];
                    if (h[j] > 0) {
                        float d_h = d_out * w.W2[j][0];
                        w.b1[j] -= learning_rate * d_h;
                        w.W1[0][j] -= learning_rate * d_h * s.features[0];
                        w.W1[1][j] -= learning_rate * d_h * s.features[1];
                        w.W1[2][j] -= learning_rate * d_h * s.features[2];
                    }
                }
            }
        }

        // 4. 参数上传
        float w1_t[24];
        for (int j = 0; j < 8; ++j) for (int i = 0; i < 3; ++i) w1_t[j * 3 + i] = w.W1[i][j];
        
        // 这里的 scale 设为 1.0，因为特征已经在训练阶段通过 Rk 归一化了
        // 推理 Kernel 里也要同步改为除以当前的最佳距离或预估 Rk
        float scales[3] = {1.0f, 1.0f, 1.0f}; 

        upload_mlp_constants(scales, w1_t, w.b1, &w.W2[0][0], w.b2);
        std::printf("[AutoTune] Uploaded. b2=%.4f, Samples=%lu\n", w.b2[0], train_data.size());
    }
};

#endif