"""Predeclared process-level attribution,never selecting a favorable estimator."""
import argparse,json
from pathlib import Path
from bind import require_closed
import numpy as np
from protocol import VARIANTS,load,save,sha
from quality import table
def paired(candidate,baseline):
    a=np.asarray(candidate,float);b=np.asarray(baseline,float);assert a.shape==b.shape==(6,) and (a>0).all() and (b>0).all()
    logs=np.log(a/b);rng=np.random.default_rng(2026101705);boots=np.exp(logs[rng.integers(0,6,(20000,6))].mean(axis=1))
    return dict(candidate_over_comparator=float(np.exp(logs.mean())),bootstrap95=list(map(float,np.quantile(boots,[.025,.975]))),marginal_median_ratio=float(np.median(a)/np.median(b)),process_wins=int((a<b).sum()),candidate_process_values=list(map(float,a)),comparator_process_values=list(map(float,b)),forward_ratio=float(np.exp(logs[::2].mean())),reverse_ratio=float(np.exp(logs[1::2].mean())))
def summarize(p,j,checked):
    m=checked['metadata'];ops=table(str(p)+'.ops.csv');pairs=table(str(p)+'.pairs.csv');u=table(str(p)+'.updates.csv');result={**j,'metadata':m,'native_moves':checked['native_moves'],'final_assignments':checked['final_assignments'],'RAW':checked['expected_RAW'],'WAW':checked['expected_WAW'],'ledger':checked['ledger']}
    for name,kind in (('delete',0),('insert',1),('query',2)):
        values=np.array([float(r['ack_ms']) for r in ops if int(r['kind'])==kind]);result[name+'_mean_ms']=float(values.mean());result[name+'_p50_ms']=float(np.quantile(values,.5));result[name+'_p95_ms']=float(np.quantile(values,.95));result[name+'_total_ms']=float(values.sum())
    result['replacement_mean_ms']=float(np.mean([float(r['ack_ms']) for r in pairs]));result['replacement_p95_ms']=float(np.quantile([float(r['ack_ms']) for r in pairs],.95));result['service_ms']=m['service_ms'];result['capture_mean_ms']=checked['ledger']['capture_ms']/len(u);result['plan_construction_mean_ms']=checked['ledger']['plan_ms']/len(u)
    result['delete_points_per_s']=1000*m['replacements']/result['delete_total_ms'];result['insert_points_per_s']=1000*m['replacements']/result['insert_total_ms'];result['replacement_points_per_s']=1000*m['replacements']/sum(float(r['ack_ms']) for r in pairs)
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();w=a.work;require_closed(w);assert load(w/'qualification/RESULTS.json')['complete'] and load(w/'primary/RESULTS.json')['complete'];a.out.mkdir()
    reg=load(w/'REGISTERED.json');jobs=reg['schedule']['primary'];records=[];visits={}
    for j in jobs:
        path=w/'primary/outputs'/j['label'];checked=load(w/'primary'/(j['label']+'.checked.json'));key=(j['family'],j['batch'],j['micro']);visits.setdefault(key,checked['query_coordinate_visits']);assert visits[key]==checked['query_coordinate_visits'],'query work changed across variants'
        records.append(summarize(path,j,checked))
    groups={};contrasts=[];metrics=('service_ms','delete_mean_ms','insert_mean_ms','query_mean_ms','replacement_mean_ms','delete_p95_ms')
    for key in visits:
        family,b,micro=key;group=[]
        for v in VARIANTS:
            rows=sorted((r for r in records if (r['family'],r['batch'],r['micro'],r['variant'])==(*key,v)),key=lambda r:r['round']);assert [r['round'] for r in rows]==list(range(1,7))
            summary={metric:dict(median=float(np.median([r[metric] for r in rows])),p10=float(np.quantile([r[metric] for r in rows],.1)),p90=float(np.quantile([r[metric] for r in rows],.9))) for metric in metrics};group.append(dict(variant=v,metrics=summary))
        groups[str(key)]=group
        comparisons=[('NATIVE',v) for v in VARIANTS[1:]]+[('WAVES','GENERIC_WAVES'),('GENERIC_WAVES','GENERIC_DSE'),('GENERIC_DSE','TAIL_GENERIC'),('TAIL_GENERIC','TAIL_CUSTOM'),('GENERIC_DSE','TAIL_CUSTOM')]
        for baseline,candidate in comparisons:
            cell={v:sorted((r for r in records if (r['family'],r['batch'],r['micro'],r['variant'])==(*key,v)),key=lambda r:r['round']) for v in (baseline,candidate)}
            contrasts.append(dict(family=family,batch=b,micro=micro,comparator=baseline,candidate=candidate,ratios={m:paired([r[m] for r in cell[candidate]],[r[m] for r in cell[baseline]]) for m in metrics}))
    save(a.out/'PROCESSES.json',records);save(a.out/'SUMMARY.json',dict(groups=groups,contrasts=contrasts,query_coordinate_visits_invariant=True,bootstrap_seed=2026101705,bootstrap_resamples=20000,scope='Process-conditional on fixed synthetic traces;no cross-family pooled win,no exclusive algorithm novelty',registration_sha256=sha(w/'REGISTERED.json')))
    print('ANALYZED',len(records),'processes',len(contrasts),'contrasts',flush=True)
if __name__=='__main__':main()
