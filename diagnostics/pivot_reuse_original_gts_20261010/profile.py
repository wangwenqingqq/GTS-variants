#!/usr/bin/env python3
"""Query-only G0/G1 NSYS attribution, reusing the preceding SQLite analyzer."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('campaign','reference','data','out','trace-analyzer'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--python',required=True);p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True)
    a=p.parse_args();c=a.campaign.resolve();out=a.out.resolve();ref=a.reference.resolve();data=a.data.resolve()
    sys.path.insert(0,str(c));from run import sha,write,runtime_errors
    from analyze import validate_chain
    contract,frozen=validate_chain(c);identity=frozen['identity']
    assert a.gpu==identity['gpu'] and a.numa==identity['numa']
    assert sha(data)==identity['data_sha256'] and sha(ref/'GIST.index')==identity['index_sha256']
    design=Path(__file__).with_name('PROFILE_CONTRACT.json')
    assert sha(a.trace_analyzer)==json.loads(design.read_text())['trace_analyzer_sha256']
    spec=importlib.util.spec_from_file_location('trace_analysis',a.trace_analyzer.resolve())
    analyzer=importlib.util.module_from_spec(spec);spec.loader.exec_module(analyzer)
    nsys=str(Path(shutil.which('nsys')).resolve())
    inputs={**{'campaign/'+n:c/n for n in identity if n not in ('data_sha256','index_sha256','gpu','numa')},
            'extension/profile.py':Path(__file__),'extension/PROFILE_CONTRACT.json':design,
            'campaign/analyze.py':c/'analyze.py','campaign/run.py':c/'run.py',
            'data':data,'index':ref/'GIST.index','diag32.qid':c/'diag32.qid',
            'oracle_diag32.json':c/'oracle_diag32.json',
            'analyzer':a.trace_analyzer,'nsys':Path(nsys)}
    before={name:sha(path) for name,path in inputs.items()}
    out.mkdir(exist_ok=False);results={}
    write(out/'PROFILE_FROZEN.json',{'inputs':before,'frozen_production_identity':identity,
          'tool_version':subprocess.check_output([nsys,'--version'],text=True).strip()})
    for mode in ('G0','G1'):
        binary=c/f'v2/{mode}.bench';assert sha(binary)==identity[f'v2/{mode}.bench']
        prefix=out/mode;report=out/'runs'/mode
        command=[sys.executable,c/'locked.py','--gpu',a.gpu,'--numa-node',str(a.numa),'--output',report,'--',
            nsys,'profile','--trace=cuda,nvtx,osrt','--sample=none','--cpuctxsw=none','--capture-range=nvtx',
            '--nvtx-capture=formal.query_pass','--env-var=NSYS_NVTX_PROFILER_REGISTER_ONLY=0',
            '--capture-range-end=stop','--force-overwrite=false','-o',prefix,
            binary,data,c/'diag32.qid',8,1,1,ref/'GIST.index',prefix,2]
        subprocess.run(list(map(str,command)),check=True)
        receipt=json.loads((report/'receipt.json').read_text());assert receipt['runtime_valid']
        assert not runtime_errors((report/'stdout.log').read_text()+(report/'stderr.log').read_text())
        quality=out/(mode+'.quality.json')
        subprocess.run([a.python,c/'helpers/verify_outputs.py','check-gts','--data',data,
            '--reference',c/'oracle_diag32.json','--result',out/(mode+'.bin'),'--out',quality],check=True)
        q=json.loads(quality.read_text());assert q['recall_tie_aware']==1 and q['distance_tolerance_pass']
        subprocess.run([nsys,'export','--type=sqlite','--output',out/(mode+'.sqlite'),out/(mode+'.nsys-rep')],check=True)
        results[mode]=analyzer.trace(out/(mode+'.sqlite'))
        results[mode].update({'quality':q,'receipt_sha256':sha(report/'receipt.json'),
                             'nsys_report_sha256':sha(out/(mode+'.nsys-rep')),'binary_sha256':sha(binary)})
    assert (out/'G0.bin').read_bytes()==(out/'G1.bin').read_bytes()
    assert before=={name:sha(path) for name,path in inputs.items()},'profile collection drift'
    write(out/'PROFILE_RESULT.json',{'scope':'diagnostic only, no formal speed ratio','results':results,
        'contract_sha256':sha(design),'frozen_manifest_sha256':sha(out/'PROFILE_FROZEN.json'),
        'trace_analyzer_sha256':sha(a.trace_analyzer),'nsys_executable_sha256':sha(Path(nsys)),
        'full_bins_bit_identical':True})
    print('PASS query-scoped G0/G1 profile attribution and complete result equality')

if __name__=='__main__':main()
