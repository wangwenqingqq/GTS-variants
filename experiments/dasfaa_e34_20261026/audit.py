"""Check every returned object against independent exhaustive CPU top-k distances."""
import json,sys
from pathlib import Path
import numpy as np

def audit(root,case,result):
    root=Path(root);p=Path(str(result)+'.ids');a=np.fromfile(p,dtype='<i4').reshape(-1,8)
    assert len(a) in (1000,1024),a.shape
    raw=(root/case['oracle']).read_bytes();assert len(raw)==1000*10*12
    kth=np.frombuffer(raw,dtype='<f8',offset=1000*10*4).reshape(1000,10)[:,7]
    h=np.fromfile(root/case['base'],dtype='<i4',count=2);x=np.memmap(root/case['base'],dtype='<f4',mode='r',offset=8,shape=tuple(h))[:case['N']]
    q=np.fromfile(root/case['query'],dtype='<f4',offset=8).reshape(1000,case['D'])
    valid=(a>=0)&(a<case['N']);safe=np.clip(a,0,case['N']-1)
    dd=np.sqrt(((np.asarray(x[safe],dtype=np.float64)-q[np.arange(len(a))%1000,None,:].astype(np.float64))**2).sum(2))
    good=(dd<=kth[np.arange(len(a))%1000,None]*(1+1e-5))&valid
    duplicates=sum(len(np.unique(row))!=8 for row in a)
    out={'results':int(a.size),'rows':len(a),'invalid_ids':int((~valid).sum()),'duplicate_rows':duplicates,'distance_failures':int((~good).sum()),'tie_aware_recall':float(good.mean()),'correct':bool(good.all() and not duplicates),'oracle':'independent exhaustive CPU FP64 differences','oracle_k':8,'tolerance':1e-5}
    Path(str(result)+'.audit.json').write_text(json.dumps(out,indent=2)+'\n');return out
if __name__=='__main__':
    root=Path(sys.argv[1]);cases=json.loads((root/'DATA_MANIFEST.json').read_text())['cases'];case=next(x for x in cases if f'{x["family"]}_{x["N"]}'==sys.argv[2]);print(json.dumps(audit(root,case,sys.argv[3])))
