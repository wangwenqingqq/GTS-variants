#!/usr/bin/env python3
"""Verify a private small bundle and independently recompute exact structure gates."""
import argparse,hashlib,json,tarfile
from pathlib import Path
from analyze import Tree,compare,sha,dump

def main():
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('manifest',type=Path);p.add_argument('result',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir()
    expected=json.loads(a.manifest.read_text());seen=set()
    with tarfile.open(a.archive,'r:gz') as t:
        for item in t:
            assert item.isfile() and item.name in expected and item.name not in seen
            name=Path(item.name);assert not name.is_absolute() and '..' not in name.parts
            data=t.extractfile(item).read();e=expected[item.name];assert len(data)==e['bytes'] and hashlib.sha256(data).hexdigest()==e['sha256']
            target=a.output/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);seen.add(item.name)
    assert seen==set(expected)
    closure=json.loads((a.output/'CLOSURE.json').read_text())
    assert sha(a.output/'summary_final/RESULT.json')==sha(a.result)==closure['result_sha256']
    assert sha(a.output/'RAW_MANIFEST.json')==closure['raw_manifest_sha256']
    assert sha(a.output/'SOURCE_AUDIT.json')==closure['source_audit_sha256']
    assert sha(a.output/'CONTRACT.json')==closure['contract_sha256']
    for phase,previous in (('C2','C1'),('C3','C2')):
        admit=json.loads((a.output/f'ADMIT_{phase}.json').read_text())
        assert admit['admitted'] and sha(a.output/f'summary_{previous}/RESULT.json')==admit['evidence_sha256']
        assert sha(a.output/f'ADMIT_{phase}.json')==closure['phase_bindings'][phase]['admit_sha256']
    admit=json.loads((a.output/'ADMIT_C3.json').read_text())
    assert sha(a.output/'CLOSURE_C2_v1.json')==admit['C2_closure_sha256']
    old_closure=json.loads((a.output/'CLOSURE_C2_v1.json').read_text())
    saved=a.output/'RAW_MANIFEST_C2_v1.json'
    if saved.exists():assert sha(saved)==old_closure['raw_manifest_sha256']
    else:
        # Exact recovery for the historical reader that had no BOUNDARY payloads.
        raw=json.loads((a.output/'RAW_MANIFEST.json').read_text())
        historic={k:v for k,v in raw.items() if not k.startswith(('runs/R1_C3/','runs/R2_C3/')) and not k.endswith('/BOUNDARY.json')}
        historic_bytes=(json.dumps(historic,indent=2)+'\n').encode()
        assert hashlib.sha256(historic_bytes).hexdigest()==old_closure['raw_manifest_sha256']
        dump(a.output/'RECOVERED_C2_RAW_MANIFEST.json',historic)
    for r in (1,2):
        for name in ('order.i32','nodes.bin','empty.i32'):
            assert sha(a.output/f'runs/R{r}_PRE'/name)==sha(a.output/f'prior_snapshots/PRE_R{r}'/name)
    result=json.loads(a.result.read_text());rows=[]

    for x in result['rebuilds']:
        r=x['rebuild'];pre=Tree(a.output/f'prior_snapshots/PRE_R{r}')
        post=a.output/f'prior_snapshots/POST_R{r}'
        for m in x['modes']:
            mode=m['mode'];run=a.output/f'runs/R{r}_{mode}'
            # No raw keys in this small bundle: validate complete structural state only.
            shadow=a.output/f'local_structures/R{r}_{mode}';shadow.mkdir(parents=True)
            for name in ('base.i32','live.i32'):(shadow/name).write_bytes((post/name).read_bytes())
            for name in ('order.i32','nodes.bin','empty.i32'):(shadow/name).write_bytes((run/name).read_bytes())
            tree=Tree(shadow);measured=compare(pre,tree)
            assert measured==m['vs_pre'],(r,mode,'structure summary differs')
            if mode=='C0':
                for name in ('order.i32','nodes.bin','empty.i32'):assert sha(post/name)==sha(run/name)
            rows.append({'rebuild':r,'mode':mode,'leaf_unchanged':measured['leaf']['exact_unchanged'],'passed':True})
    dump(a.output/'LOCAL_CLOSURE.json',{'passed':True,'archive_sha256':sha(a.archive),'manifest_sha256':sha(a.manifest),'result_sha256':sha(a.result),'files':len(seen),'gate_evidence_bindings_passed':True,'historic_C2_raw_manifest_recovered_exactly':True,'independent_structure_comparisons':rows,'scope':'all private small bundle bytes and complete structure-derived result fields; large AoS/packed coordinates and raw distance keys verified on host only'})
    print('PASS small archive and all exact structure-derived results')
if __name__=='__main__':main()
