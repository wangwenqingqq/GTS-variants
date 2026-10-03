#!/usr/bin/env python3
"""Frozen P7 bridge, 10k preparation/selection and resumable single-GPU runs."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from qualification import BASE,native_ivf,check_output

ROOT=Path(__file__).resolve().parent
COMPLETE=('GTS_ORIG','O_FULL','IVF_ALL','O_BOUND','FAISS_FLAT','O_MASK')
ORDERS=[list(COMPLETE),['O_FULL','O_BOUND','GTS_ORIG','O_MASK','IVF_ALL','FAISS_FLAT'],
        ['O_BOUND','O_MASK','O_FULL','FAISS_FLAT','GTS_ORIG','IVF_ALL'],
        ['IVF_ALL','GTS_ORIG','FAISS_FLAT','O_FULL','O_MASK','O_BOUND'],
        ['FAISS_FLAT','IVF_ALL','O_MASK','GTS_ORIG','O_BOUND','O_FULL'],
        ['O_MASK','FAISS_FLAT','O_BOUND','IVF_ALL','O_FULL','GTS_ORIG']]
TARGETS=(.99,.999,1.)

def save(p,value):
    p=Path(p);temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(p)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for part in iter(lambda:f.read(8<<20),b''):h.update(part)
    return h.hexdigest()
def qfile(p,ids):
    assert not p.exists();p.write_text(str(len(ids))+'\n'+''.join(f'{x}\n' for x in ids))
def datafile(a,d):return a.data_root/f'{d}/1000000/fixtures/data.f32bin'
def invoke(a,label,cmd,timeout=7200,env=None):
    run=ROOT/'runs'/label
    if run.exists():
        receipt=json.loads((run/'receipt.json').read_text())
        assert receipt['runtime_valid'],f'retained failed runtime {label}'
        assert receipt['binary_sha256']==sha(cmd[0]),f'changed executable {label}'
        assert json.loads((run/'logical_command.json').read_text())==list(map(str,cmd)),f'changed command {label}'
        return receipt
    run.parent.mkdir(exist_ok=True)
    command=[sys.executable,ROOT/'run_locked.py','--gpu',a.gpu,'--output',run,'--timeout-seconds',timeout,'--',*cmd]
    p=subprocess.run(list(map(str,command)),env={**os.environ,**(env or {})},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    if run.exists():save(run/'logical_command.json',list(map(str,cmd)))
    assert p.returncode==0,f'{label}: runtime failure retained; {p.stdout[-2000:]}'
    return json.loads((run/'receipt.json').read_text())

def commands(a,d,m,k,b,qs,out,config=None):
    c=config or {};warm=ROOT/f'fixtures/{d}_warm{b}.qid'
    if not warm.exists():warm=ROOT/f'fixtures/{d}_dev1024.qid'
    if m.startswith('O_'):
        return [ROOT/'opt_knn_bench',datafile(a,d),qs,BASE/f'{d}.index',ROOT/'fixtures/seeds_1000000.i32',m,k,b,out,warm,0]
    if m=='GTS_ORIG':return [ROOT/'gts_bench_p7',datafile(a,d),qs,k,b,1,BASE/f'{d}.index',out,8,warm]
    cmd=[a.cuvs_python if m=='CAGRA' else a.faiss_python,ROOT/'native_knn.py','--data',datafile(a,d),'--method',m,
         '--qids',qs,'--warm',warm,'--k',k,'--b',b,'--out',out]
    if 'nlist' in c:cmd+=['--nlist',c['nlist'],'--nprobe',c['nprobe']]
    if 'itopk_size' in c:cmd+=['--itopk',c['itopk_size'],'--width',c['search_width']]
    return cmd

def collect(a,row,pool):
    label=row['label'];out=ROOT/'outputs'/label;out.parent.mkdir(exist_ok=True)
    audit=Path(str(out)+'.audit.json')
    if audit.exists():
        saved=json.loads(audit.read_text());assert saved['result_sha256']==sha(str(out)+'.bin')
        for key in ('dataset','method','K','B','config'):assert row[key]==saved[key]
        if row['method'] in COMPLETE:assert saved['quality']['complete_gate_pass'],f'retained complete-output rejection: {label}'
        return saved
    d,m,k,b=row['dataset'],row['method'],row['K'],row['B']
    qs=ROOT/f'fixtures/{d}_{pool}.qid';ref=json.loads((ROOT/f'oracle_{d}_{pool}.json').read_text())
    assert native_ivf.read_qids(qs).tolist()==[r['qid'] for r in ref['records']]
    receipt=invoke(a,label,commands(a,d,m,k,b,qs,out,row['config']))
    if m=='GTS_ORIG':
        values=list(csv.DictReader(Path(str(out)+'.csv').open()));assert len(values)==1
        meta={key:float(values[0][key]) for key in ('batch_p50_ms','batch_p95_ms')};meta['pass_ms']=float(values[0]['total_ms'])
        meta['setup']=json.loads(next(x[7:] for x in (ROOT/'runs'/label/'stdout.log').read_text().splitlines() if x.startswith('RESULT ')))
    else:meta=json.loads(Path(str(out)+'.json').read_text())
    source=native_ivf.load_data(datafile(a,d));quality=check_output(str(out)+'.bin',source,ref,k)
    if 'Q' in meta:assert meta['Q']==ref['Q']
    row.update(meta,quality=quality,actual_Q=ref['Q'],result_sha256=sha(str(out)+'.bin'),query_sha256=sha(qs),oracle_sha256=sha(ROOT/f'oracle_{d}_{pool}.json'),
               receipt={key:receipt[key] for key in ('binary_sha256','wall_s','runtime_valid','exit_code','stop_reason')})
    windows=list(csv.DictReader(Path(str(out)+'.windows.csv').open()))
    memory=[int(w['device_used_bytes']) for w in windows]
    assert max(memory)<=80*(1<<30),'memory admission exceeded'
    row['stability']={'sampled_memory_peak_bytes':max(memory),'retained_memory_growth_bytes':memory[-1]-memory[0],
                      'memory_growth_gate_pass':memory[-1]-memory[0]<=64*(1<<20),
                      'window_processed':[int(w['processed']) for w in windows],
                      'query_cpu':json.loads(Path(str(out)+'.cpu.json').read_text()),
                      'window_hook_overhead':'pending matched hook-off control',
                      'per_window_allocation_launch_copy_counts':'pending profiler attribution; no invented in-process count'}
    save(audit,row)
    print(f'{label}: Q={ref["Q"]} pass_ms={row["pass_ms"]:.3f} recall={quality["recall_tie_aware"]:.12f} min={quality["minimum_query_recall"]} complete={quality["complete_gate_pass"]}',flush=True)
    if m in COMPLETE:assert quality['complete_gate_pass'],f'complete-output failure retained: {label}'
    return row

def inventory(a):
    fixture=ROOT/'fixtures';fixture.mkdir(exist_ok=True);result={}
    for d,seed,bulkseed in (('GIST',2026100411,2026100413),('Deep',2026100412,2026100414)):
        if (fixture/f'{d}_dev1024.qid').exists():
            assert (ROOT/'QUERY_DEVELOPMENT.json').exists();continue
        excluded=set();files=[]
        for root in (a.p7,BASE):
            for p in sorted(root.rglob('*.qid')):
                if d not in p.name:continue
                ids=native_ivf.read_qids(p);excluded.update(map(int,ids));files.append({'name':str(p.relative_to(root)),'source':root.name,'sha256':sha(p),'Q':len(ids)})
            for p in sorted(root.rglob(f'{d}_excluded.i32')):
                ids=__import__('numpy').fromfile(p,dtype='<i4');excluded.update(map(int,ids));files.append({'name':str(p.relative_to(root)),'source':root.name,'sha256':sha(p),'Q':len(ids)})
        assert len(excluded)>=512,(d,len(excluded))
        __import__('numpy').array(sorted(excluded),dtype='<i4').tofile(fixture/f'{d}_historical_excluded.i32')
        result[d]={'files':files,'historical_count':len(excluded),'historical_sha256':sha(fixture/f'{d}_historical_excluded.i32'),'development_seed':seed,'bulk_development_seed':bulkseed}
        for pool,count,s in (('dev1024',1024,seed),('bulkdev10000',10000,bulkseed)):
            rng=random.Random(s);ids=[]
            while len(ids)<count:
                q=rng.randrange(1_000_000)
                if q not in excluded:ids.append(q);excluded.add(q)
            qfile(fixture/f'{d}_{pool}.qid',ids);result[d][pool]={'Q':count,'sha256':sha(fixture/f'{d}_{pool}.qid')}
        dev=native_ivf.read_qids(fixture/f'{d}_dev1024.qid').tolist()
        bulk=native_ivf.read_qids(fixture/f'{d}_bulkdev10000.qid').tolist()
        for b in (1,16,32,128,512,2048,8192,10000):
            source=dev if b<=128 else bulk
            qfile(fixture/f'{d}_warm{b}.qid',(source*((8*b+len(source)-1)//len(source)))[:8*b])
    if result:save(ROOT/'QUERY_DEVELOPMENT.json',result)

def oracle(a,d,pool):
    out=ROOT/f'oracle_{d}_{pool}.json'
    if out.exists():
        ref=json.loads(out.read_text());assert [r['qid'] for r in ref['records']]==native_ivf.read_qids(ROOT/f'fixtures/{d}_{pool}.qid').tolist();return
    invoke(a,f'oracle_{d}_{pool}',[a.faiss_python,BASE/'native_ivf.py','oracle','--data',datafile(a,d),'--qids',ROOT/f'fixtures/{d}_{pool}.qid','--out',out],14400)

def development(a):
    inventory(a)
    # Native search/selection and all fields are already P7; every new input is
    # qualified independently. Source qualification receipts gate this phase.
    assert (ROOT/'F0_SMALL.json').exists()
    rows=[]
    for d in ('GIST','Deep'):
        oracle(a,d,'dev1024')
        for k,b in ((8,32),(32,32),(8,1),(32,1)):
            for m in COMPLETE:
                config={'nlist':1024,'nprobe':1024} if m=='IVF_ALL' else {}
                row={'label':f'screen_{d}_{m}_k{k}_b{b}','dataset':d,'method':m,'K':k,'B':b,'config':config}
                rows.append(collect(a,row,'dev1024'));save(ROOT/'SCREEN.json',rows)
        for family in ('IVF','CAGRA'):
            python=a.faiss_python if family=='IVF' else a.cuvs_python
            invoke(a,f'dev_{d}_{family}',[python,ROOT/'campaign10k.py','native-development','--dataset',d,'--family',family,*common(a)],14400)
    save(ROOT/'DEVELOPMENT_COMPLETE.json',{'screen_processes':len(rows),'Q':1024,'state':'complete'})

def native_development(a):
    from native_knn import Backend
    source=native_ivf.load_data(datafile(a,a.dataset));qs=native_ivf.read_qids(ROOT/f'fixtures/{a.dataset}_dev1024.qid')
    ref=json.loads((ROOT/f'oracle_{a.dataset}_dev1024.json').read_text());rows=[]
    output=ROOT/'development';output.mkdir(exist_ok=True)
    for nl in ((1024,4096) if a.family=='IVF' else (0,)):
        backend=Backend(source,'IVF_APPROX' if a.family=='IVF' else 'CAGRA',nl)
        configs=[{'nlist':nl,'nprobe':p} for p in (16,64,128,256,512,1024,2048) if p<=min(nl,2048)] if a.family=='IVF' else [
            {'itopk_size':t,'search_width':w} for t in (64,128,256,512,1024) for w in (1,2,4)]
        for repeat in (1,2):
            items=[(k,b,c) for k in (8,32) for b in (1,32) for c in configs]
            if repeat==2:items=items[::-1]
            for k,b,c in items:
                suffix=f'n{nl}p{c["nprobe"]}' if a.family=='IVF' else f't{c["itopk_size"]}w{c["search_width"]}'
                label=f'dev_{a.dataset}_{a.family}_{suffix}_k{k}_b{b}_r{repeat}'
                row=backend.measure(qs,qs,k,b,c,output/label,ref)
                assert row['quality']['output_contract_pass']
                row.update(dataset=a.dataset,method='IVF_APPROX' if a.family=='IVF' else 'CAGRA',repeat=repeat,K=k,B=b,config=c,label=label)
                rows.append(row);save(ROOT/f'DEV_{a.dataset}_{a.family}.json',rows)
                print(f'{label}: {row["pass_ms"]:.3f} ms recall={row["quality"]["recall_tie_aware"]:.12f}',flush=True)
        del backend

def selected(rows):
    groups={}
    for row in rows:groups.setdefault(json.dumps(row['config'],sort_keys=True),[]).append(row)
    eligible=[r for r in groups.values() if len(r)==2 and all(x['quality']['output_contract_pass'] for x in r)]
    assert eligible
    chosen={};unreachable=[]
    for target in TARGETS:
        legal=[r for r in eligible if all(x['quality']['recall_tie_aware']>=target and (target<1 or x['quality']['complete_gate_pass']) for x in r)]
        if not legal:
            unreachable.append(target)
            legal=sorted(eligible,key=lambda r:(-min(x['quality']['recall_tie_aware'] for x in r),max(x['pass_ms'] for x in r),json.dumps(r[0]['config'],sort_keys=True)))[:1]
        best=min(legal,key=lambda r:(sum(x['pass_ms'] for x in r),json.dumps(r[0]['config'],sort_keys=True)))
        key=json.dumps(best[0]['config'],sort_keys=True)
        method=best[0]['method']
        if method=='IVF_APPROX' and best[0]['config']=={'nlist':1024,'nprobe':1024}:method='IVF_ALL'
        chosen.setdefault(key,{'method':method,'config':best[0]['config'],'anchors':[],'development_unreachable':[]})
        chosen[key]['anchors'].append(target)
        if target in unreachable:chosen[key]['development_unreachable'].append(target)
    return list(chosen.values())

def freeze_matched(a):
    assert (ROOT/'DEVELOPMENT_COMPLETE.json').exists();choices={}
    if not (ROOT/'HOOK_CONTROL_COMPLETE.json').exists():
        subprocess.run(list(map(str,[a.faiss_python,ROOT/'hook_control.py',*common(a)])),check=True)
    for d in ('GIST','Deep'):
        for k in (8,32):
            for b in (1,32):
                items=[]
                for family in ('IVF','CAGRA'):
                    rows=json.loads((ROOT/f'DEV_{d}_{family}.json').read_text())
                    items.extend(selected([r for r in rows if r['K']==k and r['B']==b]))
                choices[f'{d}_k{k}_b{b}']=items
    save(ROOT/'MATCHED_POLICY.json',choices)

def bulk_development(a):
    matched=json.loads((ROOT/'MATCHED_POLICY.json').read_text());rows=[]
    for d in ('GIST','Deep'):
        oracle(a,d,'bulkdev10000')
        for k in (8,32):
            items=[{'method':m,'config':{'nlist':1024,'nprobe':1024} if m=='IVF_ALL' else {},'anchors':[]} for m in COMPLETE]
            for b in (1,32):items.extend(matched[f'{d}_k{k}_b{b}'])
            dedup={json.dumps([i['method'],i['config']],sort_keys=True):i for i in items}
            for i,item in enumerate(dedup.values()):
                m=item['method'];chunks=(32,) if m.startswith('O_') or m=='GTS_ORIG' else (32,128,512,2048,8192,10000)
                for b in chunks:
                    for repeat in (1,2):
                        if m=='GTS_ORIG':continue # Fixed B32 policy already qualified on1024; no redundant tuning sweep.
                        row={'label':f'bulkdev_{d}_k{k}_{i}_{m}_b{b}_r{repeat}','dataset':d,'method':m,'K':k,'B':b,'config':item['config'],'repeat':repeat}
                        rows.append(collect(a,row,'bulkdev10000'));save(ROOT/'BULK_DEVELOPMENT.json',rows)
    policies={}
    for d in ('GIST','Deep'):
        for k in (8,32):
            items=[{'method':'GTS_ORIG','config':{},'B':32,'anchors':[]}]
            for m in COMPLETE[1:]+('IVF_APPROX','CAGRA'):
                rr=[r for r in rows if r['dataset']==d and r['K']==k and r['method']==m]
                groups={}
                for r in rr:groups.setdefault(json.dumps([r['B'],r['config']],sort_keys=True),[]).append(r)
                candidates=[g for g in groups.values() if len(g)==2 and all(x['quality']['output_contract_pass'] for x in g)]
                targets=TARGETS if m in ('IVF_APPROX','CAGRA') else (1.,)
                choices={}
                for target in targets:
                    legal=[g for g in candidates if all(x['quality']['recall_tie_aware']>=target and (target<1 or x['quality']['complete_gate_pass']) for x in g)]
                    unreachable=not legal
                    if unreachable:
                        legal=sorted(candidates,key=lambda g:(-min(x['quality']['recall_tie_aware'] for x in g),sum(x['pass_ms'] for x in g)))[:1]
                    best=min(legal,key=lambda g:(sum(x['pass_ms'] for x in g),g[0]['B'],json.dumps(g[0]['config'],sort_keys=True)))
                    first=best[0];key=json.dumps([first['B'],first['config']],sort_keys=True)
                    choices.setdefault(key,{'method':m,'config':first['config'],'B':first['B'],'anchors':[],'development_unreachable':[]})
                    choices[key]['anchors'].append(target)
                    if unreachable:choices[key]['development_unreachable'].append(target)
                items.extend(choices.values())
            policies[f'{d}_k{k}']=items
    save(ROOT/'BULK_POLICY.json',policies)

def final_queries(a):
    assert (ROOT/'MATCHED_POLICY.json').exists() and (ROOT/'BULK_POLICY.json').exists()
    source=json.loads((ROOT/'SOURCE_BRIDGE.json').read_text())
    for n,h in source['derived_sources'].items():assert sha(ROOT/n)==h,n
    assert (ROOT/'INPUT_IDENTITIES.json').exists()
    inputs=json.loads((ROOT/'INPUT_IDENTITIES.json').read_text())
    for record in inputs.values():assert sha(record['path'])==record['sha256'],record['path']
    frozen={'source':source,'input_identities':inputs,'matched_policy_sha256':sha(ROOT/'MATCHED_POLICY.json'),'bulk_policy_sha256':sha(ROOT/'BULK_POLICY.json'),
            'binaries':{n:sha(ROOT/n) for n in ('opt_knn_bench','gts_bench_p7')},'query_generator_sha256':sha(ROOT/'campaign10k.py'),
            'final_seeds':{'GIST':2026100421,'Deep':2026100422},'memory_limit_bytes':80*(1<<30),'Q':10000,'warmup_batches_each_actual_shape':8,'rounds':6,'keeper':'O_BOUND'}
    freeze_path=ROOT/'FROZEN_10K.json'
    if freeze_path.exists():assert json.loads(freeze_path.read_text())==frozen,'freeze drift on resume'
    else:save(freeze_path,frozen)
    fixtures=ROOT/'fixtures';result={}
    for d,seed in frozen['final_seeds'].items():
        path=fixtures/f'{d}_final10000.qid'
        np=__import__('numpy');excluded=set(map(int,np.fromfile(fixtures/f'{d}_historical_excluded.i32',dtype='<i4')))
        for pool in ('dev1024','bulkdev10000'):excluded.update(map(int,native_ivf.read_qids(fixtures/f'{d}_{pool}.qid')))
        excluded_path=fixtures/f'{d}_all_excluded.i32';np.array(sorted(excluded),dtype='<i4').tofile(excluded_path)
        # Persist generator+inventory registration before exposing any final ID.
        registration={'seed':seed,'Q':10000,'excluded_count':len(excluded),'excluded_sha256':sha(excluded_path),'frozen_sha256':sha(ROOT/'FROZEN_10K.json')}
        prereg=ROOT/f'PREREGISTER_{d}.json'
        if prereg.exists():assert json.loads(prereg.read_text())==registration
        else:save(prereg,registration)
        rng=random.Random(seed);ids=[]
        while len(ids)<10000:
            q=rng.randrange(1000000)
            if q not in excluded:ids.append(q);excluded.add(q)
        if path.exists():assert native_ivf.read_qids(path).tolist()==ids
        else:qfile(path,ids)
        result[d]={'Q':10000,'seed':seed,'sha256':sha(path),'unique':len(set(ids))}
    save(ROOT/'QUERY_FINAL.json',result)
    for d in ('GIST','Deep'):oracle(a,d,'final10000')
    save(ROOT/'FINAL_ORACLE_COMPLETE.json',{'state':'complete','Q_each':10000,'datasets':['GIST','Deep']})

def formal(a):
    frozen=json.loads((ROOT/'FROZEN_10K.json').read_text())
    for name,h in frozen['source']['derived_sources'].items():assert sha(ROOT/name)==h,name
    for name,h in frozen['binaries'].items():assert sha(ROOT/name)==h,name
    assert sha(ROOT/'MATCHED_POLICY.json')==frozen['matched_policy_sha256']
    assert sha(ROOT/'BULK_POLICY.json')==frozen['bulk_policy_sha256']
    matched=json.loads((ROOT/'MATCHED_POLICY.json').read_text());bulk=json.loads((ROOT/'BULK_POLICY.json').read_text());schedule=[]
    # Each stage completes six paired rounds before moving to the next slice.
    for protocol,shapes in [('matched_b32_k8',[(d,8,32) for d in ('GIST','Deep')]),
                            ('matched_b32_k32',[(d,32,32) for d in ('GIST','Deep')]),
                            ('matched_b1',[(d,k,1) for d in ('GIST','Deep') for k in (8,32)]),
                            ('bulk',[(d,k,0) for d in ('GIST','Deep') for k in (8,32)])]:
        for repeat in range(1,7):
            realized=shapes[(repeat-1)%len(shapes):]+shapes[:(repeat-1)%len(shapes)]
            for d,k,b in realized:
                native=matched[f'{d}_k{k}_b{b}'] if b else bulk[f'{d}_k{k}']
                items={m:{'method':m,'config':{'nlist':1024,'nprobe':1024} if m=='IVF_ALL' else {},'B':b,'anchors':[]} for m in COMPLETE} if b else {i['method']:i for i in native if i['method'] in COMPLETE}
                for i in native:
                    if i['method'] in COMPLETE:items[i['method']].update(anchors=i.get('anchors',[]),development_unreachable=i.get('development_unreachable',[]))
                ann=[i for i in native if i['method'] not in COMPLETE]
                if repeat%2==0:ann=ann[::-1]
                complete_order=[items[m] for m in ORDERS[repeat-1]]
                order=ann+complete_order if repeat%2 else complete_order+ann
                for pos,i in enumerate(order):
                    schedule.append({'label':f'{protocol}_r{repeat}_{d}_k{k}_b{i.get("B",b)}_{pos}_{i["method"]}',
                                     'protocol':protocol,'round':repeat,'position':pos,'dataset':d,'K':k,'B':i.get('B',b),'method':i['method'],'config':i['config'],'anchors':i.get('anchors',[]),'development_unreachable':i.get('development_unreachable',[])})
    assert len({r['label'] for r in schedule})==len(schedule)
    grouped={}
    for row in schedule:grouped.setdefault((row['protocol'],row['dataset'],row['K']),[]).append(row)
    for group in grouped.values():
        keeper={r['round']:r['position'] for r in group if r['method']=='O_BOUND'}
        assert set(keeper)==set(range(1,7))
        comparisons={}
        for r in group:
            if r['method']=='O_BOUND':continue
            key=json.dumps([r['method'],r['config'],r['B']],sort_keys=True)
            comparisons.setdefault(key,[]).append(r['position']<keeper[r['round']])
        for key,directions in comparisons.items():assert len(directions)==6 and sum(directions)==3,(key,directions)
    save(ROOT/'FORMAL_SCHEDULE.json',schedule)
    rows=[]
    for row in schedule:
        for record in frozen['input_identities'].values():
            s=Path(record['path']).stat()
            assert (s.st_size,s.st_mtime_ns)==(record['bytes'],record['mtime_ns']),f'input identity drift: {record["path"]}'
        value=collect(a,row,'final10000');rows.append(value);save(ROOT/'FORMAL.json',rows)
        save(ROOT/'PROGRESS.json',{'state':'running','phase':'formal','completed':len(rows),'planned':len(schedule),'last':row['label']})
    save(ROOT/'K10_MATRIX_COMPLETE.json',{'state':'complete','processes':len(rows),'Q_per_process':10000,'scope':'matched and bulk only; sustained/range/native updates remain independent'})

def common(a):return ['--gpu',a.gpu,'--data-root',a.data_root,'--faiss-python',a.faiss_python,'--cuvs-python',a.cuvs_python,'--p7',a.p7]
def pipeline(a):
    for phase in ('development','freeze-matched','bulk-development','final-queries','formal'):
        marker={'development':'DEVELOPMENT_COMPLETE.json','freeze-matched':'MATCHED_POLICY.json','bulk-development':'BULK_POLICY.json','final-queries':'FINAL_ORACLE_COMPLETE.json','formal':'K10_MATRIX_COMPLETE.json'}[phase]
        if (ROOT/marker).exists():continue
        save(ROOT/'PROGRESS.json',{'state':'running','phase':phase})
        subprocess.run(list(map(str,[sys.executable,ROOT/'campaign10k.py',phase,*common(a)])),check=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('inventory','development','native-development','freeze-matched','bulk-development','final-queries','formal','pipeline'))
    p.add_argument('--gpu',required=True);p.add_argument('--data-root',type=Path,required=True)
    p.add_argument('--faiss-python',required=True);p.add_argument('--cuvs-python',required=True);p.add_argument('--p7',type=Path,required=True)
    p.add_argument('--dataset');p.add_argument('--family');a=p.parse_args()
    try:globals()[a.phase.replace('-','_')](a)
    except Exception as e:
        status={'state':'stopped','phase':a.phase,'error':str(e),'time_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
        save(ROOT/'STOPPED.json',status);save(ROOT/'PROGRESS.json',status);raise

if __name__=='__main__':main()
