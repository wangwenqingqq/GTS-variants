#!/usr/bin/env python3
"""Generate exactly three pinned current-P variants in a fresh external scratch."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def replace_once(s,old,new):
    assert s.count(old)==1,('nonunique source anchor',old[:80]);return s.replace(old,new)

PACKED=r'''__global__ void verify_materialized(View v,const int* leaf_list,int leaf_count,float radius,int* hit,float* distances,Work w) {
    const int begin=3*blockIdx.x;
    // Uniform whole-group return only; every participating lane reaches the barrier.
    int a=begin<leaf_count?leaf_list[begin]:-1;
    int b=begin+1<leaf_count?leaf_list[begin+1]:-1;
    int c=begin+2<leaf_count?leaf_list[begin+2]:-1;
    if(a<0 && b<0 && c<0)return;
    __shared__ float query[QUERY_DIM];
    for(int j=threadIdx.x;j<v.d;j+=blockDim.x)query[j]=v.data[size_t(v.qids[0])*v.d+j];
    __syncthreads();
    const int leaf=threadIdx.x/10,lane=threadIdx.x%10;
    if(leaf>=3)return;
    int nid=leaf==0?a:(leaf==1?b:c);if(nid<0)return;
    Node node=v.nodes[nid];
    for(int j=lane;j<node.size;j+=10) {
        int id=v.order[node.lid+j];
        if(!v.deleted[id]) {
            if(id!=v.qids[0])count(w.objects,id);
            float distance;bool keep=target::hit(v.data,v.d,id,query,radius,distance);
            if(keep) {int slot=v.leaf_slot[nid]+j;hit[slot]=1;distances[slot]=distance;}
        }
    }
}'''
DUMP=r'''#ifdef REGION_COUNTERS
        const char* root=std::getenv("FIXED3_WORK_DIR");require(root,"counter dump directory required");
        static uint64_t seq=0;
        std::ofstream sink(std::string(root)+"/"+std::to_string(seq)+".bin",std::ios::binary);
        uint64_t head[]={0x43504633574f524bULL,epoch,uint64_t(view.n),uint64_t(view.node_count),uint64_t(plan.total_leaves),uint64_t(qids[0]),seq++};
        sink.write((char*)head,sizeof(head));
        for(auto item:{std::pair<unsigned long long*,int>{work.nodes,view.node_count},{work.pivots,view.node_count},{work.leaves,view.node_count},{work.objects,view.n}}) {
            std::vector<unsigned long long> x(item.second);u10_ck(cudaMemcpy(x.data(),item.first,x.size()*8,cudaMemcpyDeviceToHost));
            sink.write((char*)x.data(),x.size()*8);
        }
        std::vector<int> list(plan.total_leaves),sizes(plan.total_leaves);
        std::vector<Node> hn(view.node_count);
        u10_ck(cudaMemcpy(list.data(),leaf_list,list.size()*4,cudaMemcpyDeviceToHost));
        u10_ck(cudaMemcpy(hn.data(),view.nodes,hn.size()*sizeof(Node),cudaMemcpyDeviceToHost));
        for(size_t i=0;i<sizes.size();i++)sizes[i]=hn[plan.leaves[i]].size;
        sink.write((char*)list.data(),list.size()*4);sink.write((char*)sizes.data(),sizes.size()*4);
        require(bool(sink),"counter dump write failed");
#endif'''

def generate(keeper,out,mode):
    pins=json.loads((HERE/'KEEPER_PINS.json').read_text());meta=json.loads((keeper/'PREPARED.json').read_text())
    assert sha(keeper/'PREPARED.json')==pins['prepared_sha256'] and meta['sources']==pins['sources']
    assert sha(keeper/'bin/target')==pins['binary_sha256']
    for name,h in pins['sources'].items():assert sha(keeper/'source'/name)==h,('keeper drift',name)
    shutil.copytree(keeper/'source',out/'source')
    leaf=out/'source/include/region_output.cuh';bridge=out/'source/include/region_bridge.cuh'
    launch='verify_materialized<<<plan.total_leaves,BLOCK_THREADS>>>(view,leaf_list,radius,hit,distances,work);'
    if mode=='P1':bridge.write_text(replace_once(bridge.read_text(),launch,'verify_materialized<<<plan.total_leaves,32>>>(view,leaf_list,radius,hit,distances,work);'))
    if mode=='P2':
        s=leaf.read_text();start=s.index('__global__ void verify_materialized(');end=s.index('\n// N-sized',start)
        leaf.write_text(s[:start]+PACKED+s[end:])
        bridge.write_text(replace_once(bridge.read_text(),launch,'verify_materialized<<<(plan.total_leaves+2)/3,32>>>(view,leaf_list,plan.total_leaves,radius,hit,distances,work);'))
    sources={str(p.relative_to(out/'source')):sha(p) for p in (out/'source').rglob('*') if p.is_file()}
    changed=[n for n in pins['sources'] if sources[n]!=pins['sources'][n]]
    assert set(changed)==({'include/region_bridge.cuh','include/region_output.cuh'} if mode=='P2' else {'include/region_bridge.cuh'} if mode=='P1' else set())
    save(out/'SOURCE_PINS.json',dict(mode=mode,changed=changed,sources=sources))
    # Diagnostic fork only: same exact increments, bounded binary output, no latency claim.
    shutil.copytree(out/'source',out/'count_source')
    b=out/'count_source/include/region_bridge.cuh';s=b.read_text()
    s,n=re.subn(r'#ifdef REGION_COUNTERS\n        std::cout<<"REGION_PLAN.*?\n#endif','',s,count=1,flags=re.S);assert n==1
    start=s.index('#ifdef REGION_COUNTERS\n        std::cout<<"REGION_WORK');end=s.index('\n#endif',start)+len('\n#endif')
    b.write_text(s[:start]+DUMP+s[end:])
    save(out/'COUNT_PINS.json',{str(p.relative_to(out/'count_source')):sha(p) for p in (out/'count_source').rglob('*') if p.is_file()})

def build(root,nvcc):
    results={}
    for mode in ('P0','P1','P2'):
        out=root/mode;out.mkdir(exist_ok=False);generate(root/'keeper',out,mode)
        records={}
        for kind in ('bench','count','unit'):
            src=out/('count_source' if kind=='count' else 'source');binary=out/kind
            cmd=[nvcc,'-std=c++17','-O3','-arch=sm_120','-lineinfo','-rdc=true','-Xnvlink=--ignore-host-info','--ptxas-options=-v','-I'+str(src/'include')]
            if kind=='count':cmd+=['-DREGION_COUNTERS']
            if kind=='unit':cmd+=['-DFIXED3_MODE='+mode[-1],'-DFIXED3_PARENT="'+str(src/'src/main.cu')+'"',str(HERE/'unit.cu')]
            else:cmd+=[str(src/'src/main.cu')]
            cmd+=['-o',str(binary)]
            log=out/(kind+'.build.log');res=subprocess.run(cmd,capture_output=True,text=True);log.write_text(res.stdout+res.stderr);assert res.returncode==0,log
            resources=out/(kind+'.resources.txt');sass=out/(kind+'.sass.txt')
            resources.write_bytes(subprocess.check_output(['/usr/local/cuda-13.1/bin/cuobjdump','--dump-resource-usage',binary]))
            sass.write_bytes(subprocess.check_output(['/usr/local/cuda-13.1/bin/cuobjdump','--dump-sass',binary]))
            text=resources.read_text();match=re.search(r'Function .*verify_materialized.*\n\s*REG:(\d+) STACK:(\d+) SHARED:(\d+) LOCAL:(\d+)',text)
            assert match,('missing real leaf resource',resources)
            reg,stack,shared,local=map(int,match.groups());assert stack==local==0 and shared<=4864,(mode,kind,match.group(0))
            prop=re.search(r"Function properties for [^\n]*verify_materialized[^\n]*\n[ \t]*(\d+) bytes stack frame, (\d+) bytes spill stores, (\d+) bytes spill loads\nptxas info[ \t]*: Used (\d+) registers, used (\d+) barriers, (\d+) bytes smem",log.read_text())
            assert prop and all(int(prop.group(i))==0 for i in (1,2,3)) and int(prop.group(6))<=3840,('selected leaf stack/spill/shared',mode,kind)
            records[kind]={'command':cmd,'binary_sha256':sha(binary),'build_log_sha256':sha(log),'resources_sha256':sha(resources),'sass_sha256':sha(sass),'leaf':dict(registers=reg,stack=stack,shared=shared,local=local)}
            print('BUILT',mode,kind,records[kind]['leaf'],flush=True)
        results[mode]=records;save(out/'BUILD.json',records)
    save(root/'BUILD_GATE.json',dict(passed=True,modes=results))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--nvcc',default='/usr/local/cuda-13.1/bin/nvcc');a=p.parse_args();build(a.root.resolve(),a.nvcc)
