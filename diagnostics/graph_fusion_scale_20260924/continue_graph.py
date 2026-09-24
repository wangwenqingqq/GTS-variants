#!/usr/bin/env python3
"""Prepare and run a separately identified continuation; never overwrite old runs."""
import argparse,csv,fcntl,hashlib,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
BINARY='ef898b0709155c2192c6032a06282fa455cd8c0488cbb8b331fff67ebd276bcf'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())

def prepare(base,out):
    from prepare import BASE_SHA,runner
    evidence=HERE.parent/'graph_scale_20260923/EVIDENCE.json';old=read(evidence)
    assert sha(base/'bin/graph_bench')==BINARY and sha(base/'graph_bench.cu')==BASE_SHA
    assert sha(base/'run_scale.py')=='92580ccccd6c9623f57dc92f93df2c8204499d1ddb586d9ee6135b58472a4ace'
    for name,h in read(HERE.parent/'original_tree_redundancy/SOURCE_PINS.json')['sha256'].items():
        if name.startswith('GTS/'):assert sha(base/'source'/name.removeprefix('GTS/'))==h
    prior=old['cases']['n611756_k1']
    for name,h in prior['fixture_hashes'].items():assert sha(base/'fixtures/611756'/name)==h
    assert sha(base/'fixtures/611756/oracle.bin')==prior['cpu_oracle_sha256']
    fixture=read(base/'fixtures/611756/manifest.json')
    assert fixture['n']==611756 and fixture['file_sha256']==prior['fixture_hashes']
    assert fixture['qids']==list(map(int,(base/'fixtures/611756/queries.qid').read_text().split()))[1:]
    for name,record in old['run_inventory'].items():
        p=base/'cases'/name.split('/')[0]/'runs'/name.split('/')[1]
        assert sha(p/'receipt.json')==record['receipt_sha256']
        if 'samples_sha256' in record:assert sha(p/'result.csv')==record['samples_sha256']
    with (base/'cases/n611756_k1/runs/smoke_A/result.csv').open() as f:
        gold={r['qid']:[int(r['count']),r['ordered_hash']] for r in csv.DictReader(f)}
    assert read(base/'fixtures/611756/expected_4.json')==gold
    out.mkdir();(out/'bin').mkdir();(out/'fixtures').mkdir();(out/'cases').mkdir()
    shutil.copy2(base/'bin/graph_bench',out/'bin/graph_bench')
    shutil.copytree(base/'source',out/'source');shutil.copy2(base/'graph_bench.cu',out/'graph_bench.cu')
    shutil.copytree(base/'fixtures/611756',out/'fixtures/611756')
    shutil.copy2(HERE.parent/'graph_scale_20260923/check.py',out/'check.py')
    (out/'run_fusion.py').write_text(runner((base/'run_scale.py').read_text()))
    (out/'continuation_manifest.json').write_text(json.dumps({'binary_sha256':BINARY,'prior_evidence_sha256':sha(evidence),
      'source_sha256':BASE_SHA,'prior_archive_sha256':old['raw_archive_sha256'],'runner_sha256':sha(out/'run_fusion.py'),
      'fixture_sha256':{p.name:sha(p) for p in (out/'fixtures/611756').iterdir() if p.is_file()}},indent=2)+'\n')
    for k in [1,32]:
        p=out/'cases'/f'n611756_k{k}';p.mkdir();(p/'runs').mkdir();(p/'bin').symlink_to('../../bin');(p/'fixtures').symlink_to('../../fixtures/611756')

def run(root,phase):
    sys.path.insert(0,str(root));from run_fusion import execute,snapshot
    from check import check
    assert sha(root/'bin/graph_bench')==BINARY
    manifest=read(root/'continuation_manifest.json');assert sha(root/'run_fusion.py')==manifest['runner_sha256']
    for name,h in manifest['fixture_sha256'].items():assert sha(root/'fixtures/611756'/name)==h
    with open('/tmp/gtspp_gpu0.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);assert not snapshot('0')['apps'].strip()
        for k in ([1,32] if phase!='timing' else [32]):
            p=root/'cases'/f'n611756_k{k}';receipts={}
            if phase!='smoke':
                smoke=read(p/'smoke_complete.json');assert smoke['binary_sha256']==BINARY and smoke['complete']
                for f,h in smoke['receipts'].items():assert sha(root/f)==h
            def call(label,m,reps=1,warm=0,tool='clean',dump=False):
                assert execute(p,'0',label,m,4,reps,warm,tool,dump,k)
                receipt=p/'runs'/label/'receipt.json';receipts[str(receipt.relative_to(root))]=sha(receipt)
            if phase=='smoke':
                ref=None
                for m in 'ABC':
                    call('smoke_'+m,m,dump=True);out,gold=check(p,'smoke_'+m,4,ref);ref=out
                (p/'fixtures/expected_4.json').write_text(json.dumps(gold,indent=2)+'\n')
            elif phase=='profile':
                for m in 'BC':call('nsys_'+m,m,tool='nsys-node')
            elif phase=='timing':
                for i,order in enumerate(['ABC','CBA','BCA','ACB','CAB','BAC']):
                    for m in order:call(f'timing_{i}_{m}',m,reps=4,warm=64)
                for i,order in enumerate(['BC','CB']):
                    for m in order:call(f'sustained_{i}_{m}',m,reps=16,warm=64)
            (p/(phase+'_complete.json')).write_text(json.dumps({'complete':True,'binary_sha256':BINARY,'receipts':receipts},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('prepare');a.add_argument('base',type=Path);a.add_argument('out',type=Path)
    a=sub.add_parser('run');a.add_argument('root',type=Path);a.add_argument('phase',choices=['smoke','profile','timing'])
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.base.resolve(),a.out.resolve())
    else:run(a.root.resolve(),a.phase)
