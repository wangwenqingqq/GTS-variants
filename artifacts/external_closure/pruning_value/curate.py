#!/usr/bin/env python3
"""Whitelist aggregate records and hashes; never publish vectors, outputs, commands or host configuration."""
import argparse,json,shutil
from pathlib import Path
from build import sha,save,outside_repo
if not __debug__:raise RuntimeError('Python assertions are required')
def main(a):
    a.output=outside_repo(a.output);a.output.mkdir(exist_ok=False)
    proof=json.loads((a.raw/'FINAL_PROOF_V3.json').read_text());assert proof['passed'] and proof['GPU_processes']==11 and proof['complete_answers']==3904
    for name in ('FINAL_PROOF','RAW_MANIFEST'):shutil.copy2(a.raw/(name+'_V3.json'),a.output/(name+'.json'))
    for name in ('MAINTENANCE_V2.json','CONTENT_IDENTITY.json','PREPARED.json'):shutil.copy2(a.raw/'maintenance'/name,a.output/('MAINTENANCE_PREPARED.json' if name=='PREPARED.json' else name))
    for name in ('initial','first_rebuilt'):
        for file in ('CAPTURE.json','layers.csv','subtree_sizes.csv','queries.csv'):
            shutil.copy2(a.campaign/(name+'_cache')/file,a.output/(name+'_'+file))
        for file in ('TIMING.json','passes.csv'):shutil.copy2(a.campaign/(name+'_timing_checked')/file,a.output/(name+'_'+file))
        for file in ('queries.csv','META.json'):shutil.copy2(a.campaign/(name+'_timing')/file,a.output/(name+'_timing_'+file))
    save(a.output/'PUBLISH_MANIFEST.json',{p.name:sha(p) for p in sorted(a.output.iterdir()) if p.is_file()})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--campaign',type=Path,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
