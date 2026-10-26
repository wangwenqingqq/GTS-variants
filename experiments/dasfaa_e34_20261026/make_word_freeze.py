"""Create a no-overwrite Word phase manifest after all CPU/build artifacts exist."""
import argparse,hashlib,json,math,os,struct,tempfile
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return {'sha256':h.hexdigest(),'bytes':path.stat().st_size}


def local_file(root,name):
    name=Path(name)
    if name.is_absolute() or not (root/name).resolve().is_relative_to(root):
        raise ValueError('artifact path escapes task root: '+str(name))
    return root/name


def create(root,build):
    root=Path(root).resolve();build=Path(build).resolve()
    assert build.is_relative_to(root)
    paths={'word_manifest':'WORD_MANIFEST.json','word_build_manifest':'resume_20261026/WORD_BUILD_RECORD.json','tree_binary':'resume_20261026/word_bin/word_tree','count_binary':'resume_20261026/word_bin/word_count','scan_script':'resume_20261026/edit_scan.py','audit_script':'resume_20261026/audit_word.py','oracle_binary':'resume_20261026/word_bin/edit_oracle','oracle_source':'resume_20261026/edit_oracle.cpp','tree_source':'resume_20261026/edit_tree_bench.cu','source_build_manifest':str((build/'BUILD_MANIFEST.json').relative_to(root))}
    names=set(paths.values());m=json.loads(local_file(root,paths['word_manifest']).read_text())
    for name,expected in m['files'].items():
        assert digest(local_file(root,name))==expected,name
        names.add(name)
    b=json.loads(local_file(root,paths['source_build_manifest']).read_text())
    word_build=json.loads(local_file(root,paths['word_build_manifest']).read_text())
    for name,expected in word_build['files'].items():
        assert digest(local_file(root,name))==expected,name
        names.add(name)
    for key in ('tree_binary','count_binary','oracle_binary'):
        assert word_build['binaries'][key]==paths[key]
        assert paths[key] in word_build['files']
    for c in m['cases']:
        for key in ('base','query'):
            name=c[key];local_file(root,name)
            assert name in m['files'], 'unfrozen case input: '+name
    for name,expected in b['compiled_sources'].items():
        if name.startswith('source_p/include/'):
            p=local_file(root,str((build/name).relative_to(root)));assert digest(p)['sha256']==expected,name;names.add(str(p.relative_to(root)))
    runtime_name='resume_20261026/RUNTIME_WORD_FILES.json'
    runtime=json.loads(local_file(root,runtime_name).read_text());names.add(runtime_name)
    runtime_files=runtime['runtime_files'];assert runtime_files
    for name,expected in runtime_files.items():
        assert Path(name).is_absolute() and digest(Path(name))==expected,name
    oracles={}
    for c in m['cases']:
        if c['state']!='feasible':continue
        assert c['query_isolation']['isolated']
        name=c['oracle'];raw=local_file(root,name).read_bytes();assert len(raw)==120000
        ids=struct.unpack('<10000i',raw[:40000]);ds=struct.unpack('<10000d',raw[40000:])
        assert all(0<=i<c['N'] for i in ids)
        for row in range(1000):
            chunk=ds[row*10:(row+1)*10]
            assert len(set(ids[row*10:(row+1)*10]))==10
            assert all(math.isfinite(d) and d>=0 and d==int(d) for d in chunk)
            assert all(a<=b for a,b in zip(chunk,chunk[1:]))
        names.add(name);oracles[str(c['N'])]=digest(local_file(root,name))['sha256']
    result={'runtime_files':runtime_files,'python_invocation':runtime['python_invocation'],'paths':paths,'files':{name:digest(local_file(root,name)) for name in sorted(names)},'oracle_sha256':oracles,'data_policy':'original fixed seed/permutation, byte faithful, exact-value heldout; literal611K infeasible','timing':'host-ready complete k8; three retained passes, one excluded warmup; six PS/SP pairs','jit_policy':'phase-owned CuPy disk cache, complete .cubin/.cu hash chain outside timed scope; required before promotion'}
    path=root/'resume_20261026/WORD_PHASE_FREEZE.json'
    fd,tmp=tempfile.mkstemp(prefix='.wordfreeze_',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(result,f,indent=2);f.write('\n')
        os.link(tmp,path)
    finally:os.unlink(tmp)
    print(json.dumps({'phase_freeze':str(path),'sha256':digest(path)['sha256'],'files':len(names),'oracles':oracles}),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root');ap.add_argument('build');a=ap.parse_args();create(a.root,a.build)
