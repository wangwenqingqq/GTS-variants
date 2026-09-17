// File operations
// Created on 24-01-05

#pragma once
#include <cuda_runtime_api.h>
#include <device_launch_parameters.h>
#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <fstream>
#include <stdio.h>
#include "config.cuh"
using namespace std;
#define M 128

// Split the line
void split(const string str, vector<string> &res, const char pattern)
{
	istringstream is(str);
	string temp;
	while (getline(is, temp, pattern))
		res.push_back(temp);
	return;
}

// Load data file
void load(char *file, int *&data_info, short *&data_d, char *&data_s, int *&size_s)
{
	ifstream in(file);
	if (!in.is_open())
	{
		std::cout << "open file error" << std::endl;
		exit(-1);
	}


	string line;
	int i = 0;
	int j = 0;
	vector<string> res;
	if (cudaMallocManaged((void **)&data_info, 3 * sizeof(int)) != cudaSuccess) {
		std::cout << "Memory allocation for data_info failed." << std::endl;
		exit(-1);
	}
	// Load the file
	while (getline(in, line))
	{
		if (i == 0)
		{ // Load the first line
			split(line, res, ' ');
			for (auto r : res)
			{
				stringstream ss(r);
				int number;
				ss >> number;

				if (j == 0)
					data_info[j] = number;
				if (j == 1)
					data_info[j] = number;
				if (j == 2)
					data_info[j] = number;

				j++;
			}
			// 输出 data_info 的值进行检查
			std::cout << "data_info[0]: " << data_info[0] << ", data_info[1]: " << data_info[1] << ", data_info[2]: " << data_info[2] << std::endl;
			// Allocate memory
			if (data_info[2] != 6)
			{
				if (cudaMallocManaged((void **)&data_d, data_info[1] * data_info[0] * sizeof(short)) != cudaSuccess) {
                    std::cout << "Memory allocation for data_d failed." << std::endl;
                    exit(-1);
                }
			}
			else
			{
				if (cudaMallocManaged((void **)&data_s, data_info[1] * M * sizeof(char)) != cudaSuccess) {
                    std::cout << "Memory allocation for data_s failed." << std::endl;
                    exit(-1);
                }
                if (cudaMallocManaged((void **)&size_s, data_info[1] * sizeof(int)) != cudaSuccess) {
                    std::cout << "Memory allocation for size_s failed." << std::endl;
                    exit(-1);
                }
			}
		}
		else
		{ // Load data
			j = 0;
			if (data_info[2] != 6)
			{ // float
				split(line, res, ' ');
				if (res.size() != data_info[0]) {
					std::cout << "Unexpected number of columns in line " << i << std::endl;
					exit(-1);
				}
				for (auto r : res)
				{
					stringstream ss(r);
					float number;
					ss >> number;

					if ((i - 1) * data_info[0] + j < data_info[1] * data_info[0]) {
						*(data_d + (i - 1) * data_info[0] + j) = number;
					} else {
						std::cout << "Array index out of bounds." << std::endl;
						exit(-1);
					}

					j++;
				}
			}
			else
			{ // string
				const char *temp = line.data();
				if (strlen(temp) > M) {
					std::cout << "String length exceeds buffer size." << std::endl;
					exit(-1);
				}
				memcpy(data_s + (i - 1) * M, temp, strlen(temp));
				size_s[i - 1] = strlen(temp);
			}
		}
		res.clear();
		j = 0;
		i++;
	}
	in.close();
}

// Load query file
void loadQuery(char *file, int *&qid, int &qnum)
{
	ifstream in(file);
	if (!in.is_open())
	{
		std::cout << "open file error" << std::endl;
		exit(-1);
	}

	cout << "Loading query file..." << endl;

	string line;
	int i = 0;

	// load the file
	while (getline(in, line))
	{
		if (i == 0)
		{ // load the first line
			stringstream ss(line);
			int number;
			ss >> number;

			cudaMallocManaged((void **)&qid, number * sizeof(int));
			qnum = number;
		}
		else
		{ // load query id
			stringstream ss(line);
			int number;
			ss >> number;

			qid[i - 1] = number;
		}

		i++;
	}

	in.close();
}

// Save result file for knn
void saveK(char *filenamer, char *filenamed, int *res_id, float *dis, int k, int qnum)
{
	FILE *resr = fopen(filenamer, "w");
	FILE *resd = fopen(filenamed, "w");

	for (unsigned i = 0; i < qnum; i++)
	{
		for (unsigned j = 0; j < k; j++)
		{
			fprintf(resr, "%d ", res_id[i * k + j]);
			fflush(resr);
			fprintf(resd, "%f ", dis[i * k + j]);
			fflush(resd);
		}
		fprintf(resr, "\n");
		fflush(resr);
		fprintf(resd, "\n");
		fflush(resd);
	}
	fclose(resr);
	fclose(resd);
}

// Save result file for rnn
void saveR(char *filenamer, char *filenamed, int *res_id, float *dis, int *qresult_count, int *qresult_count_prefix, int qnum)
{
	FILE *resr = fopen(filenamer, "a");
	FILE *resd = fopen(filenamed, "a");

	for (unsigned i = 0; i < qnum; i++)
	{
		for (unsigned j = qresult_count_prefix[i]; j < qresult_count_prefix[i] + qresult_count[i]; j++)
		{
			fprintf(resr, "%d ", res_id[j]);
			fflush(resr);
			fprintf(resd, "%f ", dis[j]);
			fflush(resd);
		}
		fprintf(resr, "\n");
		fflush(resr);
		fprintf(resd, "\n");
		fflush(resd);
	}
	fclose(resr);
	fclose(resd);
}
