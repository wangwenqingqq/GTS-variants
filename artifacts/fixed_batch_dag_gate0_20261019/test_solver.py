"""Independent exhaustive finite-chain oracle and fail-closed input fixtures."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import csv
import functools
import itertools
import json
from pathlib import Path
import random
import struct
import subprocess
import numpy as np
from prepare import write_cases, save


def exact(sequences):
    @functools.lru_cache(None)
    def visit(position):
        choices = {s[k] for s,k in zip(sequences,position) if k < len(s)}
        if not choices:
            return 0
        return 1+min(visit(tuple(k+int(k < len(s) and s[k] == t)
                                 for s,k in zip(sequences,position))) for t in choices)
    return visit((0,)*len(sequences))


def witness(orders, depths, code):
    assert len(code)%4 == 0
    position = [0]*len(depths)
    for at in range(0,len(code),4):
        zone,mask = int(code[at:at+2],16),int(code[at+2:at+4],16)
        ready = sum(1<<q for q in range(len(depths))
                    if position[q] < depths[q] and orders[q][position[q]] == zone)
        assert ready == mask and mask
        for q in range(len(depths)):
            position[q] += int(bool(mask & (1<<q)))
    assert position == depths


def run(binary, out):
    out.mkdir()
    rng = random.Random(2026101902)
    examples = []
    for b,z in ((2,3),(4,5),(8,3)):
        for r in range(12):
            orders = [rng.sample(range(z),z) for _ in range(b)]
            contexts = {}
            for _ in range(10):
                d = [rng.randrange(z+1) for _ in range(b)]
                key = sum(v << (5*q) for q,v in enumerate(d))
                contexts[key] = contexts.get(key,0)+1
            examples.append((orders,contexts))
    # Full overlap, no overlap, contradictory order, empty, and delayed reconvergence.
    examples += [([[0,1,2],[0,1,2]],{0:1,3+(3<<5):1}),
                 ([[0,1,2],[1,0,2]],{1+(1<<5):1,3+(3<<5):1}),
                 ([[0,2,1],[1,0,2],[2,1,0]],{3+(3<<5)+(3<<10):1})]
    checked,strict,bounded = 0,0,0
    for i,(orders,contexts) in enumerate(examples):
        path = out/f'{i:02}.bin'
        write_cases(path,np.asarray(orders),contexts)
        for cap in (0,1,2,100000):
            result = out/f'{i:02}_{cap}.csv'
            budget = cap if cap < 3 else cap*len(contexts)
            r = subprocess.run([str(binary),str(path),str(result),str(cap),str(budget)],capture_output=True,text=True)
            assert r.returncode == 0,(r.stdout,r.stderr)
            rows = list(csv.DictReader(result.open()))
            assert len(rows) == len(contexts)
            for row in rows:
                key = int(row['key'])
                d = [(key >> (5*q)) & 31 for q in range(len(orders))]
                wanted = exact(tuple(tuple(s[:n]) for s,n in zip(orders,d)))
                lo,hi = int(row['lower']),int(row['upper'])
                assert lo <= wanted <= hi <= min(int(row[k]) for k in ('trie','fanout','lookahead'))
                assert int(row['frequency']) == contexts[key]
                witness(orders,d,row['witness'])
                assert len(row['witness'])//4 == hi
                if cap == 100000:
                    assert lo == hi == wanted
                    strict += wanted < int(row['lookahead'])
                if cap in (1,2) and int(row['expanded']):
                    bounded += 1
                checked += 1
            assert sum(int(row['expanded']) for row in rows) <= budget
    # The exact recurrence is independently checked against supersequence enumeration.
    for a,b in itertools.product(itertools.permutations(range(3)),repeat=2):
        optimum = exact((a,b))
        assert any(all(iter_subsequence(s,word) for s in (a,b))
                   for word in itertools.product(range(3),repeat=optimum))
        assert not any(all(iter_subsequence(s,word) for s in (a,b))
                       for word in itertools.product(range(3),repeat=optimum-1))
    base = (out/'00.bin').read_bytes()
    mutations = [base[:7],b'wrong!!!'+base[8:],base+b'x',base[:20]+b'\xff'+base[21:]]
    failures = 0
    for i,body in enumerate(mutations):
        f = out/f'invalid{i}.bin';f.write_bytes(body)
        r = subprocess.run([str(binary),str(f),str(out/f'invalid{i}.csv'),'1','1'],capture_output=True)
        assert r.returncode != 0
        failures += 1
    assert checked >= 1000 and strict > 0 and bounded > 0
    result = dict(passed=True,oracle_brackets_checked=checked,exact_DP_against_word_enumeration=36,
                  strict_oracle_wins=strict,bounded_search_branches=bounded,
                  batch_budget_exhaustion_checked=True,invalid_inputs_rejected=failures,
                  empty_and_reconvergent_cases=True,GPU_starts=0)
    save(out/'TESTS.json',result)
    print(json.dumps(result,sort_keys=True))


def iter_subsequence(sequence,word):
    at = iter(word)
    return all(any(x == value for x in at) for value in sequence)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    run(a.binary,a.out)
