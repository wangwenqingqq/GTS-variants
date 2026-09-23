#!/usr/bin/env python3
"""Record collection provenance once; retain full raw SASS only in scratch."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def record(root):
 p={'binaries':{v:sha(root/'bin'/v) for v in ['A','B','preflightA'] if (root/'bin'/v).exists()},'collection_source_sha256':{f.name:sha(f) for f in HERE.iterdir() if f.is_file() and f.suffix in ['.py','.cu','.cuh','.md']},'generated_manifest_sha256':{v:sha(root/f'final{v}/MANIFEST.json') for v in 'AB'},'candidate_source_variant':json.loads((root/'finalB/MANIFEST.json').read_text())['variant'],'functions':{},'hardware':{'physical_gpu':5,'name':'RTX PRO 6000 Blackwell Server Edition','sm_count':188,'driver':'590.48.01','toolkit':'13.1.115','cpu_wait':'default unchanged','pruning_mode':0},'build_flags':'-std=c++17 -O3 -arch=sm_120 -rdc=true -lineinfo -DGTS_DIAG_NVTX -Xptxas=-v -Xnvlink=--ignore-host-info -ldl'}
 for v in 'AB':
  p['functions'][v]={};resources=(root/f'logs/{v}.resources').read_text()
  for part in (root/f'logs/{v}.sass').read_text().split('Function : ')[1:]:
   name=part.splitlines()[0].strip()
   if not re.match(r'_Z\d+(dataProcessKnn|dataProcessKnnVec|mergeResKnn|mergeResKnnIds|nodeProcessKnn|getDisPQ)',name):continue
   ins=[re.sub(r'/\*.*?\*/','',l).strip() for l in part.splitlines() if re.match(r'\s*/\*[0-9a-f]+\*/',l)]
   line=resources.split('Function '+name+':')[1].splitlines()[1]
   p['functions'][v][name]={'normalized_instruction_sha256':hashlib.sha256(('\n'.join(ins)+'\n').encode()).hexdigest(),'instructions':len(ins),'resources':{k:int(value) for k,value in re.findall(r'(REG|STACK|SHARED|LOCAL):(\d+)',line)}}
 for name,cmd in [('nvcc',['/usr/local/cuda-13.1/bin/nvcc','--version']),('ncu',['/opt/nvidia/nsight-compute/2025.4.1/ncu','--version']),('nsys',['nsys','--version']),('g++',['g++','--version'])]:p[name+'_version']=subprocess.check_output(cmd,text=True)
 with (root/'logs/provenance.json').open('x') as f:json.dump(p,f,indent=2);f.write('\n')
 print('Recorded immutable collection provenance')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();record(a.root.resolve())
