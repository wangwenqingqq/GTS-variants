// Compile the exact generated production translation unit; no arithmetic stubs.
#define main fixed3_retained_main
#include FIXED3_PARENT
#undef main
#undef short
#include <random>
#include <cstring>
#include <numeric>
#include <limits>
static void demand(bool b,const char* s){if(!b)throw std::runtime_error(s);}
template<class T> T* upload(const std::vector<T>& x){T* p;u10_ck(cudaMalloc((void**)&p,x.size()*sizeof(T)));u10_ck(cudaMemcpy(p,x.data(),x.size()*sizeof(T),cudaMemcpyHostToDevice));return p;}
template<class T> std::vector<T> download(T* p,int n){std::vector<T> x(n);u10_ck(cudaMemcpy(x.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost));return x;}
int main(int argc,char** argv)try {
    demand(argc==2,"unit output required");std::ofstream sink(argv[1],std::ios::binary);int cases=0;
    for(int d:{128,960})for(int size=1;size<=20;size++)for(int nl=1;nl<=8;nl++)for(int churn=0;churn<3;churn++) {
        int n=nl*size;std::vector<rex::Node> nodes(nl);std::vector<int> order(n),slots(nl),leaves(nl),deleted(n),qid{0};
        std::iota(order.rbegin(),order.rend(),0);std::iota(slots.begin(),slots.end(),0);for(int& x:slots)x*=size;
        std::iota(leaves.begin(),leaves.end(),0);
        for(int i=0;i<nl;i++){nodes[i]={0,0,size,i*size,1};if(churn && i%3==churn-1)leaves[i]=-1;}
        std::mt19937 rng(2026101101+d+size*100+nl);std::vector<float> x(size_t(n)*d);
        for(float& f:x)f=float(int(rng()%257)-128)/256.0f;
        std::fill(x.begin(),x.begin()+d,0.0f);
        if(n>1)std::copy(x.begin(),x.begin()+d,x.begin()+d); // identity-distinct equal vector
        if(n>2){std::fill(x.begin()+2*d,x.begin()+3*d,0.0f);x[2*d]=1.0f;}
        for(int id=0;id<n;id++)deleted[id]=churn==2 && id%4==1;
        auto nd=upload(nodes);auto ord=upload(order);auto ls=upload(slots);auto ll=upload(leaves);auto dat=upload(x);auto del=upload(deleted);auto qi=upload(qid);
        auto hits=upload(std::vector<int>(n));auto fields=upload(std::vector<float>(n,-987.0f));
        rex::View v{};v.nodes=nd;v.order=ord;v.leaf_slot=ls;v.data=dat;v.deleted=del;v.qids=qi;v.n=n;v.node_count=nl;v.d=d;rex::Work w{};
        for(float radius:{0.0f,1.0f,std::nextafter(1.0f,0.0f),std::nextafter(1.0f,2.0f),1000.0f}) {
            u10_ck(cudaMemset(hits,0,n*4));std::vector<float> sentinel(n,-987.0f);u10_ck(cudaMemcpy(fields,sentinel.data(),n*4,cudaMemcpyHostToDevice));
#if FIXED3_MODE==2
            rex::verify_materialized<<<(nl+2)/3,32>>>(v,ll,nl,radius,hits,fields,w);
#else
            rex::verify_materialized<<<nl,FIXED3_MODE==0?256:32>>>(v,ll,radius,hits,fields,w);
#endif
            u10_ck(cudaGetLastError());u10_ck(cudaDeviceSynchronize());auto h=download(hits,n);auto f=download(fields,n);
            for(int leaf=0;leaf<nl;leaf++)for(int j=0;j<size;j++) {
                int slot=leaf*size+j,id=order[slot];double sum=0;
                for(int k=0;k<d;k++){volatile double delta=double(x[size_t(id)*d+k])-double(x[k]);volatile double sq=delta*delta;sum=sum+sq;}
                bool keep=leaves[leaf]>=0 && !deleted[id] && sum<=double(radius)*radius;
                demand(h[slot]==int(keep),"CPU hit oracle mismatch");float expected=keep?float(std::sqrt(sum)):-987.0f;
                demand(std::memcmp(&f[slot],&expected,4)==0,"CPU exact FP32 field mismatch");
            }
            sink.write((char*)h.data(),n*4);sink.write((char*)f.data(),n*4);++cases;
        }
        for(void* p:{(void*)nd,(void*)ord,(void*)ls,(void*)ll,(void*)dat,(void*)del,(void*)qi,(void*)hits,(void*)fields})u10_ck(cudaFree(p));
    }
    demand(bool(sink),"unit output failure");std::cout<<"UNIT_PASS "<<cases<<" cases; D128/D960; ALL leaf sizes 1..20; tails, inactive leaves, equality, deletes, pointer churn\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}
