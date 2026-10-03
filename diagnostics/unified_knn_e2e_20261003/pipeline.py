#!/usr/bin/env python3
"""Finish the registered pilot, development, freeze, formal and attribution."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from campaign import run,BASE

ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--gpu',required=True);p.add_argument('--data-root',type=Path,required=True)
    p.add_argument('--faiss-python',required=True);p.add_argument('--cuvs-python',required=True)
    p.add_argument('--reuse-development',action='store_true');a=p.parse_args()
    def local(script,*args):
        subprocess.run(list(map(str,[sys.executable,ROOT/script,*args])),check=True)
    common=['--gpu',a.gpu,'--data-root',a.data_root,'--faiss-python',a.faiss_python,'--cuvs-python',a.cuvs_python]
    assert len(json.loads((ROOT/'SANITIZER.json').read_text()))==12
    qualified=json.loads((ROOT/'QUALIFICATION.json').read_text());assert len(qualified)==28
    assert all(r['quality']['coverage']['eligible_pairs_wrongly_excluded']==0 for r in qualified)
    local('campaign.py','pilot','--tag','pilot_v4',*common)
    for dataset in ('GIST','Deep'):
        for family in ('IVF','CAGRA'):
            if a.reuse_development:
                assert len(json.loads((ROOT/f'DEV_{dataset}_{family}.json').read_text()))==(104 if family=='IVF' else 120)
                print(f'REUSE FROZEN DEVELOPMENT {dataset} {family}',flush=True);continue
            python=a.cuvs_python if family=='CAGRA' else a.faiss_python
            run(a,f'development_{dataset}_{family}',[python,ROOT/'develop.py','--dataset',dataset,'--family',family,'--data-root',a.data_root])
            print(f'DEV READY {dataset} {family}',flush=True)
    local('freeze_config.py');local('freeze_queries.py')
    for dataset in ('GIST','Deep'):
        run(a,f'oracle_{dataset}_final256',[a.faiss_python,BASE/'native_ivf.py','oracle',
            '--data',a.data_root/f'{dataset}/1000000/fixtures/data.f32bin','--qids',ROOT/f'fixtures/{dataset}_final256.qid',
            '--out',ROOT/f'oracle_{dataset}_final256.json'])
        print(f'ORACLE READY {dataset}',flush=True)
    local('campaign.py','formal',*common)
    local('analyze.py')
    local('profile_queries.py',*common)
    local('analyze_profiles.py')
    (ROOT/'COMPLETE.json').write_text(json.dumps({'state':'COMPLETE','formal_processes':len(json.loads((ROOT/'FORMAL.json').read_text())),
        'complete_mode_processes':288,'pilot_processes':21,'new_final_queries_per_dataset':256,'profiling_separate':True},indent=2)+'\n')
    print('P7 COMPLETE',flush=True)

if __name__=='__main__':main()
