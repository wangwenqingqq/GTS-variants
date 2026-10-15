"""Thin transformation of immutable clients;query source and native ownership unchanged."""
from common import BASE,PARENT,module

def replace(t,a,b):
    assert t.count(a)==1,(a,t.count(a));return t.replace(a,b)

def adapter():
    t=module('base_instrumentation',BASE/'generate.py').adapter()
    t=replace(t,'#include <unordered_map>','#include <unordered_map>\n#include <map>\n#include <memory>')
    marker='struct Store {';t=replace(t,marker,'#include "update.cuh"\n\n'+marker)
    t=replace(t,'    int next=0,capacity=0;','    RowMove* update_plan=nullptr;std::vector<PhysicalLedger> physical;\n    int next=0,capacity=0;')
    t=replace(t,'        mutations.reserve(size_t(extra)*2);','''        mutations.reserve(size_t(extra)*2);physical.reserve(32768);
#if UPDATE==2
        alloc(update_plan,512);
#endif''')
    a=t.index('    Cost erase(');b=t.index('    Cost insert(',a);native=t[a:b]
    original=native
    native=replace(native,'        Cost c;','        uint64_t previous_swaps=swapped;Cost c;')
    native=replace(native,'        return c;','''        PhysicalLedger row{};row.kind=0;row.rows=int(ids.size());row.reference_moves=(swapped-previous_swaps)/3840;
        row.copy_APIs=row.reference_moves;row.D2D_bytes=swapped-previous_swaps;row.syncs=1;physical.push_back(row);
        return c;''')
    transformed=replace(original,'        Cost c;','        BatchPlan plan(p.n,int(ids.size()),UPDATE==2);Cost c;')
    transformed=replace(transformed,'ck(cudaMemcpyAsync(p.database+size_t(row)*960,p.database+size_t(last)*960,960*4,cudaMemcpyDeviceToDevice,p.stream));','plan.push(last,row);')
    transformed=replace(transformed,'        ck(cudaStreamSynchronize(p.stream));\n#endif\n        return c;','''        plan.finish(UPDATE==1);{Zone execute("DELETE_EXECUTE");physical.push_back(execute_plan(p.database,p.stream,update_plan,plan,960));}
#endif
        return c;''')
    transformed=replace(transformed,'    Cost erase(const std::vector<int>& ids){','    Cost erase(const std::vector<int>& ids){\n        if(ids.size()==1)return erase_native(ids);')
    t=t[:a]+ '#if UPDATE==0\n'+native+'#else\n'+native.replace('    Cost erase(','    Cost erase_native(')+transformed+'#endif\n'+t[b:]
    a=t.index('    Cost insert(');b=t.index('    void query(',a);insert=t[a:b]
    insert=replace(insert,'        return c;','''        PhysicalLedger record{};record.kind=1;record.rows=count;record.copy_APIs=1;record.H2D_vector_bytes=uint64_t(count)*3840;record.syncs=1;physical.push_back(record);
        return c;''');t=t[:a]+insert+t[b:]
    t=replace(t,'    uint64_t extra_device_bytes()const{return MODE==3?uint64_t(960)*12+512*960*4+512*4:0;}',
        '    uint64_t extra_device_bytes()const{return (MODE==3?uint64_t(960)*12+512*960*4+512*4:0)+(UPDATE==2?512*sizeof(RowMove):0);}')
    t=replace(t,'    void release(){','''    void write_physical(const std::string& out,size_t first=0)const{
        std::ofstream f(out+".physical.csv");f<<"kind,rows,reference_moves,compiled_rows,copy_APIs,launches,H2D_plan_bytes,H2D_vector_bytes,D2D_bytes,kernel_payload_bytes,syncs,levels\\n";
        for(size_t i=first;i<physical.size();i++){auto r=physical[i];f<<r.kind<<','<<r.rows<<','<<r.reference_moves<<','<<r.final_rows<<','<<r.copy_APIs<<','<<r.launches<<','<<r.H2D_plan_bytes<<','<<r.H2D_vector_bytes<<','<<r.D2D_bytes<<','<<r.kernel_payload_bytes<<','<<r.syncs<<','<<r.levels<<'\\n';}require(bool(f),"physical ledger export");
    }
    void release(){
        drop(update_plan);std::vector<PhysicalLedger>().swap(physical);''')
    # Read-only proof helpers are after Store and before either client calls them.
    helpers=(__import__('pathlib').Path(__file__).parent/'validation.cuh').read_text()
    t=replace(t,'static double score(',helpers+'\nstatic double score(')
    t=replace(t,'static void final_proof(Store& s,const std::vector<float>& x,const std::vector<float>& incoming,const std::string& out){','static void final_proof(Store& s,const std::vector<float>& x,const std::vector<float>& incoming,const std::string& out){\n    strict_capacity(s,x,incoming,out);')
    t=replace(t,'    for(int i=0;i<8;i++)request(-1,i,0,false);','    std::unique_ptr<AckOracle> oracle;if(diagnostic==2)oracle=std::make_unique<AckOracle>(s.capacity);\n    for(int i=0;i<8;i++)request(-1,i,0,false);')
    t=replace(t,'ops.push_back({0,phase,-1,replaced,before,s.p.n,count,ms(begin),c.submit,c.tail});','ops.push_back({0,phase,-1,replaced,before,s.p.n,count,ms(begin),c.submit,c.tail});\n            if(oracle)oracle->after(s,x,incoming);')
    t=replace(t,'ops.push_back({1,phase,-1,replaced,before,s.p.n,count,ms(begin),c.submit,c.tail});','ops.push_back({1,phase,-1,replaced,before,s.p.n,count,ms(begin),c.submit,c.tail});\n            if(oracle)oracle->after(s,x,incoming);')
    t=replace(t,'    tick=Clock::now();final_proof(s,x,incoming,out);s.p.write_audit(out);','    tick=Clock::now();s.write_physical(out);if(oracle)oracle->persist(out);final_proof(s,x,incoming,out);s.p.write_audit(out);')
    t=t.replace('swap_D2D_request_bytes','sequential_reference_swap_bytes').replace('extra_statistics_device_bytes','extra_update_workspace_bytes')
    return t

def client():
    t=(BASE/'main.cu').read_text()
    t=t.replace('copy_calls,H2D_bytes,D2D_bytes','sequential_reference_copy_calls,H2D_bytes,sequential_reference_D2D_bytes')
    t=t.replace('s.p.bytes+240;','s.p.bytes+240+s.extra_device_bytes();')
    t=t.replace('formal_D2D_request_bytes','sequential_reference_D2D_bytes').replace('formal_H2D_request_bytes','formal_insert_H2D_bytes')
    t=replace(t,'    for(int i=0;i<8;i++)query(-1,i);','    std::unique_ptr<AckOracle> oracle;if(diag==2){oracle=std::make_unique<AckOracle>(s.capacity);oracle->after(s,x,incoming);}\n    for(int i=0;i<8;i++)query(-1,i);')
    t=replace(t,'uint64_t before_h=s.inserted,before_d=s.swapped;','uint64_t before_h=s.inserted,before_d=s.swapped;size_t physical_begin=s.physical.size();')
    t=replace(t,'double events=ms(event);if(diag==1)ck(cudaProfilerStop());','double events=ms(event);if(diag==1)ck(cudaProfilerStop());')
    # Qualification-only verification is outside each native timer;pair timing is diagnostic-only there.
    t=replace(t,'0,s.swapped-d,1});}','0,s.swapped-d,1});if(oracle)oracle->after(s,x,incoming);}')
    t=replace(t,'uint64_t(batch)*3840,0,1});}','uint64_t(batch)*3840,0,1});if(oracle)oracle->after(s,x,incoming);}')
    t=replace(t,'tick=Clock::now();final_proof(s,x,incoming,out);write_answers(s,answers,out);','tick=Clock::now();s.write_physical(out,physical_begin);if(oracle)oracle->persist(out);final_proof(s,x,incoming,out);write_answers(s,answers,out);')
    t=replace(t,'if(argc==2&&std::string(argv[1])=="--selftest"){selftest();return 0;}','if(argc==2&&std::string(argv[1])=="--selftest"){ownership_selftest();selftest();return 0;}')
    t=replace(t,'#include "adapter.cuh"','#include "adapter.cuh"\n#include "shapes.cuh"')
    t=replace(t,'    micro(argc,argv);return 0;','    if(argc==4&&std::string(argv[1])=="--shape"){shape_benchmark(argv[2],argv[3]);return 0;}\n    micro(argc,argv);return 0;')
    return t

if __name__=='__main__':
    print(len(adapter()),len(client()))
