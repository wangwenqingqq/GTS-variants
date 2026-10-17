"""Small falsification checks for the new validator and fixed estimator."""
import argparse,ctypes,json
from pathlib import Path
import numpy as np
from quality import native_fields
from analyze import paired
def fails(fn):
    try:fn()
    except AssertionError:return
    raise AssertionError('Required rejection did not occur')
def main():
    p=argparse.ArgumentParser();p.add_argument('--oracle',type=Path,required=True);a=p.parse_args()
    exact=np.array([0.,.123456789,1.],'<f8');native=exact.astype('<f4').astype('<f8');dist=np.sqrt(native).astype('<f4')
    native_fields(native,dist,exact,exact);bad=native.copy();bad[1]=np.nextafter(bad[1],np.inf);fails(lambda:native_fields(bad,dist,exact));bad=dist.copy();bad[1]=-bad[1];fails(lambda:native_fields(native,bad,exact));bad=exact.copy();bad[1]=np.nextafter(bad[1],np.inf);fails(lambda:native_fields(native,dist,exact,bad))
    fn=ctypes.CDLL(str(a.oracle.resolve())).replay;fn.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];fn.restype=ctypes.c_int
    cases=0
    for batch in (1,7,32):
        n=64;k=32;owner=list(range(n));reverse=list(range(n))+[-1]*k;next_id=n;victims=[];mutations=[];stops=np.array([0,8,16,24,32],'<i4');at=0
        for stop in stops:
            while at<stop:
                count=min(batch,int(stop)-at);ids=owner[-count:][::-1] if at else owner[:count]
                victims.extend(ids)
                for id in ids:
                    row=reverse[id];last=len(owner)-1;moved=owner[-1] if row!=last else -1;size=len(owner);mutations.append([0,id,size,row,last,moved,next_id,size-1])
                    if moved>=0:owner[row]=moved;reverse[moved]=row
                    owner.pop();reverse[id]=-1
                for _ in ids:
                    size=len(owner);mutations.append([1,next_id,size,size,-1,-1,next_id+1,size+1]);owner.append(next_id);reverse[next_id]=size;next_id+=1
                at+=count
        victims=np.array(victims,'<i4');mutations=np.array(mutations,'<i4');owner=np.array(owner,'<i4');reverse=np.array(reverse,'<i4');swaps=np.zeros(1,'<u8')
        def run():return fn(n,victims.ctypes.data,k,batch,stops.ctypes.data,mutations.ctypes.data,owner.ctypes.data,reverse.ctypes.data,swaps.ctypes.data)
        assert run()==0
        for column in range(8):
            original=mutations[0,column];mutations[0,column]=original+1;assert run()!=0;mutations[0,column]=original;cases+=1
        original=owner[0];owner[0]=-1;assert run()!=0;owner[0]=original
        original=reverse[-1];reverse[-1]=-1;assert run()!=0;reverse[-1]=original
        assert run()==0
    ratio=paired([1]*6,[2]*6);assert ratio['candidate_over_comparator']==.5 and ratio['bootstrap95']==[.5,.5] and ratio['process_wins']==6
    print(json.dumps(dict(passed=True,mutation_field_rejections=cases,fresh_occurrence_redeletion=True,native_field_rejections=3,paired_estimator=True,GPU_starts=0)))
if __name__=='__main__':main()
