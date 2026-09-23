#!/usr/bin/env python3
"""Validate complete numeric outputs before admitting their ordered hashes."""
import argparse,csv,hashlib,json,struct,math,statistics
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(pairs):
 h=1469598103934665603
 for i,d in pairs:
  for word in (i,struct.unpack('<I',struct.pack('<f',d))[0]):h=((h^word)*1099511628211)&((1<<64)-1)
 return str(((h^len(pairs))*1099511628211)&((1<<64)-1))
def clean(rec):
 assert rec['exit_code']==0 and not rec['runtime_errors'] and rec['stop_reason'] is None and rec['post_gpu_clear'],rec

def check_summary(v,r,rows):
 assert v['mode']==r['mode'] and v['queries']==len(rows)==64*r['repeats']
 assert struct.pack('<f',v['radius'])==struct.pack('<f',r['radius'])
 assert math.isclose(v['sum_query_s']*1e6/v['queries'],statistics.mean(float(x['query_us']) for x in rows),rel_tol=1e-9)
 return v

def check(path,o,radius):
 actual=[];lookup=dict(zip(o['queries'],o['distances']))
 for line in (path/'result.results').read_text().splitlines():
  fields=line.split();q,n=map(int,fields[:2]);pairs=[(int(x.split(':')[0]),float(x.split(':')[1])) for x in fields[2:]]
  expected=[i for i,d in enumerate(lookup[q]) if d<=radius]
  assert len(pairs)==n==len(expected),(path.name,q,n,len(expected))
  assert sorted(i for i,d in pairs)==expected,(path.name,q,'membership')
  assert all(abs(d-lookup[q][i])<=max(2e-6,2e-5*lookup[q][i]) for i,d in pairs),(path.name,q,'distance')
  actual.append((q,pairs))
 assert [q for q,p in actual]==o['queries']
 rows=list(csv.DictReader((path/'result.csv').open()));assert len(rows)==len(actual)
 assert all(int(r['qid'])==q and int(r['count'])==len(p) and r['ordered_hash']==digest(p) for r,(q,p) in zip(rows,actual))
 return actual

def verify(root):
 o=json.loads((root/'fixtures/oracle.json').read_text());binary=sha(root/'bin/graph_bench');checks={}
 for n,k in [('data.txt','data_sha256'),('queries.qid','qids_sha256')]:assert sha(root/'fixtures'/n)==o[k]
 for name,r in o['radii'].items():
  reference=None;reference_bits=None
  for m in ('DEUSVL' if name=='empty' else 'ADEUSVL'):
   path=root/'runs'/f'full_{name}_{m}';rec=json.loads((path/'receipt.json').read_text());clean(rec)
   assert (rec['binary_sha256'],rec['mode'],rec['radius'],rec['tool'],rec['repeats'],rec['warmup'],rec['dump'])==(binary,m,r,'clean',1,0,True)
   actual=check(path,o,r)
   bits=[(q,[(i,struct.pack('<f',d)) for i,d in pairs]) for q,pairs in actual]
   if reference_bits is None:reference_bits=bits
   assert bits==reference_bits,(name,m,'direct bitwise ordered output mismatch')
   hashes={str(q):[len(p),digest(p)] for q,p in actual}
   if reference is None:reference=hashes
   assert hashes==reference,(name,m,'bitwise ordered result mismatch')
   checks[path.name]=sha(path/'result.results')
  (root/'fixtures'/f'expected_{r:g}.json').write_text(json.dumps(reference,indent=2)+'\n')
  log=(root/'runs'/f'full_{name}_E/stdout.log').read_text()
  assert 'PASS layout bit-audit and 128 per-level flag cases' in log
 result={'binary_sha256':binary,'full_output_checks':checks,'oracle_sha256':sha(root/'fixtures/oracle.json'),'scope':'CPU float64 exact membership; tolerant distance; bitwise native ordered outputs; 512 per-level flag cases'}
 (root/'full_verified.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();print('PASS',len(verify(a.root)['full_output_checks']),'full-output runs')
