#pragma once
// Included after original TN declaration; leaf_kernels.cuh must precede config.cuh.
char tc_variant='O';
struct TcBuffers {
    int n,q,nodes,leaf_count,chunks,dense_chunks;
    int *map,*ids,*dense_ids,*dense_counts;
    float* norms;
    Leaf *leaves,*dense_leaves;
    Chunk *tile,*dense_tile;
    Pair* pairs;
    unsigned *masks,*dense_masks;
} tc{};

__global__ void translate_pairs(const int* ns,const int* qs,const int* map,Pair* pairs,int count,int nodes,int q) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<count) {
        int node=ns[i],qi=qs[i];
        assert(node>=0 && node<nodes && qi>=0 && qi<q && map[node]>=0);
        pairs[i]={qi,map[node]};
    }
}
void tc_prepare(int n,int q,TN* nodes,int nn,int* native_ids,int* empty,const std::vector<float>& norms) {
    tc.n=n;tc.q=q;tc.nodes=nn;
    std::vector<TN> hnodes(nn);std::vector<int> hids(n),hempty(nn),map(nn,-1),ids,seen(n);
    CK(cudaMemcpy(hnodes.data(),nodes,nn*sizeof(TN),cudaMemcpyDeviceToHost));
    CK(cudaMemcpy(hids.data(),native_ids,n*sizeof(int),cudaMemcpyDeviceToHost));
    CK(cudaMemcpy(hempty.data(),empty,nn*sizeof(int),cudaMemcpyDeviceToHost));
    std::vector<Leaf> leaves,dense;std::vector<Chunk> chunks,dc;
    for(int i=0;i<nn;++i) if(!hempty[i] && hnodes[i].is_leaf) {
        TN node=hnodes[i];require(node.size>0&&node.size<=20&&node.lid>=0&&node.lid+node.size<=n,"invalid native leaf");
        map[i]=leaves.size();leaves.push_back({int(ids.size()),node.size});
        for(int j=0;j<node.size;++j){int id=hids[node.lid+j];require(id>=0&&id<n&&!seen[id]++,"invalid index partition");ids.push_back(id);}
        for(int j=0;j<node.size;j+=16)chunks.push_back({map[i],j});
    }
    require(int(ids.size())==n,"incomplete index partition");
    std::vector<int> identity(n);for(int i=0;i<n;++i)identity[i]=i;
    for(int i=0;i<n;i+=16){int l=dense.size();dense.push_back({i,std::min(16,n-i)});dc.push_back({l,0});}
    tc.leaf_count=leaves.size();tc.chunks=chunks.size();tc.dense_chunks=dc.size();
    tc.map=upload(map);tc.ids=upload(ids);tc.leaves=upload(leaves);tc.tile=upload(chunks);tc.norms=upload(norms);
    tc.dense_ids=upload(identity);tc.dense_leaves=upload(dense);tc.dense_tile=upload(dc);
    tc.dense_masks=upload(std::vector<unsigned>(dense.size()*(q/16),0xffffu));
    CK(cudaMalloc(&tc.pairs,size_t(leaves.size())*q*sizeof(Pair)));
    CK(cudaMalloc(&tc.masks,leaves.size()*(q/16)*sizeof(unsigned)));
    CK(cudaMalloc(&tc.dense_counts,q*sizeof(int)));CK(cudaDeviceSynchronize());
    std::printf("layout,%d,%d,%d,%d\n",tc.n,tc.q,tc.leaf_count,tc.dense_chunks);
}
void tc_refine(const float* x,const int* qids,int q,float radius,int np,const int* plist,int offset,int stride,int* counts) {
    require(q==tc.q&&np>=0&&np<=tc.leaf_count*q,"invalid native pair count");if(!np)return;
    translate_pairs<<<(np+255)/256,256>>>(plist+offset+stride,plist+offset+2*stride,tc.map,tc.pairs,np,tc.nodes,q);
    if(tc_variant=='S')simt<<<np,128>>>(x,qids,tc.ids,tc.leaves,tc.pairs,int(radius*radius),tc.n,counts,nullptr);
    else {
        CK(cudaMemsetAsync(tc.masks,0,tc.leaf_count*(q/16)*sizeof(unsigned)));
        make_masks<<<(np+255)/256,256>>>(tc.pairs,np,tc.masks,q/16);
        tensor<<<dim3(tc.chunks,q/16),32>>>(x,tc.norms,qids,tc.ids,tc.leaves,tc.tile,tc.masks,q/16,int(radius*radius),tc.n,counts,nullptr);
    }
    CK(cudaGetLastError());CK(cudaDeviceSynchronize());
}
void tc_dense(const float* x,const int* qids,int radius,std::vector<int>& output) {
    CK(cudaMemsetAsync(tc.dense_counts,0,tc.q*sizeof(int)));
    tensor<<<dim3(tc.dense_chunks,tc.q/16),32>>>(x,tc.norms,qids,tc.dense_ids,tc.dense_leaves,tc.dense_tile,tc.dense_masks,tc.q/16,radius*radius,tc.n,tc.dense_counts,nullptr);
    CK(cudaGetLastError());CK(cudaMemcpy(output.data(),tc.dense_counts,tc.q*sizeof(int),cudaMemcpyDeviceToHost));
}
void tc_release() {
    for(void* p:{(void*)tc.map,(void*)tc.ids,(void*)tc.dense_ids,(void*)tc.dense_counts,(void*)tc.norms,(void*)tc.leaves,(void*)tc.dense_leaves,(void*)tc.tile,(void*)tc.dense_tile,(void*)tc.pairs,(void*)tc.masks,(void*)tc.dense_masks})CK(cudaFree(p));
}
