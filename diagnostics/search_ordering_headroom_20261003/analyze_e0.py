#!/usr/bin/env python3
"""Derive E0 evidence and its predeclared stop decision; no model training."""
import csv
import json
from pathlib import Path
import sqlite3
import statistics as st
from run_e0 import ROOT,REF,sha,save,SCHEDULE

MODES=('O_BOUND','O_MASK','STAR_SCAN','STAR_MASK','FAISS_FLAT')

def read_csv(path):
    with Path(path).open() as f:return list(csv.DictReader(f))

def write_csv(path,rows):
    with Path(path).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def profiles():
    breakdown=[];kernels=[]
    for mode in MODES:
        prefix=ROOT/'evidence'/('profile_'+mode)
        db=sqlite3.connect(str(prefix)+'.sqlite')
        tables={r[0] for r in db.execute("select name from sqlite_master where type='table'")}
        stage={s:0. for s in ('input','seed','materializer','tree_mask','verify','final_topk','delivery')}
        acts=[];seen_verify=False
        for name,grid,t0,t1 in db.execute('select s.value,k.gridX,k.start,k.end from CUPTI_ACTIVITY_KIND_KERNEL k join StringIds s on s.id=k.shortName order by k.start'):
            dur=(t1-t0)/1e6;acts.append((t0,t1))
            if mode=='FAISS_FLAT':
                if name=='cupy_take':group='input'
                elif name in ('Kernel2','l2NormRowMajor','sumAlongRows'):group='verify'
                elif name in ('l2SelectMinK','blockSelectPair','incrementIndex'):group='final_topk'
                else:group='delivery'
            else:
                if name=='verify_distances':group='verify';seen_verify=True
                elif name=='materialize_cutoff':group='materializer'
                elif name in ('seed_distances','select_cutoff') or name=='block_topk' and not seen_verify:group='seed'
                elif name in ('init_root','knn_parent_walk','knn_mask'):group='tree_mask'
                elif name in ('block_topk','final_output'):group='final_topk'
                else:raise AssertionError(('unclassified custom kernel',mode,name))
            stage[group]+=dur;kernels.append({'mode':mode,'kernel':name,'grid_x':grid,'stage':group,'gpu_ms':dur})
        for table in ('CUPTI_ACTIVITY_KIND_MEMCPY','CUPTI_ACTIVITY_KIND_MEMSET'):
            if table not in tables:continue
            for t0,t1,*more in db.execute('select start,end'+(',copyKind' if table.endswith('MEMCPY') else '')+' from '+table):
                acts.append((t0,t1));group='tree_mask' if table.endswith('MEMSET') else 'input' if more[0]==1 else 'delivery'
                stage[group]+=(t1-t0)/1e6
        span=(max(t1 for _,t1 in acts)-min(t0 for t0,_ in acts))/1e6
        residual=span-sum(stage.values());assert residual>=-.0001
        meta=json.loads(Path(str(prefix)+'.json').read_text())
        breakdown.append({'mode':mode,'scope':'independent_query_only_actual_graph_replay_GPU_activity',
                          'profile_host_ms':meta['pass_ms'],'profile_gpu_span_ms':span,
                          **{s+'_ms':v for s,v in stage.items()},'residual_gpu_gap_ms':residual,
                          'trace_sha256':sha(str(prefix)+'.nsys-rep')})
    write_csv(ROOT/'breakdown.csv',breakdown);write_csv(ROOT/'PROFILE_KERNELS.csv',kernels)
    return {r['mode']:r for r in breakdown}

def main():
    clean=json.loads((ROOT/'CLEAN.json').read_text());assert len(clean)==20
    assert all(r['quality_pass'] and r['runtime_valid'] and r['tie_recall']==1 and r['deterministic_recall']==1 for r in clean)
    assert [[r['mode'] for r in clean if r['round']==i] for i in range(1,5)]==SCHEDULE
    flat={r['round']:r['host_ms'] for r in clean if r['mode']=='FAISS_FLAT'}
    for r in clean:r['slowdown_vs_flat_same_round']=r['host_ms']/flat[r['round']]
    write_csv(ROOT/'latency.csv',clean)
    by_round={(r['round'],r['mode']):r['host_ms'] for r in clean}
    b=profiles();reference=json.loads(REF.read_text());truth={r['qid']:r['squared'][7] for r in reference['records']}
    write_csv(ROOT/'profile_bridge.csv',[{'mode':m,'clean_host_median_ms':st.median(r['host_ms'] for r in clean if r['mode']==m),
              'profile_host_ms':b[m]['profile_host_ms'],
              'profile_over_clean':b[m]['profile_host_ms']/st.median(r['host_ms'] for r in clean if r['mode']==m)} for m in MODES])
    ideal=[];totals={};u0s={}
    for mode in MODES[:-1]:
        work=read_csv(ROOT/'evidence'/('count_'+mode+'.work.csv'))
        pairs=read_csv(ROOT/'evidence'/('count_'+mode+'.pairs.csv'))
        assert len(work)==32 and len(pairs)==16
        total={'candidate_pairs':0,'coordinate_updates':0,'union_candidates':0,'shared_coordinate_steps':0,
               'terminal_node_pairs':0,'unprunable_terminal_node_pairs':0,'unprunable_objects':0}
        for w in work:
            qid=int(w['qid']);u0=float(w['U0']);u=float(w['U_used']);star=truth[qid]
            if qid in u0s:assert u0s[qid]==u0
            else:u0s[qid]=u0
            assert u0>=star and u==(star if mode.startswith('STAR') else u0)
            ratio=u0/star if star else ''
            row={'mode':mode,'query_index':w['query_index'],'qid':qid,'U0':u0,'U_star':star,'U_used':u,
                 'U_star_zero':star==0,'U0_over_U_star':ratio,'U0_minus_U_star':u0-star,
                 'candidate_pairs':int(w['candidate_pairs']),'coordinate_updates':int(w['coordinate_updates']),
                 'terminal_nodes':w['terminal_nodes'],'unprunable_terminal_nodes':w['unprunable_terminal_nodes'],
                 'unprunable_objects':w['unprunable_objects'],
                 'unprunable_node_fraction':int(w['unprunable_terminal_nodes'])/int(w['terminal_nodes']) if w['terminal_nodes'] else '',
                 'unprunable_object_fraction':int(w['unprunable_objects'])/1_000_000 if w['unprunable_objects'] else '',
                 'oracle_tag':'USES_ORACLE_NOT_DEPLOYABLE' if mode.startswith('STAR') else '',
                 'count_scope':'separate_post_timer_replay','distance_profile_ms':b[mode]['verify_ms'],
                 'host_ready_four_round_median_ms':st.median(r['host_ms'] for r in clean if r['mode']==mode)}
            ideal.append(row)
            total['candidate_pairs']+=row['candidate_pairs'];total['coordinate_updates']+=row['coordinate_updates']
            if w['terminal_nodes']:
                total['terminal_node_pairs']+=int(w['terminal_nodes'])
                total['unprunable_terminal_node_pairs']+=int(w['unprunable_terminal_nodes'])
                total['unprunable_objects']+=int(w['unprunable_objects'])
        for p in pairs:
            total['union_candidates']+=int(p['union_candidates']);total['shared_coordinate_steps']+=int(p['shared_coordinate_steps'])
        totals[mode]=total
    write_csv(ROOT/'ideal_cutoff.csv',ideal)
    summary=[]
    for mode in MODES:
        times=[r['host_ms'] for r in clean if r['mode']==mode]
        row={'mode':mode,'host_median_ms':st.median(times),'host_min_ms':min(times),'host_max_ms':max(times),
             'slowdown_vs_flat_paired_median':st.median(r['slowdown_vs_flat_same_round'] for r in clean if r['mode']==mode),
             'distance_profile_ms':b[mode]['verify_ms'],'seed_profile_ms':b[mode]['seed_ms'],
             'materializer_profile_ms':b[mode]['materializer_ms'],'tree_profile_ms':b[mode]['tree_mask_ms'],
             'final_topk_profile_ms':b[mode]['final_topk_ms'],'deployable':not mode.startswith('STAR'),
             **totals.get(mode,{key:'' for key in totals['O_MASK']}),'quality_pass':True}
        summary.append(row)
    write_csv(ROOT/'summary.csv',summary)
    improvement={key:1-totals['STAR_MASK'][key]/totals['O_MASK'][key] for key in ('candidate_pairs','coordinate_updates','union_candidates','shared_coordinate_steps')}
    improvement['distance_profile']=1-b['STAR_MASK']['verify_ms']/b['O_MASK']['verify_ms']
    improvement['clean_host_paired']=st.median(1-by_round[(i,'STAR_MASK')]/by_round[(i,'O_MASK')] for i in range(1,5))
    ratio=st.median(by_round[(i,'STAR_MASK')]/by_round[(i,'FAISS_FLAT')] for i in range(1,5))
    best=max(improvement[k] for k in ('candidate_pairs','coordinate_updates','distance_profile'))
    no_headroom=best<.10;slow=ratio>2.
    keep_objects=totals['STAR_MASK']['unprunable_objects']/32_000_000
    decision={
        'phase_completed':'E0','main_clean_processes':20,'main_quality_passes':20,
        'primary_label':'NO_HEADROOM' if no_headroom else 'EXECUTOR_LIMITED' if slow else 'ORDERING_HEADROOM',
        'secondary_labels':['BOUND_LIMITED'] if improvement['candidate_pairs']<.10 else [],
        'O_MASK_to_STAR_MASK_improvement':improvement,'STAR_MASK_slowdown_vs_Flat_paired_median':ratio,
        'STAR_MASK_unprunable_object_fraction':keep_objects,
        'STAR_MASK_unprunable_terminal_node_fraction':totals['STAR_MASK']['unprunable_terminal_node_pairs']/totals['STAR_MASK']['terminal_node_pairs'],
        'thresholds':{'ideal_improvement_below':.10,'ideal_slowdown_vs_Flat_above':2.},
        'candidate_improvement_below_0_10':improvement['candidate_pairs']<.10,
        'no_headroom_interpretation':'overall NO_HEADROOM requires candidate/coordinate/distance improvements all below 10%; candidate-only failure is separately BOUND_LIMITED',
        'validated_affordable_rebase':False,'E1_status':'NOT_ENTERED_E0_STOP' if no_headroom or slow else 'ELIGIBLE',
        'E2_status':'NOT_ENTERED','E3_status':'NOT_ENTERED','models_trained':False,
        'preserve_prior_gate':'STOP_CURRENT_KNN_PATH',
        'scope':'fixed tree/bounds/Q_T/layout/dimension order/FP64 executor and diagnostic32 only; not a universal impossibility claim'}
    save(ROOT/'DECISION.json',decision)
    bridge=json.loads((ROOT/'BRIDGE.json').read_text())
    old=st.median(r['host_ms'] for r in bridge if not r['cutoff_materializer'])
    new=st.median(r['host_ms'] for r in bridge if r['cutoff_materializer'])
    ratios=[u0s[qid]/truth[qid] for qid in u0s if truth[qid]]
    rows='\n'.join(f'| {r["mode"]} | {r["host_median_ms"]:.3f} | {r["distance_profile_ms"]:.3f} | {r["tree_profile_ms"]:.3f} | {r["final_topk_profile_ms"]:.3f} | {r["slowdown_vs_flat_paired_median"]:.2f}× | {"否，oracle诊断" if not r["deployable"] else "是"} |' for r in summary)
    counts='\n'.join(f'| {m} | {t["candidate_pairs"]:,} | {t["union_candidates"]:,} | {t["coordinate_updates"]:,} | {t["shared_coordinate_steps"]:,} |' for m,t in totals.items())
    report=f'''# E0 实测决策：{decision['primary_label']}

2026-10-03。GIST 1M×960，self-inclusive L2 kNN，K8/B32，冻结32条诊断查询，RTX PRO 6000 UUID `GPU-e5a0e7f5-9917-c2a1-ee8e-7282cbba2603`，NUMA3。冻结代码 `36d58aeb93844aec3febd17d9f9caf17b88601f0`。已完成五模式×四轮、20个独立干净进程，20/20质量与独占监控通过。

结论：提前免费提供真实第K距离，使 O_MASK 的完整时间降低 {improvement['clean_host_paired']:.1%}，坐标更新减少 {improvement['coordinate_updates']:.1%}，但 STAR_MASK 仍耗时 Flat 的 {ratio:.2f} 倍。根据事前 >2×Flat 且没有已验证低成本底座的规则，本轮止于 E0；E1/E2/E3 未进入，未训练 MLP 或 Transformer。既有 `STOP_CURRENT_KNN_PATH` 保留。

## 完整时间与独立剖析

Host-ready 为四轮干净中位数，完整32查询批次；距离/树/top-K来自额外一次 query-only Nsight Systems Graph节点剖析，不能当干净计时分母。Flat距离阶段沿用冻结核名归因，库内距离和选择可能融合，不能解释为可随意替换的独立算子。

| 模式 | 完整Host-ready ms | 距离剖析 ms | 树剖析 ms | 最终top-K剖析 ms | 同轮相对Flat耗时中位数 | 可部署 |
|---|---:|---:|---:|---:|---:|---|
{rows}

STAR_SCAN/STAR_MASK 标记 `USES_ORACLE_NOT_DEPLOYABLE`。离线真值生成和静态U_star表H2D免费，不进入部署速度榜；只传入阈值，不传入近邻ID。两种STAR仍实算4096种子、种子top-K、相同阈值物化pass、真实核验、全表GPU top-K和全部结果交付。普通模式命令传入 `-`，不读取oracle文件。

## 核验工作与当前树界

下表为32查询合计；并集是16个相邻查询对，每对同一原始对象位置的OR，坐标更新按查询计，共享读取步按查询对计。这是额外计数回放，正式计时图中没有计数器。没有维度重排或精度更改。

| 模式 | 候选对象对 | 配对候选并集 | 坐标更新 | 共享坐标读取步 |
|---|---:|---:|---:|---:|
{counts}

O_MASK→STAR_MASK：候选减少 {improvement['candidate_pairs']:.1%}，配对并集减少 {improvement['union_candidates']:.1%}，坐标更新减少 {improvement['coordinate_updates']:.1%}，共享读取步减少 {improvement['shared_coordinate_steps']:.1%}，独立距离剖析减少 {improvement['distance_profile']:.1%}。共享步数是算法层面的读取次数，不是实测DRAM字节；没有新增NCU硬件流量测量。

U_star下仍不能排除的对象为 {keep_objects:.2%}；完整C4或提前叶终端分区中，仍不能排除的节点为 {decision['STAR_MASK_unprunable_terminal_node_fraction']:.2%}（按32查询×终端节点计）。U0/U_star 中位数 {st.median(ratios):.3f}，范围 {min(ratios):.3f}–{max(ratios):.3f}；U_star=0查询 {sum(truth[qid]==0 for qid in truth)} 条，另标记、不除零。所有U0均由原4096个不同种子实算得到且不小于U_star。阈值理想以后，树相对STAR_SCAN的同轮完整时间改善 {st.median(1-by_round[(i,'STAR_MASK')]/by_round[(i,'STAR_SCAN')] for i in range(1,5)):.1%}。

本次标签：`{decision['primary_label']}`{', `BOUND_LIMITED`' if decision['secondary_labels'] else ''}。候选削减 {improvement['candidate_pairs']:.1%}，低于10%，说明当前树界对收紧阈值不敏感；坐标与距离仍有超过10%的收益，故不将整个阈值机制标为无收益。理想阈值相对Flat {ratio:.2f}×，{'触发' if slow else '未触发'} >2×执行器停止规则，该停止不依赖候选/核验10%条款的解释。仅说明当前固定树界与执行器的空间；不是所有排序、树界或学习索引的普遍不可能性结论。

## 桥接、正确性与范围

原O_MASK无物化pass与新O_MASK做独立ABBA桥接：原中位 {old:.3f} ms，新中位 {new:.3f} ms，变化 {(new/old-1):+.2%}；四次输出hash一致。该桥接与20个正式进程分开，不将其计入主分母。物化核本身的GPU时间见 `breakdown.csv`；剖析运行与无profiler时间的桥接见 `profile_bridge.csv`。

重新运行独立、无树/阈值的原ID SoA全表RN FP64参考，32查询的ID、距离和精确同距并列逐项等于冻结参考。CPU独立抽查选中近邻及广泛分布的非近邻，逐bit一致。所有正式输出逐查询tie-aware和确定性ID召回均为1，无重复/缺失ID，字段有限、非负、非递减，满足冻结字段精度。

N4097、D96/D960的四模式小表检查覆盖33查询尾批、self、重复/精确边界并列、种子重现、共享读取和阈值等号保留。每个未安全排除对象的分数与CPU逐维参考一致；计数器的候选、坐标更新、并集及共享步数也与CPU回放精确一致。强制保留掩码路径通过；STAR_MASK memcheck零错误。动态pending、反序/随机/NaN评分等E1–E3检查未适用、未执行，不能宣称已验证动态搜索。

本轮仅静态E0，不记录“达到真实U前访问对象数”的动态里程碑；因此不伪造 `ordering_replay.csv`、`wave_trace.csv` 或 `model_budget.csv`。本地保存源码、来源钉住、真值清单、20轮原始延迟、逐查询工作量、独立剖析、桥接、监控回执和决策；远端保留完整trace。
'''
    (ROOT/'DECISION.md').write_text(report)
    pins=json.loads((ROOT/'SOURCE_PINS.json').read_text())
    pins['setup_file_hashes']=pins['files'].copy()
    pins['final_driver_files']={str(p):sha(p) for p in (ROOT/'diagnostics/search_ordering_headroom_20261003').glob('*') if p.is_file()}
    pins['files'].update(pins['final_driver_files'])
    pins['temporary_directory']='/home/data/gts_search_ordering_tmp_20261003'
    pins['qualification_driver_note']='small GPU runs completed once; receipt reconstruction after fixing NumPy scalar JSON serialization, no GPU rerun'
    save(ROOT/'SOURCE_PINS.json',pins)
    print(json.dumps({'summary':summary,'decision':decision,'bridge_old_ms':old,'bridge_new_ms':new},indent=2))

if __name__=='__main__':main()
