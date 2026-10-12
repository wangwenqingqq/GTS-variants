"""Pure-CPU public histogram analysis; point gates, no sampling or latency inference."""
import argparse,bisect,json,math
from pathlib import Path
def load(p):return json.loads(Path(p).read_text())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def percentile(values,p):
    v=sorted(values);k=(len(v)-1)*p;i=int(k);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(k-i)
def histogram_stats(h):
    n=sum(h)
    if not n:return dict(count=0,mean=None,median=None,p10=None,p90=None,p95=None,p99=None)
    c=[];s=0
    for count in h:s+=count;c.append(s)
    def quantile(p):
        k=(n-1)*p;i=int(k);a=bisect.bisect_right(c,i);b=bisect.bisect_right(c,min(i+1,n-1));return a+(b-a)*(k-i)
    return dict(count=n,mean=sum(i*v for i,v in enumerate(h))/n,**{k:quantile(p) for k,p in [('median',.5),('p10',.1),('p90',.9),('p95',.95),('p99',.99)]})
def classify(mean,p90):
    if not all(math.isfinite(v) and 1<=v<=960 for v in (mean,p90)):return 'UNCLASSIFIED'
    if mean>576 or p90>720:return 'NO_GO_BYTE_REDUCTION'
    if mean<=384 and p90<=480:return 'GO_BYTE_REDUCTION'
    if 384<mean<=576:return 'CONDITIONAL_BYTE_REDUCTION'
    return 'UNCLASSIFIED'
def analyze(records,contract):
    N=contract['workload']['N'];D=contract['workload']['D'];qs=contract['workload']['qids']
    assert len(records)==32 and [r['qid'] for r in records]==qs
    total=[0]*(D+1);nonhits=[0]*(D+1);groups={k:[0]*(D+1) for k in ('near','medium','far')};per=[]
    for index,r in enumerate(records):
        h=r['histogram'];nh=r['nonhit_histogram']
        assert r['query_index']==index and r['N']==N and r['D']==D and len(h)==len(nh)==D+1 and h[0]==nh[0]==0
        assert all(isinstance(v,int) and v>=0 for v in h+nh) and sum(h)==N and sum(nh)==r['nonhits']
        assert r['hits']+r['nonhits']==N and r['full960_bit_mismatches']==r['false_rejections']==0
        assert all(h[k]==nh[k] for k in range(D)) and h[D]-nh[D]==r['hits'] and nh[D]==r['hard_nonhits_at_D']
        for i in range(D+1):total[i]+=h[i];nonhits[i]+=nh[i]
        margin_h=[0]*(D+1)
        for g,v in r['margin_groups'].items():
            assert g in groups and len(v['histogram'])==D+1 and sum(v['histogram'])==v['count']
            for i,count in enumerate(v['histogram']):assert isinstance(count,int) and count>=0;groups[g][i]+=count;margin_h[i]+=count
        assert margin_h==nh
        stats=histogram_stats(h)
        per.append(dict(query_index=index,qid=r['qid'],**stats,ideal_bytes=N*4*stats['mean'],hit_count=r['hits'],nonhit_mean=histogram_stats(nh)['mean'],hard_nonhits_at_D=r['hard_nonhits_at_D']))
    all_stats=histogram_stats(total);mean=all_stats['mean'];query_means=[r['mean'] for r in per]
    robustness={k:v(query_means) for k,v in [('min',min),('p10',lambda x:percentile(x,.1)),('median',lambda x:percentile(x,.5)),('p90',lambda x:percentile(x,.9)),('max',max)]}
    checks=[];hits=sum(r['hits'] for r in records);pairs=N*32
    for k in contract['checkpoints']:
        reject=sum(nonhits[:k+1]);checks.append(dict(K=k,rejected=reject,unresolved=pairs-reject,true_hits=hits,rejected_fraction=reject/pairs,unresolved_fraction=(pairs-reject)/pairs,hit_fraction=hits/pairs))
    margins={g:histogram_stats(h) for g,h in groups.items()}
    for g,v in margins.items():v.update(nonhit_fraction=v['count']/sum(nonhits),coordinate_savings_fraction=(sum((D-i)*n for i,n in enumerate(groups[g]))/sum((D-i)*n for i,n in enumerate(nonhits))) if sum((D-i)*n for i,n in enumerate(nonhits)) else None)
    return dict(all_objects=all_stats,nonhits=histogram_stats(nonhits),hits=hits,pairs=pairs,queries=32,per_query=per,query_mean_robustness=robustness,
        total_histogram=total,nonhit_histogram=nonhits,checkpoint_rejection=checks,margin_groups=margins,
        bytes=dict(full_bytes_per_object=D*4,mean_bytes_per_object=mean*4,full_bytes_per_query=N*D*4,ideal_bytes_per_query=N*mean*4,byte_fraction=mean/D,theoretical_reduction=1-mean/D),
        decision=classify(mean,robustness['p90']),GPU_starts=0,scope='Ideal FP32 coordinate payload only; not physical GPU traffic or measured latency')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--records',type=Path,required=True);p.add_argument('--contract',type=Path,default=Path(__file__).resolve().parent/'CONTRACT.json');p.add_argument('--output',type=Path,required=True);a=p.parse_args();save(a.output,analyze(load(a.records),load(a.contract)))
