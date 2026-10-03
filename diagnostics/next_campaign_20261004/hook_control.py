#!/usr/bin/env python3
"""Development-only observer overhead control; immutable search sources."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from campaign10k import ROOT,commands,common,invoke,save,sha
from qualification import native_ivf,check_output

def main():
    p=argparse.ArgumentParser();p.add_argument('--gpu',required=True);p.add_argument('--p7',type=Path,required=True)
    p.add_argument('--data-root',type=Path,required=True);p.add_argument('--faiss-python',required=True);p.add_argument('--cuvs-python',required=True);a=p.parse_args()
    dest=ROOT/'hook_control';dest.mkdir(exist_ok=True)
    # Host observer stub is the sole search-adapter difference. Kernel headers
    # and all native search calls remain byte-identical to the admitted runtime.
    for name in ('opt_knn_bench.cu','knn_cutoff.cuh','knn_select.cuh','knn_verify.cuh','native_knn.py'):
        shutil.copy2(ROOT/name,dest/name)
    (dest/'query_trace.hpp').write_text('#pragma once\n#include <string>\nstruct QueryTrace {explicit QueryTrace(std::string){} void begin(){} void sample(int,int){} void finish(double){} };\n')
    (dest/'query_trace.py').write_text('class QueryTrace:\n    def __init__(self,out):pass\n    def begin(self):pass\n    def sample(self,q,total):pass\n    def finish(self,total_ms):pass\n')
    path=dest/'native_knn.py';text=path.read_text();text=text.replace('from qualification import BASE,native_ivf,check_output','import sys\nsys.path.append(str(Path(__file__).resolve().parent.parent))\nfrom qualification import BASE,native_ivf,check_output');path.write_text(text)
    for path in ROOT.glob('*.index'):
        link=dest/path.name
        if not link.exists():link.symlink_to(path)
    build=['/usr/local/cuda/bin/nvcc','-O3','-std=c++17','-arch=sm_120','--fmad=false','-lineinfo',str(dest/'opt_knn_bench.cu'),'-o',str(dest/'opt_knn_bench')]
    with (dest/'BUILD.log').open('w') as log:subprocess.run(build,stdout=log,stderr=subprocess.STDOUT,check=True)
    save(dest/'SOURCE.json',{'control':'only QueryTrace replaced by no-op; native import bridge declared','build':build,
         'sources':{p.name:sha(p) for p in dest.iterdir() if p.suffix in ('.cu','.cuh','.hpp','.py')},'binary_sha256':sha(dest/'opt_knn_bench')})
    ref=json.loads((ROOT/'oracle_GIST_dev1024.json').read_text());source=native_ivf.load_data(a.data_root/'GIST/1000000/fixtures/data.f32bin')
    qs=ROOT/'fixtures/GIST_dev1024.qid';rows=[]
    for round_no in range(1,7):
        variants=('on','off') if round_no%2 else ('off','on')
        for m in ('O_BOUND','FAISS_FLAT','CAGRA'):
            for variant in variants:
                label=f'hook_r{round_no}_{m}_{variant}';out=dest/label
                c={'itopk_size':1024,'search_width':4} if m=='CAGRA' else {}
                cmd=commands(a,'GIST',m,8,32,qs,out,c)
                if variant=='off':
                    if m=='O_BOUND':cmd[0]=dest/'opt_knn_bench'
                    else:cmd[1]=dest/'native_knn.py'
                receipt=invoke(a,label,cmd)
                meta=json.loads(Path(str(out)+'.json').read_text());quality=check_output(str(out)+'.bin',source,ref,8)
                assert quality['output_contract_pass']
                if m!='CAGRA':assert quality['complete_gate_pass']
                rows.append({'label':label,'round':round_no,'method':m,'variant':variant,'pass_ms':meta['pass_ms'],
                             'quality':quality,'result_sha256':sha(str(out)+'.bin'),'receipt':receipt})
                save(ROOT/'HOOK_CONTROL.json',rows)
        for m in ('O_BOUND','FAISS_FLAT','CAGRA'):
            pair=[r for r in rows if r['round']==round_no and r['method']==m]
            assert pair[0]['result_sha256']==pair[1]['result_sha256'],'hook altered outputs'
    save(ROOT/'HOOK_CONTROL_COMPLETE.json',{'state':'complete','processes':36,'Q':1024,'shape':'GIST/K8/B32','directions_each':3,
         'scope':'development-only measurement overhead; full delivered output hashes identical; native ANN quality retained',
         'rows_sha256':sha(ROOT/'HOOK_CONTROL.json')})

if __name__=='__main__':main()
