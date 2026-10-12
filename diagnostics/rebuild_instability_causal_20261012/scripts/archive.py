#!/usr/bin/env python3
"""Create private full replay and small independent-structure verification bundles."""
import argparse,json,tarfile
from pathlib import Path
from analyze import sha,dump

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('prior',type=Path);a=p.parse_args();r=a.root
    raw=json.loads((r/'RAW_MANIFEST.json').read_text());assert json.loads((r/'CLOSURE.json').read_text())['raw_manifest_sha256']==sha(r/'RAW_MANIFEST.json')
    extras=[f for f in r.iterdir() if f.is_file() and f.suffix in ('.json','.log','.patch')]+list((r/'source').rglob('*'))+list((r/'scripts').rglob('*.py'))+list((r/'scripts').rglob('*.cu'))+list((r/'scripts').rglob('*.hpp'))+list((r/'failed_launch_v1').rglob('*'))
    extras=[f for f in extras if f.is_file()]+[r/'replay']
    extras+=list((r/'inputs').glob('*.json'))
    for name in ('summary_C1','summary_C2','summary_final'):extras+=list((r/name).glob('*.json'))
    full={name:r/name for name in raw};full.update({str(f.relative_to(r)):f for f in extras})
    for name,e in raw.items():assert sha(r/name)==e['sha256'] and (r/name).stat().st_size==e['bytes']
    small={name:p for name,p in full.items() if not name.startswith('runs/') or name.split('/')[-1] in ('order.i32','nodes.bin','empty.i32','DECISIONS.csv','REPLAY.json','PROCESS.json','NATIVE_GATE.json','VALIDITY.json','receipt.json')}
    small={name:p for name,p in small.items() if not name.startswith('failed_launch_v1/runs/') or p.suffix in ('.json','.log','.csv')}
    for snapshot in ('PRE_R1','POST_R1','PRE_R2','POST_R2'):
        for name in ('base.i32','live.i32','order.i32','nodes.bin','empty.i32'):
            small[f'prior_snapshots/{snapshot}/{name}']=a.prior/'snapshots'/snapshot/name
    manifests={}
    for label,entries in (('FULL_RAW',full),('SMALL_RAW',small)):
        archive=r/f'{label}.tar.gz';assert not archive.exists(),'preserve existing archive'
        manifest={name:{'bytes':p.stat().st_size,'sha256':sha(p)} for name,p in sorted(entries.items())}
        dump(r/f'{label}_MANIFEST.json',manifest)
        with tarfile.open(archive,'w:gz',compresslevel=1) as t:
            for name,p in sorted(entries.items()):t.add(p,arcname=name,recursive=False)
        manifests[label]={'archive_file':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive),'manifest_sha256':sha(r/f'{label}_MANIFEST.json'),'files':len(entries),'uncompressed_bytes':sum(e['bytes'] for e in manifest.values())}
    dump(r/'ARCHIVES.json',{'archives':manifests,'input_coordinates':'four 3.84 GB derived AoS files excluded; hashes and inverse-pack closure retained; original packed snapshot coordinates retained separately','raw_keys':'included in private FULL_RAW only','small_bundle':'complete PRE/POST and replay structures, decisions, pins and closures; raw distance keys not included'})
    print(json.dumps(manifests),flush=True)
if __name__=='__main__':main()
