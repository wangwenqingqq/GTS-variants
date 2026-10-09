#!/usr/bin/env python3
"""Bind source, full layer states, complete answers and fixed-order workflow evidence."""
import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import numpy as np
import run

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('tiles_campaign',HERE/'campaign.py')
campaign=importlib.util.module_from_spec(spec);spec.loader.exec_module(campaign)
CONTRACT=campaign.CONTRACT
sha=run.sha
validate=run.parent.validate
sys.path.insert(0,str(HERE.parent/'unified_target_workflow/phase_b'))
import oracle
spec=importlib.util.spec_from_file_location('old_campaign',HERE.parent/'unified_target_workflow/phase_b/campaign.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
spec=importlib.util.spec_from_file_location('old_profile',HERE.parent/'rebuild_tree_baselines/verify_profile.py')
profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)


def read(p):return json.loads(p.read_text())
def rows(p):
    with p.open() as f:return list(csv.DictReader(f))
def save(p,x):
    assert not p.exists(),'do not replace a completed proof'
    p.write_text(json.dumps(x,indent=2)+'\n')
def hashes(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def function(text,name):
    start=text.index('__global__ void '+name+'(');begin=text.index('{',start);end=begin+1;depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]


def source_identity(build,sass,parent_build):
    prepared=read(build/'PREPARED.json');manifest=read(build/'BUILD.json')
    assert sha(build/'bin/target')==manifest['binary_sha256']
    assert hashes(build/'source')==prepared['sources']
    assert all(sha(HERE/name)==digest for name,digest in prepared['tiles_files'].items())
    pinned=read(HERE.parent/'unified_target_workflow/phase_b/evidence/SOURCE_IDENTITY.json')['executed_sources']
    # The generated parent is independently bound to the qualified original source.
    assert hashes(build/'parent/source')==prepared['parent_sources']
    base=parent_build/'source';assert hashes(base)==pinned
    src=build/'source';changed={'include/tree.cuh','include/numeric.cuh','src/main.cu','include/build_tiles.hpp'}
    assert all(sha(src/name)==digest for name,digest in pinned.items() if name not in changed)
    tree=(src/'include/tree.cuh').read_text();original=(base/'include/tree.cuh').read_text()
    kernels=re.findall(r'__global__ void (\w+)\(',original)
    assert all(function(tree,k)==function(original,k) for k in kernels)
    native=function(original,'getPivotDis');tiled=function(tree,'getPivotDisTiled')
    reversed_tile=tiled.replace('getPivotDisTiled(', 'getPivotDis(',1)
    reversed_tile=reversed_tile.replace(', int tiles_per_node)\n',')\n',1)
    reversed_tile=reversed_tile.replace('int bid = int(blockIdx.x) / tiles_per_node;\n\tint tile = int(blockIdx.x) % tiles_per_node;','int bid = blockIdx.x;',1)
    reversed_tile=reversed_tile.replace('if (tile == 0) pid_list[nid] = pid[0];','pid_list[nid] = pid[0];',1)
    reversed_tile=reversed_tile.replace('for (int i = tid + lid + tile * THREAD_NUM; (i >= lid && i <= rid && i < lid + (tile + 1) * THREAD_NUM); i += THREAD_NUM)',
        'for (int i = tid + lid; (i >= lid && i <= rid); i += THREAD_NUM)')
    assert reversed_tile==native,'non-mapping change in scoring arithmetic'
    numeric=(src/'include/numeric.cuh').read_text().replace('namespace bt {void refit(const double*,const double*,const int*,int);}\n','',1)
    numeric=numeric.replace('bounds_refresh_ms.push_back(u10_ms(start));bt::refit(bounds.lo,bounds.hi,empty,nn);','bounds_refresh_ms.push_back(u10_ms(start));',1)
    assert numeric==(base/'include/numeric.cuh').read_text()
    assert tree.count('cudaDeviceSynchronize')==original.count('cudaDeviceSynchronize')
    assert tree.count('thrust::sort_by_key')==original.count('thrust::sort_by_key')
    normalized=profile.normalize_dump(sass.read_text());functions={}
    for line in normalized.splitlines():
        if line.startswith('Function:'):key=line[10:];functions[key]=[]
        elif line.endswith(';'):functions[key].append(line)
    own={k:v for k,v in functions.items() if 'getPivotDis' in k}
    assert len(own)==2 and len(functions)==113
    resource={}
    log=(build/'BUILD.log').read_text()
    for k in own:
        pattern=r'Function properties for '+re.escape(k)+r'\n([^\n]+)\n([^\n]+)'
        match=re.search(pattern,log);assert match
        resource[k]=dict(instructions=len(own[k]),compiler=match.group(1).strip()+'; '+match.group(2).strip())
    return dict(passed=True,binary_sha256=manifest['binary_sha256'],prepared_sha256=sha(build/'PREPARED.json'),
        source_hashes=prepared['sources'],original_tree_kernels_verbatim=True,scoring_arithmetic_reversible_mapping_only=True,
        unchanged_query_and_policy_headers=True,sort_and_explicit_fence_count_unchanged=True,
        normalized_SASS_sha256=__import__('hashlib').sha256(normalized.encode()).hexdigest(),GPU_functions=len(functions),
        instructions=sum(map(len,functions.values())),scoring_resources=resource,
        resource_scope='static compilation only; large inherited metric stack retained; no occupancy/traffic claim')


def completed(a):
    record=read(a.work/'REGISTERED.json');raw=read(a.work/'RAW_ROWS.json')
    driver=a.executed_driver or HERE/'campaign.py'
    assert record['contract_sha256']==sha(HERE/'CONTRACT.json') and record['executed_driver_sha256']==sha(driver)
    assert record['jobs']==campaign.jobs(record['stage']) and len(raw)==len(record['jobs'])
    assert sha(a.build/'bin/target')==record['binary_sha256']
    assert sha(a.build/'BUILD.json')==record['build_sha256'] and sha(a.build/'PREPARED.json')==record['prepared_sha256']
    assert read(a.cases/'CASES.json')==record['case_hashes']
    assert all(sha(a.cases/name)==digest for name,digest in record['case_hashes'].items())
    assert record['data_sha256']==validate.TARGET_DATA_SHA256
    groups=[a.work/'guard'/f'round_{i}' for i in range(1,7)] if record['stage']=='primary' else [a.work/'guard/campaign']
    for group in groups:
        guard=read(group/'receipt.json');checks=read(group/'checks.json')
        assert guard['runtime_valid'] and guard['exit_code']==0 and guard['stop_reason'] is None
        assert checks and not any(x['foreign'] for x in checks)
        assert not read(group/'before.json')['apps'] and not read(group/'after.json')['apps']
    for job,row in zip(record['jobs'],raw):
        assert all(row[k]==v for k,v in job.items())
        receipt=read(a.work/'runs'/job['label']/'receipt.json')
        assert all(row[k]==v for k,v in receipt.items()) and receipt['exit_code']==0
        assert receipt['empty_before'] and receipt['empty_after'] and receipt['binary_sha256']==record['binary_sha256']
        prefix=a.work/'outputs'/job['label'];summary=read(Path(str(prefix)+'.summary.json'));scope=read(Path(str(prefix)+'.scope.json'))
        region=read(Path(str(prefix)+'.region.json'));mapping=read(Path(str(prefix)+'.build_tiles.json'))
        live=read(Path(str(prefix)+'.unified.json'));numeric=read(Path(str(prefix)+'.numeric.json'))
        command=read(a.work/'runs'/job['label']/'command.json')
        expected_env=dict(REGION_MODE='PAR_STRONG',KNN_MODE='FULL',BUILD_MAPPING=CONTRACT['modes'][job['mode']],
            TARGET_WARMUP='1',U10_OBSERVE='1',U10_TREE_AUDIT='0',TARGET_RESTORE_AUDIT='0')
        assert all(command['env'].get(k)==v for k,v in expected_env.items()),'wrong execution contract'
        assert ('BUILD_AUDIT_DIR' in command['env'])==job['audit']
        assert (region['mode'],live['knn_mode'])==(1,'FULL')
        assert not region['final_owned_bytes'] and not live['final_owned_bytes'] and not numeric['final_bytes']
        events=a.cases/job['case']/'events.txt';operations=state_rows(prefix)
        assert len(operations)==int(events.read_text().splitlines()[0])
        rebuilds=sum(int(r['flag'])==0 and int(r['buffer_before'])==9 for r in operations)
        assert region['refreshes']==live['refreshes']==numeric['refreshes']==numeric['epoch']==rebuilds+1
        assert mapping['build_calls']==3+rebuilds
        assert [scope[k] for k in ('warmup_events','warmup_queries','warmup_rebuilds')]==[19,8,1]
        assert all(scope[k]==0 for k in ('setup_delay_ms','trace_delay_ms','write_delay_ms'))
        assert row['trace_ms']==summary['trace_ms'] and row['results']==summary['results'] and summary['observe']
        assert scope['warmup'] and row['warmup_ms']==scope['warmup_total_ms']
        assert row['setup_plus_trace_ms']==region['setup_plus_trace_ms'] and row['initial_setup_ms']==region['setup_ms']
        assert math.isfinite(row['trace_ms']) and row['trace_ms']>0
        assert mapping['mode']==CONTRACT['modes'][job['mode']] and mapping['audit']==job['audit'] and mapping['new_owned_GPU_bytes']==0
        if job.get('tool'):
            text=(a.work/'runs'/job['label']/'stdout.log').read_text()+(a.work/'runs'/job['label']/'stderr.log').read_text()
            expected='RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if job['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors'
            assert expected in text
    return dict(registered_sha256=sha(a.work/'REGISTERED.json'),raw_rows_sha256=sha(a.work/'RAW_ROWS.json'),
        output_hashes=hashes(a.work/'outputs'),audit_hashes=hashes(a.work/'audit') if (a.work/'audit').exists() else {},
        run_hashes=hashes(a.work/'runs'),guard_hashes=hashes(a.work/'guard'))


STATE_COLUMNS=('step','flag','base_before','buffer_before','base_after','buffer_after')
def state_rows(p):return [{k:r[k] for k in STATE_COLUMNS} for r in rows(Path(str(p)+'.ops.csv'))]
def same_answers(a,b,events):
    qa=rows(Path(str(a)+'.queries.csv'));qb=rows(Path(str(b)+'.queries.csv'));assert qa==qb
    assert len(state_rows(a))==len(state_rows(b))==events and state_rows(a)==state_rows(b)
    total=sum(int(r['count']) for r in qa)
    for suffix in ('.ids.i32','.dist.f32'):
        x=Path(str(a)+suffix);y=Path(str(b)+suffix)
        assert x.stat().st_size==y.stat().st_size==total*4 and sha(x)==sha(y)
    for suffix in ('.ids.i32','.dist.f32','.queries.csv'):
        assert sha(Path(str(a)+'.warmup'+suffix))==sha(Path(str(b)+'.warmup'+suffix))
    return dict(queries=len(qa),items=total,complete_ordered_byte_identity=True,events=events,operation_state_identity=True)


def parent_binding(parent):
    proof_path=HERE.parent/'unified_target_workflow/phase_b/evidence/PRIMARY_QUALITY.json'
    assert sha(proof_path)=='b03505ad24615549011c31a17c7838e14c8fe55344309e8b0187be9ab3ba3f18'
    proof=read(proof_path);binding=proof['evidence_binding']
    assert sha(parent/'REGISTERED.json')==binding['registered_sha256'] and sha(parent/'RAW_ROWS.json')==binding['raw_rows_sha256']
    for name,digest in binding['guard_hashes'].items():
        if name.startswith('guard/round_1/'):assert sha(parent/name)==digest
    checked=profile.bind_parent(parent,proof,'B')
    return dict(quality_sha256=sha(proof_path),checked_parent_hashes=checked,registered_sha256=binding['registered_sha256'],raw_rows_sha256=binding['raw_rows_sha256'])


def inherited_answer(prefix,parent,prefix_only=False):
    previous=parent/'outputs/round_1_B';fresh=rows(Path(str(prefix)+'.queries.csv'));original=rows(Path(str(previous)+'.queries.csv'))
    assert fresh==(original[:31] if prefix_only else original)
    total=sum(int(r['count']) for r in fresh)
    for suffix in ('.ids.i32','.dist.f32'):
        value=Path(str(prefix)+suffix).read_bytes();old_value=Path(str(previous)+suffix).read_bytes()
        assert len(value)==total*4 and value==old_value[:total*4]
    state=state_rows(prefix);expected=state_rows(previous);assert state==(expected[:51] if prefix_only else expected)
    for suffix in ('.ids.i32','.dist.f32','.queries.csv'):
        assert sha(Path(str(prefix)+'.warmup'+suffix))==sha(Path(str(previous)+'.warmup'+suffix))
    return dict(queries=len(fresh),items=total,admitted_exhaustive_parent_identity=True,events=len(state))


def build_shape(n):
    height=1;tail=n
    while tail>20:tail-=9*(tail//10);height+=1
    height=max(3,height);front=[n];levels=0
    for _ in range(height-1):
        levels+=1;following=[]
        for size in front:
            following.extend(([size//10]*9+[size-9*(size//10)]) if size>20 else [0]*10)
        if not any(size>20 for size in following):break
        front=following
    return sum(10**i for i in range(height)),levels


def layer_identity(work,case,expected_sizes):
    left=work/'audit'/(case+'_B0');right=work/'audit'/(case+'_B1');lh=hashes(left);rh=hashes(right)
    assert set(lh)==set(rh) and lh
    expected=set();sizes={}
    for b,n in enumerate(expected_sizes):
        prefix=f'build{b}/';nn,count=build_shape(n)
        expected.add(prefix+'META.json')
        for key,size in (('refit.lo',8*nn),('refit.hi',8*nn),('refit.empty',4*nn)):sizes[prefix+key]=size
        for level in range(count):
            label=prefix+f'level{level}.'
            expected.update(label+key for key in ('GEOMETRY.json','DISTANCE_DIAGNOSTIC.json'))
            for key,size in (('input.nodes',20*nn),('input.empty',4*nn),('input.split',4*nn),('input.order',4*n),
                ('distance.keys',8*n),('distance.pids',4*nn),('sorted.keys',8*n),('sorted.order',4*n),
                ('after_split.nodes',20*nn),('after_split.empty',4*nn),('after_split.split',4*nn)):sizes[label+key]=size
        meta=read(left/(prefix+'META.json'));assert meta['n']==n and meta['nn']==nn
    expected.update(sizes)
    assert set(lh)==expected,'incomplete or unexpected build/layer file family'
    assert all((left/name).stat().st_size==(right/name).stat().st_size==size for name,size in sizes.items()),'truncated layer state'
    exceptions=('META.json','GEOMETRY.json','DISTANCE_DIAGNOSTIC.json')
    defined=[name for name in lh if not name.endswith(exceptions)]
    assert all(lh[name]==rh[name] for name in defined),'defined layer/topology/bounds changed'
    geometries=[];node_type=np.dtype([('pid','<i4'),('min_dis','<f4'),('size','<i4'),('lid','<i4'),('leaf','<i4')])
    for name in sorted(k for k in lh if k.endswith('GEOMETRY.json')):
        folder=left/Path(name).parent;other=right/Path(name).parent;meta=read(folder/'META.json');m2=read(other/'META.json')
        assert {k:v for k,v in meta.items() if k!='mode'}=={k:v for k,v in m2.items() if k!='mode'}
        geometry=read(left/name);tiled=read(right/name);level=int(Path(name).name.split('.')[0][5:]);n=meta['n'];nn=meta['nn']
        upper=n
        for _ in range(level):upper=upper//10+9
        width=(upper+511)//512
        assert geometry==dict(slots=10**level,start=sum(10**i for i in range(level)),upper=upper,tiles=1,grid=10**level,threads=512)
        assert tiled=={**geometry,'tiles':width,'grid':geometry['slots']*width}
        label=f'level{level}.';nodes=np.fromfile(folder/(label+'input.nodes'),dtype=node_type)
        empty=np.fromfile(folder/(label+'input.empty'),dtype='<i4');split=np.fromfile(folder/(label+'input.split'),dtype='<i4')
        order=np.fromfile(folder/(label+'input.order'),dtype='<i4')
        assert len(nodes)==len(empty)==len(split)==nn and len(order)==n and np.array_equal(np.sort(order),np.arange(n))
        assert np.fromfile(folder/(label+'distance.keys'),dtype='<f8').size==n
        assert np.fromfile(folder/(label+'sorted.keys'),dtype='<f8').size==n
        covered=np.zeros(n,dtype=np.uint8);objects=split_nodes=0
        for nid in range(geometry['start'],geometry['start']+geometry['slots']):
            if empty[nid]:continue
            node=nodes[nid];size=int(node['size']);lid=int(node['lid']);assert 0<size<=upper and 0<=lid<=n-size
            assert not covered[lid:lid+size].any();covered[lid:lid+size]=1;objects+=size;split_nodes+=bool(split[nid])
            assert (size+511)//512<=width
        geometries.append(dict(build=Path(name).parent.name,level=level,n=n,objects_owned=objects,splitting_nodes=split_nodes,baseline=geometry,candidate=tiled,
            baseline_diagnostic_ms=read(folder/(label+'DISTANCE_DIAGNOSTIC.json'))['launch_through_existing_fence_ms'],
            candidate_diagnostic_ms=read(other/(label+'DISTANCE_DIAGNOSTIC.json'))['launch_through_existing_fence_ms']))
    return dict(case=case,builds=len(list(left.glob('build*'))),layers=len(geometries),defined_files=len(defined),
        all_defined_state_bitwise_identical=True,exact_interval_partition_and_unique_tile0_pivot=True,geometry=geometries)


def qualify(a):
    assert read(a.work/'REGISTERED.json')['stage']=='qualification'
    binding=completed(a);source=source_identity(a.build,a.sass,a.parent_build)
    parent=parent_binding(a.parent) if a.parent else {'independent_CPU_oracle_replay':True}
    cpu=old.verify_cpu_library(a.library);validate.scores=oracle.install(a.library)
    results=[];layers=[]
    warm=a.cases/'root20/events.txt'
    for case in CONTRACT['qualification']['cases']:
        b0=a.work/'outputs'/(case+'_B0');b1=a.work/'outputs'/(case+'_B1');events=a.cases/case/'events.txt'
        count=int(events.read_text().splitlines()[0]);identity=same_answers(b0,b1,count)
        if case=='million_prefix' and a.parent:quality=inherited_answer(b0,a.parent,True)
        else:
            data=a.data if case=='million_prefix' else a.cases/case/'data.f32bin'
            if case=='million_prefix':validate.verify_target_data(data)
            quality=validate.check(data,events,b0,CONTRACT['scope']['radius'],8,(1,'FULL'))
            validate.check(data,warm,Path(str(b0)+'.warmup'),CONTRACT['scope']['radius'],8,(1,'FULL'))
        results.append(dict(case=case,identity=identity,quality=quality))
        initial=read(Path(str(b0)+'.scope.json'))['initial_n']
        expected_sizes=[initial,initial+9,initial]+[int(r['base_after']) for r in state_rows(b0) if int(r['flag'])==0 and int(r['buffer_before'])==9]
        layers.append(layer_identity(a.work,case,expected_sizes))
    for job in campaign.jobs('qualification'):
        if job.get('tool'):
            same_answers(a.work/'outputs'/job['label'],a.work/'outputs'/(job['case']+'_B0'),int((a.cases/job['case']/'events.txt').read_text().splitlines()[0]))
    registration=read(a.work/'REGISTERED.json')
    proof=dict(passed=True,binary_sha256=registration['binary_sha256'],contract_sha256=registration['contract_sha256'],data_sha256=registration['data_sha256'],
        source_identity=True,all_layer_identity=True,sanitizers_passed=True,source=source,rows=results,layers=layers,
        source_analysis_sha256=sha(Path(__file__)),evidence_binding=binding,parent_binding=parent,CPU_binding=cpu,
        ordinary_access_sync_only=True,leak_status='UNRESOLVED_CONTEXT_SYMBOLS_NOT_CLEAN',default_promoted=False,long_started=False)
    save(a.output or a.work/'QUALIFICATION.json',proof);print('PASS exact source/layer/output identity and four ordinary-access/sync sanitizers',flush=True)


def bind_admission(a,record):
    assert a.admission and sha(a.admission)==record['admission_sha256'],'missing or changed qualification admission'
    admission=read(a.admission)
    assert admission['passed'] and admission['binary_sha256']==record['binary_sha256'] and admission['contract_sha256']==record['contract_sha256']
    assert admission['data_sha256']==record['data_sha256'] and admission['source_identity'] and admission['all_layer_identity'] and admission['sanitizers_passed']
    assert sha(a.qualification_analysis)==admission['source_analysis_sha256']
    assert completed(SimpleNamespace(work=a.admission.parent,build=a.build,cases=a.cases,executed_driver=a.qualification_driver))==admission['evidence_binding']
    return sha(a.admission)


def primary(a):
    record=read(a.work/'REGISTERED.json');assert record['stage']=='primary';bind_admission(a,record)
    binding=completed(a)
    parent=parent_binding(a.parent) if a.parent else {'independent_CPU_oracle_replay':True}
    if not a.parent:
        parent['CPU_binding']=old.verify_cpu_library(a.library);validate.scores=oracle.install(a.library);validate.verify_target_data(a.data)
    checked=[];raw=read(a.work/'RAW_ROWS.json');by={r['label']:r for r in raw}
    for i in range(1,7):
        b0=a.work/'outputs'/f'round_{i}_B0';b1=a.work/'outputs'/f'round_{i}_B1'
        identity=same_answers(b0,b1,336)
        if a.parent:quality=inherited_answer(b0,a.parent)
        elif i==1:
            quality=validate.check(a.data,a.cases/'primary/events.txt',b0,CONTRACT['scope']['radius'],8,(1,'FULL'))
            validate.check(a.data,a.cases/'root20/events.txt',Path(str(b0)+'.warmup'),CONTRACT['scope']['radius'],8,(1,'FULL'))
        else:quality=same_answers(b0,a.work/'outputs/round_1_B0',336)
        checked.append(dict(round=i,identity=identity,quality=quality))
    values=[by[f'round_{i}_B0']['trace_ms']/by[f'round_{i}_B1']['trace_ms'] for i in range(1,7)]
    paired=old.bootstrap(values);strata={order:float(np.exp(np.log([values[i] for i,o in enumerate(CONTRACT['primary']['orders']) if o==order]).mean())) for order in ('B0B1','B1B0')}
    accepted=paired['CI95'][0]>1 and sum(v>1 for v in values)>=5 and min(strata.values())>1
    cost=[]
    for row in raw:
        prefix=a.work/'outputs'/row['label'];summary=read(Path(str(prefix)+'.summary.json'))
        operations=rows(Path(str(prefix)+'.ops.csv'));numeric=read(Path(str(prefix)+'.numeric.json'))
        region=read(Path(str(prefix)+'.region.json'));live=read(Path(str(prefix)+'.unified.json'))
        groups={}
        for flag,name in enumerate(('insert','delete','range','knn')):
            v=[float(r['ack_ms']) for r in operations if int(r['flag'])==flag]
            groups[name]=dict(count=len(v),sum_ms=sum(v),p50_p99_ms=list(map(float,np.quantile(v,[.5,.99]))))
        cost.append(dict(label=row['label'],mode=row['mode'],initial_setup_ms=row['initial_setup_ms'],setup_plus_trace_ms=row['setup_plus_trace_ms'],
            warmup_ms=row['warmup_ms'],cpu_user_s=summary['cpu_user_s'],cpu_system_s=summary['cpu_system_s'],
            sampled_device_peak_bytes=summary['sampled_device_peak_bytes'],host_output_capacity_bytes=summary['host_output_capacity_bytes'],
            cold_build_ms=summary['cold_build_ms'],final_drain_ms=summary['final_drain_ms'],operations=groups,
            rebuilds_ms=[float(r['rebuild_ms']) for r in operations if float(r['rebuild_ms'])>0],stages=summary['stages'],
            numeric=numeric,region=region,live=live))
    result=dict(status='MEASURED_FIXED_SHORT_SCOPE',internal_win_gate_passed=accepted,paired=paired,raw_ratios=values,
        order_strata=strata,candidate_wins=sum(v>1 for v in values),marginal_median_ratio=float(np.median([r['trace_ms'] for r in raw if r['mode']=='B0'])/np.median([r['trace_ms'] for r in raw if r['mode']=='B1'])),
        variants={mode:dict(values_ms=[r['trace_ms'] for r in raw if r['mode']==mode],p10_median_p90_ms=list(map(float,np.quantile([r['trace_ms'] for r in raw if r['mode']==mode],[.1,.5,.9])))) for mode in ('B0','B1')},
        rows=raw,cost_rows=cost,quality=checked,parent_binding=parent,evidence_binding=binding,analysis_sha256=sha(Path(__file__)),
        binary_sha256=record['binary_sha256'],contract_sha256=record['contract_sha256'],data_sha256=record['data_sha256'],
        qualification_sha256=record['admission_sha256'],default_promoted=False,long_started=False,external_dynamic_comparison=False)
    save(a.work/'RESULTS.json',result);print('PASS fixed12 workflows, complete outputs and paired summary; win=',accepted,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('qualification','primary','source'))
    for name in ('work','build','cases','data','parent','parent-build','library','sass','output','executed-driver','admission','qualification-driver','qualification-analysis'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();assert __debug__
    if a.action=='source':save(a.output,source_identity(a.build,a.sass,a.parent_build))
    else:(qualify if a.action=='qualification' else primary)(a)
