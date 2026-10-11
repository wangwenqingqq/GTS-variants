#!/usr/bin/env python3
"""Portable scalar consistency and receipt audit; raw arrays remain external."""
import argparse
import csv
import gzip
import hashlib
import io
import json
from tiles import HERE,SIZES,SNAPS,load,sha,stats,summarize,decide,costs,source_hashes


def main(seal=False):
    root=HERE;c=load(root/'CONTRACT.json');p=load(root/'evidence/PROOF.json');v=load(root/'evidence/VERIFY.json');reg=load(root/'evidence/REGISTERED.json');cur=load(root/'evidence/CURATION.json')
    assert p['passed'] and v['passed'] and cur['passed'] and p['source_hashes']==v['source_hashes']==reg['source_hashes']==source_hashes()
    assert v['proof_sha256']==sha(root/'evidence/PROOF.json') and reg['contract_sha256']==sha(root/'CONTRACT.json')
    assert v['verification_source_sha256']==sha(root/'verify_tiles.py')
    assert p['query_rows']==v['owner_based_query_rows']==320 and p['independent_partition_builds']==v['independent_stable_sort_partitions']==10
    assert p['numerical_tests_passed']==v['numerical_tests_passed']==8 and p['false_prune_tiles']==v['false_prune_tiles']==0
    assert p['anchor256_exact'] and p['nested_member_sets'] and v['all_layouts_summaries_costs_and_decision_reconstructed'] and reg['nice_actual']==15 and reg['CPU_threads_max']==4
    for r in cur['files']:assert sha(root/r['published_file'])==r['sha256'] and r['transform']=='byte-identical'
    for source,target in [('GRANULARITY_RESULTS.json','granularity/GRANULARITY_RESULTS.json'),('ORACLE_BY_TILE.json','oracle/ORACLE_BY_TILE.json'),('COST_PROXY.json','cost/COST_PROXY.json'),('REGISTERED.json','evidence/REGISTERED.json'),('DECISION.json','evidence/DECISION.json')]:assert sha(root/target)==p['raw_files'][source]
    q=load(root/'granularity/GRANULARITY_RESULTS.json');assert len(q['rows'])==320 and len(q['layouts'])==len(q['summary'])==10
    assert summarize(q['rows'])==q['summary'] and costs(q['rows'])==load(root/'cost/COST_PROXY.json') and decide(q['summary'])==load(root/'evidence/DECISION.json')
    occupancy=root/'granularity/TILE_STATS.csv.gz';assert sha(occupancy)==cur['occupancy_gzip_sha256'];decoded=gzip.decompress(occupancy.read_bytes())
    assert hashlib.sha256(decoded).hexdigest()==cur['occupancy_uncompressed_sha256']==p['raw_files']['TILE_STATS.csv']
    groups={}
    for r in csv.DictReader(io.StringIO(decoded.decode())):groups.setdefault((r['snapshot'],int(r['tile_size'])),[]).append(r)
    assert sum(map(len,groups.values()))==v['direct_tile_rows']==126976 and len(groups)==10
    oldroot=root.parent/'certificate_aware_partition_20261010';assert sha(oldroot/'query/BLOCK_SELECTIVITY.json')==c['global4_result_sha256']
    assert sha(oldroot/'evidence/STATIC_PROOF.json')==c['partition_proof_sha256'] and sha(oldroot/'evidence/STATIC_VERIFY.json')==c['partition_verification_sha256']
    old=load(oldroot/'query/BLOCK_SELECTIVITY.json')['rows']
    for n in SNAPS:
        binding=p['bindings'][n];assert binding['queries']==c['inputs'][n]['qids'] and binding['occurrence_sha256']==c['occurrence_sha256'][n] and binding['anchor_exact'] and binding['nested_member_sets_verified']
        assert binding['partition256_sha256']==c['partition_sha256'][n] and binding['data_sha256']==c['inputs'][n]['data_sha256']
        anchor=[r for r in old if (r['snapshot'],r['strategy'],r['partition'],r['pivot_count'])==(n,'S1','P2',4)]
        previous=None
        for t in SIZES:
            l=next(r for r in q['layouts'] if (r['snapshot'],r['tile_size'])==(n,t));bb=groups[n,t];sizes=[int(b['objects']) for b in bb];nb=len(bb)
            assert [int(b['tile']) for b in bb]==list(range(nb)) and sum(sizes)==1000000 and min(sizes)>0 and max(sizes)<=t
            assert l['occupancy']==stats(sizes) and l['physical_slots']==nb*t and l['physical_occupancy']==1000000/(nb*t)
            assert l['total_tiles']==nb and l['metadata_bytes']==64*nb and l['endpoint_reads']==8*nb
            rr=[r for r in q['rows'] if (r['snapshot'],r['tile_size'])==(n,t)];assert len(rr)==32
            assert [r['qid'] for r in rr]==c['inputs'][n]['qids'] and [r['query'] for r in rr]==list(range(32))
            for r in rr:
                assert 0<=r['oracle_required_tiles']<=r['surviving_tiles']<=nb and r['false_prune_tiles']==0 and r['total_tiles']==nb
                assert r['surviving_object_fraction']==r['surviving_objects']/1000000 and r['surviving_tile_fraction']==r['surviving_tiles']/nb and r['oracle_tile_fraction']==r['oracle_required_tiles']/nb
                assert r['oracle_gap_tiles']==r['empty_but_surviving_tiles']==r['surviving_tiles']-r['oracle_required_tiles']
                assert r['true_hit_count']<=r['oracle_objects_in_required_tiles']<=r['surviving_objects']
                assert r['endpoint_reads']==r['certificate_scalar_reads']==8*nb and r['certificate_checks']==nb and r['pivot_interval_checks']==4*nb and r['metadata_bytes']==64*nb and r['query_pivot_distances']==4
                assert r['modeled_fullD_distances']==r['surviving_objects']+4
            if previous:assert all(b['surviving_objects']<=a['surviving_objects'] and b['true_hit_count']==a['true_hit_count'] for a,b in zip(previous,rr))
            previous=rr
            if t==256:
                for r,o in zip(rr,anchor):assert r['surviving_objects']==o['candidate_objects_in_surviving_blocks'] and r['surviving_tiles']==o['surviving_blocks'] and r['oracle_required_tiles']==o['oracle_required_blocks']
    oracle=[{k:r[k] for k in ('snapshot','tile_size','query','qid','total_tiles','oracle_required_tiles','oracle_tile_fraction','oracle_objects_in_required_tiles','empty_but_surviving_tiles','oracle_gap_tiles','true_hit_count','false_prune_tiles')} for r in q['rows']]
    assert oracle==load(root/'oracle/ORACLE_BY_TILE.json')['rows']
    for name in ('tile_vs_surviving_objects','tile_vs_metadata','tradeoff_frontier'):
        with (root/'figures'/(name+'.csv')).open() as f:plot=list(csv.DictReader(f))
        assert len(plot)==10
        for r,l,s in zip(plot,q['layouts'],q['summary']):
            assert r['snapshot']==l['snapshot'] and int(r['tile_size'])==l['tile_size']
            if 'mean_surviving_object_percent' in r:assert float(r['mean_surviving_object_percent'])==100*s['statistics']['surviving_object_fraction']['mean']
            if 'metadata_bytes' in r:assert int(r['metadata_bytes'])==l['metadata_bytes'] and int(r['endpoint_reads'])==l['endpoint_reads']
    inventory={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='DELIVERY_MANIFEST.json'}
    if seal:(root/'DELIVERY_MANIFEST.json').write_text(json.dumps(dict(files=inventory),indent=2)+'\n')
    else:assert inventory==load(root/'DELIVERY_MANIFEST.json')['files']
    print(json.dumps(dict(passed=True,query_rows=320,tile_rows=126976,false_prune=0,decision=decide(q['summary'])['decision'],files=len(inventory)+1)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seal',action='store_true');main(p.parse_args().seal)
