"""Reuse Gate2's selected-function SASS normalization; CPU-only gate."""
import argparse,hashlib,subprocess,sys
from pathlib import Path
from trace import ART,HERE,read,save,sha
sys.path.insert(0,str(ART/'progressive_gpu_gate2_20261013'))
from static_evidence import functions,opcodes
def run(w):
    reg=read(w/'REGISTERED.json');ready=read(w/'READY.json');root=w/'build';texts={};records={}
    paths={'old_D0':Path(reg['old_strengthened_binary']),'Gate2':Path(reg['Gate2_binary']),'D0':root/'D0','D1':root/'D1'}
    for name,path in paths.items():
        p=root/(name+'.sass.txt');resource=root/(name+'.resources.txt')
        with p.open('x') as f:subprocess.run(['/usr/local/cuda-13.1/bin/cuobjdump','--dump-sass',str(path)],stdout=f,check=True)
        with resource.open('x') as f:subprocess.run(['/usr/local/cuda-13.1/bin/cuobjdump','--dump-resource-usage',str(path)],stdout=f,check=True)
        texts[name]=functions(p.read_text());records[name]=dict(container_sha256=sha(path),sass_dump_sha256=sha(p),resources_sha256=sha(resource))
    b={m:{k:v for k,v in texts[m].items() if 'squared_l2_b1' in k} for m in ('old_D0','D0')};assert len(b['D0'])==1 and b['D0']==b['old_D0'],'strengthened range kernel changed'
    p={m:{k:v for k,v in texts[m].items() if 'progressive_stage' in k or 'progressive_fields' in k} for m in ('Gate2','D1')};assert len(p['D1'])==5 and p['D1']==p['Gate2'],'Gate2 selected kernel codegen changed'
    selected={k:dict(normalized_sass_sha256=hashlib.sha256(v.encode()).hexdigest(),instructions=sum(opcodes(v).values()),opcodes=dict(opcodes(v))) for k,v in p['D1'].items()}
    assert ready['binaries']=={m:records[m]['container_sha256'] for m in ('D0','D1')}
    save(root/'STATIC.json',dict(passed=True,no_GPU_starts=True,registration_sha256=sha(w/'REGISTERED.json'),static_tool_sha256=sha(HERE/'static.py'),records=records,D0_selected_identical_to_strengthened=True,D1_selected_identical_to_Gate2=True,D0_kernel_hash=hashlib.sha256(next(iter(b['D0'].values())).encode()).hexdigest(),selected=selected))
    print('STATIC PASS: inherited B1 + five Gate2 selected SASS functions identical',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);run(p.parse_args().work)
