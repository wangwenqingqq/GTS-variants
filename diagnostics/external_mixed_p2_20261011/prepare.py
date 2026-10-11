#!/usr/bin/env python3
"""Copy immutable qualified inputs into a new scratch; no GPU execution or rebuild."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for x in iter(lambda:f.read(8<<20),b''):h.update(x)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,j):Path(p).write_text(json.dumps(j,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser()
    for k in ('root','fixed3','external','reference','data'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();r=a.root;c=read(r/'CONTRACT.json');assert not (r/'INPUTS.json').exists()
    assert sha(a.data)==c['shape']['data_sha256']
    shutil.copytree(a.fixed3/'P2',r/'P2',ignore=shutil.ignore_patterns('count*','unit*'))
    pins=read(r/'P2/SOURCE_PINS.json')['sources'];assert all(sha(r/'P2/source'/n)==h for n,h in pins.items())
    shutil.copytree(a.external/'E_build',r/'E')
    shutil.copytree(a.external/'campaign/cases',r/'cases')
    shutil.copytree(a.external/'analysis_repo',r/'checker',ignore=shutil.ignore_patterns('.git','__pycache__'))
    reg=read(a.external/'campaign/REGISTERED.json');assert all(sha(a.reference.parent/n)==h for n,h in reg['reference'].items())
    assert sha(r/'cases/target/events.txt')==c['shape']['events_sha256']
    assert sha(r/'P2/bench')==c['binaries']['P2'] and sha(r/'E/scan')==c['binaries']['E']
    assert sha(r/'checker/artifacts/external_closure/pe_check.py')=='1fc5b6626979677f4938157e1811cbd94eb4049819785e67793fbb50d0f3da29'
    env={**os.environ,**read(r/'E/REGISTERED.json')['environment']};ldd=subprocess.check_output(['ldd',r/'E/scan'],env=env,text=True);assert 'not found' not in ldd
    libs={str(Path(s.split('=>',1)[1].split('(')[0].strip()).resolve()) for s in ldd.splitlines() if '=>' in s}
    library_hashes={x:sha(x) for x in sorted(libs)}
    spec=read(r/'E/REGISTERED.json')
    # Rebind every registered E source and native static library, not only the wrapper binary.
    for n,h in spec['source'].items():assert sha(a.external/'repo/artifacts/external_closure'/n)==h
    shutil.copytree(a.external/'repo/artifacts/external_closure',r/'E/source',ignore=shutil.ignore_patterns('__pycache__'))
    faiss=next(x for x in spec['command'] if x.endswith('/libfaiss.a'));assert sha(faiss)==spec['dependencies']['libfaiss.a'];library_hashes[faiss]=sha(faiss)
    header_root=Path(next(x[2:] for x in spec['command'] if x.startswith('-I') and 'faiss-1.' in x))
    for n,h in spec['upstream_headers'].items():assert sha(header_root/n)==h
    inputs={str(x.relative_to(r)):sha(x) for x in r.rglob('*') if x.is_file() and '__pycache__' not in x.parts and (x.parts[len(r.parts)] in ('P2','E','cases','checker','deps') or x.name in ('CONTRACT.json','run.py','prepare.py','analyze.py','test_recipe.py'))}
    save(r/'INPUTS.json',dict(inputs=inputs,reference=reg['reference'],external_registration_sha256=sha(a.external/'campaign/REGISTERED.json'),fixed3_closure_sha256=sha(a.fixed3/'CLOSURE.json'),library_hashes=library_hashes,data_sha256=sha(a.data),ldd=ldd))
    print('PREPARED',len(inputs),'immutable files',len(library_hashes),'libraries')
if __name__=='__main__':main()
