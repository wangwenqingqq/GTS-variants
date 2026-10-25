"""Audit CPU-oracle structure and hashes, without claiming any GPU correctness."""
import hashlib,json,math,statistics,struct,sys
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

def inspect(path,meta):
    with path.open('rb') as f:
        def take(fmt):
            size=struct.calcsize(fmt);b=f.read(size);assert len(b)==size;return struct.unpack(fmt,b)
        n,nq,nr=take('<iii');radii=take('<fff')
        assert (n,nq,nr)==(meta['n'],1024,3) and list(radii)==meta['radii']
        counts=[[],[],[]]
        for q in meta['test_qids']:
            assert take('<i')[0]==q
            for k,r in enumerate(radii):
                count,=take('<i');assert 1<=count<=n;counts[k].append(count)
                # Packed ID/double records have no native-struct padding.
                packed=f.read(count*12);assert len(packed)==count*12
                last=-1;self_found=False
                for obj,d in struct.iter_unpack('<id',packed):
                    assert last<obj<n and math.isfinite(d) and 0<=d<=r
                    last=obj
                    if obj==q:assert d==0;self_found=True
                assert self_found
            assert counts[0][-1]<=counts[1][-1]<=counts[2][-1]
        assert not f.read(1)
    return counts

def main(root,output):
    root=Path(root);cal=json.loads((root/'fixtures/calibration.json').read_text())
    out={'scope':'CPU calibration/oracle only; no GPU output has been validated',
         'calibration_sha256':sha(root/'fixtures/calibration.json'),'datasets':{},'files':{}}
    for name,v in cal['datasets'].items():
        counts=inspect(root/f'fixtures/{name}.oracle',v)
        raw=json.loads((root/f'fixtures/{name}.cal.json').read_text())
        assert sha(root/f'fixtures/{name}.cal.json')==v['calibration_raw_sha256']
        assert sha(root/f'fixtures/{name}.test.qid')==v['test_qids_sha256']
        assert set(v['calibration_qids']).isdisjoint(v['test_qids'])
        cases=[]
        for k,target in enumerate(cal['targets']):
            for q in [1,32,1024]:
                c=counts[k][:q]
                cases.append({'target':target,'radius':v['radii'][k],'Q':q,'oracle_hits_min_median_max':[min(c),statistics.median(c),max(c)],'oracle_hits_total':sum(c)})
        out['datasets'][name]={'n':v['n'],'radii':v['radii'],'calibration_median_hits':
            [statistics.median(row[int(r)] for row in raw['histograms']) for r in v['radii']] if name=='words' else None,'cases':cases}
        for fn in [f'{name}.oracle',f'{name}.cal.json',f'{name}.cal.qid',f'{name}.test.qid']:
            p=root/'fixtures'/fn;out['files']['fixtures/'+fn]={'sha256':sha(p),'bytes':p.stat().st_size}
    for fn in ['words.txt','tloc.f32bin']:
        p=root/'fixtures'/fn;out['files']['fixtures/'+fn]={'sha256':sha(p),'bytes':p.stat().st_size}
    for fn in ['oracle.cpp','fixtures.py','admission.py','test_cpu.py','bin/oracle','CONTRACT.md']:
        p=root/fn;out['files'][fn]={'sha256':sha(p),'bytes':p.stat().st_size}
    Path(output).write_text(json.dumps(out,indent=2)+'\n')
    print('PASS complete CPU oracle structure; NOT a GPU validation')

if __name__=='__main__':main(*sys.argv[1:])
