"""Generate one minimal zone-order adapter against the preserved P1 harness."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import difflib
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'pdx_bond_gpu_realizability_gate4_20261015'
def load(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x') as f: json.dump(v,f,indent=2);f.write('\n')
def replace(s,a,b,count=1):
    assert s.count(a)==count,(a,s.count(a),count)
    return s.replace(a,b)


def headers(repo):
    base=(repo/'artifacts/progressive_gpu_gate2_20261013/progressive.cuh').read_text()
    # Qualification-only authority export; primary/NCU modes never take this branch.
    base=replace(base,'std::string audit_prefix;', 'std::vector<double> last_scores;\n    std::string audit_prefix;')
    at='outputs.push_back({double(invocation),field_ms,final_wall});++invocation;'
    export='''if(audit_mode==2||audit_mode==4){
            std::vector<PrefixState> state(active);last_scores.clear();
            if(active)ck(cudaMemcpy(state.data(),active_state,size_t(active)*16,cudaMemcpyDeviceToHost));
            for(auto& value:state)last_scores.push_back(value.sum);
            if(audit_mode==2){std::ofstream f(audit_prefix+".authority."+std::to_string(invocation)+".f64",std::ios::binary);
                f.write((char*)last_scores.data(),last_scores.size()*8);if(!f)throw std::runtime_error("authority export");}
        }
        '''+at
    keeper=replace(base,at,export)
    host=(PRIOR/'pdx.cpp').read_text().split('extern "C" int pdx_zone_order',1)[1].split('extern "C" int validate_ordered_scores',1)[0]
    host='static int pdx_zone_order'+host
    helper='''__device__ double ordered_subset(const float* x,const float* q,int row,int end,const int* inverse){
    double sum=0;
    for(int j=0;j<960;j++)if(inverse[j/32]<end/32){
        double delta=__dsub_rn(double(x[size_t(row)*960+j]),double(q[j]));
        sum=__dadd_rn(sum,__dmul_rn(delta,delta));
    }
    return sum;
}
'''
    candidate=replace(keeper,'template<int START,int END>',host+'\n'+helper+'template<int START,int END>')
    candidate=replace(candidate,'const float* x,const float* q,const PrefixState* input,','const float* x,const float* q,const int* order,const int* inverse,const PrefixState* input,')
    candidate=replace(candidate,'float delta=__fsub_rn(x[size_t(owner)*960+j],q[j]);','int coordinate=order[j/32]*32+j%32;\n        float delta=__fsub_rn(x[size_t(owner)*960+coordinate],q[coordinate]);')
    candidate=replace(candidate,'sum=ordered_prefix(x,q,owner,END);','sum=ordered_subset(x,q,owner,END,inverse);')
    candidate=replace(candidate,'int n=0,d=960,','std::array<float,960> means{};int *order=nullptr,*inverse=nullptr;\n    std::vector<std::array<double,3>> ordering;\n    int n=0,d=960,')
    candidate=replace(candidate,'n=rows;d=dim;ck(cudaStreamCreate(&stream));','''n=rows;d=dim;ck(cudaStreamCreate(&stream));
        const char* p=std::getenv("PDX_MEANS");if(!p)throw std::runtime_error("mean input");
        std::ifstream m(p,std::ios::binary);m.read((char*)means.data(),3840);
        if(!m||m.peek()!=EOF)throw std::runtime_error("mean length");
        for(float v:means)if(!std::isfinite(v))throw std::runtime_error("finite mean");
        alloc(order,30);alloc(inverse,30);''')
    candidate=replace(candidate,'ck(cudaMemcpyAsync(query,q,960*4,cudaMemcpyHostToDevice,stream));','''auto order_start=Clock::now();int dims[960],zones[30],inverse_host[30],tie;float ranks[30];
        if(pdx_zone_order(q,means.data(),dims,ranks,zones,&tie))throw std::runtime_error("zone priority");
        for(int i=0;i<30;i++)inverse_host[zones[i]]=i;
        double priority_ms=ms(order_start);order_start=Clock::now();
        ck(cudaMemcpyAsync(order,zones,120,cudaMemcpyHostToDevice,stream));
        ck(cudaMemcpyAsync(inverse,inverse_host,120,cudaMemcpyHostToDevice,stream));
        ordering.push_back({double(invocation),priority_ms,ms(order_start)});
        ck(cudaMemcpyAsync(query,q,960*4,cudaMemcpyHostToDevice,stream));''')
    candidate=replace(candidate,'>(database,query,','>(database,query,order,inverse,',4)
    candidate=replace(candidate,'void release(){drop(database);','void release(){drop(order);drop(inverse);drop(database);')
    candidate=replace(candidate,'if(!f||!o)throw std::runtime_error("P1 audit persistence");','''std::ofstream rank(prefix+".ordering.csv");rank<<"invocation,priority_ms,order_submit_ms\\n"<<std::setprecision(17);
        for(auto& x:ordering)rank<<x[0]<<','<<x[1]<<','<<x[2]<<'\\n';
        if(!f||!o||!rank)throw std::runtime_error("P1 audit persistence");''')
    candidate='#include <numeric>\n#include <cfenv>\n#include <cstdlib>\n'+candidate
    fixture=(repo/'artifacts/progressive_gpu_gate2_20261013/fixtures.hpp').read_text()
    fixture=replace(fixture,'for(int s=0;s<4;s++)if(n>5+s)data[size_t(5+s)*960+(s==0?127:s==1?255:s==2?511:959)]=2.f;',
        '''int order[960],zones[30],tie;float ranks[30],means[960]{};
        if(pdx_zone_order(q.data(),means,order,ranks,zones,&tie))throw std::runtime_error("fixture order");
        for(int s=0;s<4;s++)if(n>5+s)data[size_t(5+s)*960+order[(s==0?128:s==1?256:s==2?512:960)-1]]=2.f;''')
    a=fixture.index('        for(int r=0;r<n;r++){');b=fixture.index('        ProgressiveScan slots',a)
    expected='''        int inverse[960];for(int j=0;j<960;j++)inverse[order[j]]=j;
        for(int r=0;r<n;r++){
            double sum=0;double terms[960];bool active=true;
            for(int j=0;j<960;j++){double delta=double(data[size_t(r)*960+j])-double(q[j]);
                terms[j]=delta*delta;sum=sum+terms[j];}
            scores[r]=sum;if(sum==double(radius)*radius)++boundary;
            for(int stage=0;stage<4;stage++){
                double prefix=0;for(int j=0;j<960;j++)if(inverse[j]<ends[stage])prefix=prefix+terms[j];
                if(prefix<=double(radius)*radius)expected[stage].push_back(r);
                else if(active){++rejected[stage];active=false;}
            }
        }
'''
    fixture=fixture[:a]+expected+fixture[b:]
    fixture=replace(fixture,'s.build(data,n,960);s.audit_mode=4;','s.build(data,n,960);s.means.fill(0);s.audit_mode=4;')
    fixture=replace(fixture,'double target=scores[ids[i]];float score=float(target);','double target=scores[ids[i]];float score=float(target);\n                if(s.last_scores[i]!=target)throw std::runtime_error("fixture FP64 authority");')
    return keeper,candidate,fixture


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--parent',type=Path,required=True)
    p.add_argument('--cpu',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--gpu',required=True)
    a=p.parse_args();contract=load(HERE/'GPU_CONTRACT.json');old=load(a.parent/'REGISTERED.json')
    assert all(sha(a.repo/n)==h for n,h in contract['parents'].items())
    assert load(a.cpu/'RESULTS.json')['complete'] and sha(a.cpu/'RESULTS.json')==contract['cpu_results_sha256']
    assert sha(a.cpu/'raw/global_means.f32')==contract['global_means_sha256']
    assert sha(old['data'])==contract['data_sha256'] and old['q32']==contract['qids']
    for n,h in old['reference_hashes'].items():assert sha(Path(old['reference'])/n)==h
    # Import all preserved guards/validators without initializing CUDA.
    preflight=subprocess.check_output([sys.executable,'-c','import static_guard; assert callable(static_guard.snapshot); assert callable(static_guard.outside_repo)'],cwd=a.repo/'artifacts/external_closure',env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'},text=True)
    original=a.parent/'build/candidate';assert sha(original)==load(a.parent/'READY.json')['binaries']['candidate']
    assert not subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    w=a.work.resolve();assert not w.exists();w.mkdir();(w/'build').mkdir()
    (w/'pool32.txt').write_text('\n'.join(map(str,old['q32']))+'\n')
    save(w/'GPU_PARENT.json',old)
    keeper,candidate,fixture=headers(a.repo)
    (w/'build/keeper.cuh').write_text(keeper);(w/'build/candidate.cuh').write_text(candidate)
    (w/'build/bond_fixtures.hpp').write_text(fixture)
    original_source=(a.parent/'build/candidate.cu').read_text()
    import re
    paths=re.findall(r'#include "([^"]+/artifacts/progressive_gpu_gate2_20261013/progressive.cuh)"',original_source)
    assert len(paths)==1,'exact legacy source root'
    previous_repo=Path(paths[0]).parents[2]
    original_source=original_source.replace(str(previous_repo)+'/artifacts/',str(a.repo)+'/artifacts/')
    for name,header in [('keeper','keeper'),('candidate','candidate')]:
        src=replace(original_source,str(a.repo/'artifacts/progressive_gpu_gate2_20261013/progressive.cuh'),str(w/'build'/f'{header}.cuh'))
        if name=='candidate':src=replace(src,str(a.repo/'artifacts/progressive_gpu_gate2_20261013/fixtures.hpp'),str(w/'build/bond_fixtures.hpp'))
        (w/'build'/f'{name}.cu').write_text(src)
    (w/'build/ADAPTER_DIFF.patch').write_text(''.join(difflib.unified_diff(keeper.splitlines(True),candidate.splitlines(True),fromfile='keeper.cuh',tofile='candidate.cuh')))
    env={**old['environment'],'PDX_MEANS':str(a.cpu/'raw/global_means.f32'),'CUDA_VISIBLE_DEVICES':a.gpu}
    inputs={str(p):sha(p) for p in [HERE/'GPU_CONTRACT.json',HERE/'RECOVERY.json',PRIOR/'GPU_DESIGN.md',HERE/'gpu_prepare.py',HERE/'gpu_campaign.py',PRIOR/'pdx.cpp']}
    sources={str(p):sha(p) for p in (w/'build').iterdir() if p.is_file()}
    command=old['commands']['candidate']
    save(w/'REGISTERED.json',{'before_GPU':True,'dependency_preflight_passed':True,'preflight_stdout':preflight,'gpu':a.gpu,'numa':old['numa'],'environment':env,'parent_registration_sha256':sha(a.parent/'REGISTERED.json'),
        'parent':str(a.parent),'repo':str(a.repo),'cpu':str(a.cpu),'input_sources':inputs,'generated_sources':sources,'data':old['data'],
        'q32':old['q32'],'radius':old['radius'],'reference':old['reference'],'reference_hashes':old['reference_hashes'],'command_template':command})
    binaries={}
    for name in ('keeper','candidate'):
        cmd=[str(w/'build'/f'{name}.cu') if v==str(a.parent/'build/candidate.cu') else str(w/'build'/name) if v==str(original) else v for v in command]
        with (w/'build'/f'{name}.compile.log').open('x') as log:subprocess.run(cmd,env={**os.environ,**env},stdout=log,stderr=log,check=True)
        output=subprocess.check_output(['ldd',str(w/'build'/name)],env={**os.environ,**env},text=True);assert 'not found' not in output
        libs={}
        for row in output.splitlines():
            v=row.split()
            if '=>' in v and len(v)>2 and v[2].startswith('/'):libs[v[0]]={'sha256':sha(v[2])}
        assert libs==old['libraries'],'linked-library drift'
        binaries[name]=sha(w/'build'/name)
    save(w/'READY.json',{'passed':True,'registration_sha256':sha(w/'REGISTERED.json'),'binaries':binaries,'libraries':old['libraries']})
    print('BUILT one PDX adapter and same-source keeper;0 GPU starts',flush=True)


if __name__=='__main__':main()
