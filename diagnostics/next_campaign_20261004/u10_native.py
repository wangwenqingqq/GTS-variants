#!/usr/bin/env python3
"""Long native multiset correctness replay using the frozen U0 observer."""
import argparse
import csv
import difflib
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import numpy as np
from campaign10k import ROOT,invoke,save,sha

SEEDS=(2026100431,2026100432,2026100433)

# Separate lean host-output adapter. GPU kernels/arithmetic and all registered
# operations stay original; the only search repair remains rnum[0]=0.
TIMED_MAIN=r'''
int main(int argc,char** argv) try {
    if(argc!=6 || std::string(argv[3])!="2")throw std::runtime_error("native timed arguments");
    u10_ck(cudaFree(nullptr));auto start=U10Clock::now();
    load(argv[1],data_info,data_d,data_s,size_s);
    loadUpdate(argv[2],update_list,update_num);
    r=std::stof(argv[4]);int queries=0;
    for(int i=0;i<update_num;++i)queries+=update_list[i].update_flag==2;
    u10_ck(cudaDeviceSynchronize());u10.load_ms=u10_ms(start);
    u10.initialize(data_info[1],queries,update_num);
    start=U10Clock::now();nvtxRangePushA("native.cold_build");
    indexConstru(data_d,data_s,size_s,data_info,id_list,node_list,max_node_num,tree_h,empty_list);
    u10_ck(cudaDeviceSynchronize());nvtxRangePop();u10.cold_build_ms=u10_ms(start);
    u10.begin();
    updateIndexRnn(data_d,node_list,id_list,max_node_num,qid_list,1,r,tree_h,data_info,empty_list,
                   qresult_count,qresult_count_prefix,result_id,result_dis,data_s,size_s,nullptr,
                   time_update_s,time_update_u,count_update_s,count_update_u);
    start=U10Clock::now();
    for(void* p:{(void*)data_info,(void*)data_d,(void*)data_s,(void*)size_s,(void*)id_list,
                (void*)node_list,(void*)max_node_num,(void*)qid_list,(void*)empty_list,
                (void*)update_list,(void*)res,(void*)res_dis})u10_ck(cudaFree(p));
    u10_ck(cudaDeviceSynchronize());u10.drain_ms=u10_ms(start);u10.finish();
    u10.write(argv[5]);return 0;
}catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<std::endl;return 1;}
'''

def prepare_timed(a):
    sys.path.insert(0,str(a.u0));import u0
    pins=json.loads((a.u0/'ORIGINAL_SOURCE.json').read_text())
    source=a.u0/'run/original';dest=ROOT/'native_timed/source'
    assert all(sha(source/n)==h for n,h in pins['files'].items())
    dest.parent.mkdir(exist_ok=True);shutil.copytree(source,dest)
    shutil.copy2(ROOT/'u10_trace.hpp',dest/'include/u10_trace.hpp')
    def once(text,old,new):
        assert text.count(old)==1,old
        return text.replace(old,new)
    path=dest/'src/main.cu';text=path.read_text()
    text='#include "u10_trace.hpp"\n'+text[:text.index('int main(int argc, char **argv)')]+TIMED_MAIN
    path.write_text(text)
    path=dest/'include/update.cuh';text=path.read_text()
    text=once(text,'\tprintf("Updating...\\n");','')
    text=once(text,'\t\t\tif (in_size > 0)\n','\t\t\trnum[0] = 0;\n\t\t\tif (in_size > 0)\n')
    text=once(text,'\tfor (int i = 0; i < update_num; i++)\n\t{',
              '\tfor (int i = 0; i < update_num; i++)\n\t{\n\t\tu10.begin_op(i,update_list[i].update_flag,tree_size,in_size);')
    text=once(text,'\t\t\tif (in_size == MAX_IN_SIZE)\n\t\t\t{',
              '\t\t\tif (in_size == MAX_IN_SIZE)\n\t\t\t{\n\t\t\t\tu10.begin_rebuild();\n\t\t\t\t{U10Stage stage(5);')
    construct='\t\t\t\tindexConstru(data_d, data_s, size_s, data_info, id_list, node_list, max_node_num, tree_h, empty_list);'
    text=once(text,construct,'\t\t\t\t}\n\t\t\t\t{U10Stage stage(6);\n'+construct+'\n\t\t\t\t}\n\t\t\t\t{U10Stage stage(7);')
    text=once(text,'\t\t\t\tin_size = 0;','\t\t\t\tin_size = 0;\n\t\t\t\t}\n\t\t\t\tu10.end_rebuild();')
    tree='searchIndexRnnUpdate(data_d, node_list, id_list, max_node_num, qid_list, qnum, r, tree_h, data_info, empty_list,\n\t\t\t\t\t\t\t\t qresult_count, qresult_count_prefix, result_id, result_dis, data_s, size_s);'
    text=once(text,tree,'{U10Stage stage(0);'+tree+'}')
    buffer='searchNaiveRnn(data_info, obj_r, data_d, data_s, size_s, qid_list[0], in_size, r, insert_list, rnum);'
    text=once(text,buffer,'{U10Stage stage(1);'+buffer+'}')
    text=once(text,'\t\t\ttotal_result_num = qresult_count[0] + rnum[0];',
              '\t\t\t{U10Stage stage(2);\n\t\t\ttotal_result_num = qresult_count[0] + rnum[0];')
    text=once(text,'\t\t\tfprintf(fcost, "%d ", total_result_num);\n\t\t\tfflush(fcost);',
              '\t\t\t}\n\t\t\tu10.deliver(i,qid_list[0],tree_size,in_size,total_result_num,total_result_id,total_result_dis);')
    # Stop deletion-prefix scope at its existing fence; retain cudaStatus's
    # outer scope because the buffer deletion branch reuses it.
    anchor='\t\t\t// printf("Deleting ...\\n");'
    text=once(text,anchor,anchor+'\n\t\t\t{U10Stage stage(3);')
    anchor='\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tis_delete_prefix, tree_size, in_size, is_delete);\n\t\t\tcudaDeviceSynchronize();'
    text=once(text,anchor,anchor+'\n\t\t\t}')
    text=once(text,'\t\t\t\tCHECK(cudaMemset(is_delete_in, 0, in_size * sizeof(int)));',
              '\t\t\t\tU10Stage stage(4);\n\t\t\t\tCHECK(cudaMemset(is_delete_in, 0, in_size * sizeof(int)));')
    text=once(text,'\t\t\ttime_update_s += diff.count();\n\t\t}\n\t}',
              '\t\t\ttime_update_s += diff.count();\n\t\t}\n\t\tu10.end_op(tree_size,in_size);\n\t}')
    path.write_text(text)
    path=dest/'include/tree.cuh';text=path.read_text()
    text=once(text,'\tprintf("Index construction...\\n");','')
    text=once(text,'\tprintf("Tree height: %d\\n", tree_h);',
              '\tif(u10.tree_audit){\n'+u0.TREE_OBSERVATION+'\n\t}')
    path.write_text(text)
    # Existing host synchronization failures must stop, not merely print.
    for name in ('tree.cuh','update.cuh','search_naive.cuh'):
        path=dest/'include'/name
        path.write_text(path.read_text().replace('cudaDeviceSynchronize();','u10_ck(cudaDeviceSynchronize());'))
    diffs={}
    for name in pins['files']:
        before=(source/name).read_text();after=(dest/name).read_text()
        if before!=after:
            diffs[name]=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='original/'+name,tofile='lean/'+name))
    (dest.parent/'adapter.diff').write_text('\n'.join(diffs.values()))
    binary=dest.parent/'u0_lean_full_output'
    cmd=['/usr/local/cuda/bin/nvcc','-std=c++17','-O3','-arch=sm_120','-rdc=true','-lineinfo',
         '-Xnvlink=--ignore-host-info','-I'+str(dest/'include'),dest/'src/main.cu','-o',binary]
    with (dest.parent/'BUILD.log').open('w') as log:subprocess.run(list(map(str,cmd)),stdout=log,stderr=subprocess.STDOUT,check=True)
    save(dest.parent/'SOURCE.json',{'upstream':pins,'sources':{n:sha(dest/n) for n in pins['files']},
         'observer_sha256':sha(dest/'include/u10_trace.hpp'),'binary_sha256':sha(binary),'build':list(map(str,cmd)),
         'search_change':'rnum[0]=0 only; unchanged kernels/arithmetic/topology',
         'adapter':'bounded full IDs/FP32 fields Host buffers; same ACK fences in on/off; disk writes after trace',
         'tree_audit':'optional correctness only; never a performance sample'})

def check_timed(a,seed,label,bridge=False):
    case=ROOT/'native'/str(seed);m=json.loads((case/'expected.json').read_text())
    assert sha(case/'data.txt')==m['data_sha256'] and sha(case/'events.txt')==m['events_sha256']
    out=ROOT/'native_timed'/label
    ids=np.fromfile(str(out)+'.ids.i32',dtype='<i4');fields=np.fromfile(str(out)+'.dist.f32',dtype='<f4')
    records=list(csv.DictReader(open(str(out)+'.queries.csv')));assert len(records)==len(m['expected'])
    total=0;previous=0
    for rec,ref in zip(records,m['expected']):
        for key in ('step','qid','tree_size','buffer'):assert int(rec[key])==ref[key],(seed,ref['step'],key)
        start,count=int(rec['offset']),int(rec['count']);assert start==previous and count==len(ref['ids'])
        got=ids[start:start+count];distance=fields[start:start+count]
        assert len(got)==count and len(set(map(int,got)))==count and set(map(int,got))==set(ref['ids']),(seed,ref['step'],'membership')
        want=dict(zip(ref['ids'],ref['distances']))
        assert all(np.isfinite(v) and v>=0 and np.float32(v).tobytes()==np.float32(want[int(i)]).tobytes() for i,v in zip(got,distance)),(seed,ref['step'],'fields')
        total+=count;previous=start+count
    assert previous==len(ids)==len(fields)
    summaries=json.loads(Path(str(out)+'.summary.json').read_text())
    operations=list(csv.DictReader(open(str(out)+'.ops.csv')))
    if summaries['observe']:
        assert len(operations)==len(m['operations']);base=1000;alive=1000;buf=0;rebuilds=0
        for step,(actual,(flag,idx)) in enumerate(zip(operations,m['operations'])):
            for key,want in (('step',step),('flag',flag),('base_before',base),('buffer_before',buf)):assert int(actual[key])==want
            rebuilt=False
            if flag==0:
                buf+=1
                if buf==10:base=alive+buf;alive=base;buf=0;rebuilt=True;rebuilds+=1
            elif flag==1:
                if idx<alive:alive-=1
                else:buf-=1
            assert int(actual['base_after'])==base and int(actual['buffer_after'])==buf
            assert (float(actual['rebuild_ms'])>0)==rebuilt and float(actual['ack_ms'])>=float(actual['rebuild_ms'])
        assert rebuilds==50
        summaries['latency_ms']={}
        for name,values in [(name,[float(r['ack_ms']) for r in operations if int(r['flag'])==flag]) for flag,name in enumerate(('insert','delete','query'))]+[('rebuild',[float(r['rebuild_ms']) for r in operations if float(r['rebuild_ms'])>0])]:
            summaries['latency_ms'][name]={'count':len(values),'p50':float(np.percentile(values,50)),'p95':float(np.percentile(values,95)),
                                         'p99':float(np.percentile(values,99)),'max':max(values),'sum':sum(values)}
    if bridge:
        sys.path.insert(0,str(a.u0));import u0
        data=np.loadtxt(case/'data.txt',skiprows=1,dtype=np.int64).tolist()
        trees=[json.loads(line[8:]) for line in (ROOT/'runs'/label/'stdout.log').open() if line.startswith('U0_TREE ')]
        assert len(trees)==51
        summaries['ancestor_member_checks']=sum(u0.tree_audit(tree,[data[i] for i in base]) for tree,base in zip(trees,m['build_base_maps']))
        # Compare each ID and exact FP32 field with the preserved observer too;
        # range output is a multiset, so no artificial output-order contract.
        observer=ROOT/'native_observer'/f'{seed}.log';position=0
        for line in observer.open():
            if not line.startswith('U0_RESULT '):continue
            ref=json.loads(line[10:]);rec=records[position];start,count=int(rec['offset']),int(rec['count'])
            observed={int(i):np.float32(v).tobytes() for i,v in zip(ref['ids'],ref['distances'])}
            actual={int(i):v.tobytes() for i,v in zip(ids[start:start+count],fields[start:start+count])}
            assert actual==observed;position+=1
        assert position==10000
        summaries['observer_bridge_sha256']=sha(observer)
    result={'seed':seed,'label':label,'state':'correctness_passed','queries':10000,'operations':12000,'threshold_rebuilds':50,
            'results_checked':total,'FN':0,'FP':0,'duplicates':0,'exact_FP32_fields':True,'summary':summaries,
            'outputs':{suffix:sha(str(out)+suffix) for suffix in ('.ids.i32','.dist.f32','.queries.csv','.ops.csv','.summary.json')},
            'admission':'bridge/observer-cost qualification pending; no dynamic speedup/concurrency claim'}
    save(str(out)+'.CHECK.json',result);return result

def generate(a):
    dest=ROOT/'native';dest.mkdir(exist_ok=True)
    source=a.u0/'run/fixtures/query_only.data'
    data=np.loadtxt(source,skiprows=1,dtype=np.int64);assert data.shape==(1000,128)
    # Exact integer metric; every FP32 dimension sum is below 2^24.
    norms=(data*data).sum(axis=1)
    sq=norms[:,None]+norms[None,:]-2*(data@data.T)
    assert sq.min()==0 and sq.max()<2**24
    for seed,radius in zip(SEEDS,(0,10000,512)):
        case=dest/str(seed)
        if case.exists():continue
        case.mkdir();(case/'data.txt').write_bytes(source.read_bytes())
        rng=random.Random(seed);base=np.arange(1000);alive=np.ones(1000,dtype=bool);buf=[];ops=[];expected=[];builds=[base.tolist()]
        def query():
            q=rng.randrange(len(base));step=len(ops);ops.append([2,q])
            live=np.r_[base[alive],np.array(buf,dtype=np.int64)]
            distances=sq[base[q],live];ids=np.flatnonzero(distances<=radius*radius)
            expected.append({'step':step,'qid':q,'tree_size':len(base),'buffer':len(buf),
                             'ids':ids.tolist(),'distances':np.sqrt(distances[ids].astype(np.float64)).astype(np.float32).tolist(),'active_size':len(live)})
        def update(flag,idx):
            nonlocal base,alive,buf
            ops.append([flag,idx])
            if flag==0:
                buf.append(int(base[idx]))
                if len(buf)==10:
                    base=np.r_[base[alive],np.array(buf,dtype=np.int64)];alive=np.ones(len(base),dtype=bool);buf=[];builds.append(base.tolist())
            else:
                positions=np.flatnonzero(alive)
                if idx<len(positions):alive[positions[idx]]=False
                else:buf.pop(idx-len(positions))
        for cycle in range(100):
            for pair in range(10):
                query()
                if cycle%2==0:
                    rank=rng.randrange(int(alive.sum()));update(1,rank);query();update(0,rng.randrange(len(base)));query()
                else:
                    update(0,rng.randrange(len(base)));query();update(1,int(alive.sum())+len(buf)-1);query()
            for i in range(70):query()
            assert len(base)==1000 and int(alive.sum())==1000 and not buf
        assert len(ops)==12000 and len(expected)==10000 and len(builds)==51
        (case/'events.txt').write_text('12000\n'+''.join(f'{f} {i}\n' for f,i in ops))
        save(case/'expected.json',{'seed':seed,'radius':radius,'operations':ops,'expected':expected,'build_base_maps':builds,
                                 'data_sha256':sha(case/'data.txt'),'events_sha256':sha(case/'events.txt'),
                                 'membership':'exact integer squared L2; live multiset ranks','fresh_external_arrivals':False})
    save(dest/'REGISTERED.json',{'seeds':SEEDS,'Q_each':10000,'events_each':12000,'insert_each':1000,'delete_each':1000,
                              'rebuilds_each':50,'timer':'U0 observer; correctness only, no performance promotion',
                              'binary_sha256':sha(a.u0/'run/bin/u0_rnum_reset_obs'),
                              'traces':{str(s):{'expected_sha256':sha(dest/str(s)/'expected.json'),'events_sha256':sha(dest/str(s)/'events.txt')} for s in SEEDS}})

def check(a,seed):
    sys.path.insert(0,str(a.u0))
    import u0
    case=ROOT/'native'/str(seed);manifest=json.loads((case/'expected.json').read_text())
    assert sha(case/'data.txt')==manifest['data_sha256'] and sha(case/'events.txt')==manifest['events_sha256']
    data=np.loadtxt(case/'data.txt',skiprows=1,dtype=np.int64).tolist();results=[];trees=[]
    log=ROOT/'runs'/f'u10_native_{seed}'/'stdout.log'
    for line in log.open():
        if line.startswith('U0_RESULT '):results.append(json.loads(line[10:]))
        elif line.startswith('U0_TREE '):trees.append(json.loads(line[8:]))
    assert len(results)==10000 and len(trees)==51,(len(results),len(trees))
    checked_members=0
    for tree,base_map in zip(trees,manifest['build_base_maps']):
        checked_members+=u0.tree_audit(tree,[data[i] for i in base_map])
    total=0
    for actual,expected in zip(results,manifest['expected']):
        for key in ('step','qid','tree_size','buffer'):assert actual[key]==expected[key],(seed,expected['step'],key)
        ids=actual['ids'];assert len(ids)==len(set(ids)) and set(ids)==set(expected['ids']),(seed,expected['step'],'membership')
        fields=dict(zip(expected['ids'],expected['distances']))
        assert len(ids)==len(actual['distances'])
        for idx,value in zip(ids,actual['distances']):
            ref=fields[idx];assert np.isfinite(value) and value>=0 and abs(value-ref)<=1e-5*max(1,ref),(seed,expected['step'],'field')
        total+=len(ids)
    result={'seed':seed,'state':'passed','query_checkpoints':10000,'actual_rebuilds':len(trees)-1,'events':12000,'results_checked':total,
            'ancestor_member_checks':checked_members,'FN':0,'FP':0,'duplicates':0,'invalid_IDs':0,'fields_pass':True,'raw_log_sha256':sha(log),
            'visibility':'serialized native loop; no concurrency/fresh-arrival claim','timing_scope':'correctness observer; no latency/QPS claim'}
    save(case/'CHECK.json',result);print(json.dumps(result),flush=True);return result

def run(a):
    generate(a);rows=[]
    for seed in SEEDS:
        case=ROOT/'native'/str(seed);m=json.loads((case/'expected.json').read_text())
        expected=json.loads((ROOT/'native/REGISTERED.json').read_text())['binary_sha256']
        binary=a.u0/'run/bin/u0_rnum_reset_obs';assert sha(binary)==expected
        invoke(a,f'u10_native_{seed}',[binary,case/'data.txt',case/'events.txt',2,m['radius'],case/'counts.txt'],14400)
        rows.append(check(a,seed));save(ROOT/'U10_NATIVE.json',rows)
    print('U10 NATIVE CORRECTNESS COMPLETE: 30000 query events, 150 threshold rebuilds',flush=True)

def timed_process(a,seed,label,observe=True,bridge=False):
    binary=ROOT/'native_timed/u0_lean_full_output';sources=ROOT/'native_timed/SOURCE.json'
    assert sha(binary)==json.loads(sources.read_text())['binary_sha256']
    case=ROOT/'native'/str(seed);m=json.loads((case/'expected.json').read_text())
    out=ROOT/'native_timed'/label
    mode={'U10_OBSERVE':str(int(observe)),'U10_TREE_AUDIT':str(int(bridge))}
    registered=out.with_suffix('.MODE.json')
    if registered.exists():assert json.loads(registered.read_text())==mode
    else:save(registered,mode)
    identities=[sources,registered,case/'expected.json',*list((ROOT/'native_timed/source').rglob('*.cuh')),
                ROOT/'native_timed/source/src/main.cu',ROOT/'native_timed/source/include/u10_trace.hpp']
    if bridge:identities.append(ROOT/'native_observer'/f'{seed}.log')
    receipt=invoke(a,label,[binary,case/'data.txt',case/'events.txt',2,m['radius'],out],14400,env=mode,identity_files=identities)
    result=check_timed(a,seed,label,bridge);result['receipt']=receipt
    save(str(out)+'.CHECK.json',result);return result

def bridge_timed(a):
    result=timed_process(a,SEEDS[0],'u10_lean_bridge',bridge=True)
    save(ROOT/'U10_LEAN_BRIDGE.json',result)
    print('U10 LEAN BRIDGE PASSED: seed1, 10000 queries, exact fields, 51 complete trees',flush=True)

def hook_timed(a):
    from hook_control import bootstrap_upper
    assert json.loads((ROOT/'U10_LEAN_BRIDGE.json').read_text())['state']=='correctness_passed'
    registration={'seeds':SEEDS,'pairs_each':6,'bootstrap_seed':2026100441,'directions':'alternating 3 on/off and 3 off/on',
                  'material_limit_ratio':1.03,'outputs':'byte-identical complete IDs/fields/query states',
                  'timer':'whole trace plus cleanup/final drain; file writes excluded in both modes',
                  'off':'full-output delivery and ACK fences retained; optional host timing/NVTX/snapshots off',
                  'source_sha256':sha(ROOT/'native_timed/SOURCE.json')}
    reg=ROOT/'U10_LEAN_HOOK_REGISTERED.json'
    if reg.exists():assert json.loads(reg.read_text())==json.loads(json.dumps(registration))
    else:save(reg,registration)
    rows=[];summaries=[]
    for seed in SEEDS:
        ratios=[];same=True
        for round_no in range(1,7):
            pair={}
            for variant in (('on','off') if round_no%2 else ('off','on')):
                label=f'u10_lean_{seed}_r{round_no}_{variant}'
                pair[variant]=timed_process(a,seed,label,observe=variant=='on')
                rows.append(pair[variant]);save(ROOT/'U10_LEAN_HOOK_ROWS.json',rows)
            hashes=all(pair['on']['outputs'][suffix]==pair['off']['outputs'][suffix] for suffix in ('.ids.i32','.dist.f32','.queries.csv'))
            same &= hashes;ratios.append(pair['on']['summary']['trace_ms']/pair['off']['summary']['trace_ms'])
        point,upper=bootstrap_upper(ratios)
        summaries.append({'seed':seed,'ratios':ratios,'on_off_geomean':point,'upper95':upper,
                          'output_hashes_identical':same,'timer_admitted':same and upper<=1.03})
        save(ROOT/'U10_LEAN_HOOK_SUMMARY.json',summaries)
        print(f'U10 LEAN HOOK {seed}: ratio={point:.6f} upper95={upper:.6f} hashes={same}',flush=True)
    result={'state':'collection_complete','observer_admitted':all(s['timer_admitted'] for s in summaries),
            'summary':summaries,'rows_sha256':sha(ROOT/'U10_LEAN_HOOK_ROWS.json'),'registration_sha256':sha(reg)}
    save(ROOT/'U10_LEAN_HOOK_COMPLETE.json',result)
    if result['observer_admitted']:save(ROOT/'U10_LEAN_TIMING_ADMITTED.json',result)

def main():
    phases={'generate':generate,'run':run,'prepare-timed':prepare_timed,'bridge-timed':bridge_timed,'hook-timed':hook_timed}
    p=argparse.ArgumentParser();p.add_argument('phase',choices=phases);p.add_argument('--gpu',required=True)
    p.add_argument('--u0',type=Path,required=True);a=p.parse_args();phases[a.phase](a)

if __name__=='__main__':main()
