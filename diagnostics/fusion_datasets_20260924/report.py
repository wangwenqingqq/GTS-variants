#!/usr/bin/env python3
import argparse,csv,json,statistics as st
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def build(e,out):
    table=[]
    for d,v in e['data'].items():
        c,ee=[st.median(x['mean_us'] for x in v['primary'][m]) for m in 'CE'];p=v['paired']
        table.append({'dataset':d,'dimension':v['dimension'],'metric':v['metric'],'n':2000,
                      'normal_radius':v['normal_radius'],'median_hits':v['hit_median'],
                      'C_us':c,'E_us':ee,'median_ratio':c/ee,'paired_geomean':p['paired_geomean'],
                      'lower95':p['bootstrap_95'][0],'upper95':p['bootstrap_95'][1],'wins':p['wins'],
                      'sustained_CE':v['sustained'][0]['C_over_E'],'sustained_EC':v['sustained'][1]['C_over_E'],
                      'count_kernel_C_us':v['nsys']['C']['selected_kernel_us']['getQresultCount('],
                      'selector_kernel_E_us':v['nsys']['E']['selected_kernel_us']['fusedResultSelect(']})
    with (out/'RESULTS.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]),lineterminator='\n');w.writeheader();w.writerows(table)
    fig,axes=plt.subplots(1,2,figsize=(10.7,4.1),layout='constrained')
    xs=list(range(len(table)));names=[f"{r['dataset']}\n"+('edit' if r['dataset']=='Words' else f"{r['dimension']}D L2") for r in table]
    for m,label in [('C','Unfused + Graph'),('E','Result fusion + Graph')]:
        axes[0].plot(xs,[r[m+'_us'] for r in table],marker='o',linewidth=2,label=label)
    axes[0].set_yscale('log');axes[0].set_ylabel('Completed hot query (us)');axes[0].legend(fontsize=8)
    y=[r['paired_geomean'] for r in table]
    axes[1].errorbar(xs,y,yerr=[[r['paired_geomean']-r['lower95'] for r in table],[r['upper95']-r['paired_geomean'] for r in table]],
                     marker='o',capsize=4,linewidth=2,label='Paired C/E; 95% interval')
    axes[1].axhline(1,color='black',linewidth=.8)
    axes[1].set_ylabel('Result-fusion speedup C/E');axes[1].legend(fontsize=8)
    for ax in axes:ax.set_xticks(xs,names);ax.set_xlabel('Dataset (all N=2000)');ax.grid(True,alpha=.25)
    fig.suptitle('Result fusion across pinned datasets, batch one; Graph in both arms',fontsize=11)
    for ext in ['png','svg','pdf']:fig.savefig(out/f'datasets.{ext}',dpi=220)
    plt.close(fig)
    a=e['data']['Words']['legacy_anchor'];cm,em=[st.median(x['mean_us'] for x in a['primary'][m]) for m in 'CE']
    peak=max(table,key=lambda x:x['median_ratio']);low=min(table,key=lambda x:x['median_ratio'])
    lines=['# 结果融合在不同数据集上的效果','',
           f"四组固定 N=2000 的同卡配对实验已完成。加速比从 {low['dataset']} 的 **{low['median_ratio']:.3f}×** 到 {peak['dataset']} 的 **{peak['median_ratio']:.3f}×**。",
           '比较 C（原结果整理＋CUDA Graph）与 E（结果融合＋CUDA Graph）。其他遍历、布局、容量和完整输出传输相同。', '',
           '![四组实验曲线](datasets.png)', '',
           '| 数据集 | 维度/度量 | 正常半径 | 命中中位数 | C μs | E μs | 中位数加速比 | 配对加速比 [95% 区间] | 胜出 |',
           '|---|---|---:|---:|---:|---:|---:|---|---:|']
    for r in table:
        metric=f"{r['dimension']}D L2" if r['dataset']!='Words' else '字节编辑距离'
        lines.append(f"| {r['dataset']} | {metric} | {r['normal_radius']:.6g} | {r['median_hits']:g} | {r['C_us']:.3f} | {r['E_us']:.3f} | {r['median_ratio']:.3f}× | {r['paired_geomean']:.4f} [{r['lower95']:.4f}, {r['upper95']:.4f}] | {r['wins']}/6 |")
    lines += ['', '每个数据集做六轮独立进程配对，CE/EC 交替；数据集顺序也交替反转。'
              '表中延迟为进程平均查询延迟的中位数；区间来自六轮配对 log 比值的全部 6^6 重采样。'
              '不同数据集半径按原 CPU oracle 固定，不能将绝对耗时当成相同难度的横向比较。', '',
              f"Words 绝对节省 {table[0]['C_us']-table[0]['E_us']:.1f} μs，GIST 也节省 {table[1]['C_us']-table[1]['E_us']:.1f} μs；"
              'GIST 的整次查询约 7.6 ms，因此同量级的节省只占约 0.7%。'
              '此前新布局实验用的就是 GIST/Deep/Tloc 的已融合 E 路径，测到的是布局的额外变化。'
              '本轮同卡 C/E 对照显示，换成这些数据集后，结果融合本身的完整查询收益已经不同于 Words 的 1.8×。', '',
              '## 旧 Words 1.8× 同会话对照', '',
              f"保存的旧二进制在同一 GPU、同一 Words fixture 重测为 {cm:.3f} → {em:.3f} μs，{cm/em:.3f}×；"
              f"配对 {a['paired']['paired_geomean']:.3f} [{a['paired']['bootstrap_95'][0]:.3f}, {a['paired']['bootstrap_95'][1]:.3f}]，"
              f"{a['paired']['wins']}/6 胜出。上表统一新二进制的 Words 点与旧程序分开。", '',
              '## 结果段归因', '',
              '旧计数核 `getQresultCount` 在 batch=1 下只由一个线程对候选结果做归约；融合核用一个 512 线程 CTA 合并计数、压紧与写出。'
              '当遍历与叶子距离计算占据更多总时间时，减少结果整理的开销对完整查询的相对收益会缩小。'
              'Profiler 只用于判断这个方向，不能将单核时间直接从主计时的 64 查询均值相减。', '',
              '| 数据集 | C kernels/query | E kernels/query | C 计数核 μs（诊断） | E 融合核 μs（诊断） |',
              '|---|---:|---:|---:|---:|']
    for r in table:
        v=e['data'][r['dataset']]['nsys']
        lines.append(f"| {r['dataset']} | {v['C']['kernels_per_query']} | {v['E']['kernels_per_query']} | {r['count_kernel_C_us']:.3f} | {r['selector_kernel_E_us']:.3f} |")
    lines += ['', '每组 NSYS 为 8 个固定查询、8 次预热和一次首次查询（共 17 个执行）。'
              'trace 核验 C/E 公共遍历/叶子路径及保留的删除前缀扫描一致；其插桩时间不作为端到端加速比。', '',
              '## 双顺序长测', '',
              '| 数据集 | CE 顺序 C/E | EC 顺序 C/E |', '|---|---:|---:|']
    for r in table:lines.append(f"| {r['dataset']} | {r['sustained_CE']:.3f}× | {r['sustained_EC']:.3f}× |")
    lines += ['', '## 验证与口径', '',
              '- 162 次运行核验预登记的输入、作者源码、生成代码、二进制、阶段顺序及 GPU 监控记录。',
              '- 46 次完整输出：A 与 C/E 的成员、距离、数量和 float32 稳定顺序；覆盖正常、零、全命中与负半径。其中 Words 包含旧二进制的两个完整输出锚点。',
              '- 24 次 sanitizer、8 组连续查询压力、60 组主计时（含 12 个旧程序锚点）、16 组双顺序长测及 8 组 NSYS。所有后续查询核验完整有序输出哈希。',
              '- 主计时预热 64 次；Words/Tloc 每进程 4096 查询，GIST/Deep 512 查询。长测均翻倍。',
              '- 计时包含查询输入、GPU 工作、2,220 槽完整结果回传以及 CPU 等待完成；建树、初始化、Graph 捕获、预热和结果哈希另计。',
              '- RTX PRO 6000、CUDA 13.1.115、sm_120；CPU 共享未绑核，GPU 时钟未锁定。采样监控未发现外部 GPU 进程。',
              '- 结论限定于这些固定 2,000 条数据、各自正常半径和 batch=1；没有百万规模、动态更新或冷启动结果。', '',
              '[数值表](RESULTS.csv) · [机器可读审计证据](EVIDENCE.json) · [实验约定](CONTRACT.md)', '']
    (out/'RESULTS.md').write_text('\n'.join(lines))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('evidence',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(json.loads(a.evidence.read_text()),a.output)
