// Differential intermediate-state and work-count checks, never timed.
#define GTS_ABLATION_NO_MAIN
#include "graph_bench.cu"
#include <set>

int main(int argc,char** argv) {
    assert(argc==3);load(argv[1],data_info,data_d,data_s,size_s);
    assert(data_info[1]==2000 && data_info[2]==6);
    indexConstru(data_d,data_s,size_s,data_info,id_list,node_list,max_node_num,tree_h,empty_list);
    ck(cudaDeviceSynchronize());assert(tree_h==3 && max_node_num[0]==111 && TREE_ORDER==10);
    std::ifstream qf(argv[2]);int nq;qf>>nq;assert(nq==64);std::vector<int> queries(nq);
    for(int& q:queries)qf>>q;
    std::vector<int> original_empty(111), empty(111), b(111), other(111);
    ck(cudaMemcpy(original_empty.data(),empty_list,111*sizeof(int),cudaMemcpyDeviceToHost));
    int *flags[4], *work, *qid;
    for(auto& f:flags)alloc(f,111);alloc(work,3);alloc(qid,1);
    int cases=0;
    for(int pattern=0;pattern<4;++pattern) {
        empty=original_empty;
        for(int nid=1;nid<111;++nid) {
            if(pattern==1 && (nid-1)%10==0)empty[nid]=1;
            if(pattern==2 && (nid-1)/10==1)empty[nid]=1;
            if(pattern==3 && nid%2==0)empty[nid]=1;
        }
        ck(cudaMemcpy(empty_list,empty.data(),111*sizeof(int),cudaMemcpyHostToDevice));
        for(float radius:{-1.f,0.f,4.f,256.f}) {
            long long total_child=0,total_parent=0;
            for(int qi=0;qi<(pattern==0?64:8);++qi) {
                ck(cudaMemcpy(qid,&queries[qi],sizeof(int),cudaMemcpyHostToDevice));
                ck(cudaMemset(work,0,3*sizeof(int)));
                for(auto f:flags) {ck(cudaMemset(f,0x7f,111*sizeof(int)));initQnode<<<1,512>>>(f,1,max_node_num);}
                fusedTraversal<true><<<1,512>>>(flags[2],1,node_list,radius,data_d,qid,10,max_node_num,data_info,empty_list,data_s,size_s,3,work+1);
                int start=1,num=10,expected_child=0,expected_parent=0;
                for(int level=1;level<3;++level) {
                    ck(cudaMemcpy(b.data(),flags[0],111*sizeof(int),cudaMemcpyDeviceToHost));
                    std::set<int> parents;
                    for(int i=0;i<num;++i) {
                        int nid=start+i,parent=(nid-1)/10;
                        if(b[parent]==1 && empty[nid]==0){++expected_child;parents.insert(parent);}
                    }
                    expected_parent+=parents.size();
                    findNextRnn<<<1,512>>>(flags[0],start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list,data_s,size_s);
                    auditLevel<true><<<1,512>>>(flags[1],start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list,data_s,size_s,work);
                    dedupLevel<true><<<1,512>>>(flags[3],start,node_list,radius,data_d,qid,num,max_node_num,data_info,empty_list,data_s,size_s,work+2);
                    ck(cudaMemcpy(b.data(),flags[0],111*sizeof(int),cudaMemcpyDeviceToHost));
                    for(int idx:{1,3}) {ck(cudaMemcpy(other.data(),flags[idx],111*sizeof(int),cudaMemcpyDeviceToHost));assert(other==b);}
                    for(int idx:{0,1,3})updatePnodeFlag<<<1,512>>>(flags[idx],start,num,max_node_num,empty_list);
                    start+=num;num*=10;
                }
                ck(cudaMemcpy(b.data(),flags[0],111*sizeof(int),cudaMemcpyDeviceToHost));
                for(int idx:{1,2,3}) {ck(cudaMemcpy(other.data(),flags[idx],111*sizeof(int),cudaMemcpyDeviceToHost));assert(other==b);}
                int counts[3];ck(cudaMemcpy(counts,work,3*sizeof(int),cudaMemcpyDeviceToHost));
                assert(counts[0]==expected_child && counts[1]==expected_child && counts[2]==expected_parent);
                total_child+=counts[0];total_parent+=counts[2];++cases;
            }
            printf("WORK pattern=%d radius=%.0f child=%lld fused=%lld parent=%lld\n",pattern,radius,total_child,total_child,total_parent);
        }
    }
    for(auto f:flags)ck(cudaFree(f));ck(cudaFree(work));ck(cudaFree(qid));
    for(void* p:{(void*)data_info,(void*)data_s,(void*)size_s,(void*)id_list,(void*)node_list,(void*)max_node_num,(void*)empty_list})ck(cudaFree(p));
    ck(cudaGetLastError());assert(cases==352);printf("PASS traversal %d cases\n",cases);
}
