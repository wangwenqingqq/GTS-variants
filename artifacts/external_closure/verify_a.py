#!/usr/bin/env python3
"""Fail-closed completeness/binding gate for this bounded Stage A campaign.

This does not replace the numerical oracle: it binds its original proof to all
required executions, outputs and the strengthened CPU boundary matrix.
"""
import argparse, hashlib, json
from pathlib import Path
from common import outside_repo
import qualify
sha=qualify.cpu.sha
HERE=Path(__file__).resolve().parent
EXPECTED={
    'qualify_r2':{**{f'range_n{n}':True for n in (0,1,7,513,4096)},
                  **{f'range_service_{t}':True for t in ('memcheck','racecheck','synccheck')},'tree_native_0':False},
    'tree_qualify_r3':{'tree_native_0':True},
    'tree_diagnose':{'tree_adapt_0':True,'tree_native_1':True,'tree_adapt_1':True,'tree_adapt_memcheck':False},
    'tree_safe_qualify':{k:True for k in ('tree_adapt_1','tree_adapt_memcheck','tree_adapt_racecheck','tree_adapt_synccheck')},
    'range_snapshots':{'initial':True,'first_rebuilt':True}}
NEGATIVE_QUALITY={'tree_qualify_r3/tree_native_0','tree_diagnose/tree_adapt_0'}
FLAT={'CPU_FLAT_INCLUSIVE_ADAPT/'+n for n in ('initial','first_rebuilt')}

def read(p):return json.loads(Path(p).read_text())
def required_receipts(receipts):
    expected={f'{folder}/{name}':valid for folder,jobs in EXPECTED.items() for name,valid in jobs.items()}
    assert len(receipts)==len(expected)==20
    assert {r['case']:r['runtime_valid'] for r in receipts}==expected

def edge_matrix(edge,methods,inclusive):
    assert edge['passed'] is True and edge['inclusive_adapter'] is inclusive
    assert edge['adapter_sha256']==sha(HERE/'native_cpu.py') and edge['checker_sha256']==sha(HERE/'cpu_edges.py')
    expected={(m,leaf,n,repeat,task,radius) for m in methods for leaf in (32,128,512)
              for n in (0,1,7,513) for repeat in range(32)
              for task,radius in [('knn',None),*[( 'range',r) for r in (-1.,0.,1.,100.)]]}
    actual=[(r['method'],r['leaf'],r['N'],r['repeat'],r['task'],r.get('radius')) for r in edge['rows']]
    assert len(actual)==len(expected) and set(actual)==expected
    assert all(r['passed'] is True for r in edge['rows'])

def verify(work,proof,tree_edge,flat_edge):
    required_receipts(proof['receipts'])
    assert proof['GPU_processes']==20 and proof['primary_processes']==0 and proof['GPU_TREE_admission'] is False
    # Original proof sources are immutable; newer checkers do not relabel them.
    def source_bound(digest,candidates):
        assert any(p.is_file() and sha(p)==digest for p in candidates),('source not bound',digest)
    source_bound(proof['checker_sha256'],[work/'EXECUTED_QUALIFICATION.py',HERE/'finish_a.py'])
    source_bound(proof['payload_checker_sha256'],[work/'EXECUTED_PAYLOAD_CHECKER.py',HERE/'qualify.py'])
    contract=(HERE/'CONTRACT.md').read_bytes().splitlines(keepends=True)
    contract_prefixes={hashlib.sha256(b''.join(contract[:i])).hexdigest() for i in range(1,len(contract)+1)}
    summaries=[];seen=set()
    for folder,expected in EXPECTED.items():
        root=work/folder;reg=read(root/'REGISTERED.json')
        source_bound(reg['script_sha256'],[root/'EXECUTED.py',work/'tree_diagnose/EXECUTED.py'])
        assert reg['contract_sha256'] in contract_prefixes
        jobs={j['label']:j for j in reg['jobs']};assert len(jobs)==len(reg['jobs'])
        actual={p.parent.name for p in (root/'guards').glob('*/receipt.json')};assert actual==set(expected)
        for label,valid in expected.items():
            key=folder+'/'+label;guard=root/'guards'/label;receipt=read(guard/'receipt.json');job=jobs[label]
            row=next(r for r in proof['receipts'] if r['case']==key)
            assert sha(guard/'receipt.json')==row['receipt_sha256'] and receipt['runtime_valid'] is valid
            assert read(guard/'before.json')['apps']==read(guard/'after.json')['apps']==''
            checks=read(guard/'checks.json');assert checks and all(not c['foreign'] for c in checks)
            cmd=receipt['command']
            cpu_nodes=[c.split('=',1)[1] for c in cmd if c.startswith('--cpunodebind=')]
            memory_nodes=[c.split('=',1)[1] for c in cmd if c.startswith('--membind=')]
            assert len(cpu_nodes)==1 and cpu_nodes==memory_nodes
            if 'numa_node' in reg:assert cpu_nodes==[str(reg['numa_node'])]
            # Guard's binary hash identifies numactl; bind the real adapter too.
            binaries=[Path(c) for c in cmd if Path(c).is_file() and Path(c).name==Path(job.get('binary',job.get('exe',''))).name]
            assert len(binaries)==1 and sha(binaries[0])==job['binary_sha256']
            assert sha(job['requests'])==job['request_sha256']
            if valid:
                assert receipt['exit_code']==0 and receipt['stop_reason'] is None
                seen.add(key);q=proof['checks'][key]
                assert q['passed'] is (key not in NEGATIVE_QUALITY)
                count=int(Path(job['requests']).read_text().splitlines()[0]);assert len(q['per_query'])==count
                assert all(r['passed'] is q['passed'] for r in q['per_query'])
                if folder=='range_snapshots' or job.get('exe')=='range_service':
                    assert q['native_squared_observed'] is True
                    assert label+'.native_squared.f64' in q['output_sha256']
                for name,digest in q['output_sha256'].items():
                    assert Path(name).name==name and sha(root/'outputs'/name)==digest
                if job.get('tool'):
                    token='RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if job['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors'
                    assert token in (guard/'stdout.log').read_text()+(guard/'stderr.log').read_text()
            else:assert receipt['exit_code']!=0
            summaries.append(dict(case=key,registration_sha256=sha(root/'REGISTERED.json'),binary_sha256=job['binary_sha256'],receipt_sha256=row['receipt_sha256']))
    assert set(proof['checks'])==seen|FLAT
    for name in ('initial','first_rebuilt'):
        q=proof['checks']['CPU_FLAT_INCLUSIVE_ADAPT/'+name];root=work/('cpu_flat_'+name)
        assert q['passed'] is True and q['native_squared_observed'] is True and len(q['per_query'])==64
        for filename,digest in q['output_sha256'].items():assert Path(filename).name==filename and sha(root/filename)==digest
    edge_matrix(read(tree_edge),('CPU_KD','CPU_BALL'),False);edge_matrix(read(flat_edge),('CPU_FLAT',),True)
    return dict(passed=True,required_GPU_cases=20,runtime_valid_cases=18,new_primary_processes=0,
        GPU_TREE_admission=False,GPU_RANGE_admission=True,CPU_tree_admission=True,CPU_FLAT_INCLUSIVE_ADAPT_admission=True,
        CPU_boundary_proof_sha256=sha(tree_edge),CPU_FLAT_inclusive_proof_sha256=sha(flat_edge),
        CPU_boundary_rows=len(read(tree_edge)['rows'])+len(read(flat_edge)['rows']),
        records=summaries,verifier_sha256=sha(__file__),CPU_boundary_checker_sha256=sha(HERE/'cpu_edges.py'),
        scope='Post-hoc fail-closed binding plus new CPU boundary checks; no new GPU or timing measurements')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('work','proof','tree-edge','flat-edge','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();assert __debug__;outside_repo(a.work);out=outside_repo(a.output);assert not out.exists()
    report=verify(a.work,read(a.proof),a.tree_edge,a.flat_edge);report['original_proof_sha256']=sha(a.proof)
    qualify.save(out,report);print('PASS complete Stage A admission binding')
