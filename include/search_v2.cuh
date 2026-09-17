// Search v2. Dynamically adjust memory allocation
// Created on 24-01-05

#pragma once
#include <cuda_runtime_api.h>
#include <device_launch_parameters.h>
#include <device_functions.h>
#include <stdio.h>
#include <thrust/reduce.h>
#include <stack>
#include <thrust/count.h>
#include <cuda_runtime.h>
#include "file.cuh"
#include "tree.cuh"
#include "config.cuh"
using namespace std;

// 在文件开头添加内存布局常量
#define TASK_INDEX_OFFSET 0
#define DISTANCE_OFFSET 1  
#define ENCODED_DISTANCE_OFFSET 2
#define NODE_ID_OFFSET 3
#define QUERY_ID_OFFSET 4

stack<int> st;			  // Instead of recursive calls, control the query interval of each layer (qs, qe, cur_level, qnum_up, offset_n, qs_up, size_a).
int *res;				  // The output result of range query.
float *res_dis;			  // The output result of knn query.
int qs, qe;				  // The start id and the end id of query at each process.
int *p_list;			  // The total list of queries to process for all layers.
double *p_list_k;		  // The total list of queries to process for all layers for knn queries.
int size_avg;			  // The average size of remaining levels.
int *size_list;			  // The real size of each level.
int qnum_l;				  // The number of queries that can be processed simultaneously at the current layer.
int qnum_up;			  // The number of queries that can be processed simultaneously at the upper layer.
int nnum_l;				  // The number of nodes at the current level.
int size_a;				  // The available size.
int offset_p;			  // The offset of the starting position of the p_list at current layer.
int offset_up_p;		  // The offset of the starting position of the p_list at upper layer.
int offset_n;			  // The offset of the starting position of the node_list at current layer.
int qs_up;				  // The start id of query at upper layer.
float *disk;			  // The distance to the current k-th neighbor.
bool update_disk = false; // The flag to determine whether the disk has been updated.
float input_size = 0;

// 添加内存布局优化结构体
struct MemoryLayout {
    int offset_p;
    int cur_level;
    int *size_list;
    int max_size;
    
    // 计算各种偏移量
    __device__ int getBlockSize() const {
        return size_list[cur_level] / (MAX_SIZE * 3 + 3);
    }
    
    __device__ int getDistanceOffset() const {
        return offset_p + getBlockSize() * DISTANCE_OFFSET;
    }
    
    __device__ int getTaskOffset() const {
        return offset_p + getBlockSize() * TASK_INDEX_OFFSET;
    }
    
    __device__ int getEncodedDistanceOffset() const {
        return offset_p + getBlockSize() * ENCODED_DISTANCE_OFFSET;
    }
    
    __device__ int getNodeIdOffset() const {
        return offset_p + getBlockSize() * NODE_ID_OFFSET;
    }
    
    __device__ int getQueryIdOffset() const {
        return offset_p + getBlockSize() * QUERY_ID_OFFSET;
    }
};


// 添加优化的排序内核
__global__ void optimizedSortKernel(double *p_list_k, MemoryLayout layout, int lnum)
{
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    int total_threads = gridDim.x * blockDim.x;
    
    __shared__ double shared_distances[THREAD_NUM];
    __shared__ int shared_tasks[THREAD_NUM];
    
    // 每个线程处理一个数据块
    for (int block_id = tid; block_id < lnum; block_id += total_threads) {
        int block_offset = block_id * layout.max_size;
        int distance_start = layout.getDistanceOffset();
        int task_start = layout.getTaskOffset();
        
        // 批量加载到共享内存
        if (threadIdx.x < layout.max_size) {
            shared_distances[threadIdx.x] = p_list_k[distance_start + block_offset + threadIdx.x];
            shared_tasks[threadIdx.x] = (int)p_list_k[task_start + block_offset + threadIdx.x];
        }
        __syncthreads();
        // 这里使用简单的插入排序
        for (int i = 1; i < layout.max_size; i++) {
            double key_dist = shared_distances[i];
            int key_task = shared_tasks[i];
            int j = i - 1;
            
            while (j >= 0 && shared_distances[j] > key_dist) {
                shared_distances[j + 1] = shared_distances[j];
                shared_tasks[j + 1] = shared_tasks[j];
                j--;
            }
            shared_distances[j + 1] = key_dist;
            shared_tasks[j + 1] = key_task;
        }
        __syncthreads();
        
        // 写回结果
        if (threadIdx.x < layout.max_size) {
            p_list_k[distance_start + block_offset + threadIdx.x] = shared_distances[threadIdx.x];
            p_list_k[task_start + block_offset + threadIdx.x] = shared_tasks[threadIdx.x];
        }
    }
}

// Process the nodes of the current layer and determine if the node will be pruned.
// A thread is assigned for a (query, node) pair.
__global__ void nodeProcessRnn(TN *node_list, float r, short *data_d, int *qid_list, int *data_info, int *empty_list,
							   char *data_s, int *size_s, int qnum_l, int qnum_up, int nnum_l, int *p_list, int offset_p, int offset_up_p, int offset_n,
							   int qs, int qs_up)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;

	for (int i = tid; i < nnum_l * qnum_l; i += total_num)
	{
		int qid_p = i % qnum_l;				   // Query idx in p_list
		int qid_p_up = qid_p + qs - qs_up;	   // Query idx at upper layer in p_list
		int qid = qid_p + qs;				   // Query idx in qid_lsit
		int nid_p = i / qnum_l;				   // Node idx in p_list at current level.
		int nid_parent_p = nid_p / TREE_ORDER; // Parent node idx in p_list at upper level.
		int nid = nid_p + offset_n;			   // Node idx in node_list

		// Reset p_list
		p_list[offset_p + i] = 0;

		if (p_list[offset_up_p + nid_parent_p * qnum_up + qid_p_up] == 1 && (empty_list[nid] == 0))
		{
			TN node = node_list[nid];

			float dis_q = 0;
			if (data_info[2] == 2)
			{ // L2 distance
				for (int j = 0; j < data_info[0]; j++)
				{
					dis_q += pow(data_d[node.pid * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j], 2);
				}
				dis_q = pow(dis_q, 0.5);
			}
			else if (data_info[2] == 1)
			{ // L1 distance
				for (int j = 0; j < data_info[0]; j++)
				{
					dis_q += abs(data_d[node.pid * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j]);
				}
			}
			else if (data_info[2] == 0)
			{ // Max value
				float temp = 0;
				for (int j = 0; j < data_info[0]; j++)
				{
					temp = abs(data_d[node.pid * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j]);
					if (temp > dis_q)
						dis_q = temp;
				}
			}
			else if (data_info[2] == 5)
			{
				float sa1 = 0, sa2 = 0, sa3 = 0;
				for (int j = 0; j < data_info[0]; j++)
				{
					sa1 += data_d[node.pid * data_info[0] + j] * data_d[node.pid * data_info[0] + j];
					sa2 += data_d[qid_list[qid] * data_info[0] + j] * data_d[qid_list[qid] * data_info[0] + j];
					sa3 += data_d[node.pid * data_info[0] + j] * data_d[qid_list[qid] * data_info[0] + j];
				}
				sa1 = pow(sa1, 0.5);
				sa2 = pow(sa2, 0.5);
				if (sa1 * sa2 == 0)
				{
					printf("Error!!!\n");
				}
				dis_q = sa3 / (sa1 * sa2);
				if (dis_q > 1)
				{
					dis_q = 0.99999999999999999;
				}
				dis_q = abs(acos(dis_q) * 180 / 3.1415926);
			}
			else if (data_info[2] == 6)
			{
				int n = size_s[node.pid];
				int m = size_s[qid_list[qid]];
				int table[M][M];
				if (n == 0)
					dis_q = m;
				if (m == 0)
					dis_q = n;
				if (n != 0 && m != 0)
				{
					for (int j = 0; j <= n; j++)
						table[j][0] = j;
					for (int k = 0; k <= m; k++)
						table[0][k] = k;
					for (int j = 1; j <= n; j++)
					{
						for (int k = 1; k <= m; k++)
						{
							int cost = (data_s[node.pid * M + j - 1] == data_s[qid_list[qid] * M + k - 1]) ? 0 : 1;
							table[j][k] = 1 + min(table[j - 1][k], table[j][k - 1]);
							table[j][k] = min(table[j - 1][k - 1] + cost, table[j][k]);
						}
					}
					dis_q = table[n][m];
				}
			}

			float dis_lb = node.min_dis - dis_q;
			dis_lb = max(dis_lb, 0.0);
			if (nid % TREE_ORDER != 0)
			{
				float dis_lb2 = dis_q - node_list[nid + 1].min_dis;
				dis_lb = max(dis_lb, dis_lb2);
			}

			if (dis_lb <= r)
				p_list[offset_p + i] = 1;
		}
	}
}

// Process the nodes of the current layer and determine if the node will be pruned.
// A thread is assigned for a (query, node) pair.
__global__ void nodeProcessKnn(TN *node_list, float *disk, int *empty_list, int qnum_l, int qnum_up, int nnum_l, double *p_list_k,
							   int offset_p, int offset_up_p, int offset_n, int qs, int qs_up)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;

	for (int i = tid; i < nnum_l * qnum_l; i += total_num)
	{
		int qid_p = i % qnum_l;				   // Query idx in p_list
		int qid_p_up = qid_p + qs - qs_up;	   // Query idx at upper layer in p_list
		int qid = qid_p + qs;				   // Query idx in qid_lsit
		int nid_p = (i / qnum_l);			   // The node idx in p_list at current level.
		int nid_parent_p = nid_p / TREE_ORDER; // Parent node idx in p_list at upper level.
		int nid = nid_p + offset_n;			   // Node idx in node_list
		int temp = (nnum_l / TREE_ORDER / TREE_ORDER * 3);
		int ofst_up = temp * qnum_up;				   // Offset at upper level.
		int ofst = (nnum_l / TREE_ORDER * 3) * qnum_l; // Offset at current level.
		int idx_p = nid_parent_p * qnum_l + qid_p;	   // The index of position that holds the distance between pivot and query.

		// Reset p_list 
		p_list_k[offset_p + ofst + i] = 0;
		// 父节点候选且当前节点非空
		if (p_list_k[offset_up_p + ofst_up + nid_parent_p * qnum_up + qid_p_up] == 1 && (empty_list[nid] == 0))
		{
			TN node = node_list[nid];
			// 获取查询到枢轴的距离
			float dis_q = p_list_k[offset_p + ofst / 3 + idx_p];
			// 计算下界:查询到节点内最近数据点的最小可能距离
			// 未探明的节点区域到枢轴P最小距离min_dis-查询q到枢轴距离dis_q即一个三角形中，查询q 枢轴p 任一节点构成三角形 已知两边 求第三边下届
			float dis_lb = node.min_dis - dis_q;
			dis_lb = max(dis_lb, 0.0);
			// 利用相邻节点信息进一步收紧下界
			// 如果当前节点不是父节点的第一个子节点
			if (nid % TREE_ORDER != 0)
			{
				// 利用相邻节点计算相邻下界
				float dis_lb2 = dis_q - node_list[nid + 1].min_dis;
				// 进一步收缩下界
				dis_lb = max(dis_lb, dis_lb2);
			}
			// disk[qid]是当前找到的第k个最近邻的距离 也就是上界
			if (dis_lb <= disk[qid])
				p_list_k[offset_p + ofst + i] = 1;
		}
	}
}

// Initialize p_list.
__global__ void initPList(int *p_list, int qnum)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;

	for (int i = tid; i < qnum; i += total_num)
	{
		p_list[i] = 1;
	}
}

// Initialize p_list. 所有线程同时启动，每个线程负责自己的工作
__global__ void initPListKnn(double *p_list_k, int qnum)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x; // 当前线程的全局索引
	int total_num = gridDim.x * blockDim.x; // 总线程数

	for (int i = tid; i < qnum; i += total_num) 
	{
		p_list_k[i] = 1;
	}
}

// Get counts of query.
__global__ void getQCount(int ls, int le, int *p_list, int offset_up_p, int offset_p, int qnum_up, int nnum_up)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;

	for (int i = tid; i < qnum_up * nnum_up; i += total_num)
	{
		int qid_p = i % qnum_up; // Query idx in p_list
		int nid_p = i / qnum_up; // Node idx in p_list at current level.

		if (p_list[offset_up_p + i] == 1 && qid_p >= ls && qid_p < le)
		{
			p_list[offset_p + (qid_p - ls) * nnum_up + nid_p] = 1;
		}
		else if (p_list[offset_up_p + i] == 0 && qid_p >= ls && qid_p < le)
		{
			p_list[offset_p + (qid_p - ls) * nnum_up + nid_p] = 0;
		}
	}
}

// Get counts of query for knn.
__global__ void getQCountKnn(int ls, int le, double *p_list_k, int offset_up_p, int offset_p, int qnum_up, int nnum_up)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;
	int ofst_up = (nnum_up / TREE_ORDER * 3) * qnum_up; // Offset at upper level.

	for (int i = tid; i < qnum_up * nnum_up; i += total_num)
	{
		int qid_p = i % qnum_up; // Query idx in p_list
		int nid_p = i / qnum_up; // Node idx in p_list at current level.
		// 检查上层父节点是否被标记为候选 且当前查询在范围内 ls：当前批次的起始查询索引 le：当前批次的结束查询索引
		if (p_list_k[offset_up_p + ofst_up + i] == 1 && qid_p >= ls && qid_p < le)
		{
			p_list_k[offset_p + (qid_p - ls) * nnum_up + nid_p] = 1;
		}
		else if (p_list_k[offset_up_p + ofst_up + i] == 0 && qid_p >= ls && qid_p < le)
		{
			p_list_k[offset_p + (qid_p - ls) * nnum_up + nid_p] = 0;
		}
	}
}

// Merge leaf node.
// A thread is assigned for a (query, node) pair.
__global__ void mergeLNode(int ls, int le, int *p_list, int offset_up_p, int offset_up_n, int qs_up, int offset_p, int *size_list,
						   int cur_level, int qnum_up, int nnum_up)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;

	for (int i = tid; i < qnum_up * nnum_up; i += total_num)
	{
		int qid_p = i % qnum_up;	   // Query idx in p_list
		int qid = qid_p + qs_up;	   // Query idx in qid_lsit
		int nid_p = i / qnum_up;	   // Node idx in p_list at current level.
		int nid = nid_p + offset_up_n; // Node idx in node_list

		// Merge leaf node.
		if (p_list[offset_up_p + i] == 1 && qid_p >= ls && qid_p < le)
		{
			int idx_pre = p_list[offset_p + (qid_p - ls) * nnum_up + nid_p];			  // Idx in prefix sum list
			p_list[offset_p + size_list[cur_level] / (MAX_SIZE + 3) + idx_pre] = nid;	  // Merge the real node ID in plist
			p_list[offset_p + size_list[cur_level] / (MAX_SIZE + 3) * 2 + idx_pre] = qid; // Merge the real query ID in plist
		}
	}
}

// Merge leaf nodes for knn.
// A thread is assigned for a (query, node) pair.
__global__ void mergeLNodeKnn(int ls, int le, double *p_list_k, int offset_up_p, int offset_up_n, int qs_up, int offset_p, int *size_list,
							  int cur_level, int qnum_up, int nnum_up)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;
	int ofst_up = (nnum_up / TREE_ORDER * 3) * qnum_up; // Offset at upper level.

	for (int i = tid; i < qnum_up * nnum_up; i += total_num)
	{
		int qid_p = i % qnum_up;	   // Query idx in p_list
		int qid = qid_p + qs_up;	   // Query idx in qid_lsit
		int nid_p = i / qnum_up;	   // Node idx in p_list at current level.
		int nid = nid_p + offset_up_n; // Node idx in node_list

		// Merge leaf node.
		if (p_list_k[offset_up_p + ofst_up + i] == 1 && qid_p >= ls && qid_p < le)
		{
			//  p_list_k[offset_p + (qid_p - ls) * nnum_up + nid_p]即获取(qid_p - ls) * nnum_up + nid_p该位置的前缀和
			int idx_pre = p_list_k[offset_p + (qid_p - ls) * nnum_up + nid_p];					// Idx in prefix sum list
			// p_list_k是分段结构[前缀和段] [节点ID段] [查询ID段] [其他数据段]
  								// ↑           ↑           ↑
								//offset_p   node_offset  query_offset	
			// MAX_SIZE * 3 + 3 是每个节点的内存分配单位
			// 3表示：节点ID、查询ID、其他数据各占1个单位
			// +3表示：额外的管理开销
			// 节点id段的偏移量
			p_list_k[offset_p + size_list[cur_level] / (MAX_SIZE * 3 + 3) + idx_pre] = nid;		// Merge the real node ID in plist
			// 查询id段的偏移量 
			p_list_k[offset_p + size_list[cur_level] / (MAX_SIZE * 3 + 3) * 2 + idx_pre] = qid; // Merge the real query ID in plist
		}
	}
}

// Process the nodes of the current layer and determine if the node will be pruned.
__global__ void dataProcessRnn(TN *node_list, float r, short *data_d, int *qid_list, int *data_info, char *data_s, int *size_s,
							   int *p_list, int offset_p, int *id_list, int cur_level, int *size_list, int nnum_up)
{
	int bid = blockIdx.x;
	int tid = threadIdx.x;

	int nid_p = bid;																// Node idx in p_list.
	int qid_p = bid;																// Query idx in p_list.
	int did = tid;																	// Data idx in the leaf node.
	int nid = p_list[offset_p + size_list[cur_level] / (MAX_SIZE + 3) + nid_p];		// Node idx in node_list
	int qid = p_list[offset_p + size_list[cur_level] / (MAX_SIZE + 3) * 2 + qid_p]; // Query idx in qid_lsit
	TN node = node_list[nid];														// Leaf node

	if (did < node.size && node.is_leaf == 1)
	{
		int data_id = id_list[node.lid + did]; // Data idx in dataset.
		// printf("data_id: %d\n", data_id);

		float result = 0;
		if (data_id == qid_list[qid])
		{
		}
		else if (data_info[2] == 2)
		{ // L2 distance
			for (int j = 0; j < data_info[0]; j++)
			{
				result += pow(data_d[data_id * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j], 2);
			}
			result = pow(result, 0.5);
		}
		else if (data_info[2] == 1)
		{ // L1 distance
			for (int j = 0; j < data_info[0]; j++)
			{
				result += abs(data_d[data_id * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j]);
			}
		}
		else if (data_info[2] == 0)
		{ // Max value
			float temp = 0;
			for (int j = 0; j < data_info[0]; j++)
			{
				temp = abs(data_d[data_id * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j]);
				if (temp > result)
					result = temp;
			}
		}
		else if (data_info[2] == 5)
		{
			float sa1 = 0, sa2 = 0, sa3 = 0;
			for (int j = 0; j < data_info[0]; j++)
			{
				sa1 += data_d[data_id * data_info[0] + j] * data_d[data_id * data_info[0] + j];
				sa2 += data_d[qid_list[qid] * data_info[0] + j] * data_d[qid_list[qid] * data_info[0] + j];
				sa3 += data_d[data_id * data_info[0] + j] * data_d[qid_list[qid] * data_info[0] + j];
			}
			sa1 = pow(sa1, 0.5);
			sa2 = pow(sa2, 0.5);
			if (sa1 * sa2 == 0)
			{
				printf("Error!!!\n");
			}
			result = sa3 / (sa1 * sa2);
			if (result > 1)
			{
				result = 0.99999999999999999;
			}
			result = abs(acos(result) * 180 / 3.1415926);
		}
		else if (data_info[2] == 6)
		{
			int n = size_s[data_id];
			int m = size_s[qid_list[qid]];
			int table[M][M];
			if (n == 0)
				result = m;
			if (m == 0)
				result = n;
			if (n != 0 && m != 0)
			{
				for (int j = 0; j <= n; j++)
					table[j][0] = j;
				for (int k = 0; k <= m; k++)
					table[0][k] = k;
				for (int j = 1; j <= n; j++)
				{
					for (int k = 1; k <= m; k++)
					{
						int cost = (data_s[data_id * M + j - 1] == data_s[qid_list[qid] * M + k - 1]) ? 0 : 1;
						table[j][k] = 1 + min(table[j - 1][k], table[j][k - 1]);
						table[j][k] = min(table[j - 1][k - 1] + cost, table[j][k]);
					}
				}
				result = table[n][m];
			}
		}

		if (result <= r)
		{
			// p_list[2 * offset_p - offset_up_p + 2 * lnum + i] = qid + 1;
			// atomicAdd(&res[qid], 1);
			p_list[offset_p + size_list[cur_level] / (MAX_SIZE + 3) * 3 + bid * MAX_SIZE + did] = 1;
		}
		else
			p_list[offset_p + size_list[cur_level] / (MAX_SIZE + 3) * 3 + bid * MAX_SIZE + did] = 0;
	}

	else if (did < MAX_SIZE)
	{
		p_list[offset_p + size_list[cur_level] / (MAX_SIZE + 3) * 3 + bid * MAX_SIZE + did] = 0;
	}
}

// Process the nodes of the current layer and determine if the node will be pruned.
__global__ void dataProcessKnn(TN *node_list, float *disk, short *data_d, int *qid_list, int *data_info, char *data_s, int *size_s,
							   double *p_list_k, int offset_p, int *id_list, int cur_level, int *size_list, int nnum_up)
{
	int bid = blockIdx.x;
	int tid = threadIdx.x;

	int nid_p = bid;																	  // Node idx in p_list.
	int qid_p = bid;																	  // Query idx in p_list.
	int nid = p_list_k[offset_p + size_list[cur_level] / (MAX_SIZE * 3 + 3) + nid_p];	  // Node idx in node_list
	int qid = p_list_k[offset_p + size_list[cur_level] / (MAX_SIZE * 3 + 3) * 2 + qid_p]; // Query idx in qid_lsit
	TN node = node_list[nid];															  // Leaf node

	for (int did = tid; did < MAX_SIZE; did += THREAD_NUM)
	{
		double result = INFI_DIS;
		// 数据点索引在节点范围内&当前节点是叶子节点
		if (did < node.size && node.is_leaf == 1)
		{
			// 数据点在数据集中的绝对ID=node.lid：节点在数据集中的起始位置+did：数据点在节点中的相对位置
			int data_id = id_list[node.lid + did]; // Data idx in dataset.

			result = 0;
			if (data_id == qid_list[qid])
			{
			}
			else if (data_info[2] == 2)
			{ // L2 distance
				for (int j = 0; j < data_info[0]; j++)
				{
					result += pow(data_d[data_id * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j], 2);
				}
				result = pow(result, 0.5);
			}
			else if (data_info[2] == 1)
			{ // L1 distance
				for (int j = 0; j < data_info[0]; j++)
				{
					result += abs(data_d[data_id * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j]);
				}
			}
			else if (data_info[2] == 0)
			{ // Max value
				float temp = 0;
				for (int j = 0; j < data_info[0]; j++)
				{
					temp = abs(data_d[data_id * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j]);
					if (temp > result)
						result = temp;
				}
			}
			else if (data_info[2] == 5)
			{
				float sa1 = 0, sa2 = 0, sa3 = 0;
				for (int j = 0; j < data_info[0]; j++)
				{
					sa1 += data_d[data_id * data_info[0] + j] * data_d[data_id * data_info[0] + j];
					sa2 += data_d[qid_list[qid] * data_info[0] + j] * data_d[qid_list[qid] * data_info[0] + j];
					sa3 += data_d[data_id * data_info[0] + j] * data_d[qid_list[qid] * data_info[0] + j];
				}
				sa1 = pow(sa1, 0.5);
				sa2 = pow(sa2, 0.5);
				if (sa1 * sa2 == 0)
				{
					printf("Error!!!\n");
				}
				result = sa3 / (sa1 * sa2);
				if (result > 1)
				{
					result = 0.99999999999999999;
				}
				result = abs(acos(result) * 180 / 3.1415926);
			}
			else if (data_info[2] == 6)
			{
				int n = size_s[data_id];
				int m = size_s[qid_list[qid]];
				int table[M][M];
				if (n == 0)
					result = m;
				if (m == 0)
					result = n;
				if (n != 0 && m != 0)
				{
					for (int j = 0; j <= n; j++)
						table[j][0] = j;
					for (int k = 0; k <= m; k++)
						table[0][k] = k;
					for (int j = 1; j <= n; j++)
					{
						for (int k = 1; k <= m; k++)
						{
							int cost = (data_s[data_id * M + j - 1] == data_s[qid_list[qid] * M + k - 1]) ? 0 : 1;
							table[j][k] = 1 + min(table[j - 1][k], table[j][k - 1]);
							table[j][k] = min(table[j - 1][k - 1] + cost, table[j][k]);
						}
					}
					result = table[n][m];
				}
			}

			if (result > disk[qid])
			{
				result = INFI_DIS;
			}
		}

		// Save result.
		// 任务索引存储
		p_list_k[offset_p + size_list[cur_level] / (MAX_SIZE * 3 + 3) * 3 + bid * MAX_SIZE + did] = bid * MAX_SIZE + did;
		// 距离值存储
		p_list_k[offset_p + size_list[cur_level] / (MAX_SIZE * 3 + 3) * (3 + MAX_SIZE) + bid * MAX_SIZE + did] = result;
		// 距离值编码存储
		p_list_k[offset_p + size_list[cur_level] / (MAX_SIZE * 3 + 3) * (3 + 2 * MAX_SIZE) + bid * MAX_SIZE + did] =
			double(result / INFI_DIS + qid * DIS_CODE);
	}
}

// Merge result.
__global__ void mergeResRnn(int ls, int le, int *p_list, int offset_p, int *size_list, int cur_level, int nnum_up, int lnum, int *res)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;

	for (int i = tid; i < (le - ls); i += total_num)
	{
		int s = offset_p + size_list[cur_level] / (MAX_SIZE + 3) * 3 + p_list[offset_p + i * nnum_up] * MAX_SIZE;
		int e;
		if (i < le - ls - 1)
		{
			e = offset_p + size_list[cur_level] / (MAX_SIZE + 3) * 3 + p_list[offset_p + (i + 1) * nnum_up] * MAX_SIZE;
		}
		else
		{
			e = offset_p + size_list[cur_level] / (MAX_SIZE + 3) * 3 + lnum * MAX_SIZE;
		}

		int qid = p_list[offset_p + size_list[cur_level] / (MAX_SIZE + 3) * 2 + p_list[offset_p + i * nnum_up]];
		int num = thrust::reduce(thrust::device, p_list + s, p_list + e, 0);
		res[qid] = num;
	}
}

// Merge result. K近邻结果的最终合并
__global__ void mergeResKnn(int ls, int le, double *p_list_k, int offset_p, int *size_list, int cur_level, int nnum_up, float *res_dis, int k)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;

	for (int i = tid; i < (le - ls); i += total_num)
	{
		// 查询对应的任务索引起始位置	
		int s = offset_p + size_list[cur_level] / (MAX_SIZE * 3 + 3) * 3 + p_list_k[offset_p + i * nnum_up] * MAX_SIZE;
		// 查询对应的任务索引
		int idx = p_list_k[s + k - 1];
		// 查询ID
		int idx_q = offset_p + size_list[cur_level] / (MAX_SIZE * 3 + 3) * 2 + p_list_k[offset_p + i * nnum_up];
		int qid = p_list_k[idx_q];
		// 距离值
		res_dis[qid] = p_list_k[offset_p + size_list[cur_level] / (MAX_SIZE * 3 + 3) * (3 + MAX_SIZE) + idx];
	}
}

// Initialize res.
__global__ void initResV2(int *res, int qnum)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;

	for (int i = tid; i < qnum; i += total_num)
	{
		res[i] = 0;
	}
}

// Initialize disk. disk数组记录每个查询的"当前第k近邻的距离阈值" 初始化为无穷大
__global__ void initDisK(float *disk, int qnum)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;

	for (int i = tid; i < qnum; i += total_num)
	{
		disk[i] = INFI_DIS;
	}
}

// Label child nodes without varification. 标记子节点为候选节点
__global__ void labelCNode(int *empty_list, int qnum_l, int qnum_up, int nnum_l, double *p_list_k, int offset_p, int offset_up_p, int offset_n,
						   int qs, int qs_up)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;
	int ofst = (nnum_l / TREE_ORDER * 3) * qnum_l; // Offset at current level. 
	int temp = (nnum_l / TREE_ORDER / TREE_ORDER * 3);
	int ofst_up = temp * qnum_up; // Offset at upper level.

	/*if (tid == 0) {
		printf("ofst: %d\n", ofst);
		printf("ofst_up: %d\n", ofst_up);
	}*/

	for (int i = tid; i < nnum_l * qnum_l; i += total_num)
	{
		//存储方式上来讲，二维坐标上，查询是列，节点是行，相邻线程可访问相邻内存位置
		int qid_p = i % qnum_l;				   // Query idx in p_list 查询在当前层的索引
		int qid_p_up = qid_p + qs - qs_up;	   // Query idx at upper layer in p_list 查询在上层的索引
		int nid_p = i / qnum_l;				   // Node idx in p_list at current level. 节点在当前层的索引
		int nid_parent_p = nid_p / TREE_ORDER; // Parent node idx in p_list at upper level. 父节点在上层的索引
		int nid = nid_p + offset_n;			   // Node idx in node_list 节点在node_list中的索引 

		// Reset p_list
		p_list_k[offset_p + ofst + i] = 0;
		// 两个判断条件：1. 父节点是候选节点 2. 子节点是空节点
		// 子节点继承父节点的候选状态
		if (p_list_k[offset_up_p + ofst_up + nid_parent_p * qnum_up + qid_p_up] == 1 && (empty_list[nid] == 0))
		{
			p_list_k[offset_p + ofst + i] = 1;
		}
	}
}

// Compute the distances between pivots and queries at current level.
__global__ void getDisPQ(TN *node_list, short *data_d, int *qid_list, int *data_info, int *empty_list, char *data_s,
						 int *size_s, int qnum_l, int qnum_up, int nnum_l, double *p_list_k, int offset_p, int offset_up_p, int offset_n,
						 int qs, int qs_up, int pnum_level_total)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;

	for (int i = tid; i < pnum_level_total * qnum_l; i += total_num)
	{
		int qid_p = i % qnum_l;						   // Query idx in p_list 当前层查询索引
		int qid_p_up = qid_p + qs - qs_up;			   // Query idx at upper layer in p_list
		int qid = qid_p + qs;						   // Query idx in qid_lsit 
		int nid_p = (i / qnum_l) * TREE_ORDER;		   // The first node idx in p_list at current level.
		int nid_parent_p = nid_p / TREE_ORDER;		   // Parent node idx in p_list at upper level.
		int nid = nid_p + offset_n;					   // Node idx in node_list
		int ofst = (nnum_l / TREE_ORDER * 3) * qnum_l; // Offset at current level.
		int temp = (nnum_l / TREE_ORDER / TREE_ORDER * 3);
		int ofst_up = temp * qnum_up; // Offset at upper level.

		double dis_q = INFI_DIS;

		if (p_list_k[offset_up_p + ofst_up + nid_parent_p * qnum_up + qid_p_up] == 1 && (empty_list[nid] == 0))
		{
			TN node = node_list[nid];

			dis_q = 0;
			if (data_info[2] == 2)
			{ // L2 distance
				for (int j = 0; j < data_info[0]; j++)
				{
					dis_q += pow(data_d[node.pid * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j], 2);
				}
				dis_q = pow(dis_q, 0.5);
			}
			else if (data_info[2] == 1)
			{ // L1 distance
				for (int j = 0; j < data_info[0]; j++)
				{
					dis_q += abs(data_d[node.pid * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j]);
				}
			}
			else if (data_info[2] == 0)
			{ // Max value
				float temp = 0;
				for (int j = 0; j < data_info[0]; j++)
				{
					temp = abs(data_d[node.pid * data_info[0] + j] - data_d[qid_list[qid] * data_info[0] + j]);
					if (temp > dis_q)
						dis_q = temp;
				}
			}
			else if (data_info[2] == 5)
			{
				float sa1 = 0, sa2 = 0, sa3 = 0;
				for (int j = 0; j < data_info[0]; j++)
				{
					sa1 += data_d[node.pid * data_info[0] + j] * data_d[node.pid * data_info[0] + j];
					sa2 += data_d[qid_list[qid] * data_info[0] + j] * data_d[qid_list[qid] * data_info[0] + j];
					sa3 += data_d[node.pid * data_info[0] + j] * data_d[qid_list[qid] * data_info[0] + j];
				}
				sa1 = pow(sa1, 0.5);
				sa2 = pow(sa2, 0.5);
				if (sa1 * sa2 == 0)
				{
					printf("Error!!!\n");
				}
				dis_q = sa3 / (sa1 * sa2);
				if (dis_q > 1)
				{
					dis_q = 0.99999999999999999;
				}
				dis_q = abs(acos(dis_q) * 180 / 3.1415926);
			}
			else if (data_info[2] == 6)
			{
				int n = size_s[node.pid];
				int m = size_s[qid_list[qid]];
				int table[M][M];
				if (n == 0)
					dis_q = m;
				if (m == 0)
					dis_q = n;
				if (n != 0 && m != 0)
				{
					for (int j = 0; j <= n; j++)
						table[j][0] = j;
					for (int k = 0; k <= m; k++)
						table[0][k] = k;
					for (int j = 1; j <= n; j++)
					{
						for (int k = 1; k <= m; k++)
						{
							int cost = (data_s[node.pid * M + j - 1] == data_s[qid_list[qid] * M + k - 1]) ? 0 : 1;
							table[j][k] = 1 + min(table[j - 1][k], table[j][k - 1]);
							table[j][k] = min(table[j - 1][k - 1] + cost, table[j][k]);
						}
					}
					dis_q = table[n][m];
				}
			}
		}

		// Save result. 将结果保存到p_list_k缓冲区的不同段
		p_list_k[offset_p + i] = i; // 任务索引
		p_list_k[offset_p + ofst / 3 + i] = dis_q; // 原始距离值
		// 将距离归一化到[0,1]范围 ； 添加查询索引信息，用于高效排序
		p_list_k[offset_p + ofst / 3 * 2 + i] = double(dis_q / INFI_DIS + qid_p * DIS_CODE); // 编码距离
	}
}

// Update disk. 更新每个查询的k近邻距离阈值，用于后续的剪枝
__global__ void updateDisK(int qnum_l, double *p_list_k, float *disk, int nnum_l, int offset_p, int qs, int k)
{
	int tid = blockDim.x * blockIdx.x + threadIdx.x;
	int total_num = gridDim.x * blockDim.x;
	int ofst = (nnum_l / TREE_ORDER * 3) * qnum_l; // Offset at current level.

	for (int i = tid; i < qnum_l; i += total_num)
	{
		int qid_p = i;		  // Query idx in p_list
		int qid = qid_p + qs; // Query idx in qid_lsit
		// float dis = INFI_DIS / INFI_DIS + qid_p * DIS_CODE;
		/*float* address = thrust::find(thrust::device, p_list_k + offset_p + ofst / 3 * 2 + nnum_l / TREE_ORDER * qid_p,
			p_list_k + offset_p + ofst / 3 * 2 + nnum_l / TREE_ORDER * (qid_p + 1), dis);
		int idx = address - (p_list_k + offset_p + ofst / 3 * 2 + nnum_l / TREE_ORDER * qid_p);*/
		// offset_p 是基础偏移； nnum_l / TREE_ORDER * qid_p 是查询偏移  k - 1是第k小的索引
		int idx = p_list_k[offset_p + nnum_l / TREE_ORDER * qid_p + k - 1];
		// 通过比较与k-1的距离值来更新
		if (disk[qid] > p_list_k[offset_p + ofst / 3 + idx])
		{
			disk[qid] = p_list_k[offset_p + ofst / 3 + idx];
			// printf("disk[qid]: %f, qid: %d\n", disk[qid], qid);
		}
	} 
}

// Range query
void searchIndexRnnV2(short *data_d, TN *node_list, int *id_list, int *max_node_num, int *qid_list,
					  int qnum, float r, int tree_h, int *data_info, int *empty_list, char *data_s, int *size_s)
{
	cout << "Searching..." << endl;

	CHECK(cudaMallocManaged((void **)&res, qnum * sizeof(int)));
	CHECK(cudaMallocManaged((void **)&size_list, (tree_h + 1) * sizeof(int)));

	// Get GPU available memory.
	size_t avail;
	size_t total;
	cudaMemGetInfo(&avail, &total);
	// if (input_size <= 0 || input_size > avail) {
	// 	printf("Out of memory !!!\n");
	// 	return;
	// }
	// cout << "avail: " << avail << endl;
	// cout << "input: " << input_size << endl;
	// avail = input_size;
	avail = avail / 2; // Allocate storage space as a half of available space.
	// cout << "avail: " << avail << endl;
	// cout << "total: " << total << endl;

	// Allocate memory
	// 计算可以分配多少个整数的存储空间，用作内存分配的容量控制
	size_a = avail / sizeof(int); // Get the total int num.
	CHECK(cudaMalloc((void **)&p_list, size_a * sizeof(int)));// p_list 即工作缓冲区 被分段使用，存储不同类型的数据：
	// 包括以下四种
	// - 候选节点ID
	// - 距离值  
	// - 查询索引
	// - 临时计算结果
	// cout << "size_a: " << size_a << endl;

	// Initialize the query information
	// 在 GPU 设备内存中设置内存块的值 参数：指针地址 设定值（0-255之间）
	CHECK(cudaMemset(size_list, 0, (tree_h + 1) * sizeof(int)));
	CHECK(cudaMemset(p_list, 0, size_a * sizeof(int)));
	// 根节点（第0层）的节点数量设置为 qnum
	size_list[0] = qnum;
	// 从总可用大小 size_a 中减去根节点占用的数量
	size_a -= qnum;
	// 计算平均大小
	size_avg = size_a / tree_h;

	nnum_l = TREE_ORDER;
	qnum_l = min(size_avg / nnum_l, qnum);
	size_a -= qnum_l * nnum_l;
	size_list[1] = qnum_l * nnum_l;
	for (int i = 0; i < qnum; i += qnum_l)
	{
		int end = min(i + qnum_l - 1, qnum - 1);
		st.push(i);
		st.push(end);
		st.push(1);
		st.push(qnum);
		st.push(1);
		st.push(0);
		st.push(size_a);
	}
	initPList<<<(qnum + THREAD_NUM - 1) / THREAD_NUM, THREAD_NUM>>>(p_list, qnum);
	cudaDeviceSynchronize();
	cudaError_t cudaStatus = cudaGetLastError();
	if (cudaStatus != cudaSuccess)
		fprintf(stderr, "initPlist error: %s\n", cudaGetErrorString(cudaStatus));
	/*initResV2 << < (qnum + THREAD_NUM - 1) / THREAD_NUM, THREAD_NUM >> > (res, qnum);
	cudaDeviceSynchronize();
	cudaStatus = cudaGetLastError();
	if (cudaStatus != cudaSuccess) fprintf(stderr, "initRes error: %s\n", cudaGetErrorString(cudaStatus));*/

	// Range query
	while (!st.empty())
	{
		// Get the preparation information for queries
		size_a = st.top();
		st.pop();
		qs_up = st.top();
		st.pop();
		offset_n = st.top();
		st.pop();
		qnum_up = st.top();
		st.pop();
		cur_level = st.top();
		st.pop();
		qe = st.top();
		st.pop();
		qs = st.top();
		st.pop();
		qnum_l = qe - qs + 1;
		offset_p = thrust::reduce(thrust::device, size_list, size_list + cur_level, 0);
		offset_up_p = offset_p - size_list[cur_level - 1];
		nnum_l = pow(TREE_ORDER, cur_level);
		int block_num = (qnum_l * nnum_l + THREAD_NUM - 1) / THREAD_NUM;

		// Evaluating
		if (cur_level < tree_h)
		{ // Processing node.
			nodeProcessRnn<<<block_num, THREAD_NUM>>>(node_list, r, data_d, qid_list, data_info, empty_list, data_s,
													  size_s, qnum_l, qnum_up, nnum_l, p_list, offset_p, offset_up_p, offset_n, qs, qs_up);
			cudaDeviceSynchronize();
			cudaStatus = cudaGetLastError();
			if (cudaStatus != cudaSuccess)
				fprintf(stderr, "nodeProcessRnn error: %s\n", cudaGetErrorString(cudaStatus));
		}
		else
		{ // Processing data in leaf node.
			// Get query information.
			int ls = qs;
			int le = qe;
			int offset_up_n = offset_n;
			int nnum_up = pow(TREE_ORDER, cur_level - 1);

			// Get counts of query.
			block_num = (qnum_up * nnum_up + THREAD_NUM - 1) / THREAD_NUM;
			getQCount<<<block_num, THREAD_NUM>>>(ls, le, p_list, offset_up_p, offset_p, qnum_up, nnum_up);
			cudaDeviceSynchronize();
			cudaStatus = cudaGetLastError();
			if (cudaStatus != cudaSuccess)
				fprintf(stderr, "getQCount error: %s\n", cudaGetErrorString(cudaStatus));

			// Gets the prefix sum of p_list at leaf node layer.
			int lnum = thrust::reduce(thrust::device, p_list + offset_p, p_list + offset_p + (le - ls) * nnum_up, 0);
			thrust::exclusive_scan(thrust::device, p_list + offset_p, p_list + offset_p + (le - ls) * nnum_up,
								   p_list + offset_p);

			// Merge leaf node.
			mergeLNode<<<block_num, THREAD_NUM>>>(ls, le, p_list, offset_up_p, offset_up_n, qs_up, offset_p, size_list,
												  cur_level, qnum_up, nnum_up);
			cudaDeviceSynchronize();
			cudaStatus = cudaGetLastError();
			if (cudaStatus != cudaSuccess)
				fprintf(stderr, "mergeLNode error: %s\n", cudaGetErrorString(cudaStatus));

			// Processing data in leaf node.
			block_num = lnum;
			// printf("lnum: %d\n", block_num);

			dataProcessRnn<<<block_num, THREAD_NUM>>>(node_list, r, data_d, qid_list, data_info, data_s, size_s, p_list,
													  offset_p, id_list, cur_level, size_list, nnum_up);
			cudaDeviceSynchronize();
			cudaStatus = cudaGetLastError();
			if (cudaStatus != cudaSuccess)
				fprintf(stderr, "dataProcessRnn error: %s\n", cudaGetErrorString(cudaStatus));

			// Merge result.
			block_num = (le - ls + THREAD_NUM - 1) / THREAD_NUM;
			mergeResRnn<<<block_num, THREAD_NUM>>>(ls, le, p_list, offset_p, size_list, cur_level, nnum_up, lnum, res);
			cudaDeviceSynchronize();
			cudaStatus = cudaGetLastError();
			if (cudaStatus != cudaSuccess)
				fprintf(stderr, "mergeResRnn error: %s\n", cudaGetErrorString(cudaStatus));
		}

		// Update the query and storage space information and of lower layer.
		if (cur_level < tree_h)
		{
			int cur_level_low = cur_level + 1;
			int size_avg_low = size_a / (tree_h - cur_level);
			int offset_n_low = offset_n + nnum_l;

			if (cur_level_low < tree_h)
			{ // The lower layer evaluates the entire nodes.
				// Update the query and storage space information and of lower layer.
				int nnum_l_low = pow(TREE_ORDER, cur_level_low);
				int qnum_l_low = min(size_avg_low / nnum_l_low, size_list[cur_level] / nnum_l);
				size_list[cur_level_low] = qnum_l_low * nnum_l_low;
				for (int i = 0; i < qnum_l; i += qnum_l_low)
				{
					int end = min(i + qs + qnum_l_low - 1, qe);
					st.push(i + qs);
					st.push(end);
					st.push(cur_level_low);
					st.push(qnum_l);
					st.push(offset_n_low);
					st.push(qs);
					st.push(size_a - size_list[cur_level_low]);
				}
			}
			else
			{ // The lower layer evaluates the data in leaf nodes.
				// Update the query and storage space informationand of lower layer.
				unsigned long size_l = min((unsigned long)size_avg_low / (MAX_SIZE + 3), (unsigned long)size_list[cur_level]);
				size_list[cur_level_low] = size_l * (MAX_SIZE + 3);
				// printf("size_l: %d, MAX_SIZE: %d,  nnum_l: %d", size_l, MAX_SIZE, nnum_l);
				unsigned long qnum_l_low = size_l / (nnum_l);
				printf("qnum_l_low: %d\n", qnum_l_low);
				for (int i = 0; i < qnum_l; i += qnum_l_low)
				{
					int end = min((int)(i + qnum_l_low), qnum_l);
					st.push(i);
					st.push(end);
					st.push(cur_level_low);
					st.push(qnum_l);
					st.push(offset_n);
					st.push(qs);
					st.push(size_a - size_list[cur_level_low]);
				}
			}
		}
	}
	size_t total_memory = qnum * sizeof(int) + (tree_h + 1) * sizeof(int) + size_a * sizeof(int);
	printf("Total memory of Range query_RNN_v2: %f MB\n", total_memory / 1024.0 / 1024.0);
	// Release memory
	cudaFree(p_list);
	cudaFree(size_list);
}

// knn query
void searchIndexKnnV2(short *data_d, TN *node_list, int *id_list, int *max_node_num, int *qid_list,
					  int qnum, int k, int tree_h, int *data_info, int *empty_list, char *data_s, int *size_s)
{   /*
    qnum: 查询数量
    k: 最近邻数量
    tree_h: 树的高度
    data_info: 数据信息
    empty_list: 空列表
    data_s: 数据大小
    size_s: 数据大小
*/
	cout << "Searching..." << endl;

	CHECK(cudaMallocManaged((void **)&res_dis, qnum * sizeof(float)));
	CHECK(cudaMallocManaged((void **)&size_list, (tree_h + 1) * sizeof(int)));
	CHECK(cudaMalloc((void **)&disk, qnum * sizeof(float)));

	// Get GPU available memory.
	size_t avail;
	size_t total;
	cudaMemGetInfo(&avail, &total);
	// if (input_size <= 0 || input_size > avail) {
	// 	printf("Out of memory !!!\n");
	// 	return;
	// }
	// cout << "avail: " << avail << endl;
	// cout << "input: " << input_size << endl;
	// avail = input_size;
	// 获取GPU可用内存并分配一半作为工作空间 不去对比out of GPU memory
	avail = avail / 2; // Allocate storage space as a half of available space.
	// cout << "avail: " << avail << endl;
	// cout << "total: " << total << endl;

	// Allocate memory
	size_a = avail / (sizeof(double)); // Get the total num.
	CHECK(cudaMalloc((void **)&p_list_k, size_a * sizeof(double)));
	// CHECK(cudaMalloc((void**)&p_list_dis, size_a * sizeof(float)));
	// CHECK(cudaMalloc((void**)&p_list_disc, size_a * sizeof(float)));
	// cout << "size_a: " << size_a << endl;

	// Initialize the query information
	CHECK(cudaMemset(size_list, 0, (tree_h + 1) * sizeof(int)));
	// CHECK(cudaMemset(p_list, 0, size_a * sizeof(int)));
	// 设置根节点数量为 qnum 查询数量 开始阶段根节点的节点数是最多的，后续分给子节点
	size_list[0] = qnum;
	//  从总可用大小 size_a 中减去根节点占用的数量
	size_a -= qnum;
	// 计算每层的查询批次大小和节点数量 一次并行查询的节点数量
	size_avg = size_a / tree_h;
	// 设置本层节点数量为树的阶数
	nnum_l = TREE_ORDER;
	// 计算每层的查询批次大小 TREE_ORDER * 3是 节点ID（或索引）、距离值、距离编码 存储三份数据用到的额外空间
	// 一个是允许查询的节点数量，一个是外部指令的查询数量，比较哪个更小，这是一种现实查询节点数情况
	qnum_l = min(size_avg / (nnum_l + nnum_l / TREE_ORDER * 3), qnum);
	// 这里算出现实允许的节点数，并计算本身和数轴映射的空间，再用总空间减去得到剩余空间
	size_a -= qnum_l * (nnum_l + nnum_l / TREE_ORDER);
	size_list[1] = qnum_l * (nnum_l + nnum_l / TREE_ORDER);
	for (int i = 0; i < qnum; i += qnum_l)
	{
		int end = min(i + qnum_l - 1, qnum - 1);
		st.push(i);   // 查询起始索引 
		st.push(end); // 查询结束索引  这一批的结束索引
		st.push(1);   // 当前层级（从1开始，根节点是0）
		st.push(qnum);  // 上层查询数量
		st.push(1);  // 上层节点偏移
		st.push(0);    // 起始查询索引
		st.push(size_a);   // 可用存储空间
	}
	// p_list_k是记录每个查询状态的辅助数组。 初始化p_list_k
	// 核函数参数左边是线程块数，右边是线程数，后面是实参
	initPListKnn<<<(qnum + THREAD_NUM - 1) / THREAD_NUM, THREAD_NUM>>>(p_list_k, qnum);
	cudaDeviceSynchronize();
	cudaError_t cudaStatus = cudaGetLastError();
	if (cudaStatus != cudaSuccess)
		fprintf(stderr, "initPlist error: %s\n", cudaGetErrorString(cudaStatus));

	// 初始化disk ：disk数组记录每个查询的"当前第k近邻的距离阈值" 初始化为无穷大
	initDisK<<<(qnum + THREAD_NUM - 1) / THREAD_NUM, THREAD_NUM>>>(disk, qnum);
	cudaDeviceSynchronize();
	cudaStatus = cudaGetLastError();
	if (cudaStatus != cudaSuccess)
		fprintf(stderr, "initDisk error: %s\n", cudaGetErrorString(cudaStatus));

	// knn query
	while (!st.empty())
	{
		// Get the preparation information for queries
		size_a = st.top(); // 本批次可用的存储空间
		st.pop();
		qs_up = st.top(); // 上一层（父层）查询的起始索引
		st.pop();
		offset_n = st.top(); // 本层节点在node_list中的起始偏移
		st.pop();
		qnum_up = st.top(); // 上一层（父层）查询数量
		st.pop();
		cur_level = st.top(); // 当前层级
		st.pop();
		qe = st.top(); // 本批次查询的结束索引
		st.pop();
		qs = st.top(); // 本批次查询的起始索引
		st.pop();
		qnum_l = qe - qs + 1; // 本批次查询数量
		// 并行累加（归约）函数  thrust::device代表是GPU上操作
		// offset_p 本层分区的起点  size_list 本层分区数量  cur_level 当前层级
		offset_p = thrust::reduce(thrust::device, size_list, size_list + cur_level, 0);
		offset_up_p = offset_p - size_list[cur_level - 1]; // 上一层分区的起始偏移量
		nnum_l = pow(TREE_ORDER, cur_level); // 本层节点总数 树的阶数^当前层级
		// 所有可能得查询-节点对任务分配 每个线程块处理一个查询-节点对
		int block_num = (qnum_l * nnum_l + THREAD_NUM - 1) / THREAD_NUM; // 线程块数

		// Evaluating 非叶子节点
		if (cur_level < tree_h)
		{ // Processing node.
			// 有效节点数量 有效节点数量 = 本层节点总数 - 空节点数量
			// 空节点数量= 本层节点的empty_list加和，空节点是1，非空节点是0，因此reduce函数求和的值就是空节点数量
			int pnum_level = nnum_l - thrust::reduce(thrust::device, empty_list + start_idx, empty_list + start_idx + nnum_l, 0);
			// 有效pivot数量（不包括空节点） 有效节点数量除以树的阶数（每TREE_ORDER个节点共用一个pivot（父节点））
			pnum_level = pnum_level / TREE_ORDER;
			// printf("pnum level: %d\n", pnum_level);
			// 全部节点（包括空节点）的枢轴数量
			int pnum_level_total = nnum_l / TREE_ORDER;
			// printf("pnum level total: %d\n", pnum_level_total);
			// 开始阶段没有更新距离 update_disk就是false；
			// k 是输入的需要查询的最近邻数量，早期阶段如果pivot数量少于k，说明候选节点不多，不需要严格剪枝
			if (update_disk == false && (pnum_level < k || cur_level <= 2))
			{
				// 标记候选节点
				labelCNode<<<block_num, THREAD_NUM>>>(empty_list, qnum_l, qnum_up, nnum_l, p_list_k, offset_p, offset_up_p, offset_n, qs, qs_up);
				cudaDeviceSynchronize();
				cudaStatus = cudaGetLastError();
				if (cudaStatus != cudaSuccess)
					fprintf(stderr, "labelCNode error: %s\n", cudaGetErrorString(cudaStatus));
			}
			else // 严格剪枝
			{
				update_disk = true;

				if (pnum_level >= k)
				{
					// Compute the distances between pivots and queries at current level.
					block_num = (pnum_level_total * qnum_l + THREAD_NUM - 1) / THREAD_NUM;
					// 根据距离类别，计算距离并更新最近邻
					getDisPQ<<<block_num, THREAD_NUM>>>(node_list, data_d, qid_list, data_info, empty_list, data_s, size_s, qnum_l,
														qnum_up, nnum_l, p_list_k, offset_p, offset_up_p, offset_n, qs, qs_up, pnum_level_total);
					cudaDeviceSynchronize();
					cudaStatus = cudaGetLastError();
					if (cudaStatus != cudaSuccess)
						fprintf(stderr, "getDisPQ error: %s\n", cudaGetErrorString(cudaStatus));

					// Sort by distances.
					int ofst = (nnum_l / TREE_ORDER * 3) * qnum_l; // Offset at current level.
					// 按距离排序 - 使用优化的排序函数替代thrust排序
					/*
					thrust::sort_by_key(thrust::device, p_list_k + offset_p + ofst / 3 * 2,
										p_list_k + offset_p + ofst / 3 * 2 + pnum_level_total * qnum_l, p_list_k + offset_p);
					cudaStatus = cudaGetLastError();
					if (cudaStatus != cudaSuccess)
						fprintf(stderr, "sort_by_key error: %s\n", cudaGetErrorString(cudaStatus));
					*/
					
					// 使用优化的排序函数 - 使用更高级的optimizedSortKernel
					int block_num_sort = (pnum_level_total * qnum_l + THREAD_NUM - 1) / THREAD_NUM;
					MemoryLayout layout;
					layout.offset_p = offset_p;
					layout.cur_level = cur_level;
					layout.size_list = size_list;
					layout.max_size = MAX_SIZE;
					optimizedSortKernel<<<block_num_sort, THREAD_NUM>>>(p_list_k, layout, pnum_level_total * qnum_l);
					cudaDeviceSynchronize();
					cudaStatus = cudaGetLastError();
					if (cudaStatus != cudaSuccess)
						fprintf(stderr, "optimizedSortKernel error: %s\n", cudaGetErrorString(cudaStatus));

					// Update disk.
					// 更新距离阈值 按照每个查询更新一次距离阈值，所以只需要qnum_l块
					updateDisK<<<(qnum_l + THREAD_NUM - 1) / THREAD_NUM, THREAD_NUM>>>(qnum_l, p_list_k, disk, nnum_l, offset_p, qs, k);
					cudaDeviceSynchronize();
					cudaStatus = cudaGetLastError();
					if (cudaStatus != cudaSuccess)
						fprintf(stderr, "updateDisK error: %s\n", cudaGetErrorString(cudaStatus));
				}

				// Process the nodes of the current layer and determine if the node will be pruned.
				block_num = (nnum_l * qnum_l + THREAD_NUM - 1) / THREAD_NUM;
				 // 处理节点剪枝
				nodeProcessKnn<<<block_num, THREAD_NUM>>>(node_list, disk, empty_list, qnum_l, qnum_up, nnum_l, p_list_k, offset_p,
														  offset_up_p, offset_n, qs, qs_up);
				cudaDeviceSynchronize();
				cudaStatus = cudaGetLastError();
				if (cudaStatus != cudaSuccess)
					fprintf(stderr, "nodeProcessKnn error: %s\n", cudaGetErrorString(cudaStatus));
			}
		}
		else
		{ // Processing data in leaf node.
			// Get query information.
			int ls = qs;
			int le = qe;
			int offset_up_n = offset_n;
			int nnum_up = pow(TREE_ORDER, cur_level - 1);

			// Get counts of query.
			block_num = (qnum_up * nnum_up + THREAD_NUM - 1) / THREAD_NUM;
			// 处理叶子节点中的数据点
			getQCountKnn<<<block_num, THREAD_NUM>>>(ls, le, p_list_k, offset_up_p, offset_p, qnum_up, nnum_up);
			cudaDeviceSynchronize();
			cudaStatus = cudaGetLastError();
			if (cudaStatus != cudaSuccess)
				fprintf(stderr, "getQCountKnn error: %s\n", cudaGetErrorString(cudaStatus));

			// Gets the prefix sum of p_list at leaf node layer.
			// 累加求和
			int lnum = thrust::reduce(thrust::device, p_list_k + offset_p, p_list_k + offset_p + (le - ls) * nnum_up, 0);
			// 前缀和：把前面元素的索引加和作为当下元素的索引
			thrust::exclusive_scan(thrust::device, p_list_k + offset_p, p_list_k + offset_p + (le - ls) * nnum_up,
								   p_list_k + offset_p);
			// printf("lnum: %d\n", lnum);

			// Merge leaf node. 存储列表进行前缀和
			mergeLNodeKnn<<<block_num, THREAD_NUM>>>(ls, le, p_list_k, offset_up_p, offset_up_n, qs_up, offset_p, size_list,
													 cur_level, qnum_up, nnum_up);
			cudaDeviceSynchronize();
			cudaStatus = cudaGetLastError();
			if (cudaStatus != cudaSuccess)
				fprintf(stderr, "mergeLNodeKnn error: %s\n", cudaGetErrorString(cudaStatus));

			// Processing data in leaf node.
			block_num = lnum;
			// 给出查询距离
			dataProcessKnn<<<block_num, THREAD_NUM>>>(node_list, disk, data_d, qid_list, data_info, data_s, size_s, p_list_k,
													  offset_p, id_list, cur_level, size_list, nnum_up);
			cudaDeviceSynchronize();
			cudaStatus = cudaGetLastError();
			if (cudaStatus != cudaSuccess)
				fprintf(stderr, "dataProcessKnn error: %s\n", cudaGetErrorString(cudaStatus));

			// Sort by distances.
			// 排序并合并最终结果 - 使用更高级的optimizedSortKernel
			int block_num_sort = (lnum + THREAD_NUM - 1) / THREAD_NUM;
			MemoryLayout layout;
			layout.offset_p = offset_p;
			layout.cur_level = cur_level;
			layout.size_list = size_list;
			layout.max_size = MAX_SIZE;
			optimizedSortKernel<<<block_num_sort, THREAD_NUM>>>(p_list_k, layout, lnum);
			cudaDeviceSynchronize();
			cudaStatus = cudaGetLastError();
			if (cudaStatus != cudaSuccess)
				fprintf(stderr, "optimizedSortKernel error: %s\n", cudaGetErrorString(cudaStatus));

			// Merge result.
			block_num = (le - ls + THREAD_NUM - 1) / THREAD_NUM;
			mergeResKnn<<<block_num, THREAD_NUM>>>(ls, le, p_list_k, offset_p, size_list, cur_level, nnum_up, res_dis, k);
			cudaDeviceSynchronize();
			cudaStatus = cudaGetLastError();
			if (cudaStatus != cudaSuccess)
				fprintf(stderr, "mergeResKnn error: %s\n", cudaGetErrorString(cudaStatus));
		}

		// Update the query and storage space information and of lower layer. 更新查询和存储空间信息以及下层
		if (cur_level < tree_h)
		{
			// 下一层级的编号 
			int cur_level_low = cur_level + 1;
			// 本层级平均可用内存
			int size_avg_low = size_a / (tree_h - cur_level);
			// 下一层节点在node_list中的起始偏移
			int offset_n_low = offset_n + nnum_l;

			if (cur_level_low < tree_h)
			{ // The lower layer evaluates the entire nodes.
				// Update the query and storage space information and of lower layer. 
				// 下一层节点总数
				int nnum_l_low = pow(TREE_ORDER, cur_level_low);
				// 下一层查询数量 在内存限制和上批次查询数量之间取最小值 查询是固定的输入数据，下层的查询必须来自上层
				int qnum_l_low = min(size_avg_low / (nnum_l_low + nnum_l_low / TREE_ORDER * 3), qnum_up);
				// 为下一层级分配存储空间  查询数量*（节点总数+枢轴数量）
				size_list[cur_level_low] = qnum_l_low * (nnum_l_low + nnum_l_low / TREE_ORDER * 3);
				for (int i = 0; i < qnum_l; i += qnum_l_low)
				{
					//子批次边界计算
					int end = min(i + qs + qnum_l_low - 1, qe);
					st.push(i + qs);  // 子批次查询起始索引
					st.push(end); // 子批次查询结束索引
					st.push(cur_level_low); // 下一层级编号
					st.push(qnum_l); // 上层查询数量
					st.push(offset_n_low); // 下一层节点在node_list中的起始偏移
					st.push(qs); // 上批次查询的起始索引
					st.push(size_a - size_list[cur_level_low]); // 本批次可用存储空间
				}
			}
			else
			{ // The lower layer evaluates the data in leaf nodes.
				// Update the query and storage space informationand of lower layer.
				// 计算叶子节点层可以处理的数据块数量
				unsigned long size_l = min((unsigned long)size_avg_low / (MAX_SIZE * 3 + 3), (unsigned long)qnum_l * nnum_l);
				size_list[cur_level_low] = size_l * (MAX_SIZE * 3 + 3);
				// printf("size_l: %d, MAX_SIZE: %d,  nnum_l: %d\n", size_l, MAX_SIZE, nnum_l);
				// 计算查询批次大小
				unsigned long qnum_l_low = size_l / (nnum_l);
				printf("qnum_l_low: %d\n", qnum_l_low);
				for (int i = 0; i < qnum_l; i += qnum_l_low)
				{
					int end = min((int)(i + qnum_l_low), qnum_l);
					st.push(i);  // 这里不需要qs 是因为叶子节点 直接处理当前层级的查询
					st.push(end); 
					st.push(cur_level_low); // 叶子节点层级编号
					st.push(qnum_l); // 上层查询数量
					st.push(offset_n); // 本层节点在node_list中的起始偏移
					st.push(qs); // 上批次查询的起始索引
					st.push(size_a - size_list[cur_level_low]); // 本批次可用存储空间
				}
			}
		}
	}
	size_t total_memory = qnum * sizeof(float) + (tree_h + 1) * sizeof(int) + qnum * sizeof(float) + size_a * sizeof(double);
	printf("Total memory of knn query_v2: %f MB\n", total_memory / 1024.0 / 1024.0);
	// Release memory
	cudaFree(p_list_k);
	cudaFree(size_list);
	cudaFree(disk);
}


