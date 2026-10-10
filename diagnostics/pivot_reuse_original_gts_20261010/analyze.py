#!/usr/bin/env python3
"""Predeclared six-process paired estimator; no missing/failed-row promotion."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

def percentile(xs,p):
    xs=sorted(xs);pos=(len(xs)-1)*p;i=int(pos)
    return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(pos-i)

def paired(a,b,orders):
    assert len(a)==len(b)==len(orders)==6
    assert all(math.isfinite(x) and x>0 for x in a+b)
    logs=[math.log(x/y) for x,y in zip(a,b)]
    rng=random.Random(202610101333)
    bootstrap=[math.exp(statistics.mean(rng.choices(logs,k=6))) for _ in range(20000)]
    interval=[percentile(bootstrap,.025),percentile(bootstrap,.975)]
    return {'paired_geometric_G0_over_G1':math.exp(statistics.mean(logs)),
            'bootstrap_95':interval,'process_wins_G1':sum(x>y for x,y in zip(a,b)),
            'raw_paired_ratios':[x/y for x,y in zip(a,b)],
            'marginal_median_ratio':statistics.median(a)/statistics.median(b),
            'order_split':{first:math.exp(statistics.mean([logs[i] for i,o in enumerate(orders) if o[0]==first]))
                           for first in ('G0','G1')},
            'decision':'confirmed_win' if interval[0]>1 else 'confirmed_regression' if interval[1]<1 else 'inconclusive'}

def validate_chain(root):
    """Verify the complete frozen evidence chain before interpreting any timing."""
    identity=json.loads((root/'IDENTITY.json').read_text())
    gates={}
    for phase in ('diagnose','qualify','freeze','formal'):
        gate=json.loads((root/(phase+'.gate.json')).read_text())
        assert gate['identity']==identity,(phase,'identity drift')
        for name,digest in gate['outputs'].items():
            path=(root/name).resolve()
            assert path.is_relative_to(root.resolve()),name
            assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,(phase,name)
        gates[phase]=gate
    assert hashlib.sha256((root/'CONTRACT.json').read_bytes()).hexdigest()==identity['CONTRACT.json']
    frozen=json.loads((root/'FROZEN.json').read_text())
    assert frozen['identity']==identity
    assert frozen['orchestrator_sha256']==gates['freeze']['orchestrator_sha256']==gates['formal']['orchestrator_sha256']
    assert hashlib.sha256((root/'run.py').read_bytes()).hexdigest()==frozen['orchestrator_sha256']
    assert hashlib.sha256((root/'HISTORICAL_INVENTORY.json').read_bytes()).hexdigest()==frozen['inventory_sha256']
    return json.loads((root/'CONTRACT.json').read_text()),frozen

def analyze(root):
    contract,frozen=validate_chain(root);orders=contract['process_orders']
    values={m:[] for m in ('G0','G1')};rows=[]
    for number,order in enumerate(orders,1):
        for position,mode in enumerate(order):
            label=f'formal_r{number}_{mode}'
            receipt=json.loads((root/'runs'/label/'receipt.json').read_text())
            assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None
            assert json.loads((root/'runs'/label/'eligibility.json').read_text())['eligible']
            quality=json.loads((root/(label+'.quality.json')).read_text())
            assert quality['recall_tie_aware']==1 and quality['distance_tolerance_pass']
            samples=list(csv.DictReader((root/(label+'.csv')).open()));assert len(samples)==1 and samples[0]['sample']=='0'
            ms=float(samples[0]['total_ms']);values[mode].append(ms)
            rows.append({'round':number,'position':position,'mode':mode,'Q':256,'total_ms':ms,'quality':quality,
                         'workspace':json.loads((root/(label+'.reuse.json')).read_text())})
    distributions={m:{'raw_ms':x,'p10_ms':percentile(x,.1),'median_ms':statistics.median(x),'p90_ms':percentile(x,.9),
                      'arithmetic_mean_ms':statistics.mean(x),'geometric_mean_ms':math.exp(statistics.mean(map(math.log,x)))}
                   for m,x in values.items()}
    return {'scope':contract['timing_scope'],'estimator':contract['statistics'],'rows':rows,
            'distributions':distributions,'ratio':paired(values['G0'],values['G1'],orders),
            'query_scope':frozen['scope']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();x=analyze(a.root)
    with a.out.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
    print(json.dumps(x['ratio'],indent=2))
