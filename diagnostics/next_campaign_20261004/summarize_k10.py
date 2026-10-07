#!/usr/bin/env python3
"""CPU-only closure of the frozen 834 K10 rows; no measurement or retuning."""
import argparse
from collections import Counter, defaultdict
import hashlib
from itertools import combinations
import json
from pathlib import Path

import numpy as np

BASE_COMMIT = '5b145bceabbc7aa544e6d6ff25657403ea92e151'
COMPLETE = ('GTS_ORIG', 'O_FULL', 'IVF_ALL', 'O_BOUND', 'FAISS_FLAT', 'O_MASK')
ORDERS = [list(COMPLETE), ['O_FULL','O_BOUND','GTS_ORIG','O_MASK','IVF_ALL','FAISS_FLAT'],
          ['O_BOUND','O_MASK','O_FULL','FAISS_FLAT','GTS_ORIG','IVF_ALL'],
          ['IVF_ALL','GTS_ORIG','FAISS_FLAT','O_FULL','O_MASK','O_BOUND'],
          ['FAISS_FLAT','IVF_ALL','O_MASK','GTS_ORIG','O_BOUND','O_FULL'],
          ['O_MASK','FAISS_FLAT','O_BOUND','IVF_ALL','O_FULL','GTS_ORIG']]
REASONS = {
    'runtime_invalid': '运行无效', 'members_incomplete': '完整成员失败',
    'distance_fields_failed': '距离字段超容差', 'fields_only_failed': '仅字段失败',
    'output_contract_failed': '字段/输出合同失败', 'strict_quality_failed': '严格完整质量失败',
    'target_missed': '冻结召回目标未达', 'development_unreachable': '开发目标不可达，保留诊断',
    'observer_hash_mismatch': '观察器on/off输出hash不一致',
    'observer_upper_unproven': '观察成本上95未通过3%门槛',
    'observer_unregistered': 'method/config/tile未覆盖',
    'observer_source_mismatch': '代表观察器测量源码不匹配',
    'memory_failed': '内存门槛失败', 'throughput_unobservable': '调用内首/尾2k吞吐不可测',
    'throughput_declined': '已观测吞吐下降超过10%',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def config_key(config):
    return json.dumps(config, sort_keys=True, separators=(',', ':'))


def condition(row):
    return (row['protocol'], row['dataset'], row['K'],
            None if row['protocol'] == 'bulk' else row['B'])


def group_key(row):
    return (row['protocol'], row['dataset'], row['K'], row['B'], row['method'], config_key(row['config']))


def group_id(row):
    cfg = ','.join(f'{k}={v}' for k, v in sorted(row['config'].items())) or 'default'
    return f"{row['method']}[B{row['B']};{cfg}]"


def condition_id(key):
    protocol, dataset, k, b = key
    return f'{protocol}:{dataset}:K{k}' + (f':B{b}' if b is not None else '')


def expected_schedule(matched, bulk):
    """Reproduce the recorded schedule rule, not a newly chosen order."""
    expected = {}
    slices = [('matched_b32_k8', [(d,8,32) for d in ('GIST','Deep')]),
              ('matched_b32_k32', [(d,32,32) for d in ('GIST','Deep')]),
              ('matched_b1', [(d,k,1) for d in ('GIST','Deep') for k in (8,32)]),
              ('bulk', [(d,k,0) for d in ('GIST','Deep') for k in (8,32)])]
    for protocol, shapes in slices:
        for repeat in range(1, 7):
            for d, k, b in shapes:
                native = matched[f'{d}_k{k}_b{b}'] if b else bulk[f'{d}_k{k}']
                items = {m:dict(method=m, config={'nlist':1024,'nprobe':1024} if m=='IVF_ALL' else {},
                               B=b, anchors=[]) for m in COMPLETE} if b else {
                               i['method']:i.copy() for i in native if i['method'] in COMPLETE}
                require(set(items) == set(COMPLETE), '冻结策略缺少必选方法')
                for i in native:
                    if i['method'] in COMPLETE and (b or i['B']==items[i['method']]['B']):
                        items[i['method']].update(anchors=i.get('anchors', []),
                                                  development_unreachable=i.get('development_unreachable', []))
                ann = [i for i in native if i['method'] not in COMPLETE or
                       (not b and i['B'] != items[i['method']]['B'])]
                if repeat % 2 == 0:
                    ann = ann[::-1]
                controls = [items[m] for m in ORDERS[repeat-1]]
                for pos, item in enumerate(ann+controls if repeat % 2 else controls+ann):
                    row = dict(protocol=protocol, dataset=d, K=k, B=item.get('B',b),
                               round=repeat, position=pos, method=item['method'], config=item['config'],
                               anchors=item.get('anchors', []),
                               development_unreachable=item.get('development_unreachable', []))
                    label = f"{protocol}_r{repeat}_{d}_k{k}_b{row['B']}_{pos}_{row['method']}"
                    require(label not in expected, '冻结计划出现重复标签')
                    expected[label] = row
    return expected


def group_rows(rows):
    labels = set(); measured = set(); groups = defaultdict(list)
    for row in rows:
        require(row['label'] not in labels, '重复逻辑标签: '+row['label'])
        require(row['measurement_label'] not in measured, '重复实际测量标签')
        labels.add(row['label']); measured.add(row['measurement_label'])
        groups[group_key(row)].append(row)
    for group in groups.values():
        require(len(group)==6 and {r['round'] for r in group}==set(range(1,7)),
                '缺轮或重复轮: '+group_id(group[0]))
        group.sort(key=lambda r:r['round'])
    return groups


def target_status(row):
    quality = row['quality']
    out = {}
    for target in row['anchors']:
        reached = (quality['output_contract_pass'] and quality['recall_tie_aware'] is not None and
                   quality['recall_tie_aware'] >= target and (target < 1 or quality['complete_gate_pass']))
        out[str(target)] = ('diagnostic_only' if target in row['development_unreachable'] else
                            'admitted' if reached else 'missed_target')
    return out


def row_gates(row, policy, controls):
    quality, stability, observer = (row[k] for k in ('quality','stability','observer'))
    runtime = bool(row['receipt']['runtime_valid'] and row['receipt']['exit_code']==0 and
                   row['receipt']['stop_reason'] is None)
    members = bool(quality['complete_query_fraction']==1 and quality['minimum_query_recall']==1 and
                   quality['missing_neighbor_slots']==0)
    fields = bool(quality['output_contract_pass'])
    strict = bool(quality['complete_gate_pass'])
    require(not strict or (members and fields), '完整质量标记与成员/字段不一致')
    memory = bool(stability['sampled_memory_peak_bytes'] <= policy['memory_cap_bytes'] and
                  stability['retained_memory_growth_bytes'] <= policy['retained_growth_limit_bytes'])
    require(memory == stability['memory_growth_gate_pass'], '内存标记不一致')
    targets = target_status(row)
    require(targets == row['admission']['target_admission'], '目标准入标记不一致')
    require(strict == row['admission']['strict_quality_admitted'], '严格准入标记不一致')
    require(observer['qualified'] == row['admission']['observer_qualified'], '计时准入标记不一致')
    reasons = []
    if not runtime: reasons.append('runtime_invalid')
    if not members: reasons.append('members_incomplete')
    if not quality['distance_tolerance_pass']: reasons.append('distance_fields_failed')
    if not fields: reasons.append('fields_only_failed' if members else 'output_contract_failed')
    if not strict: reasons.append('strict_quality_failed')
    if 'missed_target' in targets.values(): reasons.append('target_missed')
    if 'diagnostic_only' in targets.values(): reasons.append('development_unreachable')
    if observer.get('cases'):
        cases = [controls[n] for n in observer['cases']]
        registered = {'IVF_ALL':{'nlist':1024,'nprobe':1024},
                      'CAGRA':{'itopk_size':1024,'search_width':4}}.get(row['method'],{})
        require(row['config']==registered and all(c['method']==row['method'] and c['B']==row['B'] for c in cases),
                '代表控制不属于当前method/config/tile')
        if not observer['measured_entry_and_observer_sources_match']: reasons.append('observer_source_mismatch')
        if any(not c['output_hashes_identical'] for c in cases): reasons.append('observer_hash_mismatch')
        if any(c['upper95'] > policy['observer_material_ratio'] for c in cases): reasons.append('observer_upper_unproven')
        qualified = observer['measured_entry_and_observer_sources_match'] and all(c['timer_admitted'] for c in cases)
        require(bool(qualified)==observer['qualified'], '观察器资格与登记成本控制不一致')
    else:
        require(not observer['qualified'], '缺少登记控制却声明合格计时')
        reasons.append('observer_unregistered')
    if not memory: reasons.append('memory_failed')
    observed = 'throughput_decline_over_10pct' in stability
    if not observed: reasons.append('throughput_unobservable')
    elif stability['throughput_decline_over_10pct']: reasons.append('throughput_declined')
    return dict(runtime=runtime, complete_members=members, output_fields=fields, strict_quality=strict,
                targets=targets, timer=observer['qualified'], memory=memory,
                throughput_observable=observed,
                throughput_declined=stability.get('throughput_decline_over_10pct'), reasons=reasons)


def describe(group, gates):
    q = [r['quality'] for r in group]; times = np.array([r['pass_ms'] for r in group])
    g = [gates[r['label']] for r in group]
    require(np.isfinite(times).all() and (times>0).all(), '非法完整pass时延')
    exact_target_ok = all(x['targets'].get('1.0', 'admitted')=='admitted' for x in g)
    comparable = all(x['runtime'] and x['strict_quality'] and x['timer'] and x['memory'] for x in g) and exact_target_ok
    return dict(method=group[0]['method'], B=group[0]['B'], frozen_config=group[0]['config'],
                anchors=group[0]['anchors'], development_unreachable=group[0]['development_unreachable'],
                category='A' if comparable else 'B' if group[0]['method'] in ('IVF_APPROX','CAGRA') else 'C',
                complete_quality_and_timer_comparable=comparable,
                stability_fully_observed=all(x['memory'] and x['throughput_observable'] for x in g) and
                                         sum(x['throughput_declined'] is True for x in g)<2,
                median_pass_ms=float(np.median(times)), round_pass_ms=times.tolist(),
                process_p10_p50_p90_ms=np.quantile(times,[.1,.5,.9]).tolist(),
                qps=10000000/float(np.median(times)), amortized_ms_per_query=float(np.median(times))/10000,
                amortization_is_request_latency=False,
                recall_by_round=[x['recall_tie_aware'] for x in q],
                minimum_query_recall_by_round=[x['minimum_query_recall'] for x in q],
                complete_query_fraction_by_round=[x['complete_query_fraction'] for x in q],
                squared_distance_error_by_round=[x['squared_distance_max_relative_scale1'] for x in q],
                distance_error_by_round=[x['distance_max_abs'] for x in q],
                reason_counts=dict(Counter(code for x in g for code in x['reasons'])),
                rounds=[dict(round=r['round'], position=r['position'], label=r['label'],
                             measurement_label=r['measurement_label'], gates=gates[r['label']]) for r in group])


def paired(left, right, statistical_protocol):
    """Same seeded bootstrap and estimator as P7 paired(); Q is actually 10000."""
    require([r['round'] for r in left]==[r['round'] for r in right]==list(range(1,7)), '必须按六个同轮进程配对')
    ratios = np.array([a['pass_ms']/b['pass_ms'] for a,b in zip(left,right)])
    logs = np.log(ratios)
    rng = np.random.default_rng(statistical_protocol['bootstrap_seed'])
    indices = rng.integers(0,6,(statistical_protocol['bootstrap_resamples'],6))
    bootstrap_logs = logs[indices].mean(axis=1)
    ci = np.quantile(np.exp(bootstrap_logs), [.025,.975])
    latency_ci = np.quantile(np.exp(-bootstrap_logs), [.025,.975])
    order = {}
    for name, before in [('numerator_before',True),('numerator_after',False)]:
        values = [logs[i] for i,(a,b) in enumerate(zip(left,right)) if (a['position']<b['position'])==before]
        order[name] = dict(rounds=len(values), geometric_ratio=float(np.exp(np.mean(values))) if values else None)
    wins = int((ratios>1).sum())
    return dict(geometric_ratio=float(np.exp(logs.mean())), bootstrap95=ci.tolist(),
                marginal_median_ratio=float(np.median([r['pass_ms'] for r in left])/np.median([r['pass_ms'] for r in right])),
                round_ratios=ratios.tolist(), wins=wins, order_split=order,
                robust_warm_win=bool(ci[0]>statistical_protocol['robust_ratio_lower_bound'] and
                                     wins>=statistical_protocol['robust_min_wins']),
                denominator_over_numerator_latency_bootstrap95=latency_ci.tolist(),
                latency_non_regression_gate=bool(latency_ci[1]<=statistical_protocol['non_regression_candidate_over_keeper_upper']))


def compare(left, right, a, b, contract):
    reasons = []
    for field in ('protocol','dataset','K'):
        if any(x[field]!=y[field] for x,y in zip(left,right)): reasons.append(field+'_mismatch')
    for name, stats in [('numerator',a),('denominator',b)]:
        if not stats['complete_quality_and_timer_comparable']:
            reasons.extend(name+':'+reason for reason in stats['reason_counts'])
    same_b = all(x['B']==y['B'] for x,y in zip(left,right))
    if left[0]['protocol']!='bulk' and not same_b: reasons.append('matched_B_mismatch')
    for field in ('actual_Q','query_sha256','oracle_sha256'):
        if any(x[field]!=y[field] for x,y in zip(left,right)): reasons.append(field+'_mismatch')
    before = sum(x['position']<y['position'] for x,y in zip(left,right))
    if before!=3: reasons.append('order_not_3_before_3_after')
    tree = {left[0]['method'],right[0]['method']}=={'O_BOUND','O_MASK'}
    if tree:
        key = f"{left[0]['protocol']}:{left[0]['dataset']}:K{left[0]['K']}:B{left[0]['B']}"
        require(key in contract['static_parameters_by_condition'], '缺少树净收益共同配置证据')
        require(same_b and left[0]['config']==right[0]['config'], '树净收益配置不同')
    admissible = not reasons
    stats = paired(left,right,contract['statistical_protocol']) if admissible else None
    return dict(numerator=group_id(left[0]), denominator=group_id(right[0]), comparable=admissible,
                reasons=sorted(set(reasons)), protocol='bulk_whole_pass' if left[0]['protocol']=='bulk' else 'matched_same_B',
                same_B=same_b, tree_extra_configuration_verified=tree,
                paired_measurement_labels=[[x['measurement_label'],y['measurement_label']] for x,y in zip(left,right)],
                statistics=stats)


def analyze(root):
    evidence = root/'evidence/recovery'
    def load(name): return json.loads((evidence/name).read_text())
    publication = load('PUBLICATION.json')
    names = ['K10_FORMAL_ROWS.json','K10_COMPLETION.json','K10_EXECUTION_CONTRACT.json',
             'MATCHED_POLICY.json','BULK_POLICY.json','HOOK_CONTROL_COMPLETE.json']
    for name in names:
        require(sha(evidence/name)==publication[name]['public_sha256'], '公开输入SHA改变: '+name)
    bundle, completion, contract = (load(n) for n in names[:3])
    rows = bundle['rows']; policy = json.loads((root/'ADMISSION_POLICY.json').read_text())
    require(contract['baseline_commit']==BASE_COMMIT, '分析基点改变')
    require(policy['version']==completion['freeze']['admission_policy'], '资格政策不一致')
    require(sha(root/'ADMISSION_POLICY.json')==contract['admission_policy_sha256'], '不得修改冻结资格政策')
    require(completion['decision']['comparison_admitted'] is False, '不得修改全局准入政策')
    require(bundle['raw_FORMAL_sha256']==contract['raw_FORMAL_sha256']==completion['raw_provenance_sha256']['FORMAL.json'], '原始采集身份改变')
    for name, key in [('MATCHED_POLICY.json','matched_policy_sha256'),('BULK_POLICY.json','bulk_policy_sha256')]:
        require(sha(evidence/name)==completion['freeze'][key], '冻结配置改变: '+name)
    expected = expected_schedule(load('MATCHED_POLICY.json'),load('BULK_POLICY.json'))
    require(len(rows)==len(expected)==834 and {r['label'] for r in rows}==set(expected), '正式行集与冻结计划不一致')
    replacement = {i['original_label']:(p,i) for p in contract['contamination_replacements'] for i in p['affected_round']}
    controls = {r['case']:r for r in load('HOOK_CONTROL_COMPLETE.json')['summary']}
    require(sha(evidence/'HOOK_CONTROL_COMPLETE.json')==completion['freeze']['observer_receipt_sha256'], '观察器控制身份改变')
    gates = {}
    for row in rows:
        require(all(row[k]==v for k,v in expected[row['label']].items()), '行与冻结配置/顺序不一致: '+row['label'])
        require(row['actual_Q']==10000 and row.get('Q',10000)==10000, 'actual_Q必须10000')
        q = contract['queries'][row['dataset']]
        require(row['query_sha256']==q['sha256'] and row['oracle_sha256']==q['oracle_sha256'], '查询顺序/参考身份改变')
        require(row['receipt']['binary_sha256'] in contract['entry_sha256_by_method'][row['method']], '测量入口身份改变')
        if row['method'] in ('O_BOUND','O_MASK','O_FULL','GTS_ORIG'):
            entry = 'gts_bench_p7' if row['method']=='GTS_ORIG' else 'opt_knn_bench'
            require(row['receipt']['binary_sha256']==completion['freeze']['binaries'][entry], '静态二进制身份改变')
        require(row['measurement_label'] in contract['raw_identity_sha256_by_measurement_label'], '实际测量身份缺失')
        if row['label'] in replacement:
            plan, item = replacement[row['label']]
            require(row['measurement_label']==item['measurement_label'] and
                    row['contamination_replacement']['number']==plan['number'] and
                    row['contamination_replacement']['plan_sha256']==plan['raw_plan_sha256'], '污染替代轮来源改变')
        else:
            require(row['measurement_label']==row['label'] and 'contamination_replacement' not in row, '未登记替代轮')
        gates[row['label']] = row_gates(row,policy,controls)
    groups = group_rows(rows); by_condition = defaultdict(dict)
    for group in groups.values(): by_condition[condition(group[0])][group_id(group[0])] = group
    result = dict(baseline_commit=BASE_COMMIT, input_sha256={n:sha(evidence/n) for n in names},
                  policy_sha256=sha(root/'ADMISSION_POLICY.json'), analyzer_sha256=sha(Path(__file__)),
                  statistical_protocol=contract['statistical_protocol'], numpy_version=np.__version__,
                  collection_complete=True, candidate_stable=completion['decision']['candidate_stable'],
                  comparison_admitted=False, processes=834, groups=len(groups), conditions=[],
                  unified_search_update_candidate_exists=False)
    for key, points in sorted(by_condition.items()):
        stats = {label:describe(group,gates) for label,group in sorted(points.items())}
        pairs = []
        for first, second in combinations(sorted(points),2):
            left, right = points[first],points[second]
            if left[0]['method']=='O_MASK' or (right[0]['method']!='O_MASK' and right[0]['method']=='GTS_ORIG'):
                left,right = right,left
            pairs.append(compare(left,right,stats[group_id(left[0])],stats[group_id(right[0])],contract))
        result['conditions'].append(dict(id=condition_id(key), protocol=key[0],dataset=key[1],K=key[2],matched_B=key[3],
                                         methods=stats, comparisons=pairs))
    counts = Counter(code for g in gates.values() for code in g['reasons'])
    result['row_reason_counts'] = {name:counts.get(name,0) for name in REASONS}
    result['group_categories'] = dict(Counter(g['category'] for c in result['conditions'] for g in c['methods'].values()))
    result['method_config_tile_gaps'] = []
    for c in result['conditions']:
        for label,g in c['methods'].items():
            if not g['reason_counts']: continue
            frozen_exact_ok = all(r['gates']['targets'].get('1.0','admitted')=='admitted' for r in g['rounds'])
            missing_only = (all(r['gates']['strict_quality'] and r['gates']['runtime'] and r['gates']['memory'] for r in g['rounds']) and
                            frozen_exact_ok and g['reason_counts'].get('observer_unregistered')==6)
            priority = ('P1_complete_external_missing_control' if missing_only and g['method'] in ('FAISS_FLAT','IVF_ALL') else
                        'P2_missing_ablation_control' if missing_only else 'P2_retained_diagnostic')
            result['method_config_tile_gaps'].append(dict(condition=c['id'], method=g['method'], frozen_config=g['frozen_config'],
                B=g['B'], priority=priority, reason_counts=g['reason_counts'],
                previously_failed_control=any(n in g['reason_counts'] for n in ('observer_hash_mismatch','observer_upper_unproven')),
                action='登记必要的最小补充控制；不回填旧资格' if priority.startswith('P1') else
                       '保留失败/未覆盖；不自动重测', new_measurement_performed=False))
    require(sum(not g['timer'] for g in gates.values())==completion['decision']['unqualified_timer_rows'], '计时失败计数不一致')
    require(sum(not g['strict_quality'] for g in gates.values())==completion['decision']['strict_rejected_rows'], '质量失败计数不一致')
    require(sum('missed_target' in g['targets'].values() for g in gates.values())==completion['decision']['missed_target_rows'], '目标失败计数不一致')
    return result


def values(numbers, digits=3):
    return ', '.join('未知' if n is None else f'{n:.{digits}f}' for n in numbers)


def report(result):
    matched=[p for c in result['conditions'] if c['protocol']!='bulk' for p in c['comparisons'] if p['comparable']]
    original=[p['statistics']['geometric_ratio'] for p in matched if p['numerator'].startswith('GTS_ORIG[') and p['denominator'].startswith('O_MASK[')]
    tree=[p for p in matched if p['numerator'].startswith('O_BOUND[') and p['denominator'].startswith('O_MASK[')]
    b1=[100*(1/p['statistics']['geometric_ratio']-1) for p in tree if '[B1;' in p['denominator']]
    external=[p for p in matched if p['denominator'].startswith('O_MASK[') and p['numerator'].split('[')[0] in ('FAISS_FLAT','IVF_ALL','IVF_APPROX','CAGRA')]
    lines = ['# K10：合格子比较与保留失败', '',
             f'基点 `{BASE_COMMIT}`。仅分析原834进程，未运行GPU、修改算法、换查询或重新选择参数。', '',
             '`collection_complete=true`；静态O_MASK在本合同中稳定；全局`comparison_admitted=false`。统一search/update候选不存在。', '',
             f"八个matched条件中，原始GTS/O_MASK的配对几何倍率为{min(original):.3f}–{max(original):.3f}；这是累计静态执行改善。O_BOUND/O_MASK达到预登记稳健胜出的条件为{sum(p['statistics']['robust_warm_win'] for p in tree)}/8；B1全部回退，O_MASK完整pass几何时延增加{min(b1):.2f}%–{max(b1):.2f}%。GIST/B32有约2%的小收益，Deep/B32轻微回退，不能主张统一树优势。", '',
             f"与O_MASK可比较的合格matched外部点共有{len(external)}个；{sum(p['statistics']['geometric_ratio']>1 for p in external)}个O_MASK较快，{sum(p['statistics']['geometric_ratio']<1 for p in external)}个外部较快。全部合格IVF_ALL点均比O_MASK快；bulk没有六轮质量与计时联合合格外部点，速度结论留空。", '',
             '六轮为独立进程，刻画固定查询集的运行波动，不证明跨分布泛化。时间为完整10000查询warm Host-ready pass（ms），包含输入桥接、完整输出、同步及观察器；不含冷加载/建树/layout/refit/Graph capture或计时后文件写入。', '',
             '估计量及3%/5轮门槛沿用事前合同：配对log-ratio几何均值、seeded bootstrap95、胜出轮数及顺序分层。seed20261003与20000次重采样继承既有P7 paired()；K10冻结文件未单列这两个数，本次作为采集后的分析实现参数公开，不冒充新的事前登记。稳健胜出要求下95>1.03且至少5/6轮胜出；不换成中位数之比。配对标签、全部方法/每对资格、p10/median/p90及中位数比见[K10_COMPARISON_STATUS.json](K10_COMPARISON_STATUS.json)。', '',
             'A只纳入六轮联合通过的完整质量和计时组。B保留所有ANN配置与实际质量，未资格化时间仅诊断。C逐项列失败/未覆盖/不可测；这些原因可以重叠。缺轮或身份改变会报错，不挑通过轮。', '']
    for protocol in ('matched','bulk'):
        conditions = [c for c in result['conditions'] if (c['protocol']=='bulk')==(protocol=='bulk')]
        lines += ['## '+('匹配B1/B32' if protocol=='matched' else '独立冻结chunk的bulk'), '',
                  'bulk只比较全批完成时间，方法可使用不同B，摊销值不是请求时延。' if protocol=='bulk' else 'matched要求同B、同Q、同查询顺序和参考及完整输出合同。', '',
                  '### A：完整质量与计时可比', '',
                  '| 条件 | 方法/冻结配置 | pass中位数 ms | 六轮pass ms（r1→r6） |',
                  '|---|---|---:|---|']
        for c in conditions:
            for label,g in c['methods'].items():
                if g['category']=='A': lines.append(f"| {c['id']} | {label} | {g['median_pass_ms']:.3f} | {values(g['round_pass_ms'])} |")
        lines += ['', '### 四笔账：合格的六轮同轮配对', '',
                  '| 条件 | 分子 / 分母 | 几何倍率 [95%区间] | 六轮比值 | 分母更快轮数 | 稳健胜出 |',
                  '|---|---|---|---|---:|---|']
        for c in conditions:
            external = []
            for p in c['comparisons']:
                num,den = p['numerator'].split('[')[0],p['denominator'].split('[')[0]
                primary = (num,den) in [('GTS_ORIG','O_BOUND'),('GTS_ORIG','O_MASK'),('O_BOUND','O_MASK')]
                is_external = den=='O_MASK' and num in ('FAISS_FLAT','IVF_ALL','IVF_APPROX','CAGRA')
                if not (primary or is_external) or not p['comparable']: continue
                if is_external: external.append(p['numerator'])
                s=p['statistics'];lo,hi=s['bootstrap95']
                lines.append(f"| {c['id']} | {p['numerator']} / {p['denominator']} | {s['geometric_ratio']:.6f} [{lo:.6f}, {hi:.6f}] | {values(s['round_ratios'],6)} | {s['wins']}/6 | {'是' if s['robust_warm_win'] else '否'} |")
            if not external: lines.append(f"| {c['id']} | 合格外部 / O_MASK | — | 无六轮联合合格外部点；具体原因见C及JSON | — | — |")
        lines += ['', '原始GTS/O_BOUND是已声明多项差异的累计执行改善；原始GTS/O_MASK是完整静态候选改善，均不全归因于coalescing。O_BOUND/O_MASK核对同二进制、seed4096、depth、数据/树/seed/warm身份及非模式配置后，只解释树前置在warm查询内的净收益，refit冷成本不在此倍率中。倍率>1表示分母更快；外部/O_MASK<1表示外部更快。所有合格外部均保留，不选慢对手。未依据正式结果新增dispatch规则。', '',
                  '### B：ANN实际质量与诊断时延', '',
                  '| 条件 | 方法/冻结配置 | 目标（逐轮状态） | Recall六轮 | 完整查询比例六轮 | 平方字段误差六轮 | pass中位数 / 六轮 ms | 计时 |',
                  '|---|---|---|---|---|---|---|---|']
        for c in conditions:
            for label,g in c['methods'].items():
                if g['method'] not in ('IVF_APPROX','CAGRA'): continue
                targets={str(t):[r['gates']['targets'][str(t)] for r in g['rounds']] for t in g['anchors']}
                lines.append(f"| {c['id']} | {label} | {json.dumps(targets,ensure_ascii=False)} | {values(g['recall_by_round'],8)} | {values(g['complete_query_fraction_by_round'],6)} | {values(g['squared_distance_error_by_round'],9)} | {g['median_pass_ms']:.3f} / {values(g['round_pass_ms'])} | {'合格' if all(r['gates']['timer'] for r in g['rounds']) else '仅诊断'} |")
        lines += ['', '### C：拒收、未覆盖与窗口不可测', '',
                  '| 条件 | 方法/冻结配置 | 原因（六轮中的次数） | Recall / 完整查询比例（最小） | 平方字段误差（最大） | pass中位数 / 六轮 ms（失败仍保留） |',
                  '|---|---|---|---|---:|---|']
        for c in conditions:
            for label,g in c['methods'].items():
                if not g['reason_counts']: continue
                reasons='；'.join(f'{REASONS[n]}:{v}/6' for n,v in sorted(g['reason_counts'].items()))
                lines.append(f"| {c['id']} | {label} | {reasons} | {min(g['recall_by_round']):.8f} / {min(g['complete_query_fraction_by_round']):.6f} | {max(g['squared_distance_error_by_round']):.9g} | {g['median_pass_ms']:.3f} / {values(g['round_pass_ms'])} |")
    lines += ['', '开发不可达目标仍为diagnostic_only，测试集偶然通过不改名。观察成本上界未通过不是实际开销必然超过3%的证明；on/off合法tie变化也不能代替原hash合同。90项大原生调用的首/尾2k吞吐不可测，未计为通过。', '',
              '两次污染替代均使用登记的完整轮actual measurement labels，原有效部分/失败receipt保留；未把旧轮与替代轮拼接。完整结果文件哈希已在5b145bc发布前核对，本次从公开标量证据重建，不声称重新计算oracle或原始逐窗口质量。', '',
              'R10、30k、全冷总计及统一更新候选仍未完成，见[CLOSURE.md](CLOSURE.md)。', '']
    return '\n'.join(lines)


def closure(result):
    reasons=result['row_reason_counts']
    priority_gaps=[g for g in result['method_config_tile_gaps'] if g['priority'].startswith('P1')]
    gap_names='、'.join(f"{g['condition']} {g['method']} B{g['B']} {config_key(g['frozen_config'])}" for g in priority_gaps) or '无'
    return '\n'.join([
        '# 统计闭合后的剩余门槛', '',
        f'基点 `{BASE_COMMIT}`；834行/139配置组/12条件已做纯CPU六轮统计；全局comparison_admitted仍false。未运行新的GPU任务。', '',
        '## 当前实际实现身份', '',
        '统一search/update候选**不存在**。静态kNN使用P7派生O_MASK/O_BOUND，search commit `d65c6e41effad67dde8ae1f1f68e656562607817`、parent `7bce3679c3e32e77fa25cf7842805926509e1412`；O_MASK二进制`70520e34a97b155a0aeffa58d0b1c851684a6be4cd4fd71b170099da64cfae17`。树mask、seed cutoff、完整验证/topK及Graph/AoSoA均限于该静态入口。', '',
        '原生范围更新使用独立lean U10入口`f96746e38adabd9ff1dc511202bd5e4782c83101db31b2fe86e3af8c695c18ad`，保留原insert/delete/buffer occupancy-triggered整理重建及live-rank多重集。N1000/D128物理行重插入、串行立即可见性已测；不是稳定外部ID、任意新向量、并发或N1M动态。没有把静态AoSoA、树界refit或Graph刷新接入这个更新入口；更新后的静态副本/工作区/Graph刷新与发布时机未桥接。静态range的历史P4/P5入口仍为独立合同，不能与K10 topK输出互换。', '',
        '资源复用、Tloc阶段连续性、P4/P5范围候选组织及U10-prefix归因仍是独立证据；未自动合入一个keeper。有限overfetch REF64及旧direct-insert不晋升。不存在整合GTS++搜索—更新端到端倍率，历史静态与更新倍率不相乘。', '',
        '| 优先级 | 缺口/实际状态 | 影响的主张 | 下一步及证据来源 |',
        '|---|---|---|---|',
        '| P0 已完成 | K10每行资格、每组六轮、全部子比较和三类表 | 累计静态改善、树额外净收益、合格外部竞争 | 一键重建本报告；使用已有834行，不重跑GPU |',
        f"| P1 | {reasons.get('observer_unregistered',0)}行method/config/tile未覆盖；{reasons.get('observer_hash_mismatch',0)}行继承hash失败；{reasons.get('observer_upper_unproven',0)}行继承成本上界未过 | 外部frontier或必要O_FULL对照计时 | 先依据具体受阻比较登记最小缺失控制；已结束失败不自动重跑，新身份不回填旧834行 |",
        '| P1 | 外部成员失败与仅字段失败分别保留，ANN目标失败不删 | 同质量精确竞争；native速度仍是竞争信号 | 复用当前oracle/audit及既有Flat定位；不放宽容差、不以有限候选精算恢复旧native、不开混合精度项目 |',
        '| P1 | O_BOUND/O_MASK的逐条件净收益与负例已列；不是全形状树优势 | 树前置的实际贡献和 keeper 选择 | 不根据正式结果补选dispatch；维持冻结候选/控制，负例保留 |',
        '| P1 | 四份直接工作计数已采集，核名/launch/查询/单位与校准未闭合 | 工作减少、每坐标bytes；纯coalescing尚未证明 | 下一提交先分析既有query-pass NCU和直接计数；范围不匹配则不除，不默认新NCU |',
        '| P2 | 搜索—更新统一候选不存在，静态副本/界/工作区/Graph刷新未桥接 | 整合系统真实存在、总维护/查询收益 | 先CANDIDATE_MANIFEST；按已有阶段预算选择一个兼容组件，再做更新前query→insert→立即query→delete→query→一次rebuild→重查小桥接；确需新源码/小GPU测量 |',
        '| P2 | U10是独立原生有界基线，prefix约139.6ms/18.6s instrumented trace，尚未缓存 | 更新等待与维护收益 | 重复次数不代替预算；组件桥接确有净收益后复用登记U10轨迹，维护/layout/Graph/final drain全计时，rebuild不重复相加 |',
        '| P2 原计划未完成 | R10范围10k、单进程三次10k持续性 | 长范围完整交付、连续状态稳定 | 不能从本次静态kNN six fresh rounds推得；候选身份后按具体论文主张恢复登记测量 |',
        '| P2 原计划未完成 | 全冷总计、逐窗口质量派生、allocation/copy/CPU有用工作剩余归因 | 完整工作流端到端、CPU等待/PCIe/coalescing因果 | 先复用保存的raw输出、profile与冷阶段；缺失context/layout/Graph/warm证据才登记最小新测量，不加重叠区间 |',
        '', '## method/config/tile缺口排序', '',
        f'完整明细见K10_COMPARISON_STATUS.json的method_config_tile_gaps，或合格结果报告C表。六轮完整质量已通过、未被开发目标诊断边界阻挡且缺少tile成本控制的必要外部点为：{gap_names}。这不准许事后改写旧834行资格；只有论文确需该bulk对照时才登记新的补充控制/计时身份。其他native质量或目标失败不能只补计时控制后恢复完整质量比较。', '',
        'O_FULL/B1未覆盖只阻挡额外full-scan消融，不阻挡已合格的GTS_ORIG/O_BOUND/O_MASK主比较。CAGRA已失败的hash控制和Flat已失败的成本控制不自动重跑；其余ANN参数未覆盖与数值/目标失败分别保留。native全部实测速率是竞争信号，未准入时仍不提供正式倍率。',
        '', '这些优先级是采集后的工作排序，不是改写原统计合同或追加事前登记。首次统计提交不包含新kernel、精度修复、R10/30k或新10K任务。', ''])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args(); result=analyze(args.root)
    (args.root/'K10_COMPARISON_STATUS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (args.root/'K10_QUALIFIED_RESULTS.md').write_text(report(result))
    (args.root/'CLOSURE.md').write_text(closure(result))
    eligible=sum(p['comparable'] for c in result['conditions'] for p in c['comparisons'])
    print(f"CPU ANALYSIS: 834 rows, {result['groups']} groups, {len(result['conditions'])} conditions, {eligible} qualified pairs; global comparison_admitted=false")


if __name__=='__main__':
    main()
