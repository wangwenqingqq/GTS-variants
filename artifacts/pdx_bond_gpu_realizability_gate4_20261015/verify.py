"""Public-subset reconstruction, host fixtures, and honest unexecuted GPU boundary."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from analyze import analyze,load,sha

HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();assert (a.repo/'artifacts/pdx_bond_gpu_realizability_gate4_20261015').resolve()==HERE
    manifest=load(HERE/'PUBLIC_MANIFEST.json')['files']
    files={str(p.relative_to(HERE)):p for p in HERE.rglob('*') if p.is_file() and p.name!='PUBLIC_MANIFEST.json'}
    assert set(files)==set(manifest)
    for n,r in manifest.items():
        assert not files[n].is_symlink() and files[n].stat().st_size==r['bytes'] and sha(files[n])==r['sha256']
    c=load(HERE/'CONTRACT.json');g=load(HERE/'GPU_CONTRACT.json');e=load(HERE/'evidence/EXECUTION.json')
    assert sha(HERE/'CONTRACT.json')==e['contract_sha256']==g['cpu_contract_sha256']
    assert all(sha(a.repo/n)==h for n,h in c['parents'].items())
    assert all(sha(a.repo/n)==h for n,h in g['parents'].items())
    for n,h in e['executed_source_hashes'].items():assert sha(HERE/n if n in files else a.repo/n)==h
    assert e['population_starts']==1 and e['complete_population_pairs']==32000000
    assert e['GPU_starts']==e['NCU_starts']==e['CUDA_initializations']==0
    assert not g['decision_priority_approved']
    preparation=load(HERE/'evidence/GPU_PREPARATION.json')
    assert preparation['GPU_starts']==preparation['nvcc_invocations']==0 and not preparation['GPU_work_created']
    assert len(preparation['mismatches'])==4 and sum(r['missing'] for r in preparation['mismatches'])==1
    for n in ('gpu/KEEPER_TIMING.json','gpu/PDX_TIMING.json','gpu/DRAM.json','gpu/OP_BREAKDOWN.json','quality/EXACTNESS.json'):
        r=load(HERE/n);assert r['status']=='NOT_RUN'
        assert all(v is None for k,v in r.items() if k not in ('status','reason'))
    a.out.mkdir(parents=True,exist_ok=False)
    result=analyze(a.repo,load(HERE/'evidence/SCALARS.json'),a.out/'analysis')
    assert result['GPU_admitted'] and result['final'] is None and result['logical']=='LOGICAL_MODERATE' and result['source']=='SOURCE_WIN'
    for path in (a.out/'analysis').rglob('*.json'):
        assert load(path)==load(HERE/path.relative_to(a.out/'analysis'))
    command=['g++',*c['compiler_flags'],str(HERE/'pdx.cpp'),'-o',str(a.out/'pdx.so')]
    subprocess.run(command,check=True)
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PDX_LIBRARY':str(a.out/'pdx.so')}
    subprocess.run([sys.executable,'-m','unittest','-v','test_pdx'],cwd=HERE,env=env,check=True)
    refused=subprocess.run([sys.executable,'-O',str(HERE/'run.py')],env=env,capture_output=True)
    assert refused.returncode!=0 and b'Optimized Python disables mandatory checks' in refused.stderr
    # Source generator smoke test is CPU-only; it proves no CUDA compilation.
    import gpu_prepare
    keeper,candidate,fixture=gpu_prepare.headers(a.repo)
    assert candidate.count('>(database,query,order,inverse,')==4
    assert 'ordered_subset(x,q,owner,END,inverse)' in candidate and 'ordered_prefix(x,q,owner,960)' in candidate
    assert 'fixture FP64 authority' in fixture and 'std::partial_sort' in candidate
    assert all(sha(files[n])==r['sha256'] for n,r in manifest.items())
    receipt={'passed':True,'public_files':len(files)+1,'full_population_histograms_reconstructed':64,
             'CPU_fixtures_passed':4,'GPU_source_generation_only':True,'GPU_starts':0,
             'GPU_performance_or_final_label':'NOT_ESTABLISHED','raw_vectors_not_recomputed':True,
             'public_manifest_sha256':sha(HERE/'PUBLIC_MANIFEST.json')}
    (a.out/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__':main()
