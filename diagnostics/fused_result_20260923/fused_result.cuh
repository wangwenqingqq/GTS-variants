#pragma once
#include <cassert>
#include <cub/block/block_scan.cuh>

// Bounded query-only selection; leaf CTAs complete at the preceding stream edge.
__global__ void fusedResultSelect(const int* candidates, const int* hits,
                                  const int* rawids, const float* rawdis,
                                  const int* deletion_prefix, int* count,
                                  int* outids, float* outdis) {
    using Scan = cub::BlockScan<int,512>;
    __shared__ Scan::TempStorage scratch;
    const int limit=*candidates*20;
    assert(*candidates>=0 && *candidates<=111 && blockDim.x==512 && gridDim.x==1);
    int carry=0;
    for(int base=0;base<limit;base+=512) {
        const int i=base+threadIdx.x;
        const int hit=i<limit ? hits[i] : 0;
        int rank, total;
        Scan(scratch).ExclusiveSum(hit,rank,total);
        if(hit) {
            const int id=rawids[i];
            outids[carry+rank]=id-deletion_prefix[id];
            outdis[carry+rank]=rawdis[i];
        }
        __syncthreads(); // Every lane releases CUB scratch before the next tile.
        carry+=total;
    }
    if(threadIdx.x==0)*count=carry;
}
