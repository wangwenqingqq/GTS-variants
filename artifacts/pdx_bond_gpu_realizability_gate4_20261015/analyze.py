"""Reconstruct CPU gates exactly from full-population histograms."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import hashlib
import importlib.util
import json
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fraction(x):
    return {'numerator': x.numerator, 'denominator': x.denominator, 'decimal': float(x)}


def logical_gate(capture):
    return 'LOGICAL_STRONG' if capture >= Fraction(3,5) else 'LOGICAL_MODERATE' if capture >= Fraction(3,10) else 'LOGICAL_WEAK'


def analyze(repo, data, out):
    c = load(HERE/'CONTRACT.json')
    assert data['complete'] and data['contract_sha256'] == sha(HERE/'CONTRACT.json')
    assert data['pairs'] == 32000000 and data['GPU_starts'] == 0 and len(data['records']) == 32
    assert all(sha(repo/n) == h for n, h in c['parents'].items())
    spec = importlib.util.spec_from_file_location('histogram', repo/'artifacts/exact_representation_gate1_20261012/analyze.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    totals = {k: [0]*961 for k in ('nominal','safe')}
    raw, rows, hits = {}, [], 0
    for i, r in enumerate(data['records']):
        assert r['query_index'] == i and r['qid'] == c['qids'][i] and r['N'] == 1000000 and r['D'] == 960
        assert r['full_score_bit_mismatches'] == r['safe_false_rejections'] == 0
        assert sorted(r['zone_ids']) == list(range(30))
        assert r['zone_ids'][:3] == sorted(r['zone_ids'][:3]) and r['zone_ids'][3:] == sorted(r['zone_ids'][3:])
        for k, h in r['histograms'].items():
            assert k in totals and len(h) == 961 and h[0] == 0 and sum(h) == c['N']
            assert all(type(v) is int and v >= 0 for v in h) and h[-1] >= r['hits']
            totals[k] = [a+b for a,b in zip(totals[k],h)]
        assert all(r['survivors'][str(s)] == sum(r['histograms']['safe'][s+1:]) for s in (128,256,512))
        raw.update(r['raw']); rows.append(r); hits += r['hits']
    assert hits == 6590
    sums = {k: sum(i*v for i,v in enumerate(h)) for k,h in totals.items()}
    capture = {k: Fraction(5353331672-s, 5353331672-1408598728) for k,s in sums.items()}
    labels = {k: logical_gate(v) for k,v in capture.items()}
    assert labels['nominal'] == labels['safe'], 'unstable guard admission;stop'
    out.mkdir(parents=True, exist_ok=False)
    def write(name,v):
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
    write('logical/PDX_BOND.json', {'status':'MEASURED_CPU_DIAGNOSTIC', 'pairs':32000000,'true_hits':hits,
        **{k:{**old.histogram_stats(h),'p50':old.histogram_stats(h)['median'],'dimension_sum':sums[k],'histogram':h} for k,h in totals.items()},
        'cutoff_ties':sum(r['cutoff_tie_count'] for r in rows),'guard_changed_pairs':sum(r['nominal_hit_cross_guard_fallback_difference'][2] for r in rows),
        'scope':'ideal per-coordinate first crossing within fixed zone order;not stage fetch count or GPU traffic'})
    write('logical/GAP_CAPTURE.json', {'status':'MEASURED_CPU_DIAGNOSTIC','captures':{k:fraction(v) for k,v in capture.items()},
        'labels':labels,'guard_gate_stable':True,'CPU_passes':1,'GPU_admitted_logically':labels['safe']!='LOGICAL_WEAK'})
    survivor_sums={str(s):sum(r['survivors'][str(s)] for r in rows) for s in (128,256,512)}
    write('source/STAGE_SURVIVORS.json', {'status':'MEASURED_CPU_DIAGNOSTIC','pairs':32000000,'survivor_sums':survivor_sums,
        'per_query':[{'query_index':r['query_index'],'qid':r['qid'],**r['survivors']} for r in rows]})
    source=None;source_label='NOT_RUN'
    if labels['safe']!='LOGICAL_WEAK':
        total=4*(32*c['N']*128+survivor_sums['128']*128+survivor_sums['256']*256+survivor_sums['512']*448)
        source=Fraction(total,32)
        source_label='SOURCE_WIN' if source<=800000000 else 'SOURCE_MARGINAL' if source<=950000000 else 'SOURCE_LOSE'
    write('source/SOURCE_BYTES.json', {'status':'DERIVED_SOURCE_MODEL' if source is not None else 'NOT_RUN','source_label':source_label,
        'mean_coordinate_source_bytes':fraction(source) if source is not None else None,
        'over_keeper':fraction(source/1014828776) if source is not None else None,
        'per_query_bytes':[4*(c['N']*128+r['survivors']['128']*128+r['survivors']['256']*256+r['survivors']['512']*448) for r in rows] if source is not None else None,
        'full_original_order_score_reload_bytes':None,'includes_actual_DRAM_or_control':False,
        'scope':'frozen stage coordinate model;FP64 restoration/retention/spill/output remain separately chargeable'})
    write('evidence/SCALARS.json',data)
    write('evidence/RAW_MANIFEST.json',{'private_only':True,'files':raw,'global_means_sha256':data['means_sha256'],'includes_dataset':False})
    write('quality/CPU_EXACTNESS.json',{'status':'CPU_CERTIFICATE_AND_AUTHORITY_PASS','pairs':32000000,
        'ordered_full_scores_bit_checked':32000000,'full_score_bit_mismatches':0,'certificate_false_rejections':0,
        'nominal_hit_crossings':sum(r['nominal_hit_cross_guard_fallback_difference'][0] for r in rows),
        'guard_fallback_nonhits':sum(r['nominal_hit_cross_guard_fallback_difference'][1] for r in rows),
        'full_GPU_output_quality':'NOT_RUN;not inferred from CPU certificates'})
    final='PRIOR_ART_LOSES' if labels['safe']=='LOGICAL_WEAK' or source_label=='SOURCE_LOSE' else None
    result={'logical':labels['safe'],'source':source_label,'final':final,'GPU_admitted':final is None,'GPU_starts':0,
        'capture':float(capture['safe']),'source_bytes':float(source) if source is not None else None}
    write('evidence/CPU_DECISION.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--results',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(analyze(a.repo,load(a.results),a.out)))
