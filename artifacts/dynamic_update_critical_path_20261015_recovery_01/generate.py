"""Exact textual instrumentation of the immutable Store, never a storage rewrite."""
from common import PARENT


def replace(text, old, new):
    assert text.count(old) == 1, (old, text.count(old)); return text.replace(old, new)


def adapter():
    text = (PARENT/'service.cu').read_text()
    zone = '''
#include <nvtx3/nvToolsExt.h>
#ifndef TRACE
#error Explicit TRACE required
#endif
struct Zone {
#if TRACE
    bool active=true;
#endif
    explicit Zone(const char* name){
#if TRACE
        nvtxRangePushA(name);
#else
        (void)name;
#endif
    }
    void close(){
#if TRACE
        if(active){nvtxRangePop();active=false;}
#endif
    }
    ~Zone(){close();}
};
'''
    text = replace(text, '#include <unordered_map>', '#include <unordered_map>\n'+zone)
    text = replace(text, 'int main(int argc,char** argv)try{', 'int frozen_service_main(int argc,char** argv)try{')
    text = replace(text, 'Cost erase(const std::vector<int>& ids){', 'Cost erase(const std::vector<int>& ids){\n        Zone operation("U_DELETE");')
    text = replace(text, 'std::set<int> unique;for(int id:ids)require(id>=0&&id<next&&position.at(id)>=0&&unique.insert(id).second,"live unique delete IDs");',
        'Zone validate("DELETE_VALIDATE");std::set<int> unique;for(int id:ids)require(id>=0&&id<next&&position.at(id)>=0&&unique.insert(id).second,"live unique delete IDs");validate.close();')
    text = replace(text, 'for(int id:ids){int row=position[id]', '{Zone owners("DELETE_ROWS");for(int id:ids){int row=position[id]')
    text = replace(text, 'if(moved>=0)require(occurrence[row]==moved&&position[moved]==row,"swap local owner");\n        }',
        'if(moved>=0)require(occurrence[row]==moved&&position[moved]==row,"swap local owner");\n        }}')
    text = replace(text, 'Cost insert(const float* values,int count){', 'Cost insert(const float* values,int count){\n        Zone operation("U_INSERT");')
    text = replace(text, 'int start=p.n;ck(cudaMemcpyAsync(p.database+size_t(start)*960,values,size_t(count)*960*4,cudaMemcpyHostToDevice,p.stream));',
        'int start=p.n;{Zone submit("INSERT_SUBMIT");ck(cudaMemcpyAsync(p.database+size_t(start)*960,values,size_t(count)*960*4,cudaMemcpyHostToDevice,p.stream));}')
    text = replace(text, 'for(int k=0;k<count;k++){\n            int id=next;', '{Zone owners("INSERT_OWNERS");for(int k=0;k<count;k++){\n            int id=next;')
    text = replace(text, 'require(occurrence.back()==id&&position[id]==p.n-1,"insert local owner");\n        }',
        'require(occurrence.back()==id&&position[id]==p.n-1,"insert local owner");\n        }}')
    text = replace(text, 'void query(const float* q,float radius,Answer& a){', 'void query(const float* q,float radius,Answer& a){\n        Zone operation("Q");')
    # The new marked legacy diagnostic captures one complete formal interval.
    text = replace(text, 'getrusage(RUSAGE_SELF,&cpu_before);auto service=Clock::now();int replaced=0;',
        'getrusage(RUSAGE_SELF,&cpu_before);if(diagnostic==3)ck(cudaProfilerStart());auto service=Clock::now();int replaced=0;')
    text = replace(text, 'if(diagnostic==3)ck(cudaProfilerStart());\n            auto begin', 'auto begin')
    text = replace(text, 'if(diagnostic==3)ck(cudaProfilerStop());\n            if(interleaved)', 'if(interleaved)')
    text = replace(text, 'double events=ms(service);getrusage(RUSAGE_SELF,&cpu_after);', 'double events=ms(service);if(diagnostic==3)ck(cudaProfilerStop());getrusage(RUSAGE_SELF,&cpu_after);')
    return text
