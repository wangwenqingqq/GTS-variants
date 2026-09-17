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

struct TrainingSample { float features[3]; float label; };
struct MLPWeightsHost { float W1[3][8]; float b1[8]; float W2[8][1]; float b2[1]; };

inline float compute_dist_cpu(const short* data, int idx1, int idx2, int dim, int metric_type) {
    float result = 0.0f;
    if (metric_type == 2) { 
        for (int j = 0; j < dim; j++) {
            float diff = (float)data[idx1 * dim + j] - (float)data[idx2 * dim + j];
            result += diff * diff;
        }
        result = sqrtf(result);
    } else {
        for (int j = 0; j < dim; j++) {
            float diff = (float)data[idx1 * dim + j] - (float)data[idx2 * dim + j];
            result += diff * diff;
        }
        result = sqrtf(result);
    }
    return result;
}

class MLPTuner {
private:
    const int hidden_size = 8;
    const int epochs = 60;
    const float learning_rate = 0.03f;

    float get_ground_truth_rk(int q_idx, short* data_h, int n, int dim, int metric_type, int k) {
        std::vector<float> dists;
        dists.reserve(512);
        std::mt19937 rng(q_idx);
        std::uniform_int_distribution<int> dist_gen(0, n - 1);
        for (int i = 0; i < 512; ++i) {
            dists.push_back(compute_dist_cpu(data_h, q_idx, dist_gen(rng), dim, metric_type));
        }
        std::sort(dists.begin(), dists.end());
        int idx = (k < (int)dists.size()) ? k : (int)dists.size() - 1;
        return dists[idx];
    }

public:
    void AutoTuneAndUpload(TN* node_list, int num_nodes, short* data_h, int* id_list_h, int dim, int n, int metric_type) {
        std::printf("\n[AutoTune] Strategy: Conservative but Effective Pruning...\n");

        std::vector<TrainingSample> train_data;
        train_data.reserve(20000);
        std::mt19937 rng(1337);

        // 1) 选代表性查询
        std::vector<int> pilot_queries;
        for (int i = num_nodes - 1; i >= 0 && pilot_queries.size() < 128; --i) {
            if (node_list[i].is_leaf && node_list[i].pid >= 0) {
                pilot_queries.push_back(node_list[i].pid);
            }
        }

        // 2) 估计 Rk 并构造训练样本（保守，正样本权重大）
        float rk_sum = 0.0f;
        int rk_cnt = 0;
        for (int q_idx : pilot_queries) {
            float Rk = get_ground_truth_rk(q_idx, data_h, n, dim, metric_type, 8);
            if (Rk < 1e-6f) Rk = 1.0f;
            rk_sum += Rk;
            rk_cnt++;

            int step = std::max(1, num_nodes / 1000);
            for (int i = 0; i < num_nodes; i += step) {
                if (node_list[i].pid < 0) continue;
                float d_qp = compute_dist_cpu(data_h, q_idx, node_list[i].pid, dim, metric_type);
                float r = node_list[i].min_dis;
                float lb = fmaxf(0.0f, d_qp - r);

                float f1 = d_qp / Rk;
                float f2 = r / Rk;
                float f3 = lb / Rk;
                if (f3 < 4.0f) {
                    float label = (lb <= Rk) ? 1.0f : 0.0f;
                    train_data.push_back({{f1, f2, f3}, label});
                }
            }
        }

        float rk_avg = (rk_cnt > 0) ? (rk_sum / rk_cnt) : 1.0f;
        if (rk_avg < 1e-6f) rk_avg = 1.0f;

        // 3) 初始化权重
        MLPWeightsHost w;
        std::uniform_real_distribution<float> init_dist(-0.05f, 0.05f);
        for (int i = 0; i < 3; i++) for (int j = 0; j < hidden_size; j++) w.W1[i][j] = init_dist(rng);
        for (int i = 0; i < hidden_size; i++) w.b1[i] = 0.0f;
        for (int i = 0; i < hidden_size; i++) w.W2[i][0] = init_dist(rng);
        w.b2[0] = 1.0f; // 偏向保留

        // 4) 训练（正样本加权，避免召回下降）
        for (int e = 0; e < epochs; ++e) {
            for (const auto& s : train_data) {
                float h[8];
                for (int j = 0; j < hidden_size; ++j) {
                    float sum = w.b1[j] + s.features[0]*w.W1[0][j] + s.features[1]*w.W1[1][j] + s.features[2]*w.W1[2][j];
                    h[j] = fmaxf(0.0f, sum);
                }
                float out = w.b2[0];
                for (int j = 0; j < hidden_size; ++j) out += h[j] * w.W2[j][0];
                float pred = 1.0f / (1.0f + expf(-out));

                float beta = (s.label > 0.5f) ? 3.0f : 1.0f; // 提升正样本权重
                float error = beta * (pred - s.label);
                float d_out = error * pred * (1.0f - pred);

                w.b2[0] -= learning_rate * d_out;
                for (int j = 0; j < hidden_size; ++j) {
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

        // 5) 上传权重与归一化尺度
        float w1_t[24];
        for (int j = 0; j < hidden_size; ++j) for (int i = 0; i < 3; ++i) w1_t[j * 3 + i] = w.W1[i][j];
        float scales[3] = {1.0f / rk_avg, 1.0f / rk_avg, 1.0f / rk_avg};

        upload_mlp_constants(scales, w1_t, w.b1, &w.W2[0][0], w.b2);
        std::printf("[AutoTune] Done. rk_avg=%.4f, samples=%lu, b2=%.4f\n", rk_avg, train_data.size(), w.b2[0]);
    }
};

#endif