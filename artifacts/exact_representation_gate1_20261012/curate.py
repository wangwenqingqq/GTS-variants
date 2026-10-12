"""Verify private raw arrays and export only public scalar/hash receipts."""
import argparse,platform,subprocess
from pathlib import Path
import numpy as np
from run import HERE,load,save,sha,sources,histogram
from analyze import analyze
def curate(work,out):
    assert not out.exists();reg=load(work/'REGISTERED.json');result=load(work/'RESULTS.json');start=load(work/'START.json');qualified=load(work/'QUALIFICATION.json');raw=load(work/'RAW_MANIFEST.json')['files']
    c=load(HERE/'CONTRACT.json');N=c['workload']['N'];D=c['workload']['D'];threshold=reg['threshold']
    assert result['complete'] and result['pairs']==32000000 and result['queries']==32 and result['GPU_starts']==0
    assert reg['source_hashes']==start['source_hashes']==sources()
    assert result['registration_sha256']==sha(work/'REGISTERED.json') and result['start_sha256']==sha(work/'START.json') and result['raw_manifest_sha256']==sha(work/'RAW_MANIFEST.json')
    assert qualified['passed'] and start['qualified_sha256']==sha(work/'QUALIFICATION.json') and sha(reg['data'])==reg['data_sha256']
    assert reg['qids']==c['workload']['qids'] and threshold.hex()==c['numerics']['threshold_hex']
    records=[];identities={}
    for index,q in enumerate(reg['qids']):
        score=work/'raw'/f'{q}.f64';required=work/'raw'/f'{q}.required.u16';ref=Path(reg['reference'])/f'{q}.f64'
        assert score.stat().st_size==ref.stat().st_size==N*8 and required.stat().st_size==N*2
        assert sha(score)==sha(ref)==raw[score.name]==reg['reference_hashes'][ref.name]
        assert sha(required)==raw[required.name]
        full=np.fromfile(score,'<f8');dims=np.fromfile(required,'<u2');hits=full<=threshold
        assert np.isfinite(full).all() and ((dims>=1)&(dims<=D)).all() and (dims[hits]==D).all()
        r=load(work/'scalars'/f'q{index:02}.json');assert r['qid']==q and r['query_index']==index
        assert histogram(dims,D)==r['histogram'] and histogram(dims[~hits],D)==r['nonhit_histogram']
        assert int(hits.sum())==r['hits'] and int(((~hits)&(dims==D)).sum())==r['hard_nonhits_at_D']
        assert r['full960_bit_mismatches']==r['false_rejections']==0 and (r['min_previous_slack'] is None or r['min_previous_slack']>=0) and (r['min_crossing_excess'] is None or r['min_crossing_excess']>0)
        margin=full-threshold;masks={'near':(~hits)&(margin<=threshold*.1),'medium':(~hits)&(margin>threshold*.1)&(margin<=threshold),'far':(~hits)&(margin>threshold)}
        for key,mask in masks.items():
            v=r['margin_groups'][key];assert v['count']==int(mask.sum()) and v['histogram']==histogram(dims[mask],D)
            assert v['margin_min']==(float(margin[mask].min()) if mask.any() else None) and v['margin_max']==(float(margin[mask].max()) if mask.any() else None)
        records.append(r)
        for p in (score,required):identities[p.name]=dict(sha256=raw[p.name],bytes=p.stat().st_size)
    lib=work/'build/progressive.so';build=load(work/'build/BUILD.json');assert sha(lib)==build['binary_sha256'] and build['registration_sha256']==sha(work/'REGISTERED.json')
    ldd=subprocess.check_output(['ldd',str(lib)],text=True);assert 'not found' not in ldd and not any(x in ldd.lower() for x in ('cuda','cuvs','cublas'))
    dependencies={}
    for line in ldd.splitlines():
        words=line.split()
        if '=>' in words and len(words)>2 and words[2].startswith('/'):dependencies[words[0]]=sha(words[2])
    out.mkdir();save(out/'QUERY_RECORDS.json',records);save(out/'AGGREGATE.json',analyze(records,c))
    save(out/'QUALITY.json',dict(passed=True,primary_queries=32,pairs=32000000,full960_bit_mismatches=0,false_rejections=0,all_first_crossing_predecessor_checks_passed=True,all_full_score_hashes_match_original_reference=True,raw_histograms_independently_reconstructed=True,required_dims_for_all_hits=D,qualification=dict(CPU_tests=3,bounded_queries=32,objects_per_query=4096,duplicates_and_boundaries=True),GPU_starts=0))
    save(out/'EXECUTION_CLOSURE.json',dict(complete=True,CPU_full_population_processes=1,CPU_workers=1,GPU_starts=0,measurement_source_hashes=reg['source_hashes'],contract_sha256=reg['contract_sha256'],registration_sha256=sha(work/'REGISTERED.json'),start_sha256=sha(work/'START.json'),results_sha256=sha(work/'RESULTS.json'),qualification_sha256=sha(work/'QUALIFICATION.json'),raw_manifest_sha256=sha(work/'RAW_MANIFEST.json'),CPU_binary_sha256=sha(lib),data_sha256=reg['data_sha256'],reference_hashes=reg['reference_hashes'],no_failed_primary_replacement=not (work/'FAILURE.json').exists()))
    cpu=next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
    save(out/'ENVIRONMENT.json',dict(CPU=cpu,architecture=platform.machine(),CPU_workers=1,priority='nice10',python=reg['python'],numpy=reg['numpy'],compiler=reg['compiler_version'],compiler_flags=c['execution']['compiler_flags'],CPU_library_dependencies=dependencies,CUDA_visible_devices='empty for this process;no global settings changed',GPU_starts=0,no_GPU_libraries_linked=True,placement='private',timing_scope='No measured latency or physical memory-traffic claim'))
    save(out/'RAW_IDENTITY.json',dict(files=identities,scope='Private full ordered scores and per-pair dimensions; only identities public'))
    print('CURATED verified all64 raw arrays,32 original reference hashes,0 numerical failures,0 GPU starts',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();curate(a.work,a.output)
