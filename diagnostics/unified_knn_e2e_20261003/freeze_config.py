#!/usr/bin/env python3
"""Select declared anchors by the mean of two complete development passes."""
import hashlib
import json
from pathlib import Path
import subprocess
from native_knn import sha

ROOT=Path(__file__).resolve().parent

def main():
    selected={};anchors={};diagnostic={}
    for dataset in ('GIST','Deep'):
        for k in (8,32):
            for b in (1,32):
                shape=f'{dataset}_k{k}_b{b}';chosen={};anchors[shape]={};diagnostic[shape]={}
                for family in ('IVF','CAGRA'):
                    rows=json.loads((ROOT/f'DEV_{dataset}_{family}.json').read_text());groups={}
                    for row in rows:
                        if (row['K'],row['B'])==(k,b):groups.setdefault(json.dumps(row['config'],sort_keys=True),[]).append(row)
                    candidates=[]
                    for encoded,group in groups.items():
                        assert len(group)==2 and {r['repeat'] for r in group}=={1,2}
                        if all(r['quality']['output_contract_pass'] for r in group):
                            candidates.append({'config':json.loads(encoded),'mean_pass_ms':sum(r['pass_ms'] for r in group)/2,
                                'min_development_recall':min(r['quality']['recall_tie_aware'] for r in group)})
                    for target in (.99,.999,1.):
                        admitted=[c for c in candidates if c['min_development_recall']>=target]
                        key=f'{family}@{target}'
                        if not admitted:anchors[shape][key]={'status':'unreachable'};continue
                        point=min(admitted,key=lambda c:(c['mean_pass_ms'],json.dumps(c['config'],sort_keys=True)))
                        config=point['config'];full=family=='IVF' and config=={'nlist':1024,'nprobe':1024}
                        label='IVF_ALL' if full else f'IVF_n{config["nlist"]}_p{config["nprobe"]}' if family=='IVF' else f'CAGRA_t{config["itopk_size"]}_w{config["search_width"]}'
                        chosen.setdefault(label,{'label':label,'method':'IVF_ALL' if full else 'IVF_APPROX' if family=='IVF' else 'CAGRA',
                                               'config':config,'anchors':[]})['anchors'].append(key)
                        anchors[shape][key]={'status':'frozen','variant':label,**point}
                    if candidates:diagnostic[shape][family]=max(candidates,key=lambda c:(c['min_development_recall'],-c['mean_pass_ms']))
                selected[shape]=list(chosen.values())
    identity=json.loads((ROOT/'IDENTITY.json').read_text())
    assert identity['optimized_implementation_commit']
    frozen={'state':'FROZEN_BEFORE_NEW_FINAL','selected':selected,'anchors':anchors,'diagnostic_best':diagnostic,'identity':identity,
            'static_index_sha256':{p.name:sha(p) for p in sorted(ROOT.glob('*.index'))},
            'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.glob('*')) if p.suffix in ('.py','.cu','.cuh')},
            'warmup':'two first development batches; original adapter changed only to use these IDs',
            'index_policy':'CAGRA serialized full dataset and graph frozen; IVF trained empty index frozen, full index serialized hash each process; Flat rebuilt and hashed'}
    target=ROOT/'FROZEN_CONFIG.json';assert not target.exists();target.write_text(json.dumps(frozen,indent=2)+'\n')
    print('CONFIG FROZEN',flush=True)

if __name__=='__main__':main()
