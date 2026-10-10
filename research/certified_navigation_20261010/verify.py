#!/usr/bin/env python3
"""Fail-closed full-output and same-semantics trace checks, not E2 admission."""
import argparse
import csv
import json
from pathlib import Path
import struct
from audit import sha,save


def result(path):
    b=Path(path).read_bytes()
    if len(b)<16:raise ValueError('truncated output')
    n,d,q,k=struct.unpack_from('<4i',b)
    if n<1 or d<1 or q<1 or k<1 or len(b)!=16+q*k*12:raise ValueError('output length')
    ids=struct.unpack_from('<'+str(q*k)+'i',b,16)
    scores=struct.unpack_from('<'+str(q*k)+'d',b,16+q*k*4)
    import math
    for row in range(q):
        keys=list(zip(scores[row*k:(row+1)*k],ids[row*k:(row+1)*k]))
        if len(set(x[1] for x in keys))!=k or any(not math.isfinite(s) or not 0<=i<n for s,i in keys):raise ValueError('invalid result')
        if keys!=sorted(keys):raise ValueError('rank key')
    return b,(n,d,q,k)


def traces(path):
    return [json.loads(x.removeprefix('TRACE ')) for x in Path(path).read_text().splitlines() if x.startswith('TRACE ')]


def verify(root,oracle,qids,out,guard_pending=False):
    reference,shape=result(oracle);queries=list(map(int,Path(qids).read_text().split()))
    if queries[0]!=shape[2] or len(queries)!=shape[2]+1:raise ValueError('query shape')
    records={};tracks={};work={}
    whole_guard=root/'guard/receipt.json'
    if not guard_pending and whole_guard.exists():
        if not json.loads(whole_guard.read_text())['runtime_valid']:raise ValueError('whole-campaign guard invalid')
    for mode in range(4):
        name='G'+str(mode);folder=root/name
        receipt=json.loads((folder/'receipt.json').read_text())
        if receipt['exit_code']!=0:raise ValueError('GPU child failed')
        if not guard_pending and not whole_guard.exists() and not receipt.get('runtime_valid',False):raise ValueError('GPU run invalid')
        b,current=result(folder/'out.bin')
        if current!=shape or b!=reference:raise ValueError('oracle mismatch: '+name)
        tracks[name]=traces(folder/'stdout.log')
        if len(tracks[name])!=shape[2]*5:raise ValueError('trace count')
        for row in tracks[name]:
            if 'visit_bits_hex' in row:
                width=10**row['level'];bits=row['visit_bits_hex']
                if len(bits)!=(width+3)//4 or any(x not in '0123456789abcdef' for x in bits):raise ValueError('visit bitset shape')
                if sum(bin(int(x,16)).count('1') for x in bits)!=row['visited']:raise ValueError('visit bitset count')
                if width%4 and int(bits[-1],16)>> (width%4):raise ValueError('visit bitset tail')
        with (folder/'out.work.csv').open() as f:work[name]=list(csv.DictReader(f))
        if len(work[name])!=shape[2] or [int(r['qid']) for r in work[name]]!=queries[1:]:raise ValueError('work query order')
        records[name]={'result_sha256':sha(folder/'out.bin'),'work_sha256':sha(folder/'out.work.csv'),'oracle_bitwise_equal':True}
    for a,b in [('G0','G1'),('G2','G3')]:
        if tracks[a]!=tracks[b]:raise ValueError('same-semantics full trace mismatch '+a+'/'+b)
        for x,y in zip(work[a],work[b]):
            for key in ['pivot_calls','leaf_calls','bound_tests']:
                if x[key]!=y[key]:raise ValueError('work mismatch '+key)
    if (root/'G2_G0_U_REPLAY').exists():
        replay=traces(root/'G2_G0_U_REPLAY/stdout.log')
        if len(replay)!=len(tracks['G0']):raise ValueError('replay trace count')
        for x,y in zip(replay,tracks['G0']):
            for key in ['upper','visited','digest',*(['visit_bits_hex'] if 'visit_bits_hex' in y else [])]:
                if x[key]!=y[key]:raise ValueError('counterfactual mismatch '+key)
        b,current=result(root/'G2_G0_U_REPLAY/out.bin')
        if b!=reference or current!=shape:raise ValueError('replay output')
    save(out,dict(stage='E1 subset correctness, not complete E2',shape=shape,records=records,
         same_semantics_trace_pairs=['G0/G1','G2/G3'],replay_checked=(root/'G2_G0_U_REPLAY').exists(),
         exact_visit_bitsets_checked=all('visit_bits_hex' in r for rows in tracks.values() for r in rows),
         oracle_sha256=sha(oracle),formal_admission=False,gpu_admission_pending=guard_pending))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('oracle',type=Path)
    p.add_argument('qids',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    verify(a.root,a.oracle,a.qids,a.out);print('PASS E1 full outputs and traces; E2 admission remains separate')
