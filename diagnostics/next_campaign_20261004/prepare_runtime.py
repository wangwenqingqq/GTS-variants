#!/usr/bin/env python3
"""Prepare a separate P7-derived runtime; never mutate the frozen executor."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

FILES = ('opt_knn_bench.cu', 'gts_bench_p7.cu', 'knn_cutoff.cuh',
         'knn_select.cuh', 'knn_verify.cuh', 'native_knn.py',
         'qualification.py', 'run_locked.py')
CAMPAIGN_FILES = ('query_trace.hpp', 'query_trace.py', 'campaign10k.py',
                  'qualify10k.py', 'diagnose10k.py', 'analyze_attribution.py',
                  'u10_native.py', 'continue10k.py', 'hook_control.py',
                  'localize_flat.py', 'flat_refine.py', 'qualify_ref64.py',
                  'test_recovery_cpu.py','u10_trace.hpp')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--p7', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    registered = json.loads((Path(__file__).parent/'evidence/SOURCE_BRIDGE.json').read_text())
    for name in FILES:
        assert sha(a.p7/name) == registered['parent_sources'][name], f'changed P7 source: {name}'
    a.output.mkdir(exist_ok=False)
    manifest = {'parent_commit': '7bce3679c3e32e77fa25cf7842805926509e1412',
                'search_commit': 'd65c6e41effad67dde8ae1f1f68e656562607817',
                'parent_sources': {}, 'derived_sources': {}}
    for name in FILES:
        src = a.p7/name
        manifest['parent_sources'][name] = sha(src)
        shutil.copy2(src, a.output/name)
    # Existing search, arithmetic, selector and graph topology stay intact.
    path = a.output/'opt_knn_bench.cu'
    text = path.read_text()
    text = replace(text, '#include "knn_verify.cuh"', '#include "knn_verify.cuh"\n#include "query_trace.hpp"')
    text = replace(text, 'ck(cudaGraphLaunch(executions[count==b?0:1],stream));',
                   'if(std::getenv("K10_EAGER"))dispatch(count);else ck(cudaGraphLaunch(executions[count==b?0:1],stream));')
    text = replace(text, 'for(int w=0;w<2;++w)batch_run(warm.data()+(size_t((w+1)*b)<=warm.size()?w*b:0),std::min(b,int(queries.size())),0);',
                   'check(warm.size()>=size_t(8*b),"eight warm batches required");\n'
                   '    for(int shape:shapes)for(int w=0;w<8;++w)batch_run(warm.data()+w*shape,shape,0);\n'
                   '    if(std::getenv("K10_STRESS")) {\n'
                   '        std::vector<int> expected_ids[2];std::vector<float> expected_dist[2];\n'
                   '        for(int cycle=0;cycle<100;++cycle) {\n'
                   '            int j=cycle%int(shapes.size()),s=shapes[j];batch_run(warm.data()+j*b,s,0);\n'
                   '            std::vector<int> ii(result_ids.begin(),result_ids.begin()+s*k);\n'
                   '            std::vector<float> dd(result_dist.begin(),result_dist.begin()+s*k);\n'
                   '            if(expected_ids[j].empty()){expected_ids[j]=ii;expected_dist[j]=dd;}\n'
                   '            else check(ii==expected_ids[j]&&dd==expected_dist[j],"stress state leakage");\n'
                   '        }\n'
                   '    }')
    text = replace(text, 'nvtxRangePushA("formal.query_pass");auto start=Clock::now();',
                   'QueryTrace trace(out);trace.begin();nvtxRangePushA("formal.query_pass");auto start=Clock::now();')
    text = replace(text, 'first);times.push_back(ms(begin));',
                   'first);times.push_back(ms(begin));trace.sample(std::min(first+b,int(queries.size())),int(queries.size()));')
    text = replace(text, 'double total_ms=ms(start);nvtxRangePop();',
                   'double total_ms=ms(start);nvtxRangePop();trace.finish(total_ms);')
    path.write_text(text)
    path = a.output/'gts_bench_p7.cu'
    text = path.read_text()
    text = replace(text, '#undef short', '#undef short\n#include "query_trace.hpp"')
    text = replace(text, 'require(nw>=2*batch,"warm count");', 'require(nw>=warm*batch,"warm count");')
    text = replace(text, 'for(int i=0;i<warm;++i) run_batch(i*batch,batch,false);',
                   'for(int i=0;i<warm;++i) run_batch(i*batch,batch,false);\n'
                   '    if(q%batch)for(int i=0;i<warm;++i)run_batch(i*(q%batch),q%batch,false);')
    text = replace(text, 'std::vector<double> batch_ms; auto begin=Clock::now();',
                   'QueryTrace trace(argv[7]);trace.begin();std::vector<double> batch_ms; auto begin=Clock::now();')
    text = replace(text, 'batch_ms.push_back(elapsed(t));}',
                   'batch_ms.push_back(elapsed(t));trace.sample(std::min(start+batch,q),q);}')
    text = replace(text, 'double total_ms=elapsed(begin);',
                   'double total_ms=elapsed(begin);trace.finish(total_ms);\n'
                   '        std::ofstream batches(std::string(argv[7])+".batches.csv");batches<<"batch_index,host_ms\\n"<<std::setprecision(12);\n'
                   '        for(size_t i=0;i<batch_ms.size();++i)batches<<i<<","<<batch_ms[i]<<"\\n";')
    path.write_text(text)
    path = a.output/'native_knn.py'
    text = path.read_text()
    text = replace(text, 'import time', 'import time\nfrom query_trace import QueryTrace')
    text = replace(text, 'native_ivf.read_qids(a.warm)',
                   'np.array(list(map(int,Path(a.warm).read_text().split()))[1:],dtype=np.int32)')
    text = replace(text, 'for w in range(2):batch(warm[w*b:(w+1)*b],0)',
                   'assert len(warm)>=8*b,"eight actual warm chunks required"\n'
                   '        for w in range(8):batch(warm[w*b:(w+1)*b],0)\n'
                   '        tail=len(qids)%b\n'
                   '        if tail:\n'
                   '            for w in range(8):batch(warm[w*tail:(w+1)*tail],0)')
    text = replace(text, 'times=[];cp.cuda.nvtx.RangePush', 'trace=QueryTrace(out);trace.begin();times=[];cp.cuda.nvtx.RangePush')
    text = replace(text, 'times.append((time.perf_counter()-start)*1000)',
                   'times.append((time.perf_counter()-start)*1000);trace.sample(min(first+b,len(qids)),len(qids))')
    text = replace(text, 'total=(time.perf_counter()-begin)*1000;cp.cuda.nvtx.RangePop()',
                   'total=(time.perf_counter()-begin)*1000;cp.cuda.nvtx.RangePop();trace.finish(total)')
    path.write_text(text)
    path = a.output/'run_locked.py'
    text = path.read_text()
    text = replace(text, "parser.add_argument('--gpu',required=True)",
                   "parser.add_argument('--timeout-seconds',type=float,default=1200)\n    parser.add_argument('--gpu',required=True)")
    text = replace(text, 'time.monotonic()-start>1200', 'time.monotonic()-start>args.timeout_seconds')
    path.write_text(text)
    for name in CAMPAIGN_FILES:
        shutil.copy2(Path(__file__).parent/name, a.output/name)
    for name in FILES+CAMPAIGN_FILES:
        manifest['derived_sources'][name] = sha(a.output/name)
    (a.output/'SOURCE_BRIDGE.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__ == '__main__':
    main()
