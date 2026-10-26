"""CPU-only creator-to-runner integration and no-overwrite/path-boundary checks."""
import json,os,struct,sys,tempfile
from unittest.mock import patch
from pathlib import Path
from make_word_freeze import create,digest,local_file
import word_campaign as W
HERE=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(dir=HERE) as d:
    root=Path(d);build=root/'builds/b';(build/'source_p/include').mkdir(parents=True)
    resume=root/'resume_20261026';(resume/'word_bin').mkdir(parents=True)
    paths=['resume_20261026/word_bin/'+x for x in ('word_tree','word_count','edit_oracle')]+['resume_20261026/'+x for x in ('edit_scan.py','audit_word.py','edit_oracle.cpp','edit_tree_bench.cu')]
    for name in paths:(root/name).write_bytes(b'fixture')
    header=build/'source_p/include/tree.cuh';header.write_bytes(b'header')
    (build/'BUILD_MANIFEST.json').write_text(json.dumps({'compiled_sources':{'source_p/include/tree.cuh':digest(header)['sha256']}}))
    keys=('tree_binary','count_binary','oracle_binary')
    binaries=dict(zip(keys,paths[:3]));sources={key:paths[-2] if key=='oracle_binary' else paths[-1] for key in keys}
    commands={};logs={}
    for key in keys:
        cmd=['/usr/bin/c++','-O3',str(root/sources[key]),'-o',str(root/binaries[key])]
        if key=='count_binary':cmd+=['-DINSTRUMENT=1']
        commands[key]=cmd;name='resume_20261026/'+key+'.guard.jsonl';logs[key]=name
        (root/name).write_text('\n'.join(json.dumps(e) for e in ({'event':'start','cmd':cmd},{'event':'end','exit_code':0}))+'\n')
    build_files={name:digest(root/name) for name in paths+list(logs.values())}
    (resume/'WORD_BUILD_RECORD.json').write_text(json.dumps({'files':build_files,'binaries':binaries,'sources':sources,'commands':commands,'guard_logs':logs,'toolchain':{'cuda':'13.1.115','target_sm':120,'cxx':'fixture c++'}}))
    (root/'base').write_bytes(b'index');(root/'query').write_bytes(b'query')
    raw=struct.pack('<10000i',*list(range(10))*1000)+struct.pack('<10000d',*list(range(10))*1000)
    cases=[]
    for n in W.NS:
        name=f'o{n}';(root/name).write_bytes(raw)
        cases.append({'family':'word','N':n,'D':109,'k':8,'Q':list(W.QS),'state':'feasible' if n!=611000 else 'infeasible: insufficient source rows after holdout','query_isolation':{'isolated':True},'base':'base','query':'query','oracle':name})
    runtime=resume/'runtime_fixture';runtime.write_bytes(b'verified fixture runtime')
    (resume/'RUNTIME_WORD_FILES.json').write_text(json.dumps({'runtime_files':{str(runtime):digest(runtime)},'python_invocation':str(__import__('sys').executable)}))
    manifest={'seed':20261026,'query_rows':1000,'stride':109,'maximum_length':32,'available_base_rows':610756,'files':{name:digest(root/name) for name in ('base','query')},'cases':cases}
    (root/'WORD_MANIFEST.json').write_text(json.dumps(manifest))
    create(root,build);out=resume/'WORD_PHASE_FREEZE.json';old=out.read_bytes()
    with patch.dict(os.environ,{'FAISS_PYTHON':sys.executable}):
        proof,verified=W.verified_inputs(root)
    assert len(verified)==4 and len(proof['runtime_files'])==1
    assert verified[-1]['state'].startswith('infeasible:')
    try:create(root,build)
    except FileExistsError:pass
    else:raise AssertionError('overwritten freeze')
    assert out.read_bytes()==old
    for bad in ('../escape','/absolute'):
        try:local_file(root,bad)
        except ValueError:pass
        else:raise AssertionError('path escape')
    manifest['cases'][0]['base']='unfrozen';(root/'WORD_MANIFEST.json').write_text(json.dumps(manifest))
    try:create(root,build)
    except AssertionError as e:assert 'unfrozen' in str(e)
    else:raise AssertionError('unfrozen case admitted')
    assert out.read_bytes()==old
print('PASS creator -> runner verification, runtime/build binding, atomic preservation, locality')
