#pragma once
#include <cstdint>
namespace rex {
constexpr int BLOCK_THREADS=256, MAX_REGION_OBJECTS=256, MAX_REGION_NODES=128;
constexpr int LOCAL_NODE_CAPACITY=128, QUERY_DIM=128;
struct Node {int pid; float min_dis; int size,lid,is_leaf;};
struct Region {int root,objects,nodes,leaves,leaf_offset,fallback;};
struct RegionTask {int query_index,region_index,root_node; uint64_t tree_epoch;};
struct View {
    const Node* nodes; const int* empty; const int* order; const float* data;
    const int* deleted; const int* qids; const Region* regions;
    const int* leaf_slot; const int* slot_pid;
    int n,node_count,region_count,arity; uint64_t tree_epoch;
};
// Counter build only: exact per-node/pivot/object membership, not hash sketches.
struct Work {unsigned long long *nodes,*pivots,*objects,*leaves;};
}
