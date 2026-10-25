"""CPU-only full retained-native-output audit, including every failed-case query."""
import collections,hashlib,json,math,struct,sys
from pathlib import Path

def read(f,n):
    b=f.read(n);assert len(b)==n;return b

def audit(root,epoch,out):
    root=Path(root);epoch=Path(epoch);quality=json.loads((epoch/'FULL_QUALITY.json').read_text());result={}
    for case in quality['cases']:
        kind,k,q=case['kind'],case['k'],case['Q'];reference=[]
        with (root/'fixtures'/(kind+'.oracle')).open('rb') as f:
            n,nq,nr=struct.unpack('<iii',read(f,12));assert nr==3 and q<=nq
            radii=struct.unpack('<fff',read(f,12))
            for qi in range(q):
                qid,=struct.unpack('<i',read(f,4))
                for j in range(3):
                    count,=struct.unpack('<i',read(f,4))
                    if j==k:group=list(struct.iter_unpack('<id',read(f,count*12)))
                    else:f.seek(count*12,1)
                reference.append((qid,group))
        for arm in ('ARS' if kind=='words' else 'ARSX'):
            label=f'full_{kind}_k{k}_q{q}_{arm}';path=root/quality['evidence'][label]['path']/'result.native.bin';mismatches=[];total=0;maxerror=0
            with path.open('rb') as f:
                for qi,(qid,expected) in enumerate(reference):
                    count,=struct.unpack('<i',read(f,4));assert 0<=count<=n
                    actual=sorted(struct.iter_unpack('<if',read(f,count*8)));total+=count
                    a=collections.Counter(i for i,d in actual);b=collections.Counter(i for i,d in expected)
                    extra=list((a-b).elements());missing=list((b-a).elements());ref=dict(expected);wrong=[]
                    for i,d in actual:
                        if i not in ref:continue
                        delta=abs(d-ref[i]);maxerror=max(maxerror,delta)
                        if not math.isfinite(d) or (delta!=0 if kind=='words' else delta>4e-6+4e-6*abs(ref[i])):wrong.append(i)
                    if extra or missing or wrong:mismatches.append({'query_index':qi,'query_id':qid,'extra':extra,'missing':missing,'distance_mismatch_ids':wrong})
                assert not f.read(1)
            status='pass' if not mismatches else 'correctness_failed';assert status==case['quality'][arm]
            result[label]={'dataset':kind,'target_index':k,'Q':q,'arm':arm,'radius':radii[k],'native_output_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'total_hits':total,'max_common_ID_distance_error':maxerror,'status':status,'mismatches':mismatches}
    assert len(result)==63 and sum(v['status']=='pass' for v in result.values())==60
    for v in result.values():
        if v['status']!='pass':assert len(v['mismatches'])==1 and v['mismatches'][0]['extra']==[417457] and not v['mismatches'][0]['missing'] and not v['mismatches'][0]['distance_mismatch_ids']
    Path(out).write_text(json.dumps(result,indent=2)+'\n')
    print('PASS independent complete native-output audit: 60 arm/cases exact IDs, 3 arm/cases with only the same single extra ID; all common distances pass')
if __name__=='__main__':audit(*sys.argv[1:])
