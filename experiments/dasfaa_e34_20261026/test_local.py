"""Small runnable checks for audit edge cases and paired statistics."""
import json,math,tempfile
from pathlib import Path
import numpy as np
from audit import audit
from prepare import fbin
from summarize import paired,slope

def test():
    a=paired([2]*6,[1]*6);assert a['ratio']==a['lo']==a['hi']==2
    assert abs(slope([1,10,100],[2,20,200])-1)<1e-12
    assert slope([1],[3]) is None
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp);x=np.arange(20,dtype=np.float32).reshape(10,2);q=np.tile(x[0],(1000,1));fbin(p/'x',x);fbin(p/'q',q)
        ids=np.tile(np.arange(10,dtype='<i4'),(1000,1));dd=np.tile(np.sqrt(((x.astype(float)-x[0])**2).sum(1)),(1000,1));(p/'o').write_bytes(ids.tobytes()+dd.astype('<f8').tobytes());ids[:,:8].copy().tofile(p/'r.ids')
        c={'base':'x','query':'q','oracle':'o','N':10,'D':2};r=audit(p,c,p/'r');assert r['correct']
        bad=ids[:,:8].copy();bad[0,0]=9;bad.tofile(p/'bad.ids');assert not audit(p,c,p/'bad')['correct']
        bad[0,0]=bad[0,1];bad.tofile(p/'dup.ids');assert audit(p,c,p/'dup')['duplicate_rows']==1
    print('PASS audit, invalid ranking, duplicate IDs, paired CI, log slope')
if __name__=='__main__':test()
