"""CPU-only code-generation ledger; no runtime/performance claim."""
import argparse,collections,re,subprocess
from pathlib import Path
from pre_cost import read,save,sha,HERE
def functions(text):
    out={}
    for part in text.split('Function : ')[1:]:
        name=part.splitlines()[0].strip();lines=[]
        for line in part.splitlines()[1:]:
            if '/*' not in line:continue
            clean=re.sub(r'/\*.*?\*/','',line).strip()
            if clean:lines.append(clean)
        out[name]='\n'.join(lines)+'\n'
    return out
def opcodes(text):
    words=[line.split() for line in text.splitlines() if line.strip()]
    return collections.Counter(row[1 if row[0].startswith('@') else 0].split('.')[0] for row in words)
def run(w):
    r=read(w/'REGISTERED.json');root=w/'build';texts={};records={}
    for name,path in [('keeper',Path(r['keeper_binary'])),('keeper_diagnostic',root/'keeper_diagnostic'),('candidate',root/'candidate')]:
        p=root/(name+'.sass.txt')
        with p.open('x') as f:subprocess.run(['/usr/local/cuda-13.1/bin/cuobjdump','--dump-sass',str(path)],stdout=f,check=True)
        resource=root/(name+'.resources.txt')
        with resource.open('x') as f:subprocess.run(['/usr/local/cuda-13.1/bin/cuobjdump','--dump-resource-usage',str(path)],stdout=f,check=True)
        texts[name]=functions(p.read_text());records[name]=dict(container_sha256=sha(path),sass_dump_sha256=sha(p),resources_sha256=sha(resource))
    import hashlib
    b={k:v for k,v in texts['keeper'].items() if 'squared_l2_b1' in k};d={k:v for k,v in texts['keeper_diagnostic'].items() if 'squared_l2_b1' in k};assert len(b)==1 and b==d
    selected={}
    for k,v in texts['candidate'].items():
        if 'progressive_stage' not in k and 'progressive_fields' not in k:continue
        ops=opcodes(v)
        selected[k]=dict(normalized_sass_sha256=hashlib.sha256(v.encode()).hexdigest(),static_instruction_count=sum(ops.values()),opcode_counts=dict(ops))
    assert len(selected)==5
    for k,v in selected.items():
        if 'progressive_stage' in k:assert v['opcode_counts'].get('DADD',0)>0 and v['opcode_counts'].get('DMUL',0)>0 and v['opcode_counts'].get('FFMA',0)>0
        assert not any(x in v['opcode_counts'] for x in ('HMMA','QMMA','IMMA','DMMA','LDL','STL')),'no TC or static local spill path'
    save(root/'STATIC.json',dict(passed=True,scope='Static generated-code gate only',records=records,keeper_selected_function=next(iter(b)),keeper_selected_sass_sha256=hashlib.sha256(next(iter(b.values())).encode()).hexdigest(),keeper_diagnostic_selected_bits_equal=True,candidate_functions=selected,static_tool_sha256=sha(HERE/'static_evidence.py'),registration_sha256=sha(w/'REGISTERED.json'),no_GPU_starts=True))
    print('STATIC PASS: B1 diagnostic selected SASS identical;5 P1 kernels;no TC/local path',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);run(p.parse_args().work)
