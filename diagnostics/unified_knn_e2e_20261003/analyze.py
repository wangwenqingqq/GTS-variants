#!/usr/bin/env python3
"""Paired process estimates, full retained quality, no historical ratios."""
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
METHODS=('GTS_ORIG','O_FULL','O_BOUND','O_MASK','FAISS_FLAT','IVF_ALL')

def paired(left,right):
    a={r['round']:r for r in left};b={r['round']:r for r in right};assert set(a)==set(b)==set(range(1,7))
    ratios=np.array([a[i]['pass_ms']/b[i]['pass_ms'] for i in range(1,7)])
    logs=np.log(ratios);rng=np.random.default_rng(20261003)
    bootstrap=np.exp(logs[rng.integers(0,6,(20000,6))].mean(axis=1))
    order={}
    for label,condition in [('numerator_before',True),('numerator_after',False)]:
        values=[logs[i-1] for i in range(1,7) if (a[i]['position']<b[i]['position'])==condition]
        order[label]={'rounds':len(values),'geometric_ratio':float(np.exp(np.mean(values))) if values else None}
    eligible=all(r['quality']['complete_gate_pass'] for r in left+right)
    return {'geometric_ratio':float(np.exp(logs.mean())),'bootstrap95':np.quantile(bootstrap,[.025,.975]).tolist(),
            'wins':int((ratios>1).sum()),'round_ratios':ratios.tolist(),'order_split':order,
            'same_achieved_100_quality':eligible}

def describe(group):
    q=[r['quality'] for r in group];t=[r['pass_ms'] for r in group]
    return {'median_pass_ms':float(np.median(t)),'round_pass_ms':t,'rounds':len(t),
            'minimum_round_recall':min(r['recall_tie_aware'] for r in q),'minimum_query_recall':min(r['minimum_query_recall'] for r in q),
            'minimum_complete_query_fraction':min(r['complete_query_fraction'] for r in q),
            'minimum_deterministic_recall':min(r['recall_deterministic'] for r in q),
            'all_output_contracts_pass':all(r['output_contract_pass'] for r in q),
            'all_complete_gates_pass':all(r['complete_gate_pass'] for r in q),
            'qps':256000/float(np.median(t)),'amortized_ms_per_query':float(np.median(t))/256,
            'amortized_is_request_latency':False}

def main():
    rows=json.loads((ROOT/'FORMAL.json').read_text());schedule=json.loads((ROOT/'FORMAL_SCHEDULE.json').read_text())
    assert len(rows)==len(schedule) and {r['label'] for r in rows}=={r['label'] for r in schedule}
    assert sum(r['method'] in METHODS for r in rows)==288
    result={};table_a=['| 数据/K/B | 方法 | Recall% | 全命中查询% | 256查询 Host-ready ms | GTS/本方法 |','|---|---|---:|---:|---:|---:|']
    table_b=['| 数据/K/B | 方法/固定配置 | 开发目标 | 最终 Recall% | 最差查询Recall% | 256查询 ms | 资格 |','|---|---|---|---:|---:|---:|---|']
    frozen=json.loads((ROOT/'FROZEN_CONFIG.json').read_text())
    for dataset in ('GIST','Deep'):
        for k in (8,32):
            for b in (1,32):
                shape=f'{dataset}_k{k}_b{b}';shapes=[r for r in rows if (r['dataset'],r['K'],r['B'])==(dataset,k,b)]
                groups={}
                for r in shapes:groups.setdefault(r['variant'],[]).append(r)
                result[shape]={'methods':{},'paired_comparisons':{}}
                for label,group in groups.items():
                    assert len(group)==6
                    stats=describe(group);result[shape]['methods'][label]=stats
                    if label in METHODS:
                        ratio=paired(groups['GTS_ORIG'],group)
                        result[shape]['paired_comparisons']['GTS_ORIG/'+label]=ratio
                        rate=f'{ratio["geometric_ratio"]:.2f}×' if ratio['same_achieved_100_quality'] else '不合格'
                        table_a.append(f'| {dataset}/{k}/{b} | {label} | {stats["minimum_round_recall"]*100:.6f} | {stats["minimum_complete_query_fraction"]*100:.3f} | {stats["median_pass_ms"]:.3f} | {rate} |')
                for num,den in [('O_BOUND','O_MASK'),('FAISS_FLAT','O_MASK'),('IVF_ALL','O_MASK')]:
                    result[shape]['paired_comparisons'][num+'/'+den]=paired(groups[num],groups[den])
                for family in ('IVF','CAGRA'):
                    for target in (.99,.999,1.):
                        key=f'{family}@{target}';point=frozen['anchors'][shape][key]
                        if point['status']=='unreachable':table_b.append(f'| {dataset}/{k}/{b} | {family} | {target*100:g}% | — | — | — | 开发不可达 |');continue
                        stats=result[shape]['methods'][point['variant']]
                        admitted=stats['all_output_contracts_pass'] and stats['minimum_round_recall']>=target
                        table_b.append(f'| {dataset}/{k}/{b} | {point["variant"]} | {target*100:g}% | {stats["minimum_round_recall"]*100:.6f} | {stats["minimum_query_recall"]*100:.3f} | {stats["median_pass_ms"]:.3f} | {"达到冻结目标" if admitted else "未达冻结目标"} |')
    (ROOT/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    report='\n'.join(table_a)+'\n\n'+'\n'.join(table_b)+'\n\n'
    report+='所有时间来自本轮全新进程的连续 Host-ready pass；数据、布局、训练、建索引、Graph 捕获和审核单列且不计入。表 A 倍率为六轮配对 log-ratio 几何均值，CI/wins/order split 见 SUMMARY.json；不是中位数之比。表 B 为原生 K 输出，无精算；100% 是测试集观察，不是图搜索的完整性证明。重复配置只运行一次。失败锚点保留，未用 final 调参。\n'
    (ROOT/'RESULTS.md').write_text(report)
    print(f'ANALYSIS COMPLETE {len(rows)} processes',flush=True)

if __name__=='__main__':main()
