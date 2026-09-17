// GTS index construction and similarity search with GTS
// Created on 24-01-05

#include <chrono>
#include <cuda_runtime_api.h>
#include <device_launch_parameters.h>
// ================= [修改 Start] =================
// 1. 定义宏：告诉 mlp_constant.cuh "我是主文件，请在这里分配内存"
#define MLP_MAIN_FILE
#include "mlp_constant.cuh"
#include "gpu_timer.cuh"
#include "tree.cuh"
#include "file.cuh"
#include "search.cuh"
#include "update.cuh"
#include "search_v2.cuh"
#include "config.cuh"
#include "mlp_tuner.cuh"



// 这个函数现在也在 main.cu 里，它能直接看到上面的变量，所以上传肯定成功
void upload_mlp_constants(float* h_scale, float* h_W1, float* h_b1, float* h_W2, float* h_b2) {
    cudaError_t err;

    // input_scale
    err = cudaMemcpyToSymbol(input_scale, h_scale, 3 * sizeof(float), 0, cudaMemcpyHostToDevice);
    if (err != cudaSuccess) printf("Error uploading input_scale: %s\n", cudaGetErrorString(err));

    // W1
    err = cudaMemcpyToSymbol(c_W1, h_W1, 24 * sizeof(float), 0, cudaMemcpyHostToDevice);
    if (err != cudaSuccess) printf("Error uploading W1: %s\n", cudaGetErrorString(err));

    // b1
    err = cudaMemcpyToSymbol(c_b1, h_b1, 8 * sizeof(float), 0, cudaMemcpyHostToDevice);
    if (err != cudaSuccess) printf("Error uploading b1: %s\n", cudaGetErrorString(err));

    // W2
    err = cudaMemcpyToSymbol(c_W2, h_W2, 8 * sizeof(float), 0, cudaMemcpyHostToDevice);
    if (err != cudaSuccess) printf("Error uploading W2: %s\n", cudaGetErrorString(err));

    // b2
    err = cudaMemcpyToSymbol(c_b2, h_b2, sizeof(float), 0, cudaMemcpyHostToDevice);
    if (err != cudaSuccess) printf("Error uploading b2: %s\n", cudaGetErrorString(err));
}
// ================= [移入的内容 End] =================
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

	// knn
	if (process_type == 0)
	{
		FILE *fcost = fopen(argv[5], "w");
		fprintf(fcost, "Knn search num: %d\nResult radius: \n", k);
		fflush(fcost);
		
		// [新增] 自适应 MLP 训练 - 在索引构建后、搜索前进行
		printf("\n[Main] Starting MLP auto-tuning for KNN search...\n");
		MLPTuner tuner;
		
		// 需要将数据拷贝到 CPU 以供训练使用
		short* data_h = new short[data_info[1] * data_info[0]];
		int* id_list_h = new int[data_info[1]];
		TN* node_list_h = new TN[max_node_num[0]];
		
		cudaMemcpy(data_h, data_d, data_info[1] * data_info[0] * sizeof(short), cudaMemcpyDeviceToHost);
		cudaMemcpy(id_list_h, id_list, data_info[1] * sizeof(int), cudaMemcpyDeviceToHost);
		cudaMemcpy(node_list_h, node_list, max_node_num[0] * sizeof(TN), cudaMemcpyDeviceToHost);
		
		// 调用自适应训练
		tuner.AutoTuneAndUpload(node_list_h, max_node_num[0], data_h, id_list_h, 
		                        data_info[0], data_info[1], data_info[2]);
		
		// 释放临时内存
		delete[] data_h;
		delete[] id_list_h;
		delete[] node_list_h;
		
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