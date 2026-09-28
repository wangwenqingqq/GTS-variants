#pragma once

// Diagnostic only: compare every final flag with the separate native path.
// Masks only deactivate existing nodes; they do not invent valid node payloads.
void auditCombo(const std::vector<int>& queries,float radius) {
    PruneLayout row(2),tile(3);
    int *qid,*mask,*flags[4];alloc(qid,1);alloc(mask,111);
    std::vector<int> original(111),host[4];
    ck(cudaMemcpy(original.data(),empty_list,111*sizeof(int),cudaMemcpyDeviceToHost));
    for(int k=0;k<4;++k){alloc(flags[k],111);host[k].resize(111);}
    int cases=0;
    for(int pattern=0;pattern<5;++pattern) {
        auto empty=original;
        for(int n=1;n<111;++n) {
            if((pattern==1 && n%10==1) || (pattern==2 && (n-1)/10==2) ||
               (pattern==3 && n%2) || pattern==4)empty[n]=1;
        }
        ck(cudaMemcpy(mask,empty.data(),111*sizeof(int),cudaMemcpyHostToDevice));
        for(int qi=0;qi<8;++qi)for(int height:{2,3}) {
            int q=queries.at(qi);ck(cudaMemcpy(qid,&q,sizeof(int),cudaMemcpyHostToDevice));
            for(auto p:flags)ck(cudaMemset(p,0xa5,111*sizeof(int)));
            initQnode<<<1,512>>>(flags[0],1,max_node_num);
            for(int level=1,start=1,num=10;level<height;++level,start+=num,num*=10) {
                findNextRnn<<<1,512>>>(flags[0],start,node_list,radius,data_d,qid,num,max_node_num,data_info,mask,data_s,size_s);
                updatePnodeFlag<<<1,512>>>(flags[0],start,num,max_node_num,mask);
            }
            fusedTraversal<false><<<1,512>>>(flags[1],1,node_list,radius,data_d,qid,10,max_node_num,data_info,mask,data_s,size_s,height,nullptr);
            fusedTraversalLayout<2><<<1,512>>>(flags[2],1,node_list,radius,data_d,qid,10,max_node_num,data_info,mask,data_s,size_s,height,row.pids,row.lower,row.packed);
            fusedTraversalLayout<3><<<1,512>>>(flags[3],1,node_list,radius,data_d,qid,10,max_node_num,data_info,mask,data_s,size_s,height,tile.pids,tile.lower,tile.packed);
            ck(cudaGetLastError());ck(cudaDeviceSynchronize());
            for(int k=0;k<4;++k)ck(cudaMemcpy(host[k].data(),flags[k],111*sizeof(int),cudaMemcpyDeviceToHost));
            for(int k=1;k<4;++k)assert(host[k]==host[0]);
            ++cases;
        }
    }
    for(auto p:flags)ck(cudaFree(p));ck(cudaFree(qid));ck(cudaFree(mask));
    assert(cases==80);printf("PASS combo 80 flag cases\n");
}
