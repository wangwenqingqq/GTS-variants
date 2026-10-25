"""Freeze disjoint deterministic query IDs and calibration-only radii."""
import hashlib,json,random,statistics,struct,sys
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ids(root):
    for name,n in [('words',611756),('tloc',1000000)]:
        sample=random.Random(20261024).sample(range(n),1040)
        assert len(set(sample))==1040
        for phase,qs in [('cal',sample[:16]),('test',sample[16:])]:
            (root/f'{name}.{phase}.qid').write_text(str(len(qs))+'\n'+'\n'.join(map(str,qs))+'\n')

def freeze(root):
    dest=root/'calibration.json';assert not dest.exists()
    out={'seed':20261024,'targets':[10,100,1000],'datasets':{}}
    for name in ['words','tloc']:
        raw=json.loads((root/f'{name}.cal.json').read_text())
        if name=='words':
            rs=[next(r for r in range(41) if statistics.median(row[r] for row in raw['histograms'])>=k) for k in [10,100,1000]]
        else:rs=[struct.unpack('<f',struct.pack('<f',statistics.median(row[k] for row in raw['kth'])))[0] for k in range(3)]
        cal=list(map(int,(root/f'{name}.cal.qid').read_text().split()))[1:]
        test=list(map(int,(root/f'{name}.test.qid').read_text().split()))[1:]
        assert len(cal)==16 and len(test)==1024 and set(cal).isdisjoint(test)
        out['datasets'][name]={'n':raw['n'],'radii':rs,'calibration_qids':cal,'test_qids':test,'calibration_raw_sha256':sha(root/f'{name}.cal.json'),'test_qids_sha256':sha(root/f'{name}.test.qid')}
    dest.write_text(json.dumps(out,indent=2)+'\n');print(dest,sha(dest))

if __name__=='__main__':
    mode,path=sys.argv[1:];globals()[mode](Path(path))
