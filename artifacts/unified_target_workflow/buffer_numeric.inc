__global__ void target_buffer(int* info,float* data,int qid,const int* insert,int n,float radius,int* hit,Obj out) {
    int i=threadIdx.x;if(i>=n)return;float field;
    hit[i]=target::hit(data,info[0],insert[i],data+size_t(qid)*info[0],radius,field);
    out.dis_q[i]=field;out.res_id_q[i]=i;
}
void searchNaiveRnn(int* info,Obj& result,float* data,char*,int*,int qid,int n,float radius,int* insert,int* count) {
    if(!n){count[0]=0;return;}Obj tmp;int* flags;
    CHECK(cudaMalloc((void**)&tmp.dis_q,size_t(n)*sizeof(float)));
    CHECK(cudaMalloc((void**)&tmp.res_id_q,size_t(n)*sizeof(int)));
    CHECK(cudaMalloc((void**)&flags,size_t(n)*sizeof(int)));
    target_buffer<<<1,32>>>(info,data,qid,insert,n,radius,flags,tmp);
    thrust::inclusive_scan(thrust::device,flags,flags+n,flags);
    CHECK(cudaMemcpy(count,flags+n-1,sizeof(int),cudaMemcpyDeviceToHost));
    getRnn<<<1,32>>>(flags,tmp,result,n);u10_ck(cudaDeviceSynchronize());
    CHECK(cudaFree(tmp.dis_q));CHECK(cudaFree(tmp.res_id_q));CHECK(cudaFree(flags));
}
