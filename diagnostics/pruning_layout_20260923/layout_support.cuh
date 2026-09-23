#pragma once

// The producer finishes before capture. Query kernels only read this layout.
__global__ void packPruning(const TN* tree,const int* empty,const float* data,
                           int dim,int* pids,float* lower,float* packed) {
    for(int n=threadIdx.x+blockIdx.x*blockDim.x;n<111;n+=blockDim.x*gridDim.x) {
        pids[n]=(n>0 && !empty[n])?tree[n].pid:0;
        lower[n]=(n>0 && !empty[n])?tree[n].min_dis:0;
    }
    if(!packed)return;
    for(int i=threadIdx.x+blockIdx.x*blockDim.x;i<16*dim;i+=blockDim.x*gridDim.x) {
        int group=i%16,j=i/16,first=group*10+1,child=first;
        if(group<11)while(child<first+10 && empty[child])++child;
        bool valid=group<11 && child<first+10;
        packed[i]=valid?data[tree[child].pid*dim+j]:0;
    }
}

__global__ void checkPruning(const TN* tree,const int* empty,const float* data,
                            int dim,const int* pids,const float* lower,const float* packed) {
    for(int n=threadIdx.x+1;n<111;n+=blockDim.x)if(!empty[n]) {
        assert(pids[n]==tree[n].pid);
        assert(__float_as_uint(lower[n])==__float_as_uint(tree[n].min_dis));
        for(int j=0;j<dim;++j)
            assert(__float_as_uint(packed[j*16+(n-1)/10])==__float_as_uint(data[tree[n].pid*dim+j]));
    }
}

struct PruneLayout {
    int* pids=nullptr;float* lower=nullptr;float* packed=nullptr;
    size_t bytes=0;double setup_s=0;
    explicit PruneLayout(bool with_pivots) {
        auto t=Clock::now();alloc(pids,111);alloc(lower,111);bytes=111*8;
        if(with_pivots){alloc(packed,16*data_info[0]);bytes+=16*data_info[0]*sizeof(float);}
        packPruning<<<(16*data_info[0]+127)/128,128>>>(node_list,empty_list,data_d,data_info[0],pids,lower,packed);
        ck(cudaGetLastError());ck(cudaDeviceSynchronize());setup_s=seconds(t);
    }
    ~PruneLayout(){ck(cudaFree(pids));ck(cudaFree(lower));if(packed)ck(cudaFree(packed));}
};
PruneLayout* prune_layout=nullptr;

void auditPruning(const std::vector<int>& queries,float radius,const std::string& out) {
    PruneLayout layout(true);
    checkPruning<<<1,128>>>(node_list,empty_list,data_d,data_info[0],layout.pids,layout.lower,layout.packed);
    ck(cudaGetLastError());ck(cudaDeviceSynchronize());
    std::vector<TN> tree(111);std::vector<int> empty(111),host[3];
    ck(cudaMemcpy(tree.data(),node_list,111*sizeof(TN),cudaMemcpyDeviceToHost));
    ck(cudaMemcpy(empty.data(),empty_list,111*sizeof(int),cudaMemcpyDeviceToHost));
    std::ofstream nodes(out+".tree.csv");nodes<<"nid,pid,lower,empty\n"<<std::setprecision(9);
    for(int n=1;n<111;++n)nodes<<n<<','<<(empty[n]?0:tree[n].pid)<<','<<(empty[n]?0:tree[n].min_dis)<<','<<empty[n]<<'\n';
    int* flags[3];int* qid;alloc(qid,1);
    for(int k=0;k<3;++k){alloc(flags[k],111);host[k].resize(111);}
    std::ofstream records(out+".flags.csv");records<<"qid,level,evaluated_children,flags\n";
    int cases=0;
    for(int q:queries) {
        ck(cudaMemcpy(qid,&q,sizeof(int),cudaMemcpyHostToDevice));
        for(auto p:flags)initQnode<<<1,512>>>(p,1,max_node_num);
        std::vector<int> previous(111);previous[0]=1;
        for(int level=1,start=1,num=10;level<3;++level,start+=num,num*=10) {
            findNextRnn<<<1,512>>>(flags[0],start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list,data_s,size_s);
            findNextLayout<false><<<1,512>>>(flags[1],start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list,data_s,size_s,layout.pids,layout.lower,layout.packed);
            findNextLayout<true><<<1,512>>>(flags[2],start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list,data_s,size_s,layout.pids,layout.lower,layout.packed);
            ck(cudaGetLastError());ck(cudaDeviceSynchronize());
            for(int k=0;k<3;++k)ck(cudaMemcpy(host[k].data(),flags[k],111*sizeof(int),cudaMemcpyDeviceToHost));
            assert(host[0]==host[1] && host[0]==host[2]);++cases;
            int evaluated=0;for(int n=start;n<start+num;++n)evaluated+=previous[(n-1)/10]==1 && !empty[n];
            records<<q<<','<<level<<','<<evaluated<<',';for(int f:host[0])records<<f;records<<'\n';
            for(auto p:flags)updatePnodeFlag<<<1,512>>>(p,start,num,max_node_num,empty_list);
            ck(cudaGetLastError());ck(cudaDeviceSynchronize());
            ck(cudaMemcpy(previous.data(),flags[0],111*sizeof(int),cudaMemcpyDeviceToHost));
        }
    }
    for(auto p:flags)ck(cudaFree(p));ck(cudaFree(qid));
    assert(cases==128);printf("PASS layout bit-audit and 128 per-level flag cases\n");
}
