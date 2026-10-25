"""Small, CPU-only regression check for the oracle, calibration and admission."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from admission import gate,UUID
from fixtures import ids,freeze
from summarize_cpu import inspect

def read_oracle(p):
    with p.open('rb') as f:
        def read(fmt):
            n=struct.calcsize(fmt);b=f.read(n);assert len(b)==n;return struct.unpack(fmt,b)
        n,nq,nr=read('<iii');rs=read('<fff');out=[]
        for _ in range(nq):
            q,=read('<i');groups=[]
            for _ in range(nr):
                count,=read('<i');groups.append([read('<id') for _ in range(count)])
            out.append((q,groups))
        assert not f.read(1)
        return (n,nq,nr),rs,out

def main():
    here=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='cpu_test_',dir=here) as tmp:
        root=Path(tmp);exe=root/'oracle'
        subprocess.run(['c++','-std=c++17','-O3','-pthread',str(here/'oracle.cpp'),'-o',str(exe)],check=True)
        (root/'q').write_text('2\n0\n1\n')
        (root/'words').write_text('2 4 6\n\na\nab\nb\n')
        (root/'l2').write_bytes(struct.pack('<iii',2,4,2)+struct.pack('<8f',0,0,3,4,0,4,0,0))
        for kind,file,rs in [('words','words',[0,1,2]),('tloc','l2',[0,4,5])]:
            out=root/(kind+'.oracle');subprocess.run([str(exe),'test',kind,str(root/file),str(root/'q'),str(out),*map(str,rs)],check=True)
            header,radii,rows=read_oracle(out);assert header==(4,2,3) and tuple(rs)==radii
            expected=([[0,1,2,1],[1,0,1,1]] if kind=='words' else [[0,5,4,0],[5,0,3,5]])
            for qi,(qid,groups) in enumerate(rows):
                assert qid==qi
                for r,hits in zip(rs,groups):assert hits==[(i,float(d)) for i,d in enumerate(expected[qi]) if d<=r]
        synthetic=root/'packed.oracle'
        with synthetic.open('wb') as f:
            f.write(struct.pack('<iiifff',4,1024,3,0,1,2))
            for _ in range(1024):
                f.write(struct.pack('<i',0))
                for hits in [[(0,0.)],[(0,0.),(1,1.),(3,1.)],[(0,0.),(1,1.),(2,2.),(3,1.)]]:
                    f.write(struct.pack('<i',len(hits)))
                    for obj,d in hits:f.write(struct.pack('<id',obj,d))
        meta={'n':4,'radii':[0.,1.,2.],'test_qids':[0]*1024}
        counts=inspect(synthetic,meta);assert counts==[[1]*1024,[3]*1024,[4]*1024]
        with synthetic.open('r+b') as f:f.seek(36);f.write(struct.pack('<d',-1.))
        try:inspect(synthetic,meta)
        except AssertionError:pass
        else:raise AssertionError('invalid oracle distance was accepted')
        ids(root);before=(root/'words.test.qid').read_bytes();ids(root);assert (root/'words.test.qid').read_bytes()==before
        for name,n in [('words',611756),('tloc',1000000)]:
            raw={'n':n,'kth':[[.1,.2,.3]]*16,'histograms':[[r*500 for r in range(41)]]*16}
            (root/f'{name}.cal.json').write_text(json.dumps(raw))
        freeze(root);cal=json.loads((root/'calibration.json').read_text())
        assert cal['datasets']['words']['radii']==[1,1,2]
        assert abs(cal['datasets']['tloc']['radii'][0]-.1)<1e-8
        try:freeze(root)
        except AssertionError:pass
        else:raise AssertionError('must not overwrite frozen calibration')
    idle=f'{UUID}, GPU, 590.48.01, 14, 0, P8, 20, 180, 400'
    assert gate(idle,'')==[]
    assert 'foreign_compute_process_present' in gate(idle,'123, foreign, 80000')
    assert 'memory_above_256_MiB' in gate(idle.replace(', 14,',', 80000,'),'')
    assert 'wrong_gpu_uuid' in gate(idle.replace(UUID,'GPU-other'),'')
    assert gate('broken','')==['unparseable_gpu_state']
    print('PASS CPU oracle, frozen calibration, disjoint IDs, admission rejection; no GPU calls')

if __name__=='__main__':main()
