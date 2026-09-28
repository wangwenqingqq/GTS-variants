#!/usr/bin/env python3
"""Add read-only tree/candidate dumps to the pinned Q driver."""
from pathlib import Path
import argparse

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'leaf_early_l2_20260924/local/build'

def once(s,old,new):
    assert s.count(old)==1,(old,s.count(old))
    return s.replace(old,new)

def make(out):
    out.mkdir(parents=True,exist_ok=True)
    s=(BASE/'graph_bench.cu').read_text()
    s=once(s,'    ck(cudaMemcpy(ids.data(),id_list,ids.size()*sizeof(int),cudaMemcpyDeviceToHost));',
'''    ck(cudaMemcpy(ids.data(),id_list,ids.size()*sizeof(int),cudaMemcpyDeviceToHost));
    if(dump) {
        std::ofstream f(out+".tree.bin",std::ios::binary);
        int header[5]={data_info[1],data_info[0],int(tree.size()),tree_h,MAX_SIZE};
        f.write((char*)header,sizeof(header));
        f.write((char*)tree.data(),tree.size()*sizeof(TN));
        f.write((char*)empty.data(),empty.size()*sizeof(int));
        f.write((char*)ids.data(),ids.size()*sizeof(int));
    }''')
    # Write query-specific leaf membership after each timed query. These
    # diagnostic copies happen outside the per-query timer.
    s=once(s,'    std::ofstream full,work; if(dump){full.open(out+".results");full<<std::setprecision(9);work.open(out+".work.csv");work<<"qid,candidates\\n";}',
'''    std::ofstream full,work,leafdump;
    if(dump){full.open(out+".results");full<<std::setprecision(9);
        work.open(out+".work.csv");work<<"qid,candidates,hit_leaves\\n";
        leafdump.open(out+".candidates.bin",std::ios::binary);
        int records=nq*repeats;leafdump.write((char*)&records,sizeof(int));}''')
    s=once(s,'        if(dump && fixed){int nc;ck(cudaMemcpy(&nc,fixed->candidate_count,4,cudaMemcpyDeviceToHost));work<<q<<\',\'<<nc<<\'\\n\';}',
'''        if(dump && fixed){
            int nc;ck(cudaMemcpy(&nc,fixed->candidate_count,4,cudaMemcpyDeviceToHost));
            std::vector<int> cand(nc),hit(nc*MAX_SIZE);
            ck(cudaMemcpy(cand.data(),fixed->candidates,nc*sizeof(int),cudaMemcpyDeviceToHost));
            ck(cudaMemcpy(hit.data(),fixed->hits,hit.size()*sizeof(int),cudaMemcpyDeviceToHost));
            int hit_leaves=0;
            for(int b=0;b<nc;++b){
                bool any=false;for(int j=0;j<MAX_SIZE;++j)any|=hit[b*MAX_SIZE+j]!=0;
                hit_leaves+=any;
            }
            work<<q<<','<<nc<<','<<hit_leaves<<'\\n';
            int record[2]={q,nc};leafdump.write((char*)record,sizeof(record));
            leafdump.write((char*)cand.data(),nc*sizeof(int));
        }''')
    (out/'graph_bench.cu').write_text(s)
    for name in ('l2_traversal.cuh','leaf_l2.cuh'):
        (out/name).write_bytes((BASE/name).read_bytes())
    (out/'run.py').write_bytes((BASE/'run.py').read_bytes())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();make(a.out)
