#pragma once
#include <vector>
namespace rca {
inline bool active=false;
struct Level {int level,slots,active_nodes;long long distance_tasks;};
inline std::vector<Level> levels;
template<class Node> inline void before_build(int level,int slots,int start,
                                             const Node* nodes,const int* flags) {
    if(!active)return;
    std::vector<Node> hn(slots);std::vector<int> hf(slots);
    u10_ck(cudaMemcpy(hn.data(),nodes+start,slots*sizeof(Node),cudaMemcpyDeviceToHost));
    u10_ck(cudaMemcpy(hf.data(),flags+start,slots*sizeof(int),cudaMemcpyDeviceToHost));
    int count=0;long long tasks=0;
    for(int j=0;j<slots;j++)if(hf[j]==1){++count;tasks+=hn[j].size;}
    levels.push_back({level,slots,count,tasks});
}
}
