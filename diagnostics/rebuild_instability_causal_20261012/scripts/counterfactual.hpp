#pragma once
#pragma push_macro("short")
#undef short
#include <algorithm>
#include <fstream>
#include <tuple>
#pragma pop_macro("short")
__managed__ int* causal_forced=nullptr;
namespace causal {
static int dose=0,allocated=0;
static std::vector<int> prebase,postbase,preorder,inverse;
static std::vector<TN> prenodes;
static std::ofstream decisions;
template<class T> std::vector<T> read(const std::string& path) {
    std::ifstream f(path,std::ios::binary|std::ios::ate);uk::require(bool(f),"open causal input");
    auto bytes=f.tellg();uk::require(bytes>=0&&size_t(bytes)%sizeof(T)==0,"causal input length");
    std::vector<T> v(size_t(bytes)/sizeof(T));f.seekg(0);f.read(reinterpret_cast<char*>(v.data()),bytes);
    uk::require(bool(f),"read causal input");return v;
}
inline void configure(const std::string& pre,const std::string& current,int frozen,const std::string& out) {
    dose=frozen;uk::require(dose>=0&&dose<=3,"causal dose");
    prebase=read<int>(pre+"/base.i32");preorder=read<int>(pre+"/order.i32");prenodes=read<TN>(pre+"/nodes.bin");
    postbase=read<int>(current+"/base.i32");int maxoid=*std::max_element(postbase.begin(),postbase.end());
    inverse.assign(maxoid+1,-1);for(int row=0;row<int(postbase.size());++row){int oid=postbase[row];
        uk::require(oid>=0&&inverse[oid]==-1,"causal unique base");inverse[oid]=row;}
    decisions.open(out+"/DECISIONS.csv");uk::require(bool(decisions),"causal decisions output");
    decisions<<"level,storage_node,pre_storage_node,requested,admitted,reason,pre_pivot_oid,native_pivot_oid,chosen_pivot_oid,intersection,current_size,pre_size\n";
}
inline void before(int level,int slots,int first,const TN* nodes,const int* order) {
    auto hn=bt::copy(nodes,bt::nn);auto ho=bt::copy(order,bt::n);
    uk::require(bt::auditing&&int(postbase.size())==bt::n,"causal capture required");
    if(dose&&!causal_forced){allocated=bt::nn;u10_ck(cudaMalloc((void**)&causal_forced,allocated*sizeof(int)));}
    std::vector<int> forced(bt::nn,-1),match(slots,-1),overlap(slots,0),oldlabel(inverse.size(),-1);
    std::vector<int> oldbest(slots,-1),newbest(slots,-1),newties(slots),oldties(slots);
    if(level<dose&&level) {
        for(int j=0;j<slots;++j){TN v=prenodes.at(first+j);
            for(int p=v.lid;p<v.lid+v.size;++p){int oid=prebase.at(preorder.at(p));if(oid<int(oldlabel.size()))oldlabel[oid]=j;}}
        std::vector<int> counts(size_t(slots)*slots,0);
        for(int i=0;i<slots;++i){TN v=hn.at(first+i);for(int p=v.lid;p<v.lid+v.size;++p){
            int old=oldlabel.at(postbase.at(ho.at(p)));if(old>=0)++counts[size_t(i)*slots+old];}}
        for(int i=0;i<slots;++i){int best=0;
            for(int j=0;j<slots;++j){int c=counts[size_t(i)*slots+j];if(c>best){best=c;newbest[i]=j;newties[i]=1;}else if(c==best&&c>0)++newties[i];}}
        for(int j=0;j<slots;++j){int best=0;
            for(int i=0;i<slots;++i){int c=counts[size_t(i)*slots+j];if(c>best){best=c;oldbest[j]=i;oldties[j]=1;}else if(c==best&&c>0)++oldties[j];}}
        for(int i=0;i<slots;++i){int j=newbest[i];if(j>=0&&newties[i]==1&&oldties[j]==1&&oldbest[j]==i){match[i]=j;overlap[i]=counts[size_t(i)*slots+j];}}
    } else if(level<dose){match[0]=0;for(int oid:prebase)if(oid<int(inverse.size())&&inverse[oid]>=0)++overlap[0];}
    for(int i=0;i<slots;++i){int nid=first+i;TN v=hn.at(nid);int middle=ho.at((2*v.lid+v.size-1)/2);
        bool requested=level<dose,admitted=false;int oldoid=-1,oldsize=0,preid=-1;std::string reason=requested?"no_correspondence":"native";
        if(requested&&match[i]>=0){preid=first+match[i];TN old=prenodes.at(preid);oldsize=old.size;
            oldoid=prebase.at(prenodes.at(preid*10+1).pid);
            int row=oldoid<int(inverse.size())?inverse[oldoid]:-1;
            if(row>=0&&std::find(ho.begin()+v.lid,ho.begin()+v.lid+v.size,row)!=ho.begin()+v.lid+v.size){forced[nid]=row;admitted=true;reason="admitted";}
            else reason="pivot_absent";}
        int chosen=admitted?forced[nid]:middle;
        decisions<<level<<','<<nid<<','<<preid<<','<<requested<<','<<admitted<<','<<reason<<','<<oldoid<<','<<postbase.at(middle)<<','<<postbase.at(chosen)<<','<<overlap[i]<<','<<v.size<<','<<oldsize<<'\n';
    }
    decisions.flush();uk::require(bool(decisions),"causal decisions write");
    if(dose)u10_ck(cudaMemcpy(causal_forced,forced.data(),forced.size()*sizeof(int),cudaMemcpyHostToDevice));
}
inline void release(){if(causal_forced)u10_ck(cudaFree(causal_forced));causal_forced=nullptr;decisions.close();}
}
