#!/usr/bin/env python3
"""Bounded admission for the optional adapter; retain the first rejection."""
import argparse
import json
from pathlib import Path
from campaign10k import ROOT,invoke,save,sha
from qualification import native_ivf,check_output

def main():
    p=argparse.ArgumentParser();p.add_argument('--gpu',required=True)
    p.add_argument('--p7',type=Path,required=True);p.add_argument('--python',required=True)
    p.add_argument('--data',type=Path,required=True);a=p.parse_args()
    rows=[];registration=ROOT/'REF64_QUALIFICATION_REGISTERED.json'
    manifest={'source_sha256':sha(ROOT/'flat_refine.py'),
              'small_shapes':{'D':[96,960],'K':[8,32],'B':[1,32],'Q':48,'tail':16},
              'later_gates':['synccheck diagnostic32','repeat developer1024','million-row developer48 tail16'],
              'role':'optional empirical adapter; raw Flat rejection remains unchanged'}
    if registration.exists():assert json.loads(registration.read_text())==manifest
    else:save(registration,manifest)
    def audit(label,data,ref,k):
        out=ROOT/'outputs'/label
        quality=check_output(str(out)+'.bin',native_ivf.load_data(data),ref,k)
        row={'label':label,'quality':quality,'output_sha256':sha(str(out)+'.bin')}
        rows.append(row);save(ROOT/'REF64_QUALIFICATION_PARTIAL.json',rows)
        assert quality['complete_gate_pass'],f'optional adapter output rejected: {label}'
    def run(label,data,qs,warm,ref,k,b,tool=None):
        cmd=[a.python,ROOT/'flat_refine.py','--data',data,'--qids',qs,'--warm',warm,
             '--k',k,'--b',b,'--out',ROOT/'outputs'/label]
        if tool:cmd=['/usr/local/cuda/bin/compute-sanitizer','--tool',tool,'--error-exitcode','90',*cmd]
        invoke(a,label,cmd);audit(label,data,ref,k)
        if tool:
            logs=''.join((ROOT/'runs'/label/f'{s}.log').read_text() for s in ('stdout','stderr'))
            assert 'ERROR SUMMARY: 0 errors' in logs
    ref=json.loads((ROOT/'oracle_GIST_dev1024.json').read_text())
    small_ref={**ref,'Q':32,'records':ref['records'][:32]}
    try:
        audit('flat_ref64_memcheck',a.data,small_ref,8)
        for d in (96,960):
            cpu=json.loads((ROOT/f'fixtures/cpu48_{d}.json').read_text())
            for k in (8,32):
                for b in (1,32):
                    run(f'ref64_small_d{d}_k{k}_b{b}',a.p7/f'fixtures/small{d}.f32bin',
                        ROOT/'fixtures/small48.qid',ROOT/'fixtures/small_warm256.qid',cpu,k,b)
        run('ref64_synccheck',a.data,ROOT/'fixtures/GIST_diagnostic32.qid',ROOT/'fixtures/GIST_warm32.qid',small_ref,8,32,'synccheck')
        run('ref64_developer_repeat',a.data,ROOT/'fixtures/GIST_dev1024.qid',ROOT/'fixtures/GIST_warm32.qid',ref,8,32)
        tail=ROOT/'fixtures/ref64_developer48.qid'
        if not tail.exists():tail.write_text('48\n'+''.join(f'{r["qid"]}\n' for r in ref['records'][:48]))
        run('ref64_million_tail48',a.data,tail,ROOT/'fixtures/GIST_warm32.qid',
            {**ref,'Q':48,'records':ref['records'][:48]},8,32)
        save(ROOT/'REF64_QUALIFICATION.json',{'state':'bounded_gates_passed','rows':rows,
             'remaining':['100 reuse cycles','other million-row shapes','formal qualification'],
             'completeness_proof':False})
    except Exception as e:
        save(ROOT/'REF64_QUALIFICATION.json',{'state':'rejected','error':str(e),'rows':rows,
             'remaining_gates':'not run after first rejection','completeness_proof':False});raise

if __name__=='__main__':main()
