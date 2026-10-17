"""Reuse the frozen instrumented native Store and all frozen query functions."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python.')
from pathlib import Path
import subprocess,sys,os
HERE=Path(__file__).resolve().parent;REPO=HERE.parent.parent
def replace(t,a,b):assert t.count(a)==1,(a,t.count(a));return t.replace(a,b)
def adapter():
    parent=REPO/'artifacts/dynamic_update_critical_path_20261015_recovery_01'
    script='import sys;sys.path.insert(0,'+repr(str(parent))+');import generate;sys.stdout.write(generate.adapter())'
    t=subprocess.check_output([sys.executable,'-c',script],text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    t=replace(t,'struct Store {','struct NativeStore {')
    t=replace(t,'static double score(','#include "candidate.cuh"\n#include "validation.cuh"\nstatic double score(')
    t=replace(t,'static void final_proof(Store& s,const std::vector<float>& x,const std::vector<float>& incoming,const std::string& out){',
        'static void final_proof(Store& s,const std::vector<float>& x,const std::vector<float>& incoming,const std::string& out){\n    strict_capacity(s,x,incoming,out);')
    t=replace(t,'std::set<int> unique;for(int id:victims)require(id>=0&&id<n&&unique.insert(id).second,"unique original victims");',
        '''// Validate the complete logical schedule,including deletion of fresh occurrences.
    std::vector<bool> live(n+victims.size(),false);std::fill_n(live.begin(),n,true);int cursor=0;
    for(int stop:ends){require(stop>=cursor&&stop<=int(victims.size()),"ordered ends");
        while(cursor<stop){int count=std::min(batch_limit,stop-cursor);std::set<int> unique;
            for(int j=0;j<count;j++){int id=victims[cursor+j];require(id>=0&&id<n+cursor&&live.at(id)&&unique.insert(id).second,"live unique scheduled victims");}
            for(int j=0;j<count;j++)live[victims[cursor+j]]=false;
            for(int j=0;j<count;j++)live[n+cursor+j]=true;cursor+=count;}}
    require(cursor==int(victims.size()),"complete scheduled input");''')
    t=replace(t,'std::min(workload==2?512:1,ends[phase]-replaced)','std::min(workload==2?batch_limit:1,ends[phase]-replaced)')
    t=replace(t,'answers.reserve(168);ops.reserve(2200);',
        'answers.reserve(168);ops.reserve(2*victims.size()/batch_limit+180);std::vector<std::array<double,4>> pairs;pairs.reserve(victims.size()/batch_limit+5);AckOracle oracle(n);')
    t=replace(t,'for(int i=0;i<8;i++)request(-1,i,0,false);','if(diagnostic==2)oracle.after(s,x,incoming);\n    for(int i=0;i<8;i++)request(-1,i,0,false);')
    t=replace(t,'auto begin=Clock::now();int before=s.p.n;Cost c=s.erase(ids);',
        'auto pair_begin=Clock::now();auto begin=Clock::now();int before=s.p.n;Cost c=s.erase(ids);')
    # Qualification callbacks are outside each ACK,never used for primary latency.
    t=replace(t,'ops.push_back({0,phase,-1,replaced,before,s.p.n,count,ms(begin),c.submit,c.tail});',
        'ops.push_back({0,phase,-1,replaced,before,s.p.n,count,ms(begin),c.submit,c.tail});\n            if(diagnostic==2)oracle.after(s,x,incoming);')
    t=replace(t,'ops.push_back({1,phase,-1,replaced,before,s.p.n,count,ms(begin),c.submit,c.tail});',
        'ops.push_back({1,phase,-1,replaced,before,s.p.n,count,ms(begin),c.submit,c.tail});\n            pairs.push_back({double(phase),double(replaced),double(count),ms(pair_begin)});\n            if(diagnostic==2)oracle.after(s,x,incoming);')
    t=replace(t,'tick=Clock::now();final_proof(s,x,incoming,out);s.p.write_audit(out);',
        '''tick=Clock::now();final_proof(s,x,incoming,out);s.write_updates(out);if(diagnostic==2)oracle.persist(out);s.p.write_audit(out);
    std::ofstream pr(out+".pairs.csv");pr<<std::setprecision(17)<<"phase,mutation,rows,ack_ms\\n";for(auto a:pairs)pr<<a[0]<<','<<a[1]<<','<<a[2]<<','<<a[3]<<'\\n';require(bool(pr),"pair export");pr.close();''')
    t=replace(t,'s.release();std::vector<Answer>().swap(answers);std::vector<Op>().swap(ops);',
        's.release();std::vector<Answer>().swap(answers);std::vector<Op>().swap(ops);std::vector<std::array<double,4>>().swap(pairs);')
    t=replace(t,'<<"{\\"mode\\":"<<MODE',
        '<<"{\\"variant\\":\\""<<variants[variant]<<"\\",\\"batch_limit\\":"<<batch_limit<<",\\"trace\\":"<<TRACE<<",\\"mode\\":"<<MODE')
    for a,b in (('swap_D2D_request_bytes','sequential_reference_swap_bytes'),('extra_statistics_device_bytes','extra_update_workspace_bytes'),('device_owned_peak_bytes','known_device_owned_peak_bytes')):t=replace(t,a,b)
    return t
def client():
    return '''#include "adapter.cuh"
#include "bitcheck.cuh"
int main(int argc,char** argv)try{
    require(argc>=3,"VARIANT followed by --selftest or frozen service arguments and B");variant=std::stoi(argv[1]);require(variant>=0&&variant<6,"variant");
    if(argc==3&&std::string(argv[2])=="--selftest"){selftest();bitcheck();return 0;}
    require(argc==11,"VARIANT DATA INPUT_PREFIX QIDS RADIUS OUT WORKLOAD DIAGNOSTIC N B");batch_limit=std::stoi(argv[10]);require(batch_limit>=1&&batch_limit<=512,"batch limit");
    argv[1]=argv[0];return frozen_service_main(argc-2,argv+1);
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\\n';return 1;}
'''
if __name__=='__main__':sys.stdout.write(adapter())
