#!/usr/bin/env python3
"""Generate a capacity-scaled driver from the frozen single-query experiment."""
import argparse, hashlib, json, shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
PIN='6065bd4b9f2de6cb231ca416afeea55dce395f5d2713c37aae1c79c0a60ee3a5'


def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)


def transform(s):
    assert hashlib.sha256(s.encode()).hexdigest()==PIN
    s=s[:s.index('int main(int argc,char** argv)')]
    s=once(s,'const int nodes=111, slots=2220;','const int nodes, slots, bundle;')
    s=once(s,'Fixed(int count_n,int h):n(count_n),height(h)',
           'Fixed(int count_n,int h,int b):nodes(*max_node_num),slots(nodes*MAX_SIZE),bundle(b),n(count_n),height(h)')
    s=once(s,'ck(cudaMemset(outdis,0,slots*sizeof(float)));',
           'ck(cudaMemset(outdis,0,slots*sizeof(float)));ck(cudaDeviceSynchronize());')
    for a,b in [('cudaMallocHost(&hq,sizeof(int))','cudaMallocHost(&hq,bundle*sizeof(int))'),
                ('cudaMallocHost(&hc,sizeof(int))','cudaMallocHost(&hc,bundle*sizeof(int))'),
                ('cudaMallocHost(&hi,slots*sizeof(int))','cudaMallocHost(&hi,size_t(bundle)*slots*sizeof(int))'),
                ('cudaMallocHost(&hd,slots*sizeof(float))','cudaMallocHost(&hd,size_t(bundle)*slots*sizeof(float))'),
                ('void enqueue(float radius)','void enqueue(float radius,int j)'),
                ('cudaMemcpyAsync(qid,hq,','cudaMemcpyAsync(qid,hq+j,'),
                ('initQnode<<<1,THREAD_NUM,0,stream>>>','initQnode<<<(nodes+511)/512,THREAD_NUM,0,stream>>>'),
                ('mergeLeafNode<<<1,512,0,stream>>>','mergeLeafNode<<<(nodes+511)/512,512,0,stream>>>'),
                ('cudaMemcpyAsync(hc,count,','cudaMemcpyAsync(hc+j,count,'),
                ('cudaMemcpyAsync(hi,outids,','cudaMemcpyAsync(hi+size_t(j)*slots,outids,'),
                ('cudaMemcpyAsync(hd,outdis,','cudaMemcpyAsync(hd+size_t(j)*slots,outdis,'),
                ('enqueue(radius);','for(int j=0;j<bundle;++j)enqueue(radius,j);'),
                ('void query(int q,float radius,bool replay)','void query(const int* qs,float radius,bool replay)'),
                ('*hq=q;','std::copy(qs,qs+bundle,hq);'),
                ('else enqueue(radius);','else for(int j=0;j<bundle;++j)enqueue(radius,j);'),
                ('if(*hc<0 || *hc>slots)','if(std::any_of(hc,hc+bundle,[&](int x){return x<0||x>slots;}))'),
                ('count<=2220','count<=int(ids.size())')]:
        # The capture and stream paths share the only enqueue implementation.
        if a=='enqueue(radius);':
            s=once(s,'cudaStreamCaptureModeGlobal));enqueue(radius);','cudaStreamCaptureModeGlobal));'+b)
        else:s=once(s,a,b)
    return s+(HERE/'main.inc').read_text()


def runner(s):
    s=once(s,'tool,dump):','tool,dump,bundle=1,qids="queries.qid"):')
    s=s.replace('fixtures/words_2000.txt','fixtures/data.txt').replace("root/'fixtures/queries.qid'","root/'fixtures'/qids")
    s=once(s,"'CUDA_VISIBLE_DEVICES':gpu","'CUDA_VISIBLE_DEVICES':gpu,'GTS_BUNDLE':str(bundle)")
    s=once(s,"limit=120 if tool=='clean' or tool.startswith('nsys') else 600","limit=300 if tool=='clean' or tool.startswith('nsys') else 1800")
    s=s.replace('nextcheck=start+1','nextcheck=start+.2').replace('nextcheck=time.monotonic()+1','nextcheck=time.monotonic()+.2').replace('time.sleep(.1)','time.sleep(.02)')
    s=once(s,"'error:' in x.lower()","'==ERROR==' in x or 'error:' in x.lower()")
    s=once(s,"ok=len(rows)==repeats*64 and all(","qs=list(map(int,(root/'fixtures'/qids).read_text().split()))[1:]\n        ok=[int(r['qid']) for r in rows]==qs*repeats and all(")
    s=once(s,"record={'label':label","record={'bundle':bundle,'input_sha256':{n:hashlib.sha256((root/'fixtures'/n).read_bytes()).hexdigest() for n in ['data.txt',qids]},'label':label")
    return s


def prepare(source,out):
    out.mkdir()
    for name in ['bin','logs','runs','cases','fixtures']:(out/name).mkdir()
    pins=json.loads((HERE.parent/'original_tree_redundancy/SOURCE_PINS.json').read_text())['sha256']
    pins={n:h for n,h in pins.items() if n.startswith('GTS/')}
    for n,h in pins.items():
        p=source/n;assert hashlib.sha256(p.read_bytes()).hexdigest()==h,n
        dest=out/'source'/n.removeprefix('GTS/');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    (out/'graph_bench.cu').write_text(transform((HERE.parent/'graph_query_20260923/graph_bench.cu').read_text()))
    (out/'run_scale.py').write_text(runner((HERE.parent/'graph_query_20260923/run.py').read_text()))
    (out/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    for n in ['oracle.cpp','fixtures.py','check.py','suite.py']:shutil.copy2(HERE/n,out/n)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();prepare(a.source,a.out)
