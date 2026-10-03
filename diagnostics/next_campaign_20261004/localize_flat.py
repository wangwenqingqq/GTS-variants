#!/usr/bin/env python3
"""Independent all-object CPU audit of the first rejected native Flat query."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from qualification import native_ivf
from campaign10k import ROOT,save,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);a=p.parse_args()
    ref=json.loads((ROOT/'oracle_GIST_dev1024.json').read_text())
    audit=json.loads((ROOT/'outputs/screen_GIST_FAISS_FLAT_k8_b32.audit.json').read_text())
    n,d,k,ids,fields=native_ivf.read_gts(ROOT/'outputs/screen_GIST_FAISS_FLAT_k8_b32.bin')
    source=native_ivf.load_data(a.data);bad=np.flatnonzero(np.array(audit['quality']['per_query_recall'])<1)
    assert len(bad)==1 and int(bad[0])==531
    row=int(bad[0]);qid=ref['records'][row]['qid'];query=source[qid].astype(np.float64)
    scores=np.empty(n,dtype=np.float64);begin=time.perf_counter()
    for first in range(0,n,100000):
        # Bounded CPU-only transpose; no candidate/GPU distance routine.
        x=np.asarray(source[first:first+100000].T,dtype=np.float64,order='C')
        total=np.zeros(x.shape[1],dtype=np.float64)
        for j in range(d):
            delta=x[j]-query[j];total+=delta*delta
        scores[first:first+len(total)]=total
    order=np.lexsort((np.arange(n),scores));nearest=order[:9]
    assert nearest[:8].tolist()==ref['records'][row]['ids'][:8]
    target=set(map(int,nearest[:8]));returned=set(map(int,ids[row]));fn=sorted(target-returned);fp=sorted(returned-target)
    descending=np.argwhere(np.diff(fields,axis=1)<0).tolist()
    flat_ids=ids.reshape(-1);queries=np.repeat(np.array([r['qid'] for r in ref['records']],dtype=np.int32),k)
    selected=np.zeros(len(flat_ids),dtype=np.float64)
    for j in range(d):
        delta=source[flat_ids,j].astype(np.float64)-source[queries,j].astype(np.float64);selected+=delta*delta
    relative=np.abs(fields.reshape(-1).astype(np.float64)**2-selected)/np.maximum(1,selected)
    failed=np.flatnonzero(relative>5e-5)
    result={'state':'rejected','dataset':'GIST','N':n,'D':d,'Q':1024,'K':k,'B':32,'row':row,'qid':qid,
            'CPU_all_object_oracle_s':time.perf_counter()-begin,'CPU_enumerated_objects':n,'CPU_matches_GPU_RN_oracle':True,
            'reference_ids':nearest[:8].tolist(),'returned_ids':ids[row].tolist(),'FN':fn,'FP':fp,
            'reference_squared':scores[nearest].tolist(),'ninth_id':int(nearest[8]),'gap_kth_to_next_squared':float(scores[nearest[8]]-scores[nearest[7]]),
            'missed_and_extra_reference_squared':{str(x):float(scores[x]) for x in fn+fp},
            'descending_field_positions':descending,'field_squared_tolerance_failed_slots':failed.tolist(),
            'worst_field_relative_squared_error':float(relative.max()),
            'output_sha256':sha(ROOT/'outputs/screen_GIST_FAISS_FLAT_k8_b32.bin'),
            'interpretation':'CPU independently confirms membership rejection. Cause requires native replay/score evidence; the exact FP64 gate is unchanged.'}
    save(ROOT/'FLAT_FAILURE_LOCALIZATION.json',result);print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
