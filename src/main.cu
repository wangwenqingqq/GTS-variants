// GTS index construction and similarity search with GTS
// Created on 24-01-05

#include <algorithm>
#include <array>
#include <chrono>
#include <cfloat>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <numeric>
#include <queue>
#include <random>
#include <sstream>
#include <string>
#include <vector>
#include <cuda_runtime_api.h>
#include <device_launch_parameters.h>
#include "gpu_timer.cuh"
#include "tree.cuh"
#include "file.cuh"
#include "search.cuh"
#include "update.cuh"
#include "search_v2.cuh"
#include "config.cuh"
#include "learned_prune.cuh"

static float computeDistanceVector(short *data_d, int dim, int lhs, int rhs, int metric)
{
	float result = 0.0f;
	if (metric == 2)
	{
		for (int j = 0; j < dim; ++j)
		{
			float diff = data_d[lhs * dim + j] - data_d[rhs * dim + j];
			result += diff * diff;
		}
		result = sqrtf(result);
	}
	else if (metric == 1)
	{
		for (int j = 0; j < dim; ++j)
		{
			result += fabsf(data_d[lhs * dim + j] - data_d[rhs * dim + j]);
		}
	}
	else if (metric == 0)
	{
		for (int j = 0; j < dim; ++j)
		{
			float diff = fabsf(data_d[lhs * dim + j] - data_d[rhs * dim + j]);
			if (diff > result)
			{
				result = diff;
			}
		}
	}
	else if (metric == 5)
	{
		float sa1 = 0.0f, sa2 = 0.0f, sa3 = 0.0f;
		for (int j = 0; j < dim; ++j)
		{
			float lhs_v = data_d[lhs * dim + j];
			float rhs_v = data_d[rhs * dim + j];
			sa1 += lhs_v * lhs_v;
			sa2 += rhs_v * rhs_v;
			sa3 += lhs_v * rhs_v;
		}
		sa1 = sqrtf(sa1);
		sa2 = sqrtf(sa2);
		if (sa1 * sa2 == 0.0f)
		{
			return 0.0f;
		}
		float cos_val = sa3 / (sa1 * sa2);
		cos_val = fminf(0.99999994f, fmaxf(-0.99999994f, cos_val));
		result = fabsf(acosf(cos_val) * 180.0f / 3.1415926f);
	}
	return result;
}

static float computeDistanceString(char *data_s, int *size_s, int lhs, int rhs)
{
	const int n = size_s[lhs];
	const int m = size_s[rhs];
	if (n == 0)
		return static_cast<float>(m);
	if (m == 0)
		return static_cast<float>(n);

	int table[M][M];
	for (int j = 0; j <= n; ++j)
	{
		table[j][0] = j;
	}
	for (int k = 0; k <= m; ++k)
	{
		table[0][k] = k;
	}
	for (int j = 1; j <= n; ++j)
	{
		for (int k = 1; k <= m; ++k)
		{
			int cost = (data_s[lhs * M + j - 1] == data_s[rhs * M + k - 1]) ? 0 : 1;
			int del = table[j - 1][k] + 1;
			int ins = table[j][k - 1] + 1;
			int sub = table[j - 1][k - 1] + cost;
			table[j][k] = std::min(del, std::min(ins, sub));
		}
	}
	return static_cast<float>(table[n][m]);
}

static float computeDistanceHost(short *data_d, char *data_s, int *size_s, int *data_info, int lhs, int rhs)
{
	if (data_info[2] == 6)
	{
		return computeDistanceString(data_s, size_s, lhs, rhs);
	}
	return computeDistanceVector(data_d, data_info[0], lhs, rhs, data_info[2]);
}

static float computeKnnRadius(short *data_d, char *data_s, int *size_s, int *data_info, int query_id, int total_points, int k)
{
	std::vector<float> distances;
	distances.reserve(total_points);
	for (int idx = 0; idx < total_points; ++idx)
	{
		float dist = computeDistanceHost(data_d, data_s, size_s, data_info, idx, query_id);
		distances.push_back(dist);
	}
	if (distances.empty())
	{
		return 0.0f;
	}
	k = std::max(1, std::min(k, total_points));
	std::nth_element(distances.begin(), distances.begin() + (k - 1), distances.end());
	return distances[k - 1];
}

static float computeNodeBestDistance(const TN &node, int query_id, const std::vector<int> &id_list_host, short *data_d,
										 char *data_s, int *size_s, int *data_info)
{
	float best = FLT_MAX;
	for (int offset = 0; offset < node.size; ++offset)
	{
		int data_idx = id_list_host[node.lid + offset];
		float dist = computeDistanceHost(data_d, data_s, size_s, data_info, data_idx, query_id);
		if (dist < best)
		{
			best = dist;
		}
	}
	return best;
}

static bool copyDeviceArray(int *device_ptr, size_t count, std::vector<int> &host)
{
	host.resize(count);
	if (count == 0)
		return true;
	return cudaMemcpy(host.data(), device_ptr, count * sizeof(int), cudaMemcpyDeviceToHost) == cudaSuccess;
}

static bool copyNodeArray(TN *device_ptr, size_t count, std::vector<TN> &host)
{
	host.resize(count);
	if (count == 0)
		return true;
	return cudaMemcpy(host.data(), device_ptr, count * sizeof(TN), cudaMemcpyDeviceToHost) == cudaSuccess;
}

static int pickQueryId(const int *qid_list_host, int qnum, int sample_idx, int total_samples)
{
	if (qnum == 0)
		return 0;
	int stride = std::max(1, qnum / std::max(1, total_samples));
	int pos = sample_idx * stride;
	if (pos >= qnum)
	{
		pos = qnum - 1;
	}
	return qid_list_host[pos];
}

static bool envFlag(const char *name)
{
	const char *value = getenv(name);
	if (value == nullptr)
	{
		return false;
	}
	return !(value[0] == '0' && value[1] == '\0');
}

static int envInt(const char *name, int default_value)
{
	const char *value = getenv(name);
	if (value == nullptr)
	{
		return default_value;
	}
	return atoi(value);
}

static float envFloat(const char *name, float default_value)
{
	const char *value = getenv(name);
	if (value == nullptr)
	{
		return default_value;
	}
	return static_cast<float>(atof(value));
}

static std::string envString(const char *name)
{
	const char *value = getenv(name);
	if (value == nullptr)
	{
		return std::string();
	}
	return std::string(value);
}

struct PruneSample
{
	float delta;
	float radius;
	float density;
	float level;
	float label;
};

struct PruneSampleCollection
{
	std::vector<PruneSample> samples;
	float max_delta = 0.0f;
	float max_radius = 0.0f;
	float max_level = 0.0f;
};

static bool collectPruneSamples(PruneSampleCollection &collection, int sample_queries, int max_nodes_per_query,
		short *data_d, char *data_s, int *size_s, int *data_info, int *qid_list, int qnum, int k, float r,
		int process_type, int *id_list, TN *node_list, int *empty_list, int max_node_count)
{
	if (sample_queries <= 0 || qnum == 0)
	{
		std::cerr << "[Prune] 采样配置无效，无法训练" << std::endl;
		return false;
	}

	std::vector<int> host_id_list;
	std::vector<TN> host_nodes;
	std::vector<int> host_empty;

	if (!copyDeviceArray(id_list, data_info[1], host_id_list) ||
		!copyNodeArray(node_list, max_node_count, host_nodes) ||
		!copyDeviceArray(empty_list, max_node_count, host_empty))
	{
		std::cerr << "[Prune] 拷贝设备数据失败，取消训练" << std::endl;
		return false;
	}

	const int total_samples = std::min(sample_queries, qnum);
	const float max_size_norm = fmaxf(1.0f, static_cast<float>(MAX_SIZE));

	for (int sample_idx = 0; sample_idx < total_samples; ++sample_idx)
	{
		int query_id = pickQueryId(qid_list, qnum, sample_idx, total_samples);
		float current_radius = (process_type == 0)
								? computeKnnRadius(data_d, data_s, size_s, data_info, query_id, data_info[1], k)
								: r;

		std::queue<int> pending;
		pending.push(0);
		int logged = 0;
		while (!pending.empty() && logged < max_nodes_per_query)
		{
			int nid = pending.front();
			pending.pop();
			if (nid >= max_node_count)
				continue;
			if (host_empty[nid] == 1)
				continue;

			const TN &node = host_nodes[nid];
			if (node.pid < 0 || node.size <= 0)
			{
				if (node.is_leaf == 0)
				{
					for (int t = 0; t < TREE_ORDER; ++t)
					{
						int child = nid * TREE_ORDER + t + 1;
						if (child < max_node_count)
							pending.push(child);
					}
				}
				continue;
			}

			float dis_q = computeDistanceHost(data_d, data_s, size_s, data_info, node.pid, query_id);
			float delta = fabsf(dis_q - node.min_dis);
			float density = fminf(1.0f, static_cast<float>(node.size) / max_size_norm);
			float level = static_cast<float>(node.level);
			float best_dist = computeNodeBestDistance(node, query_id, host_id_list, data_d, data_s, size_s, data_info);
			float label = best_dist <= current_radius ? 1.0f : 0.0f;

			collection.samples.push_back({delta, current_radius, density, level, label});
			collection.max_delta = fmaxf(collection.max_delta, delta);
			collection.max_radius = fmaxf(collection.max_radius, current_radius);
			collection.max_level = fmaxf(collection.max_level, level);
			++logged;

			if (node.is_leaf == 0)
			{
				for (int t = 0; t < TREE_ORDER; ++t)
				{
					int child = nid * TREE_ORDER + t + 1;
					if (child < max_node_count)
						pending.push(child);
				}
			}
		}
	}

	if (collection.samples.empty())
	{
		std::cerr << "[Prune] 未采集到任何样本" << std::endl;
		return false;
	}

	return true;
}

static bool saveLearnedPruneWeights(const std::string &path, const LearnedPruneWeights &weights)
{
	std::ofstream out(path);
	if (!out.is_open())
	{
		std::cerr << "[Prune] 无法保存权重到 " << path << std::endl;
		return false;
	}

	out << "distance_norm " << weights.distance_norm << '\n';
	out << "level_norm " << weights.level_norm << '\n';
	out << "threshold " << weights.threshold << '\n';

	auto dumpArray = [&out](const char *name, const float *data, size_t count)
	{
		out << name;
		for (size_t i = 0; i < count; ++i)
		{
			out << ' ' << data[i];
		}
		out << '\n';
	};

	dumpArray("w1", weights.w1, PRUNE_H1 * PRUNE_INPUT_DIM);
	dumpArray("b1", weights.b1, PRUNE_H1);
	dumpArray("w2", weights.w2, PRUNE_H2 * PRUNE_H1);
	dumpArray("b2", weights.b2, PRUNE_H2);
	dumpArray("w3", weights.w3, PRUNE_H2);
	out << "b3 " << weights.b3 << '\n';

	std::cout << "[Prune] 权重已保存到 " << path << std::endl;
	return true;
}

static float sigmoidf(float x)
{
	return 1.0f / (1.0f + expf(-x));
}

static bool trainSamplesToWeights(const PruneSampleCollection &collection, int epochs, float lr, float threshold,
		LearnedPruneWeights &out_weights, float &final_loss)
{
	const size_t sample_count = collection.samples.size();
	if (sample_count == 0)
	{
		return false;
	}

	const float distance_norm = fmaxf(1e-6f, fmaxf(collection.max_delta, collection.max_radius));
	const float level_norm = fmaxf(1.0f, collection.max_level);

	std::vector<std::array<float, PRUNE_INPUT_DIM>> features(sample_count);
	std::vector<float> labels(sample_count);
	for (size_t i = 0; i < sample_count; ++i)
	{
		const PruneSample &s = collection.samples[i];
		auto &dst = features[i];
		dst[0] = s.delta / distance_norm;
		dst[1] = s.radius / distance_norm;
		dst[2] = s.density;
		dst[3] = s.level / level_norm;
		labels[i] = s.label;
	}

	LearnedPruneWeights weights = {};
	weights.distance_norm = distance_norm;
	weights.level_norm = level_norm;
	weights.threshold = threshold;

	std::mt19937 rng(42);
	std::uniform_real_distribution<float> dist_init(-0.1f, 0.1f);
	for (float &w : weights.w1)
	{
		w = dist_init(rng);
	}
	for (float &w : weights.w2)
	{
		w = dist_init(rng);
	}
	for (float &w : weights.w3)
	{
		w = dist_init(rng);
	}
	for (int i = 0; i < PRUNE_H1; ++i)
	{
		weights.b1[i] = 0.0f;
	}
	for (int i = 0; i < PRUNE_H2; ++i)
	{
		weights.b2[i] = 0.0f;
	}
	weights.b3 = 0.0f;

	std::vector<size_t> order(sample_count);
	std::iota(order.begin(), order.end(), 0);

	for (int epoch = 0; epoch < epochs; ++epoch)
	{
		std::shuffle(order.begin(), order.end(), rng);
		for (size_t idx : order)
		{
			const auto &feat = features[idx];
			const float label = labels[idx];

			float z1[PRUNE_H1];
			float h1[PRUNE_H1];
			for (int i = 0; i < PRUNE_H1; ++i)
			{
				float acc = weights.b1[i];
				for (int j = 0; j < PRUNE_INPUT_DIM; ++j)
				{
					acc += weights.w1[i * PRUNE_INPUT_DIM + j] * feat[j];
				}
				z1[i] = acc;
				h1[i] = fmaxf(0.0f, acc);
			}

			float z2[PRUNE_H2];
			float h2[PRUNE_H2];
			for (int i = 0; i < PRUNE_H2; ++i)
			{
				float acc = weights.b2[i];
				for (int j = 0; j < PRUNE_H1; ++j)
				{
					acc += weights.w2[i * PRUNE_H1 + j] * h1[j];
				}
				z2[i] = acc;
				h2[i] = fmaxf(0.0f, acc);
			}

			float acc = weights.b3;
			for (int j = 0; j < PRUNE_H2; ++j)
			{
				acc += weights.w3[j] * h2[j];
			}
			float pred = sigmoidf(acc);
			float delta_out = pred - label;

			float delta2[PRUNE_H2];
			for (int i = 0; i < PRUNE_H2; ++i)
			{
				delta2[i] = delta_out * weights.w3[i];
				if (z2[i] <= 0.0f)
				{
					delta2[i] = 0.0f;
				}
			}

			float delta1[PRUNE_H1];
			for (int i = 0; i < PRUNE_H1; ++i)
			{
				float sum = 0.0f;
				for (int j = 0; j < PRUNE_H2; ++j)
				{
					sum += delta2[j] * weights.w2[j * PRUNE_H1 + i];
				}
				delta1[i] = (z1[i] > 0.0f) ? sum : 0.0f;
			}

			for (int j = 0; j < PRUNE_H2; ++j)
			{
				weights.w3[j] -= lr * delta_out * h2[j];
			}
			weights.b3 -= lr * delta_out;

			for (int i = 0; i < PRUNE_H2; ++i)
			{
				for (int j = 0; j < PRUNE_H1; ++j)
				{
					weights.w2[i * PRUNE_H1 + j] -= lr * delta2[i] * h1[j];
				}
				weights.b2[i] -= lr * delta2[i];
			}

			for (int i = 0; i < PRUNE_H1; ++i)
			{
				for (int j = 0; j < PRUNE_INPUT_DIM; ++j)
				{
					weights.w1[i * PRUNE_INPUT_DIM + j] -= lr * delta1[i] * feat[j];
				}
				weights.b1[i] -= lr * delta1[i];
			}
		}
	}

	const float eps = 1e-6f;
	float loss_sum = 0.0f;
	for (size_t i = 0; i < sample_count; ++i)
	{
		const auto &feat = features[i];
		float z1[PRUNE_H1];
		float h1[PRUNE_H1];
		for (int j = 0; j < PRUNE_H1; ++j)
		{
			float acc = weights.b1[j];
			for (int k = 0; k < PRUNE_INPUT_DIM; ++k)
			{
				acc += weights.w1[j * PRUNE_INPUT_DIM + k] * feat[k];
			}
			z1[j] = acc;
			h1[j] = fmaxf(0.0f, acc);
		}
		float z2[PRUNE_H2];
		float h2[PRUNE_H2];
		for (int j = 0; j < PRUNE_H2; ++j)
		{
			float acc = weights.b2[j];
			for (int k = 0; k < PRUNE_H1; ++k)
			{
				acc += weights.w2[j * PRUNE_H1 + k] * h1[k];
			}
			z2[j] = acc;
			h2[j] = fmaxf(0.0f, acc);
		}
		float acc = weights.b3;
		for (int j = 0; j < PRUNE_H2; ++j)
		{
			acc += weights.w3[j] * h2[j];
		}
		float pred = sigmoidf(acc);
		float label = labels[i];
		loss_sum += -(label * logf(fmaxf(pred, eps)) + (1.0f - label) * logf(fmaxf(1.0f - pred, eps)));
	}

	final_loss = loss_sum / static_cast<float>(sample_count);
	out_weights = weights;
	return true;
}

static bool runInlinePruneTraining(short *data_d, char *data_s, int *size_s, int *data_info, int *qid_list, int qnum,
		int k, float r, int process_type, int *id_list, TN *node_list, int *empty_list, int max_node_count)
{
	if (!envFlag("GTS_PRUNE_INLINE_TRAIN"))
	{
		return false;
	}
	if (process_type == 2)
	{
		std::cout << "[Prune] 更新模式下跳过内联训练" << std::endl;
		return false;
	}
	if (qnum <= 0)
	{
		std::cout << "[Prune] 无查询，无法训练学习剪枝" << std::endl;
		return false;
	}

	int sample_queries = envInt("GTS_PRUNE_INLINE_QUERIES", std::max(1, qnum / 100));
	int max_nodes_sample = envInt("GTS_PRUNE_INLINE_NODES", 4096);
	int epochs = envInt("GTS_PRUNE_INLINE_EPOCHS", 80);
	float lr = envFloat("GTS_PRUNE_INLINE_LR", 1e-3f);
	float threshold = envFloat("GTS_PRUNE_INLINE_THRESHOLD", 0.3f);
	int min_samples = envInt("GTS_PRUNE_INLINE_MIN_SAMPLES", 128);

	PruneSampleCollection collection;
	if (!collectPruneSamples(collection, sample_queries, max_nodes_sample, data_d, data_s, size_s, data_info,
			qid_list, qnum, k, r, process_type, id_list, node_list, empty_list, max_node_count))
	{
		return false;
	}

	if (static_cast<int>(collection.samples.size()) < min_samples)
	{
		std::cout << "[Prune] 样本数量不足 (" << collection.samples.size() << ")，跳过训练" << std::endl;
		return false;
	}

	LearnedPruneWeights weights = {};
	float final_loss = 0.0f;
	if (!trainSamplesToWeights(collection, epochs, lr, threshold, weights, final_loss))
	{
		std::cerr << "[Prune] 训练失败" << std::endl;
		return false;
	}

	if (!uploadLearnedPruneWeights(weights))
	{
		std::cerr << "[Prune] 上传训练权重失败" << std::endl;
		return false;
	}

	std::cout << "[Prune] 内联训练完成: samples=" << collection.samples.size()
			<< ", epochs=" << epochs << ", loss=" << final_loss << std::endl;

	const std::string save_path = envString("GTS_PRUNE_INLINE_SAVE");
	if (!save_path.empty())
	{
		saveLearnedPruneWeights(save_path, weights);
	}

	return true;
}

bool loadLearnedPruneWeights(const std::string &path, LearnedPruneWeights &weights)
{
	std::ifstream in(path);
	if (!in.is_open())
	{
		std::cerr << "[Prune] 无法打开权重文件: " << path << std::endl;
		return false;
	}

	std::string key;
	int filled = 0;
	while (in >> key)
	{
		if (key == "distance_norm")
		{
			in >> weights.distance_norm;
			++filled;
		}
		else if (key == "level_norm")
		{
			in >> weights.level_norm;
			++filled;
		}
		else if (key == "threshold")
		{
			in >> weights.threshold;
			++filled;
		}
		else if (key == "w1")
		{
			for (int i = 0; i < PRUNE_H1 * PRUNE_INPUT_DIM; ++i)
			{
				in >> weights.w1[i];
			}
			++filled;
		}
		else if (key == "b1")
		{
			for (int i = 0; i < PRUNE_H1; ++i)
			{
				in >> weights.b1[i];
			}
			++filled;
		}
		else if (key == "w2")
		{
			for (int i = 0; i < PRUNE_H2 * PRUNE_H1; ++i)
			{
				in >> weights.w2[i];
			}
			++filled;
		}
		else if (key == "b2")
		{
			for (int i = 0; i < PRUNE_H2; ++i)
			{
				in >> weights.b2[i];
			}
			++filled;
		}
		else if (key == "w3")
		{
			for (int i = 0; i < PRUNE_H2; ++i)
			{
				in >> weights.w3[i];
			}
			++filled;
		}
		else if (key == "b3")
		{
			in >> weights.b3;
			++filled;
		}
		else
		{
			std::string rest;
			std::getline(in, rest);
		}
	}

	const int expected = 9;
	if (filled < expected)
	{
		std::cerr << "[Prune] 权重文件缺少字段，仅解析到 " << filled << " 项" << std::endl;
		return false;
	}
	return true;
}

bool uploadLearnedPruneWeights(const LearnedPruneWeights &weights)
{
	if (cudaMemcpyToSymbol(g_prune_w1, weights.w1, sizeof(weights.w1)) != cudaSuccess)
		return false;
	if (cudaMemcpyToSymbol(g_prune_b1, weights.b1, sizeof(weights.b1)) != cudaSuccess)
		return false;
	if (cudaMemcpyToSymbol(g_prune_w2, weights.w2, sizeof(weights.w2)) != cudaSuccess)
		return false;
	if (cudaMemcpyToSymbol(g_prune_b2, weights.b2, sizeof(weights.b2)) != cudaSuccess)
		return false;
	if (cudaMemcpyToSymbol(g_prune_w3, weights.w3, sizeof(weights.w3)) != cudaSuccess)
		return false;
	if (cudaMemcpyToSymbol(g_prune_b3, &weights.b3, sizeof(weights.b3)) != cudaSuccess)
		return false;

	g_prune_cfg.distance_norm = weights.distance_norm > 1e-6f ? weights.distance_norm : 1.0f;
	g_prune_cfg.level_norm = weights.level_norm > 0.0f ? weights.level_norm : 1.0f;
	g_prune_cfg.threshold = weights.threshold;
	g_prune_cfg.enabled = 1;
	std::cout << "[Prune] 已加载神经剪枝权重，threshold=" << g_prune_cfg.threshold << std::endl;
	return true;
}

void disableLearnedPrune()
{
	g_prune_cfg.enabled = 0;
}

void configureLearnedPruneRuntime(int tree_height)
{
	g_prune_cfg.level_norm = tree_height > 1 ? static_cast<float>(tree_height - 1) : 1.0f;
}

bool exportLearnedPruneDataset(const std::string &path, int sample_queries, int max_nodes_per_query,
								 short *data_d, char *data_s, int *size_s, int *data_info, int *qid_list,
								 int qnum, int k, float r, int process_type, int *id_list, TN *node_list,
								 int *empty_list, int max_node_count)
{
	if (sample_queries <= 0 || qnum == 0)
	{
		std::cerr << "[Prune] 采样配置无效，跳过数据导出" << std::endl;
		return false;
	}

	std::ofstream out(path);
	if (!out.is_open())
	{
		std::cerr << "[Prune] 无法写入导出文件: " << path << std::endl;
		return false;
	}

	std::vector<int> host_id_list;
	std::vector<TN> host_nodes;
	std::vector<int> host_empty;

	if (!copyDeviceArray(id_list, data_info[1], host_id_list) ||
		!copyNodeArray(node_list, max_node_count, host_nodes) ||
		!copyDeviceArray(empty_list, max_node_count, host_empty))
	{
		std::cerr << "[Prune] 拷贝设备数据失败，取消导出" << std::endl;
		return false;
	}

	out << "delta_proj,current_radius,node_density,level,label" << std::endl;
	const int total_samples = std::min(sample_queries, qnum);
	const float inv_total_points = 1.0f / std::max(1, data_info[1]);

	for (int sample_idx = 0; sample_idx < total_samples; ++sample_idx)
	{
		int query_id = pickQueryId(qid_list, qnum, sample_idx, total_samples);
		float current_radius = (process_type == 0)
								? computeKnnRadius(data_d, data_s, size_s, data_info, query_id, data_info[1], k)
								: r;

		std::queue<int> pending;
		pending.push(0);
		int logged = 0;
		while (!pending.empty() && logged < max_nodes_per_query)
		{
			int nid = pending.front();
			pending.pop();
			if (nid >= max_node_count)
				continue;
			if (host_empty[nid] == 1)
				continue;

			const TN &node = host_nodes[nid];
			float dis_q = computeDistanceHost(data_d, data_s, size_s, data_info, node.pid, query_id);
			float delta = fabsf(dis_q - node.min_dis);
			float density = static_cast<float>(node.size) * inv_total_points;
			float level = static_cast<float>(node.level);
			float best_dist = computeNodeBestDistance(node, query_id, host_id_list, data_d, data_s, size_s, data_info);
			int label = best_dist <= current_radius ? 1 : 0;

			out << delta << ',' << current_radius << ',' << density << ',' << level << ',' << label << std::endl;
			++logged;

			if (node.is_leaf == 0)
			{
				for (int t = 0; t < TREE_ORDER; ++t)
				{
					int child = nid * TREE_ORDER + t + 1;
					if (child < max_node_count)
					{
						pending.push(child);
					}
				}
			}
		}
	}

	std::cout << "[Prune] 导出训练样本完成，文件: " << path << std::endl;
	return true;
}

inline size_t calcRawDataBytes(int *data_info, short *data_d, char *data_s, int *size_s)
{
	if (data_info[2] != 6)
	{
		return static_cast<size_t>(data_info[1]) * data_info[0] * sizeof(data_d[0]);
	}
	size_t char_bytes = static_cast<size_t>(data_info[1]) * M * sizeof(data_s[0]);
	size_t len_bytes = static_cast<size_t>(data_info[1]) * sizeof(size_s[0]);
	return char_bytes + len_bytes;
}

inline double bytesToMB(size_t bytes)
{
	return static_cast<double>(bytes) / (1024.0 * 1024.0);
}

int *data_info;
short *data_d;
char *data_s;
int *size_s;
int *qid_list;
int qnum;
int *max_node_num;
int *id_list;
TN *node_list;
char *file;
char *file_q;
char *file_u;
float time_index = 0;
float time_search = 0;
float time_update_s = 0;
float time_update_u = 0;
int count_update_s = 0;
int count_update_u = 0;
int tree_h;
int k;	 // k for knn
float r; // r for range query
int *empty_list;
int *qresult_count;
int *qresult_count_prefix;
int *result_id;
float *result_dis;
int process_type;
int search_type;

int main(int argc, char **argv)
{
	file = argv[1];
	load(file, data_info, data_d, data_s, size_s);
	process_type = (int)atoi(argv[3]);
	if (process_type != 2)
	{
		file_q = argv[2];
		loadQuery(file_q, qid_list, qnum);
		k = (int)atoi(argv[4]);
		r = (float)stod(argv[4]);
		// TREE_ORDER = (int)atoi(argv[5]);
		// MAX_SIZE = (int)atoi(argv[6]);
		// MAX_H = (int)atoi(argv[7]);
		// DIS_CODE = (int)atoi(argv[8]);
		// INFI_DIS = (int)atoi(argv[9]);
		// float temp_s = (float)stod(argv[10]);
		// input_size = temp_s * 1024 * 1024 * 1024;
		// printf("%f, %f\n", temp_s, input_size);
	}
	else
	{
		file_u = argv[2];
		loadUpdate(file_u, update_list, update_num);
		// search_type = (int)atoi(argv[4]);
		search_type = 1;
		// k = (int)atoi(argv[5]);
		r = (float)stod(argv[4]);
		// TREE_ORDER = (int)atoi(argv[6]);
		// MAX_SIZE = (int)atoi(argv[7]);
		// MAX_H = (int)atoi(argv[8]);
		// DIS_CODE = (int)atoi(argv[9]);
		// INFI_DIS = (int)atoi(argv[10]);
		// MAX_IN_SIZE = (int)atoi(argv[11]);
	}

	// Index Construction - 使用GPU计时
	AdvancedGPUTimer timer("Index Construction");
	timer.start();
	indexConstru(data_d, data_s, size_s, data_info, id_list, node_list, max_node_num, tree_h, empty_list);
	timer.add_measurement();
	time_index += timer.get_total_time() / 1000.0f; // 转换为秒

	size_t raw_data_bytes = calcRawDataBytes(data_info, data_d, data_s, size_s);
	size_t id_map_bytes = static_cast<size_t>(data_info[1]) * sizeof(id_list[0]);
	size_t node_bytes = static_cast<size_t>(max_node_num[0]) * sizeof(TN);
	size_t static_total_bytes = raw_data_bytes + id_map_bytes + node_bytes;

	printf("\n[Static Storage Footprint]\n");
	printf("  Raw data buffer      : %.2f MB (%zu bytes)\n", bytesToMB(raw_data_bytes), raw_data_bytes);
	printf("  ID map (id_list)     : %.2f MB (%zu bytes)\n", bytesToMB(id_map_bytes), id_map_bytes);
	printf("  Tree nodes (node_list): %.2f MB (%zu bytes)\n", bytesToMB(node_bytes), node_bytes);
	printf("  Total static storage : %.2f MB (%zu bytes)\n\n", bytesToMB(static_total_bytes), static_total_bytes);

	configureLearnedPruneRuntime(tree_h);
	bool weights_ready = runInlinePruneTraining(data_d, data_s, size_s, data_info, qid_list, qnum, k, r,
			process_type, id_list, node_list, empty_list, max_node_num[0]);
	if (!weights_ready)
	{
		const std::string weight_path = envString("GTS_PRUNE_WEIGHTS");
		const bool auto_enable = envFlag("GTS_ENABLE_LEARNED_PRUNE") || !weight_path.empty();
		if (auto_enable && !weight_path.empty())
		{
			LearnedPruneWeights weights = {};
			if (!loadLearnedPruneWeights(weight_path, weights) || !uploadLearnedPruneWeights(weights))
			{
				fprintf(stderr, "[Prune] 加载剪枝权重失败，禁用学习剪枝。\n");
				disableLearnedPrune();
			}
		}
		else
		{
			disableLearnedPrune();
		}
	}

	const std::string export_path = envString("GTS_PRUNE_EXPORT");
	if (!export_path.empty() && process_type != 2)
	{
		int sample_queries = envInt("GTS_PRUNE_EXPORT_QUERIES", std::max(1, qnum / 100));
		int max_nodes_sample = envInt("GTS_PRUNE_EXPORT_NODES", 4096);
		exportLearnedPruneDataset(export_path, sample_queries, max_nodes_sample, data_d, data_s, size_s, data_info,
								   qid_list, qnum, k, r, process_type, id_list, node_list, empty_list, max_node_num[0]);
	}

	// knn
	if (process_type == 0)
	{
		FILE *fcost = fopen(argv[5], "w");
		fprintf(fcost, "Knn search num: %d\nResult radius: \n", k);
		fflush(fcost);

		// knn - 使用GPU计时
		AdvancedGPUTimer search_timer("Knn Search");
		search_timer.start();
		searchIndexKnnV2(data_d, node_list, id_list, max_node_num, qid_list, qnum, k, tree_h, data_info, empty_list, data_s, size_s);
		search_timer.add_measurement();
		time_search += search_timer.get_total_time() / 1000.0f; // 转换为秒

		// Output results
		for (int i = 0; i < qnum; i++)
		{
			fprintf(fcost, "%f ", res_dis[i]);
			fflush(fcost);
		}
		printf("Time of index construction: %f\n", time_index);
		printf("Average search time: %f\n", time_search / qnum);
		printf("query number: %d\n", qnum);
		fprintf(fcost, "\nTime of index construction: %f\n", time_index);
		fprintf(fcost, "Average search time: %f\n", time_search / qnum);
		fprintf(fcost, "query number: %d\n", qnum);
		fflush(fcost);
		fclose(fcost);
	}

	// Range query
	else if (process_type == 1)
	{
		FILE *fcost = fopen(argv[5], "w");
		fprintf(fcost, "Range search radius: %f\nResult num: \n", r);
		fflush(fcost);

		// Range query - 使用GPU计时
		AdvancedGPUTimer rnn_search_timer("Range Search");
		rnn_search_timer.start();
		searchIndexRnnV2(data_d, node_list, id_list, max_node_num, qid_list, qnum, r, tree_h, data_info, empty_list, data_s, size_s);
		rnn_search_timer.add_measurement();
		time_search += rnn_search_timer.get_total_time() / 1000.0f; // 转换为秒

		// Output results
		for (int i = 0; i < qnum; i++)
		{
			fprintf(fcost, "%d ", res[i]);
			fflush(fcost);
		}
		printf("\nTime of index construction: %f\n", time_index);
		printf("Average search time: %f\n", time_search / qnum);
		printf("query number: %d\n", qnum);
		fprintf(fcost, "\nTime of index construction: %f\n", time_index);
		fprintf(fcost, "Average search time: %f\n", time_search / qnum);
		fprintf(fcost, "query number: %d\n", qnum);
		fflush(fcost);
		fclose(fcost);
	}

	// Update
	else
	{
		FILE *fcost = fopen(argv[5], "w");
		fprintf(fcost, "Range search radius (check for updates): %f\nResult num: \n", r);
		fflush(fcost);

		// Update
		updateIndexRnn(data_d, node_list, id_list, max_node_num, qid_list, 1, r, tree_h, data_info, empty_list,
					   qresult_count, qresult_count_prefix, result_id, result_dis, data_s, size_s, fcost, time_update_s, time_update_u,
					   count_update_s, count_update_u);

		// Output results
		printf("Time of index construction: %f\n", time_index);
		printf("Total update time: %f\n", time_update_s / count_update_s + time_update_u / count_update_u);
		printf("Search time in update: %f\n", time_update_s / count_update_s);
		printf("Update time in update: %f\n", time_update_u / count_update_u);
		fprintf(fcost, "\nTime of index construction: %f\n", time_index);
		fprintf(fcost, "Total update time: %f\n", time_update_s / count_update_s + time_update_u / count_update_u);
		fprintf(fcost, "Search time in update : % f\n", time_update_s / count_update_s);
		fprintf(fcost, "Update time in update: %f\n", time_update_u / count_update_u);
		fflush(fcost);
		fclose(fcost);
	}

	// Release memory
	cudaFree(data_info);
	cudaFree(data_d);
	cudaFree(data_s);
	cudaFree(size_s);
	cudaFree(id_list);
	cudaFree(node_list);
	cudaFree(max_node_num);
	cudaFree(qid_list);
	cudaFree(empty_list);
	cudaFree(update_list);
	cudaFree(res);
	cudaFree(res_dis);
	return 0;
}