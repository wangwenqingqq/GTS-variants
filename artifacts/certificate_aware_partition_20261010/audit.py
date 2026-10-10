#!/usr/bin/env python3
"""Audit the delivered scalar artifact and its executed-source/receipt chain."""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from partition import HERE,BASE,sha,source_hashes,stats,decide,query_summary


def load(p):return json.loads(p.read_text())


def main(seal=False):
    root=HERE;c=load(root/'CONTRACT.json');sp=load(root/'evidence/STATIC_PROOF.json')
    sr=load(root/'evidence/STATIC_REGISTERED.json');sv=load(root/'evidence/STATIC_VERIFY.json')
    up=load(root/'evidence/UPDATE_PROOF.json');ur=load(root/'evidence/UPDATE_REGISTERED.json')
    assert sp['passed'] and up['passed'] and sv['passed']
    assert sp['source_hashes']==sr['source_hashes']==ur['static_source_hashes']==source_hashes()
    assert sr['contract_sha256']==ur['contract_sha256']==sha(root/'CONTRACT.json')
    assert sv['static_proof_sha256']==ur['static_proof_sha256']==sha(root/'evidence/STATIC_PROOF.json')
    assert sv['verification_source_sha256']==sha(root/'verify_partition.py')
    assert ur['static_verification_sha256']==sha(root/'evidence/STATIC_VERIFY.json')
    assert up['registered_sha256']==sha(root/'evidence/UPDATE_REGISTERED.json')
    assert up['source_hashes']==ur['source_hashes']=={p.name:sha(p) for p in [root/'update_recheck.py',root/'verify_partition.py',root/'test_update_recheck.py',BASE/'update.py']}
    curated=load(root/'evidence/CURATION.json');assert curated['passed']
    for record in curated['files']:assert sha(root/record['published_file'])==record['sha256']
    for source,target in [('PARTITION_STATS.json','partition/PARTITION_STATS.json'),('BLOCK_SELECTIVITY.json','query/BLOCK_SELECTIVITY.json'),('DECISION.json','evidence/DECISION.json'),('REGISTERED.json','evidence/STATIC_REGISTERED.json')]:
        assert sha(root/target)==sp['raw_files'][source]
    assert sha(root/'update/UPDATE_RECHECK.json')==up['raw_files']['UPDATE_RECHECK.json']
    decoded=gzip.decompress((root/'partition/BLOCK_STATS.csv.gz').read_bytes())
    assert hashlib.sha256(decoded).hexdigest()==sp['raw_files']['BLOCK_STATS.csv']==curated['per_block_uncompressed_sha256']
    grouped={}
    for row in csv.DictReader(io.StringIO(decoded.decode())):
        key=tuple(row[k] for k in ('snapshot','strategy','partition'))
        grouped.setdefault(key,[]).append(row)
    assert len(grouped)==16 and sum(map(len,grouped.values()))==64024
    partition=load(root/'partition/PARTITION_STATS.json')['rows'];assert len(partition)==16
    for r in partition:
        rows=grouped[r['snapshot'],r['strategy'],r['partition']]
        assert [int(x['block']) for x in rows]==list(range(len(rows)))
        sizes=np.array([int(x['size']) for x in rows]);assert sizes.sum()==1000000 and stats(sizes)==r['size']
        width=np.array([[float(x['width_p'+str(i)]) for x in rows] for i in range(1,5)])
        nw=np.array([[float(x['normalized_width_p'+str(i)]) for x in rows] for i in range(1,5)])
        assert [stats(w) for w in width]==r['width_by_pivot'] and [stats(w) for w in nw]==r['normalized_width_by_pivot']
        assert stats(nw.mean(axis=0))==r['mean_normalized_width']
        assert r['total_blocks']==len(rows) and r['physical_occupancy']==1000000/(256*len(rows))
    query=load(root/'query/BLOCK_SELECTIVITY.json');assert len(query['rows'])==1024
    assert all(r['false_prune_blocks']==0 for r in query['rows'])
    for s in query['summary']:
        rows=[r for r in query['rows'] if all(r[k]==s[k] for k in ('snapshot','strategy','partition','pivot_count'))]
        assert len(rows)==32 and [r['qid'] for r in rows]==c['inputs'][s['snapshot']]['qids']
        assert query_summary(rows)==s['statistics']
        for r in rows:
            assert r['surviving_blocks']+r['rejected_blocks']==r['total_blocks']
            assert r['surviving_blocks']-r['oracle_required_blocks']==r['oracle_gap_blocks']
    decision=decide(query['summary']);assert decision==load(root/'evidence/DECISION.json')
    update=load(root/'update/UPDATE_RECHECK.json');assert update['selection']==decision['top_one']==ur['selected']
    assert update['static_decision']==decision and len(update['rows'])==2
    for r,spec in zip(update['rows'],c['updates']['intervals']):
        assert (r['actual_inserts'],r['actual_deletes'])==(spec['actual_inserts'],spec['actual_deletes'])
        assert len(r['events'])==r['actual_inserts']+r['actual_deletes']
        changed={b for e in r['events'] for b in e['affected_blocks']}
        assert len(changed)==r['changed_blocks'] and r['changed_block_fraction']==len(changed)/r['initial_total_blocks']
        assert sum(len(e['affected_blocks']) for e in r['events'])==r['certificate_refreshes']
        assert r['moved_existing_objects']==r['splits']==r['global_repartition']==0
        assert r['actual_initial_empty_slot_fraction']==1-1000000/(256*r['initial_total_blocks'])
        assert r['full_final_occurrence_lineage_and_bounds_verified']
        for label,mean in [('initial_queries','initial_query_survival_mean'),('post_update_queries','post_update_query_survival_mean')]:
            rows=r[label];assert len(rows)==32 and not any(q['false_prune_blocks'] for q in rows)
            assert float(np.mean([q['surviving_block_fraction'] for q in rows]))==r[mean]
    for filename in ('band_width_vs_survival','partition_comparison','oracle_gap'):
        with (root/'figures'/(filename+'.csv')).open() as f:rows=list(csv.DictReader(f))
        assert len(rows)==16
        for row in rows:
            n,s,k=row['snapshot'],row['strategy'],row['partition']
            p=next(x for x in partition if (x['snapshot'],x['strategy'],x['partition'])==(n,s,k))
            q=next(x['statistics'] for x in query['summary'] if (x['snapshot'],x['strategy'],x['partition'],x['pivot_count'])==(n,s,k,4))
            assert float(row['mean_normalized_width'])==p['mean_normalized_width']['mean']
            assert float(row['surviving_percent'])==100*q['surviving_block_fraction']['mean']
            assert float(row['oracle_gap_blocks'])==q['oracle_gap_blocks']['mean']
    inventory={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='DELIVERY_MANIFEST.json'}
    if seal:
        (root/'DELIVERY_MANIFEST.json').write_text(json.dumps(dict(files=inventory),indent=2)+'\n')
    else:assert inventory==load(root/'DELIVERY_MANIFEST.json')['files']
    print(json.dumps(dict(passed=True,static_rows=1024,block_rows=64024,update_query_rows=128,files=len(inventory)+1,decision=decision['decision'],reason=decision['reason'])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seal',action='store_true');main(p.parse_args().seal)
