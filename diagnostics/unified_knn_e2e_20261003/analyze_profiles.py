#!/usr/bin/env python3
import json
from pathlib import Path
import sqlite3
from qualification import BASE
import sys
sys.path.insert(0,str(BASE))
from analyze_profiles import trace

ROOT=Path(__file__).resolve().parent

def main():
    result={}
    for method in ('GTS_ORIG','O_FULL','O_BOUND','O_MASK','FAISS_FLAT','IVF_ALL','CAGRA'):
        path=ROOT/'profiles'/f'{method}.sqlite'
        info=trace(path);info['scope']='One post-warmup GIST K8 B32 pass, first32 seen development queries, no index setup'
        stages={k:0. for k in ('seed','tree_mask','distance','topk_merge','delivery','native_search','unclassified')}
        with sqlite3.connect(path) as db:
            db.row_factory=sqlite3.Row;names=dict(db.execute('SELECT id,value FROM StringIds'))
            events=db.execute('SELECT * FROM CUPTI_ACTIVITY_KIND_KERNEL ORDER BY start').fetchall()
            in_seed=method in ('O_BOUND','O_MASK')
            for event in events:
                name=names[event['demangledName']]
                if 'seed_distances' in name:stage='seed'
                elif any(s in name for s in ('knn_parent_walk','knn_mask','init_root')):in_seed=False;stage='tree_mask'
                elif 'verify_distances' in name:in_seed=False;stage='distance'
                elif 'block_topk' in name:stage='seed' if in_seed else 'topk_merge'
                elif 'select_cutoff' in name:stage='seed';in_seed=False
                elif 'final_output' in name:stage='delivery'
                elif method in ('FAISS_FLAT','IVF_ALL','CAGRA'):stage='native_search'
                elif 'dataProcessKnn' in name:stage='distance'
                elif 'sort' in name.lower():stage='topk_merge'
                else:stage='unclassified'
                stages[stage]+=(event['end']-event['start'])/1e6
        info['kernel_stage_ms']=stages
        info['unmeasured_counters']=['DRAM physical bytes/sectors','executed coordinate updates','warp longest path','CPU instruction time','library exploration counters']
        info['warning']='Kernel sums and inclusive CUDA API wait overlap GPU work. No-recorded-GPU intervals are not CPU computation. Unmeasured counters are unknown, not zero.'
        result[method]=info
    (ROOT/'TRACE_SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PROFILE ANALYSIS COMPLETE',flush=True)

if __name__=='__main__':main()
