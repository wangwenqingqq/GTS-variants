#!/usr/bin/env python3
"""Correctness-only extension against frozen binaries, after formal completion."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys

def add_ties(reference,ks):
    for record in reference['records']:
        for k in ks:
            value=record['squared'][k-1]
            # If the boundary extends outside the retained top32, the exhaustive
            # oracle already retained every K32-boundary ID, not just that prefix.
            boundary=(record['ties']['32']['boundary_ids'] if value==record['squared'][31]
                      else [i for i,d in zip(record['ids'],record['squared']) if d==value])
            record['ties'][str(k)]={'strictly_closer_ids':[i for i,d in zip(record['ids'],record['squared']) if d<value],
                                   'boundary_ids':boundary,'boundary_squared':value}
    return reference

def last_leaf(path):
    raw=path.read_bytes();n,d,h,count=struct.unpack_from('<4i',raw)
    ids=struct.unpack_from(f'<{n}i',raw,16);offset=16+4*n
    nodes=list(struct.iter_unpack('<ifiii',raw[offset:offset+20*count]))
    flags=struct.unpack_from(f'<{count}i',raw,offset+20*count)
    nid=max(i for i,x in enumerate(nodes) if not flags[i] and x[4] and x[2]>0)
    node=nodes[nid]
    return {'qid':ids[node[3]+node[2]-1],'node_id':nid,'leaf_lid':node[3],'leaf_size':node[2]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('campaign','reference','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--python',required=True);p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True)
    a=p.parse_args();c=a.campaign.resolve();ref=a.reference.resolve();out=a.out.resolve()
    sys.path.insert(0,str(c));from run import sha,write,runtime_errors
    from analyze import validate_chain
    contract,frozen=validate_chain(c);identity=frozen['identity']
    assert a.gpu==identity['gpu'] and a.numa==identity['numa']
    for mode in ('G0','G1'):assert sha(c/f'v2/{mode}.bench')==identity[f'v2/{mode}.bench']
    design=Path(__file__).with_name('BOUNDARY_CONTRACT.json')
    reference_pins=json.loads(design.read_text())['reference_sha256']
    for name,digest in reference_pins.items():assert sha(ref/name)==digest,('reference drift',name)
    inputs={**{'reference/'+n:ref/n for n in reference_pins},
            **{'campaign/'+n:c/n for n in identity if n not in ('data_sha256','index_sha256','gpu','numa')},
            'extension/boundary.py':Path(__file__),'extension/BOUNDARY_CONTRACT.json':design,
            'campaign/analyze.py':c/'analyze.py','campaign/run.py':c/'run.py'}
    before={name:sha(path) for name,path in inputs.items()}
    out.mkdir(exist_ok=False);ks=[1,2,7,8,9,31,32];rows=[]
    write(out/'BOUNDARY_FROZEN.json',{'inputs':before,'frozen_production_identity':identity,'scope':'correctness-only extension'})
    def launch(label,cmd,expected_error=None):
        report=out/'runs'/label
        result=subprocess.run([sys.executable,c/'locked.py','--gpu',a.gpu,'--numa-node',str(a.numa),
                               '--output',report,'--',*map(str,cmd)])
        receipt=json.loads((report/'receipt.json').read_text())
        logs=(report/'stdout.log').read_text()+(report/'stderr.log').read_text()
        assert receipt['stop_reason'] is None
        assert not json.loads((report/'after.json').read_text())['apps']
        assert all(not x['foreign'] for x in json.loads((report/'checks.json').read_text()))
        if expected_error:
            assert result.returncode==1 and receipt['exit_code']==1 and expected_error in logs
            assert runtime_errors(logs)==['FAIL: '+expected_error]
        else:assert result.returncode==0 and receipt['runtime_valid'] and not runtime_errors(logs)
        rows.append({'label':label,'expected_rejection':expected_error,'receipt_sha256':sha(report/'receipt.json'),
                     'stdout_sha256':sha(report/'stdout.log'),'stderr_sha256':sha(report/'stderr.log')})
    def check_query(label,mode,d,k,qids,oracle):
        table=ref/f'synthetic_{d}.f32bin';index=ref/f'synthetic{d}.index'
        assert table.is_file() and index.is_file()
        launch(label,[c/f'v2/{mode}.bench',table,qids,k,1,1,index,out/label,2])
        quality=out/(label+'.quality.json')
        subprocess.run([a.python,c/'helpers/verify_outputs.py','check-gts','--data',table,
                        '--reference',oracle,'--result',out/(label+'.bin'),'--out',quality],check=True)
        x=json.loads(quality.read_text());assert x['recall_tie_aware']==1 and x['distance_tolerance_pass']
        rows[-1].update({'quality':x,'quality_sha256':sha(quality),'result_sha256':sha(out/(label+'.bin'))})
    for d in (96,960):
        oracle=out/f'oracle_allk_{d}.json'
        write(oracle,add_ties(json.loads((ref/f'oracle_synthetic{d}.json').read_text()),ks))
        for k in ks:
            for mode in ('G0','G1'):check_query(f'd{d}_k{k}_{mode}',mode,d,k,ref/'fixtures/synthetic_ragged33.qid',oracle)
            assert (out/f'd{d}_k{k}_G0.bin').read_bytes()==(out/f'd{d}_k{k}_G1.bin').read_bytes()
        target=last_leaf(ref/f'synthetic{d}.index');write(out/f'last_leaf_{d}.json',target)
        qids=out/f'last_leaf_{d}.qid';qids.write_text(f"1\n{target['qid']}\n")
        last_oracle=out/f'oracle_last_{d}.json'
        launch(f'oracle_last_{d}',[a.python,c/'helpers/native_ivf.py','oracle','--data',ref/f'synthetic_{d}.f32bin',
                                 '--qids',qids,'--out',last_oracle])
        for mode in ('G0','G1'):check_query(f'last_d{d}_{mode}',mode,d,8,qids,last_oracle)
        assert (out/f'last_d{d}_G0.bin').read_bytes()==(out/f'last_d{d}_G1.bin').read_bytes()
    small=out/'N4.f32bin';small.write_bytes(struct.pack('<3i',96,4,2)+bytes(4*96*4))
    qids=out/'N4.qid';qids.write_text('1\n0\n')
    for mode in ('G0','G1'):
        for name,table,queries,k,b,error in [('N4',small,qids,8,1,'data outside contract'),
          ('B32',ref/'synthetic_96.f32bin',ref/'fixtures/synthetic_ragged33.qid',8,32,'arguments outside contract'),
          ('K33',ref/'synthetic_96.f32bin',ref/'fixtures/synthetic_ragged33.qid',33,1,'arguments outside contract')]:
            launch(name+'_'+mode,[c/f'v2/{mode}.bench',table,queries,k,b,1,ref/'synthetic96.index',out/(name+'_'+mode),0],error)
    assert before=={name:sha(path) for name,path in inputs.items()},'extension drift'
    write(out/'BOUNDARY_RESULT.json',{'scope':'correctness only; no latency ratio','frozen_identity':identity,
          'frozen_manifest_sha256':sha(out/'BOUNDARY_FROZEN.json'),'contract_sha256':sha(design),'rows':rows,
          'full_bins_bit_identical':True,'root_leaf_N_less_K':'unsupported, explicitly rejected; not a full-search pass'})
    print('PASS post-confirmation admitted-boundary matrix and explicit unsupported-input rejection')

if __name__=='__main__':main()
