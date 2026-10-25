"""Create small real-data empty/zero/all-hit sanitizer cases; never change full cases."""
import json,struct,subprocess,sys
from pathlib import Path

def main(root):
    root=Path(root).resolve();out=root/'bounded';out.mkdir()
    with (root/'fixtures/words.txt').open() as f:
        dim,n,metric=map(int,f.readline().split());assert n==611756 and metric==6
        lines=[f.readline() for _ in range(2000)];assert all(line.endswith('\n') for line in lines)
    (out/'words.txt').write_text(f'{dim} 2000 6\n'+''.join(lines))
    with (root/'fixtures/tloc.f32bin').open('rb') as f:
        assert struct.unpack('<iii',f.read(12))==(2,1000000,2)
        (out/'tloc.f32bin').write_bytes(struct.pack('<iii',2,2000,2)+f.read(2000*8))
    (out/'queries.qid').write_text('32\n'+'\n'.join(map(str,range(32)))+'\n')
    for name,rs in [('words',[-1,0,40]),('tloc',[-1,0,1000])]:
        data=out/('words.txt' if name=='words' else 'tloc.f32bin')
        subprocess.run([str(root/'bin/oracle'),'test',name,str(data),str(out/'queries.qid'),str(out/(name+'.oracle')),*map(str,rs)],check=True)
    (out/'scope.json').write_text(json.dumps({'N':2000,'Q':32,'IDs':list(range(32)),'radii':{'words':[-1,0,40],'tloc':[-1,0,1000]},'full_frozen_cases_modified':False},indent=2)+'\n')
if __name__=='__main__':main(sys.argv[1])
