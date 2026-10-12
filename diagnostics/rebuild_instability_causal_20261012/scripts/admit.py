#!/usr/bin/env python3
"""Generate one conditional dose admission from immutable preceding results."""
import argparse,json
from pathlib import Path
from analyze import sha,dump

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('phase',choices=['C2','C3']);a=p.parse_args()
    phase=a.phase;previous='C1' if phase=='C2' else 'C2';evidence=a.root/f'summary_{previous}/RESULT.json';result=json.loads(evidence.read_text());facts=[]
    out=a.root/f'ADMIT_{phase}.json';assert not out.exists(),'preserve original gate decisions'
    for x in result['rebuilds']:
        modes={m['mode']:m for m in x['modes']};c0=modes['C0'];m=modes[previous]
        native=c0['vs_pre']['leaf']['changed_fraction'];churn=m['vs_pre']['leaf']['changed_fraction']
        if phase=='C2':
            l1=m['vs_pre']['levels'][1];root=m['boundary'][0]
            assert l1['matched_correspondence']==10 and l1['same_pivot_under_correspondence']<=3 and root['changed_segment_objects']<=20,'observed rapid early instability route not reproduced'
        else:
            assert churn<=.5 or native-churn>=.3,'C2 failed preservation screen'
        facts.append({'rebuild':x['rebuild'],'C0_leaf_churn':native,f'{previous}_leaf_churn':churn,'absolute_reduction_percentage_points':100*(native-churn)})
    binding={}
    if phase=='C3':
        for current,saved in (('CLOSURE.json','CLOSURE_C2_v1.json'),('RAW_MANIFEST.json','RAW_MANIFEST_C2_v1.json')):
            source=a.root/current;target=a.root/saved
            if target.exists():assert sha(target)==sha(source),'preserved C2 metadata differs'
            else:target.write_bytes(source.read_bytes())
        closure=json.loads((a.root/'CLOSURE_C2_v1.json').read_text())
        assert closure['passed'] and closure['actual_gpu_construction_processes']==8
        assert closure['result_sha256']==sha(evidence) and closure['raw_manifest_sha256']==sha(a.root/'RAW_MANIFEST_C2_v1.json')
        binding['C2_closure_sha256']=sha(a.root/'CLOSURE_C2_v1.json')
    dump(out,{**binding,'admitted':True,'phase':phase,'budget':2,'contract_sha256':sha(a.root/'CONTRACT.json'),'evidence_sha256':sha(evidence),'reason':'Reproduce the recorded rapid-early-divergence C2 route or predeclared >=30 pp C3 screen; no automatic deeper expansion','facts':facts,'strict_monotonic_caveat':'A nonmonotonic root-only dose must remain disclosed; do not waive the final full-dose gate.'})
if __name__=='__main__':main()
