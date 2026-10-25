"""Compose preserved repairs in scratch; pin originals, never edit them."""
import hashlib,importlib.util,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def region(s,start,end):
    a=s.index(start);b=s.index(end,a);return a,b,s[a:b]
def prepare(original,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    pins=json.loads((HERE.parent/'diagnostics/original_tree_redundancy/SOURCE_PINS.json').read_text())['sha256']
    for name,h in pins.items():
        if not name.startswith('GTS/'):continue
        rel=name[4:];src=Path(original)/rel;assert hashlib.sha256(src.read_bytes()).hexdigest()==h,rel
        dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    search=out/'source/include/search.cuh';s=search.read_text();a,b,node=region(s,'__global__ void findNextRnn','__global__ void findNextKnn')
    node=once(node,'float dis_q = 0;', '''COUNT(0,1);
            if(data_info[2]==6)COUNT(2,size_t(size_s[node.pid])*size_s[qid_list[query_id]]);
            if(data_info[2]==2)COUNT(3,data_info[0]);
            float dis_q = 0;''')
    search.write_text(s[:a]+node+s[b:])
    grid=node.replace('void findNextRnn(', 'void findNextRnnGrid(').replace('short *data_d','float *data_d')
    grid=once(grid,'int query_id = bid;','int query_id = 0;')
    grid=once(grid,'for (int i = tid; i < node_num; i += blockDim.x)','for (int i = bid*blockDim.x+tid; i < node_num; i += blockDim.x*gridDim.x)')
    update=out/'source/include/update.cuh';s=update.read_text();a,b,leaf=region(s,'__global__ void leafProcessRnnUpdate','void searchIndexRnnUpdate')
    leaf=once(leaf,'int tid = threadIdx.x;','int tid = threadIdx.x;\n    if(tid==0)COUNT(6,blockDim.x);')
    leaf=once(leaf,'__syncthreads();','__syncthreads();\n        if(tid==0 && node[0].is_leaf==1)COUNT(4,1);')
    leaf=once(leaf,'float result = 0;', '''COUNT(5,1);
                if(data_id!=qid){COUNT(1,1);
                    if(data_info[2]==6)COUNT(2,size_t(size_s[data_id])*size_s[qid]);
                    if(data_info[2]==2)COUNT(3,data_info[0]);}
                float result = 0;''')
    rest=once(s[b:],'leafProcessRnnUpdate<<<search_num[0], THREAD_NUM>>>','if(search_num[0]>0) leafProcessRnnUpdate<<<search_num[0], THREAD_NUM>>>')
    update.write_text(s[:a]+leaf+rest)
    path=HERE.parent/'diagnostics/fusion_scale_20260924/prepare.py';spec=importlib.util.spec_from_file_location('repaired_scale',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    core=m.driver();core=core[:core.index('uint64_t digest(')]
    core=once(core,'#define main original_gts_main','''__device__ unsigned long long work[10];
#if INSTRUMENT
#define COUNT(k,n) atomicAdd(work+(k),(unsigned long long)(n))
#else
#define COUNT(k,n) ((void)0)
#endif
#define main original_gts_main''')
    core=once(core,'struct Fixed {',grid+'\nstruct Fixed {')
    core=once(core,'findNextRnn<<<1,THREAD_NUM,0,stream>>>','findNextRnnGrid<<<(num+THREAD_NUM-1)/THREAD_NUM,THREAD_NUM,0,stream>>>')
    core=once(core,'''        getQnodeCount<<<1,512,0,stream>>>(1,flags,max_node_num,nodecount,0);
        ck(cub::DeviceScan::ExclusiveSum(temp,tempbytes,nodecount,nodeprefix,1,stream));''','''        // Single-query fused output does not consume these redundant counts.''')
    (out/'fused_result.cuh').write_text(m.selector())
    normal=core+'\n'+(HERE/'bench_main.inc').read_text()
    (out/'bench.cu').write_text(normal)
    begin=normal.index('#if INSTRUMENT\n unsigned long long counts[10]')
    end=normal.index('#endif',begin)+len('#endif')
    counter_block=normal[begin:end]
    diagnostic=normal[:begin]+normal[end:]
    diagnostic=once(diagnostic,'  canonicalize(out);return out;};',counter_block+'\n  canonicalize(out);return out;};')
    (out/'bench_count.cu').write_text(diagnostic)
    shutil.copy2(HERE/'bench_io.hpp',out/'bench_io.hpp')
    (out/'source_pins.json').write_text(json.dumps({k:v for k,v in pins.items() if k.startswith('GTS/')},indent=2)+'\n')
    print('PASS pinned original source; generated combined fixed/fused/grid/Graph R and native-batch S')

if __name__=='__main__':prepare(*sys.argv[1:])
