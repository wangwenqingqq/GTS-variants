// One CTA owns one query's unchanged contiguous result segment.
const int i = blockIdx.x;
const int lane = threadIdx.x & 31;
const int warp = threadIdx.x >> 5;
const int s = offset_p + size_list[cur_level] / (MAX_SIZE + 3) * 3 + p_list[offset_p + i * nnum_up] * MAX_SIZE;
const int e = i < le - ls - 1
    ? offset_p + size_list[cur_level] / (MAX_SIZE + 3) * 3 + p_list[offset_p + (i + 1) * nnum_up] * MAX_SIZE
    : offset_p + size_list[cur_level] / (MAX_SIZE + 3) * 3 + lnum * MAX_SIZE;
const int qid = p_list[offset_p + size_list[cur_level] / (MAX_SIZE + 3) * 2 + p_list[offset_p + i * nnum_up]];
int sum = 0;
for (int j = s + threadIdx.x; j < e; j += blockDim.x) sum += p_list[j];
for (int offset = 16; offset; offset >>= 1) sum += __shfl_down_sync(0xffffffffu, sum, offset);
__shared__ int partial[16];
if (lane == 0) partial[warp] = sum;
__syncthreads();
if (warp == 0) {
    sum = lane < 16 ? partial[lane] : 0;
    for (int offset = 16; offset; offset >>= 1) sum += __shfl_down_sync(0xffffffffu, sum, offset);
    if (lane == 0) res[qid] = sum;
}
