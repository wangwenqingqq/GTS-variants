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
POLICY_VERSION='execution-recovery-v2'
ROLE={'GTS_ORIG':'original_static','O_MASK':'tree_candidate','O_BOUND':'scan_control',
      'O_FULL':'full_scan_control','FAISS_FLAT':'native_diagnostic','IVF_ALL':'native_complete_control',
      'IVF_APPROX':'native_ann','CAGRA':'native_ann'}

def target_eligible(quality,target):
    return bool(quality['output_contract_pass'] and quality['recall_tie_aware'] is not None and quality['recall_tie_aware']>=target
                and (target<1 or quality['complete_gate_pass']))

def admission(row,observer_qualified=False):
    q=row['quality'];s=row.get('stability',{});stable=bool(s.get('memory_growth_gate_pass',False))
    anchors=row.get('anchors',[]);unreachable=row.get('development_unreachable',[])
    targets={str(t):('diagnostic_only' if t in unreachable else 'admitted' if target_eligible(q,t) else 'missed_target') for t in anchors}
    strict=bool(q['complete_gate_pass']);candidate=row['method']=='O_MASK'
    return {'policy':POLICY_VERSION,'role':ROLE[row['method']],
            'strict_quality_admitted':strict,'target_admission':targets,
            'stability_admitted':stable,'observer_qualified':observer_qualified,
            'candidate_promotion_blocked':candidate and not(strict and stable),
            'candidate_stable':candidate and strict and stable and observer_qualified and row.get('actual_Q',0)>=10000,
            'diagnostic_only':not strict and not any(v=='admitted' for v in targets.values())}

def observer_decision(row):
    """Representative controls qualify only the registered method/config/tile.

    Keep failed cases local. A collected rejected timer is diagnostic evidence;
    it is never promoted by the presence of some other admitted timer.
    """
    complete=ROOT/'HOOK_CONTROL_COMPLETE.json'
    if not complete.exists():return {'qualified':False,'reason':'controls pending'}
    control=json.loads(complete.read_text())
    assert control['state']=='collection_complete'
    assert sha(ROOT/'HOOK_CONTROL.json')==control['rows_sha256']
    assert sha(ROOT/'HOOK_CONTROL_REGISTERED.json')==control['registration_sha256']
    config=row.get('config',{})
    registered={'IVF_ALL':{'nlist':1024,'nprobe':1024},'CAGRA':{'itopk_size':1024,'search_width':4}}.get(row['method'],{})
    cases=[s for s in control['summary'] if s['method']==row['method'] and s['B']==row['B']]
    if config!=registered or not cases:
        return {'qualified':False,'reason':'method/config/tile not qualified','control_sha256':sha(complete)}
    exact=[s for s in cases if s['dataset']==row['dataset']]
    # Registration explicitly uses faster Deep paths as representative controls.
    scopes=exact or [s for s in cases if s['dataset']=='Deep'] or cases
    required=['native_knn.py','query_trace.py']
    if row['method'] in ('GTS_ORIG','O_BOUND','O_MASK','O_FULL'):
        binary='gts_bench_p7' if row['method']=='GTS_ORIG' else 'opt_knn_bench'
        required=[binary,binary+'.cu','query_trace.hpp']
        if row['method']!='GTS_ORIG':required+=['knn_cutoff.cuh','knn_select.cuh','knn_verify.cuh']
    sources_match=True
    for case in scopes:
        identity=ROOT/'runs'/f'hook_c{case["case"]}_r1_on'/'identity.json'
        files=json.loads(identity.read_text())['files'] if identity.exists() else {}
        files={str(Path(p).resolve()):h for p,h in files.items()}
        sources_match &= all((ROOT/n).is_file() and files.get(str((ROOT/n).resolve()))==sha(ROOT/n) for n in required)
    return {'qualified':sources_match and all(s['timer_admitted'] for s in scopes),
            'reason':'registered representative control; retain every failure',
            'measured_entry_and_observer_sources_match':sources_match,
            'cases':[s['case'] for s in scopes],'control_sha256':sha(complete),
            'scope':'representative observer qualification; not a new timing or quality receipt'}

def matrix_decision(rows,required_labels):
    missing=sorted(set(required_labels)-{r['label'] for r in rows})
    missing_methods=sorted(set(COMPLETE+('CAGRA',))-{r['method'] for r in rows})
    collected=not missing and not missing_methods and len(rows)==len(required_labels) and all(r['receipt']['runtime_valid'] for r in rows)
    candidates=[r for r in rows if r['method']=='O_MASK']
    stable=bool(collected and candidates and all(r['admission']['candidate_stable'] for r in candidates))
    failed_targets=[r['label'] for r in rows if 'missed_target' in r['admission']['target_admission'].values()]
    unqualified_timers=[r['label'] for r in rows if not r['admission']['observer_qualified']]
    declines={}
    for r in candidates:
        key=(r.get('protocol'),r.get('dataset'),r.get('K'),r.get('B'))
        declines[key]=declines.get(key,0)+bool(r.get('stability',{}).get('throughput_decline_over_10pct',False))
    diagnosis=[str(k) for k,n in declines.items() if n>=2]
    stable=stable and not diagnosis
    external=any(r['method'] in ('FAISS_FLAT','IVF_ALL','IVF_APPROX','CAGRA') and
                 (r['admission']['strict_quality_admitted'] or 'admitted' in r['admission']['target_admission'].values()) for r in rows)
    return {'policy':POLICY_VERSION,'collection_complete':collected,'missing_required_rows':missing,'missing_required_methods':missing_methods,
            'candidate_stable':stable,'comparison_admitted':stable and external and not failed_targets and not unqualified_timers,
            'unqualified_timer_rows':unqualified_timers,
            'throughput_diagnosis_required':diagnosis,
            'missed_target_rows':failed_targets,
            'strict_rejected_rows':[r['label'] for r in rows if not r['admission']['strict_quality_admitted']]}

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
_HASH_CACHE={}
def identity_sha(path):
    path=Path(path).resolve();s=path.stat()
    # Small sources may be overwritten inside one filesystem timestamp tick.
    # Always rehash them; reserve the metadata cache for large immutable inputs.
    if s.st_size<=8<<20:return sha(path)
    key=(str(path),s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    if key not in _HASH_CACHE:_HASH_CACHE[key]=sha(path)
    return _HASH_CACHE[key]

def run_identity(a,cmd,env=None,identity_files=()):
    output_flags={'--out','--output','--export','-o','--log-file'}
    files=[Path(str(x)) for i,x in enumerate(cmd) if not(i and str(cmd[i-1]) in output_flags)
           and not str(x).endswith('counts.txt') and Path(str(x)).is_file()]
    files+=list(identity_files)
    files += [p for p in ROOT.iterdir() if p.is_file() and (p.suffix in ('.cu','.cuh','.hpp') or
              p.name in ('campaign10k.py','qualification.py','native_knn.py','run_locked.py','query_trace.py'))]
    files += list(ROOT.glob('*.index'))
    files += [p for p in BASE.glob('*.py') if p.name in ('native_ivf.py','verify_outputs.py')]
    for x in files[:]:
        if x.suffix=='.py':files += [p for p in x.parent.glob('query_trace.*') if p.is_file()]
    if 'environment' not in list(map(str,cmd)):
        for p in ROOT.glob('ENV_*.json'):
            files.append(p)
            files += [Path(x['path']) for x in json.loads(p.read_text()).get('library_sha256',[]) if 'path' in x]
    return {'policy':POLICY_VERSION,'command':list(map(str,cmd)),'gpu':a.gpu,
            'files':{str(p.resolve()):identity_sha(p) for p in files},
            'observer_mode':{'K10_EAGER':(env or {}).get('K10_EAGER',''),
                             'K10_STRESS':(env or {}).get('K10_STRESS',''),
                             'U10_OBSERVE':(env or {}).get('U10_OBSERVE',''),
                             'U10_TREE_AUDIT':(env or {}).get('U10_TREE_AUDIT','')},
            'environment':{k:os.environ.get(k,'') for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','CUDA_LAUNCH_BLOCKING')}}

def cached_admission_valid(saved,current):return saved==current

def audit_output(path,data,ref,k):
    try:return check_output(path,data,ref,k)
    except (AssertionError,ValueError,IndexError) as e:
        # Preserve malformed/duplicate candidate outputs as quality rejection,
        # without turning that failure into an independent-method exception.
        q={'complete_gate_pass':False,'output_contract_pass':False,
           'recall_tie_aware':None,'minimum_query_recall':None,'audit_error':str(e)}
        try:
            n,d,rk,ids,fields=native_ivf.read_gts(path)
            np=__import__('numpy');valid=(ids>=0)&(ids<len(data))
            q.update(invalid_IDs=int(((ids!=-1)&~valid).sum()),missing_neighbor_slots=int((ids==-1).sum()),
                     duplicate_IDs=sum(len(r[r>=0])-len(set(map(int,r[r>=0]))) for r in ids),
                     finite_pass=bool(np.isfinite(fields).all()))
        except Exception:q['output_parse']='failed; retained bytes'
        return q

def invoke(a,label,cmd,timeout=7200,env=None,identity_files=()):
    run=ROOT/'runs'/label
    identity=run_identity(a,cmd,env,identity_files)
    if run.exists():
        receipt=json.loads((run/'receipt.json').read_text())
        assert receipt['runtime_valid'],f'retained failed runtime {label}'
        assert (run/'identity.json').exists(),f'legacy receipt is qualification-only: {label}'
        assert cached_admission_valid(json.loads((run/'identity.json').read_text()),identity),f'changed measured identity: {label}'
        assert json.loads((run/'logical_command.json').read_text())==list(map(str,cmd)),f'changed command {label}'
        return receipt
    run.parent.mkdir(exist_ok=True)
    prereg=ROOT/'run_registration';prereg.mkdir(exist_ok=True);save(prereg/(label+'.json'),identity)
    command=[sys.executable,ROOT/'run_locked.py','--gpu',a.gpu,'--output',run,'--timeout-seconds',timeout,'--',*cmd]
    p=subprocess.run(list(map(str,command)),env={**os.environ,**(env or {})},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    if run.exists():
        save(run/'logical_command.json',list(map(str,cmd)));save(run/'identity.json',identity)
    assert p.returncode==0,f'{label}: runtime failure retained; {p.stdout[-2000:]}'
    assert identity==run_identity(a,cmd,env,identity_files),f'identity drift during execution: {label}'
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
    d,m,k,b=row['dataset'],row['method'],row['K'],row['B']
    qs=ROOT/f'fixtures/{d}_{pool}.qid';oracle_path=ROOT/f'oracle_{d}_{pool}.json'
    command=commands(a,d,m,k,b,qs,out,row['config'])
    if audit.exists():
        saved=json.loads(audit.read_text());assert saved['result_sha256']==sha(str(out)+'.bin')
        for key in ('dataset','method','K','B','config'):assert row[key]==saved[key]
        invoke(a,label,command,timeout=row.get('timeout_s',7200),identity_files=[oracle_path])
        assert saved['query_sha256']==sha(qs) and saved['oracle_sha256']==sha(oracle_path)
        saved['observer']=observer_decision(saved)
        saved['admission']=admission(saved,saved['observer']['qualified']);save(audit,saved)
        return saved
    ref=json.loads(oracle_path.read_text())
    assert native_ivf.read_qids(qs).tolist()==[r['qid'] for r in ref['records']]
    receipt=invoke(a,label,command,timeout=row.get('timeout_s',7200),identity_files=[oracle_path])
    if m=='GTS_ORIG':
        values=list(csv.DictReader(Path(str(out)+'.csv').read_text().splitlines()));assert len(values)==1
        meta={key:float(values[0][key]) for key in ('batch_p50_ms','batch_p95_ms')};meta['pass_ms']=float(values[0]['total_ms'])
        meta['setup']=json.loads(next(x[7:] for x in (ROOT/'runs'/label/'stdout.log').read_text().splitlines() if x.startswith('RESULT ')))
    else:meta=json.loads(Path(str(out)+'.json').read_text())
    source=native_ivf.load_data(datafile(a,d));quality=audit_output(str(out)+'.bin',source,ref,k)
    if 'Q' in meta:assert meta['Q']==ref['Q']
    row.update(meta,quality=quality,actual_Q=ref['Q'],result_sha256=sha(str(out)+'.bin'),query_sha256=sha(qs),oracle_sha256=sha(ROOT/f'oracle_{d}_{pool}.json'),
               receipt={key:receipt[key] for key in ('binary_sha256','wall_s','runtime_valid','exit_code','stop_reason')})
    windows=list(csv.DictReader(Path(str(out)+'.windows.csv').read_text().splitlines()))
    memory=[int(w['device_used_bytes']) for w in windows]
    assert max(memory)<=80*(1<<30),'memory admission exceeded'
    row['stability']={'sampled_memory_peak_bytes':max(memory),'retained_memory_growth_bytes':memory[-1]-memory[0],
                      'memory_growth_gate_pass':memory[-1]-memory[0]<=64*(1<<20),
                      'window_processed':[int(w['processed']) for w in windows],
                      'query_cpu':json.loads(Path(str(out)+'.cpu.json').read_text()),
                      'window_hook_overhead':'pending matched hook-off control',
                      'per_window_allocation_launch_copy_counts':'pending profiler attribution; no invented in-process count'}
    if ref['Q']>=10000 and b<=2048 and len(windows)>=4:
        first=next(w for w in windows if int(w['processed'])>=2000)
        last_start=next(w for w in windows if int(w['processed'])>=ref['Q']-2000)
        front=int(first['processed'])/float(first['wall_s'])
        back=(ref['Q']-int(last_start['processed']))/(float(windows[-1]['wall_s'])-float(last_start['wall_s']))
        row['stability'].update(first_2k_qps=front,last_2k_qps=back,throughput_decline_over_10pct=back<.9*front,
                                window_quality='whole output fully audited; query-scoped per-window statistics derived after collection')
    elif ref['Q']>=10000:
        row['stability']['first_last_2k']='not observable inside a large native call; windows are actual Host-ready call boundaries'
    row['observer']=observer_decision(row)
    row['admission']=admission(row,row['observer']['qualified'])
    save(audit,row)
    print(f'{label}: Q={ref["Q"]} pass_ms={row["pass_ms"]:.3f} recall={quality["recall_tie_aware"]} min={quality["minimum_query_recall"]} complete={quality["complete_gate_pass"]}',flush=True)
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
    save(ROOT/'DEVELOPMENT_COMPLETE.json',{'screen_processes':len(rows),'Q':1024,'state':'complete'})

def native_lane(a):
    inventory(a)
    for d in ([a.dataset] if a.dataset else ('GIST','Deep')):
        oracle(a,d,a.pool)
        for family in ([a.family] if a.family else ('IVF','CAGRA')):
            python=a.faiss_python if family=='IVF' else a.cuvs_python
            invoke(a,f'dev_{d}_{family}_{a.pool}',[python,ROOT/'campaign10k.py','native-development',
                   '--dataset',d,'--family',family,'--pool',a.pool,*common(a)],14400,
                   identity_files=[ROOT/f'oracle_{d}_{a.pool}.json'])
    if not a.dataset and not a.family and a.pool=='dev1024':
        save(ROOT/'NATIVE_MATCHED_COMPLETE.json',{'state':'collection_complete','datasets':['GIST','Deep'],'families':['IVF','CAGRA'],'passes_each':2})

def native_development(a):
    from native_knn import Backend
    source=native_ivf.load_data(datafile(a,a.dataset));qs=native_ivf.read_qids(ROOT/f'fixtures/{a.dataset}_{a.pool}.qid')
    ref=json.loads((ROOT/f'oracle_{a.dataset}_{a.pool}.json').read_text());rows=[]
    assert qs.tolist()==[r['qid'] for r in ref['records']]
    output=ROOT/'development';output.mkdir(exist_ok=True)
    for nl in ((1024,4096) if a.family=='IVF' else (0,)):
        backend=Backend(source,'IVF_APPROX' if a.family=='IVF' else 'CAGRA',nl)
        configs=[{'nlist':nl,'nprobe':p} for p in (16,64,128,256,512,1024,2048) if p<=min(nl,2048)] if a.family=='IVF' else [
            {'itopk_size':t,'search_width':w} for t in (64,128,256,512,1024) for w in (1,2,4)]
        for repeat in (1,2):
            batches=(1,32) if a.pool=='dev1024' else (32,128,512,2048,8192,10000)
            items=[(k,b,c) for k in (8,32) for b in batches for c in configs]
            if repeat==2:items=items[::-1]
            for k,b,c in items:
                suffix=f'n{nl}p{c["nprobe"]}' if a.family=='IVF' else f't{c["itopk_size"]}w{c["search_width"]}'
                label=f'dev_{a.pool}_{a.dataset}_{a.family}_{suffix}_k{k}_b{b}_r{repeat}'
                warm=__import__('numpy').array(list(map(int,(ROOT/f'fixtures/{a.dataset}_warm{b}.qid').read_text().split()))[1:],dtype='int32')
                row=backend.measure(qs,warm,k,b,c,output/label)
                row['quality']=audit_output(str(output/label)+'.bin',source,ref,k)
                row.update(dataset=a.dataset,method='IVF_APPROX' if a.family=='IVF' else 'CAGRA',repeat=repeat,K=k,B=b,config=c,label=label)
                window=list(csv.DictReader(Path(str(output/label)+'.windows.csv').read_text().splitlines()))
                mem=[int(w['device_used_bytes']) for w in window];assert max(mem)<=80*(1<<30)
                row['stability']={'memory_growth_gate_pass':mem[-1]-mem[0]<=64*(1<<20),'retained_memory_growth_bytes':mem[-1]-mem[0]}
                row['admission']=admission(row);rows.append(row)
                row['result_sha256']=sha(str(output/label)+'.bin')
                save(Path(str(output/label)+'.json'),row)
                save(ROOT/f'DEV_{a.dataset}_{a.family}_{a.pool}.json',rows)
                print(f'{label}: {row["pass_ms"]:.3f} ms recall={row["quality"]["recall_tie_aware"]}',flush=True)
        del backend

def selected(rows):
    groups={}
    for row in rows:groups.setdefault(json.dumps(row['config'],sort_keys=True),[]).append(row)
    eligible=[r for r in groups.values() if len(r)==2]
    assert eligible
    chosen={};unreachable=[]
    for target in TARGETS:
        legal=[r for r in eligible if all(target_eligible(x['quality'],target) and x['stability']['memory_growth_gate_pass'] for x in r)]
        if not legal:
            unreachable.append(target)
            legal=sorted(eligible,key=lambda r:(-min(x['quality']['recall_tie_aware'] if x['quality']['recall_tie_aware'] is not None else -1 for x in r),max(x['pass_ms'] for x in r),json.dumps(r[0]['config'],sort_keys=True)))[:1]
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
    # Finish controls before freezing, but preserve rejected timers as diagnostic
    # rows instead of retrying the same controls or blocking independent methods.
    assert json.loads((ROOT/'HOOK_CONTROL_COMPLETE.json').read_text())['state']=='collection_complete'
    for d in ('GIST','Deep'):
        for k in (8,32):
            for b in (1,32):
                items=[]
                for family in ('IVF','CAGRA'):
                    rows=json.loads((ROOT/f'DEV_{d}_{family}_dev1024.json').read_text())
                    items.extend(selected([r for r in rows if r['K']==k and r['B']==b]))
                choices[f'{d}_k{k}_b{b}']=items
    save(ROOT/'MATCHED_POLICY.json',choices)

def bulk_development(a):
    # Full native parameter grids are re-evaluated on actual10k chunk shapes.
    # Matched-only selections are not a global bulk optimization certificate.
    previous_pool=a.pool;a.pool='bulkdev10000';native_lane(a);a.pool=previous_pool
    rows=[]
    for d in ('GIST','Deep'):
        for family in ('IVF','CAGRA'):
            rows.extend(json.loads((ROOT/f'DEV_{d}_{family}_bulkdev10000.json').read_text()))
        for k in (8,32):
            for m in ('O_FULL','O_BOUND','O_MASK','FAISS_FLAT'):
                chunks=(32,) if m.startswith('O_') else (32,128,512,2048,8192,10000)
                for b in chunks:
                    for repeat in (1,2):
                        row={'label':f'bulkdev_{d}_k{k}_{m}_b{b}_r{repeat}','dataset':d,'method':m,'K':k,'B':b,'config':{},'repeat':repeat}
                        rows.append(collect(a,row,'bulkdev10000'));save(ROOT/'BULK_DEVELOPMENT.json',rows)
    policies={}
    for d in ('GIST','Deep'):
        for k in (8,32):
            items=[{'method':'GTS_ORIG','config':{},'B':32,'anchors':[]}]
            for m in COMPLETE[1:]+('IVF_APPROX','CAGRA'):
                rr=[r for r in rows if r['dataset']==d and r['K']==k and
                    (r['method']==m if m!='IVF_ALL' else r['method']=='IVF_APPROX' and r['config']=={'nlist':1024,'nprobe':1024})]
                groups={}
                for r in rr:groups.setdefault(json.dumps([r['B'],r['config']],sort_keys=True),[]).append(r)
                candidates=[g for g in groups.values() if len(g)==2]
                assert candidates,f'no collected bulk configurations: {d}/{k}/{m}'
                targets=TARGETS if m in ('IVF_APPROX','CAGRA') else (1.,)
                choices={}
                for target in targets:
                    legal=[g for g in candidates if all(target_eligible(x['quality'],target) and x['stability']['memory_growth_gate_pass'] for x in g)]
                    unreachable=not legal
                    if unreachable:
                        legal=sorted(candidates,key=lambda g:(-min(x['quality']['recall_tie_aware'] if x['quality']['recall_tie_aware'] is not None else -1 for x in g),sum(x['pass_ms'] for x in g)))[:1]
                    best=min(legal,key=lambda g:(sum(x['pass_ms'] for x in g),g[0]['B'],json.dumps(g[0]['config'],sort_keys=True)))
                    first=best[0];key=json.dumps([first['B'],first['config']],sort_keys=True)
                    actual=m
                    if m=='IVF_APPROX' and first['config']=={'nlist':1024,'nprobe':1024}:actual='IVF_ALL'
                    choices.setdefault(key,{'method':actual,'config':first['config'],'B':first['B'],'anchors':[],'development_unreachable':[]})
                    choices[key]['anchors'].append(target)
                    if unreachable:choices[key]['development_unreachable'].append(target)
                items.extend(choices.values())
            # Merge identical all-list entries rather than time duplicate labels.
            merged={}
            for item in items:
                key=json.dumps([item['method'],item['config'],item['B']],sort_keys=True)
                if key not in merged:merged[key]=item
                else:
                    for name in ('anchors','development_unreachable'):
                        merged[key][name]=sorted(set(merged[key].get(name,[])+item.get(name,[])))
            policies[f'{d}_k{k}']=list(merged.values())
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
            'final_seeds':{'GIST':2026100421,'Deep':2026100422},'memory_limit_bytes':80*(1<<30),'Q':10000,'warmup_batches_each_actual_shape':8,'rounds':6,
            'tree_candidate':'O_MASK','scan_control':'O_BOUND','admission_policy':POLICY_VERSION,
            'observer_receipt_sha256':sha(ROOT/'HOOK_CONTROL_COMPLETE.json'),
            'observer_policy':'per method/config/tile; unqualified timers retained as diagnostic and block comparison admission',
            'timeout_policy':'max(7200s, 3x development-scaled query pass +300s); forecast includes 8 full/tail warm batches; no reduced queries/rounds'}
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
                items={m:{'method':m,'config':{'nlist':1024,'nprobe':1024} if m=='IVF_ALL' else {},'B':b,'anchors':[]} for m in COMPLETE} if b else {}
                if not b:
                    for i in native:
                        if i['method'] in COMPLETE:items.setdefault(i['method'],i.copy())
                assert set(items)==set(COMPLETE),'missing required native/control method'
                for i in native:
                    if i['method'] in COMPLETE and (b or i.get('B')==items[i['method']]['B']):items[i['method']].update(anchors=i.get('anchors',[]),development_unreachable=i.get('development_unreachable',[]))
                ann=[i for i in native if i['method'] not in COMPLETE or (not b and i.get('B')!=items[i['method']]['B'])]
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
        keeper={r['round']:r['position'] for r in group if r['method']=='O_MASK'}
        assert set(keeper)==set(range(1,7))
        comparisons={}
        for r in group:
            if r['method']=='O_MASK':continue
            key=json.dumps([r['method'],r['config'],r['B']],sort_keys=True)
            comparisons.setdefault(key,[]).append(r['position']<keeper[r['round']])
        for key,directions in comparisons.items():assert len(directions)==6 and sum(directions)==3,(key,directions)
    # Budget forecast uses only development timings, before any final execution.
    # It is not a measured 10k result and does not replace the full six rounds.
    refs=json.loads((ROOT/'SCREEN.json').read_text())+json.loads((ROOT/'BULK_DEVELOPMENT.json').read_text())
    for p in ROOT.glob('DEV_*.json'):refs+=json.loads(p.read_text())
    for row in schedule:
        candidates=[r for r in refs if r['dataset']==row['dataset'] and r['K']==row['K'] and r['B']==row['B']
                    and r['config']==row['config'] and (r['method']==row['method'] or
                    row['method']=='IVF_ALL' and r['method']=='IVF_APPROX')]
        assert candidates,f'no development timeout reference: {row["label"]}'
        query_ms=max(r['pass_ms']*10000/r.get('actual_Q',r.get('Q',1024)) for r in candidates)
        warm_queries=8*row['B']+(8*(10000%row['B']) if 10000%row['B'] else 0)
        forecast_s=query_ms/1000*(1+warm_queries/10000)
        row.update(timeout_s=max(7200,int(3*forecast_s+300)),development_forecast_s=forecast_s)
    save(ROOT/'FORMAL_BUDGET.json',{'state':'forecast_before_formal_execution','processes':len(schedule),
         'query_and_warmup_gpu_hours':sum(r['development_forecast_s'] for r in schedule)/3600,
         'limitations':'held-out work may differ; excludes exact cold load/setup, CPU output writing/hash/audit, range and sustained; timeouts have 3x margin',
         'timeout_policy':frozen['timeout_policy'],'schedule':schedule})
    save(ROOT/'FORMAL_SCHEDULE.json',schedule)
    rows=[]
    for row in schedule:
        for record in frozen['input_identities'].values():
            s=Path(record['path']).stat()
            assert (s.st_size,s.st_mtime_ns)==(record['bytes'],record['mtime_ns']),f'input identity drift: {record["path"]}'
        value=collect(a,row,'final10000');rows.append(value);save(ROOT/'FORMAL.json',rows)
        save(ROOT/'PROGRESS.json',{'state':'running','phase':'formal','completed':len(rows),'planned':len(schedule),'last':row['label']})
    decision=matrix_decision(rows,[r['label'] for r in schedule])
    save(ROOT/'K10_MATRIX_COMPLETE.json',{'state':'collection_complete','processes':len(rows),'Q_per_process':10000,
         'scope':'matched and bulk only; sustained/range/native updates remain independent',**decision})

def common(a):return ['--gpu',a.gpu,'--data-root',a.data_root,'--faiss-python',a.faiss_python,'--cuvs-python',a.cuvs_python,'--p7',a.p7]
def pipeline(a):
    for phase in ('development','native-lane','freeze-matched','bulk-development','final-queries','formal'):
        marker={'development':'DEVELOPMENT_COMPLETE.json','native-lane':'NATIVE_MATCHED_COMPLETE.json','freeze-matched':'MATCHED_POLICY.json','bulk-development':'BULK_POLICY.json','final-queries':'FINAL_ORACLE_COMPLETE.json','formal':'K10_MATRIX_COMPLETE.json'}[phase]
        if (ROOT/marker).exists():continue
        save(ROOT/'PROGRESS.json',{'state':'running','phase':phase})
        subprocess.run(list(map(str,[sys.executable,ROOT/'campaign10k.py',phase,*common(a)])),check=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('inventory','oracle','development','native-lane','native-development','freeze-matched','bulk-development','final-queries','formal','pipeline'))
    p.add_argument('--gpu',required=True);p.add_argument('--data-root',type=Path,required=True)
    p.add_argument('--faiss-python',required=True);p.add_argument('--cuvs-python',required=True);p.add_argument('--p7',type=Path,required=True)
    p.add_argument('--dataset');p.add_argument('--family');p.add_argument('--pool',choices=('dev1024','bulkdev10000'),default='dev1024');a=p.parse_args()
    try:
        if a.phase=='oracle':oracle(a,a.dataset,a.pool)
        else:globals()[a.phase.replace('-','_')](a)
    except Exception as e:
        status={'state':'stopped','phase':a.phase,'error':str(e),'time_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
        save(ROOT/'STOPPED.json',status);save(ROOT/'PROGRESS.json',status);raise

if __name__=='__main__':main()
