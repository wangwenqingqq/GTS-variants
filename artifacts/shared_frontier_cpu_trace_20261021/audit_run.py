"""Read-only post-run custody, completeness, and frozen-membership verification."""
if not __debug__:raise SystemExit('Assertions required')
import json,random,struct
from pathlib import Path
from run import identity,load,sources
from verify import verify_target
HERE=Path(__file__).resolve().parent

def campaign(root):
 c=load(HERE/'CONTRACT.json');complete=load(root/'COMPLETE.json')
 assert complete['passed'] and not (root/'FAILURE.json').exists()
 assert complete['GPU_starts']==complete['protected_GIST_heldout_accesses']==0
 seal=load(root.with_name(root.name+'.SEAL.json'))
 actual={str(p.relative_to(root)):identity(p) for p in sorted(root.rglob('*')) if p.is_file()}
 assert seal['before_postrun_review'] and actual==seal['files']
 reg=load(root/'REGISTERED.json');assert reg['before_compile_and_population'] and reg['sources']==sources()==load(HERE/'SOURCE_FREEZE.json')['files']
 assert reg['nice']==10 and reg['threads']==1 and reg['GPU_starts']==0
 assert load(root/'BUILD.json')['passed'] and identity(root/'trace_cpu')==load(root/'BUILD.json')['binary']
 assert not (root/'compile.stderr').read_bytes() and not (root/'qualification.stderr').read_bytes()
 starts=[json.loads(s) for s in (root/'STARTS.jsonl').read_text().splitlines()]
 expected=[(n,m,s) for n in c['data'] for m,s in [('static',s) for s in c['sample']['query_seeds']]+[('updates',c['sample']['query_seeds'][0])]]
 assert len(starts)==len(complete['records'])==len(expected)==9
 spent={n:0.0 for n in c['data']};proofs={}
 for i,(n,m,s) in enumerate(expected):
  key=f'{n}_{m}_{s}';start=load(root/'receipts'/(key+'.command.json'))
  assert start==starts[i] and start['index']==i and start['before_start']
  assert (start['dataset'],start['mode'],start['seed'])==(n,m,s)
  assert start['binary']==load(root/'BUILD.json')['binary']
  binary=reg['compile_command'][-1];registered_inputs=Path(reg['input_directory'])
  assert start['command']==[binary,str(registered_inputs/(n+'.trace')),str(registered_inputs/(n+f'.{s}.qid')),str(registered_inputs/(n+'.delete')),str(Path(binary).parent/key),m]
  ex=load(root/'receipts'/(key+'.exit.json'));assert ex==complete['records'][i] and ex['returncode']==0
  assert not (root/'receipts'/(key+'.stderr')).read_bytes()
  spent[n]+=ex['wall_seconds']
  proof=load(root/'receipts'/(key+'.proof.json'));assert proof['passed'] and proof['full_output_streams_checked']==(12 if m=='static' else 6)
  proofs[key]=proof
 assert all(t<=c['resource']['max_seconds_per_dataset'] for t in spent.values())
 assert sum(p['bytes'] for p in actual.values())<=c['resource']['raw_disk_budget_bytes']
 return dict(passed=True,source_freeze=identity(HERE/'SOURCE_FREEZE.json'),contract=identity(HERE/'CONTRACT.json'),seal=identity(root.with_name(root.name+'.SEAL.json')),sealed_file_count=len(actual),sealed_bytes=sum(p['bytes'] for p in actual.values()),complete=identity(root/'COMPLETE.json'),processes=9,proofs=proofs,seconds_per_dataset=spent,GPU_starts=0,protected_GIST_heldout_accesses=0)

def audit(root,inputs):
 result=campaign(root);c=load(HERE/'CONTRACT.json');pins=load(inputs/'INPUTS.json')
 assert pins['passed'] and pins['contract']==identity(HERE/'CONTRACT.json') and pins['preparer']==identity(HERE/'prepare.py')
 assert identity(inputs/'INPUTS.json')==load(root/'REGISTERED.json')['input_manifest']
 bindings={}
 for n in c['data']:
  trace=inputs/(n+'.trace');sp=inputs/(n+'.selection.json');sel=load(sp)
  assert identity(trace)==pins['sources'][n]['trace_input']==sel['trace_input'] and identity(sp)==pins['sources'][n]['selection']
  expected_rows=sorted(random.Random(c['sample']['seeds'][n]).sample(range(c['data'][n]['source_N']),65568))
  assert sel['source_rows']==expected_rows
  expected_queries={str(s):random.Random(s).sample(range(65536),256) for s in c['sample']['query_seeds']}
  assert sel['queries']==expected_queries
  excluded=set(q for qs in expected_queries.values() for q in qs)
  assert sel['deleted']==random.Random(2026102121).sample([i for i in range(65536) if i not in excluded],32)
  assert sel['incoming']==list(range(65536,65568)) and len(sel['deleted'])==32
  members={}
  for s in c['sample']['query_seeds']:
   p=inputs/f'{n}.{s}.qid';assert p.read_text()=='\n'.join(map(str,expected_queries[str(s)]))+'\n';members[p.name]=identity(p)
  p=inputs/(n+'.delete');assert p.read_text()=='\n'.join(map(str,sel['deleted']))+'\n';members[p.name]=identity(p)
  for m,s in [('static',s) for s in c['sample']['query_seeds']]+[('updates',c['sample']['query_seeds'][0])]:
   key=f'{n}_{m}_{s}';target=root/key;assert verify_target(target,inputs,n,m,s)==result['proofs'][key]
   # Each frozen query is itself a live database row,including both update states.
   for binary in target.glob('S*_R*_*.bin'):
    zero={(qi,idx) for qi,idx,score in struct.iter_unpack('<IQd',binary.read_bytes()) if score==0}
    assert all((qi,sel['source_rows'][qid]) in zero for qi,qid in enumerate(expected_queries[str(s)]))
  bindings[n]=dict(selection=identity(sp),trace_input=identity(trace),actual_membership_files=members,deterministic_membership_equal=True)
 result.update(input_manifest=identity(inputs/'INPUTS.json'),bindings=bindings,full_output_streams_checked=sum(p['full_output_streams_checked'] for p in result['proofs'].values()),qualification=(root/'qualification.stdout').read_text().strip(),membership_limitation='The original runner did not independently bind qid/delete before launch;post-run exact files,deterministic selections,and all outputs were audited without mutation or rerun.')
 return result
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 result=audit(a.run,a.inputs)
 with a.out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
