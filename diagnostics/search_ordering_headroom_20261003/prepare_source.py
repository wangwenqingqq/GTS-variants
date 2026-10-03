#!/usr/bin/env python3
"""Generate the E0 adapter from the frozen P7 source, without editing P7."""
from pathlib import Path
import hashlib

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'unified_knn_e2e_20261003'
source=(BASE/'opt_knn_bench.cu').read_text()
assert hashlib.sha256(source.encode()).hexdigest()=='29349d546619aba227aafb1c74cf80cc9eed88f1ab691bfa68208eb68aa5d2a9'

def replace(old,new):
    global source
    assert source.count(old)==1,old
    source=source.replace(old,new)

for header in ('knn_cutoff.cuh','knn_select.cuh','knn_verify.cuh'):
    replace(f'#include "{header}"',f'#include "../unified_knn_e2e_20261003/{header}"')
replace('using Clock=', '#include "headroom_count.cuh"\nusing Clock=')
replace('check(argc==11,"usage: opt data qids tree.index seeds.i32 MODE K B out warm.qid force_all");',
        'check(argc==12,"usage: opt data qids tree.index seeds.i32 MODE K B out warm.qid force_all oracle_u.f64_or_dash");')
replace('bool bound=mode!="O_FULL",masked=mode=="O_MASK",force_all=std::stoi(argv[10])!=0;',
        'bool bound=true,star=mode=="STAR_SCAN"||mode=="STAR_MASK",masked=mode=="O_MASK"||mode=="STAR_MASK",force_all=std::stoi(argv[10])!=0;')
replace('(mode=="O_FULL"||mode=="O_BOUND"||masked)', '(mode=="O_BOUND"||mode=="O_MASK"||star)')
replace('double* cutoff=alloc<double>(b);', '''double* cutoff=alloc<double>(b);double* seed_u=alloc<double>(b);double* oracle_u=nullptr;
    if(star) {
        std::ifstream of(argv[11],std::ios::binary);int uh[3];of.read((char*)uh,12);
        check(bool(of)&&uh[0]==n&&uh[1]==d&&uh[2]==k,"oracle header");
        std::vector<double> values(n);read(of,values);
        for(int x:queries)check(std::isfinite(values[x])&&values[x]>=0,"missing diagnostic oracle U");
        for(size_t i=0;i<std::min(warm.size(),size_t(2*b));++i)check(std::isfinite(values[warm[i]])&&values[warm[i]]>=0,"missing warm oracle U");
        oracle_u=alloc<double>(n);ck(cudaMemcpy(oracle_u,values.data(),size_t(n)*8,cudaMemcpyHostToDevice));
    }else check(std::string(argv[11])=="-","ordinary modes must not load oracle");''')
replace('double refit_ms=0.;int fallback_nodes=0,refitted_nodes=0;',
        'std::vector<int> host_frontier;double refit_ms=0.;int fallback_nodes=0,refitted_nodes=0;')
replace('frontier=alloc<int>(n);', 'host_frontier=last;frontier=alloc<int>(n);')
replace('select_cutoff<<<1,32,0,stream>>>(result,cutoff,k,batch);nvtxRangePop();',
        'select_cutoff<<<1,32,0,stream>>>(result,seed_u,k,batch);nvtxRangePop();\n            materialize_cutoff<<<1,32,0,stream>>>(seed_u,oracle_u,query,cutoff,batch,star);')
replace('    // A separate replay exposes every admissible pair for small-table audit.', '''    // Work accounting is a separate, unprofiled replay after formal delivery.
    if(std::getenv("HEADROOM_COUNT")) {
        int qt=b==1?1:2,groups=(b+qt-1)/qt;
        WorkCount* count_dev=alloc<WorkCount>(groups);std::vector<WorkCount> counts(groups);
        std::vector<double> u0(b),used(b);std::vector<uint8_t> masks(size_t(n)*b,1);
        std::vector<int> terminal;
        if(masked){terminal=host_frontier;std::sort(terminal.begin(),terminal.end());terminal.erase(std::unique(terminal.begin(),terminal.end()),terminal.end());}
        std::ofstream work(out+".work.csv"),pair(out+".pairs.csv");
        work<<std::setprecision(17)<<"query_index,qid,U0,U_used,candidate_pairs,coordinate_updates,terminal_nodes,unprunable_terminal_nodes,unprunable_objects\\n";
        pair<<"first_query_index,second_query_index,union_candidates,shared_coordinate_steps\\n";
        for(int first=0;first<int(queries.size());first+=b) {
            int batch=std::min(b,int(queries.size())-first);batch_run(queries.data()+first,batch,first);
            ck(cudaMemcpy(u0.data(),seed_u,batch*8,cudaMemcpyDeviceToHost));ck(cudaMemcpy(used.data(),cutoff,batch*8,cudaMemcpyDeviceToHost));
            if(masked)ck(cudaMemcpy(masks.data(),mask,size_t(n)*batch,cudaMemcpyDeviceToHost));
            ck(cudaMemsetAsync(count_dev,0,groups*sizeof(WorkCount),stream));
            dim3 grid((n+511)/512,(batch+qt-1)/qt);int shared=qt*d*4;
#define RUN_COUNT(QT) \\
            if(masked)count_verify<QT,true><<<grid,512,shared,stream>>>(data,packed,query,cutoff,mask,n,d,batch,count_dev); \\
            else count_verify<QT,false><<<grid,512,shared,stream>>>(data,packed,query,cutoff,mask,n,d,batch,count_dev);
            if(qt==1){RUN_COUNT(1)}else{RUN_COUNT(2)}
#undef RUN_COUNT
            ck(cudaGetLastError());ck(cudaStreamSynchronize(stream));ck(cudaMemcpy(counts.data(),count_dev,groups*sizeof(WorkCount),cudaMemcpyDeviceToHost));
            for(int q=0;q<batch;++q) {
                unsigned long long keep_nodes=0,keep_objects=0;
                if(masked) {
                    for(int nid:terminal)keep_nodes+=masks[size_t(q)*n+nodes[nid].lid]!=0;
                    for(int p=0;p<n;++p)keep_objects+=masks[size_t(q)*n+p]!=0;
                }
                auto c=counts[q/qt];
                work<<first+q<<','<<queries[first+q]<<','<<u0[q]<<','<<used[q]<<','<<c.candidate[q%qt]<<','<<c.updates[q%qt]<<',';
                if(masked)work<<terminal.size()<<','<<keep_nodes<<','<<keep_objects;else work<<",,";
                work<<'\\n';
                if(q%qt==0)pair<<first+q<<','<<(qt==2&&q+1<batch?first+q+1:-1)<<','<<c.unions<<','<<c.shared_steps<<'\\n';
            }
        }
        ck(cudaFree(count_dev));
    }
    // A separate replay exposes every admissible pair for small-table audit.''')
replace('(void*)cutoff,(void*)out_ids', '(void*)cutoff,(void*)seed_u,(void*)oracle_u,(void*)out_ids')
(HERE/'headroom_bench.cu').write_text(source)
print(hashlib.sha256(source.encode()).hexdigest())
