"""CPU-only source transform, workload, independent replay and negative regression."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import copy
import ctypes
import json
import os
import signal
import subprocess
import sys
import time
import numpy as np
from pathlib import Path
from common import HERE, PARENT, jobs, save
from generate import adapter
from analyze import check
from quality import distance_fields, operator_group


def guard_cleanup(out):
    # Exercise only dummy CPU processes: the observer must not outlive SIGINT.
    monitor=out/'dummy_monitor.py';monitor.write_text('import sys,time,signal\nsignal.signal(signal.SIGINT,signal.SIG_IGN)\nwith open(sys.argv[1],"w") as f:\n while True:f.write("x");f.flush();time.sleep(.02)\n')
    guard=out/'dummy_guard.py';guard.write_text('''import subprocess,sys,time,json
from pathlib import Path
p=subprocess.Popen([sys.executable,sys.argv[1],sys.argv[2]])
Path(sys.argv[3]).write_text(json.dumps(dict(monitor=p.pid)))
try:
 while True:time.sleep(1)
finally:
 time.sleep(.2)
 p.terminate();p.wait(timeout=5)
''')
    driver=out/'dummy_controller.py';driver.write_text(f'''import os,sys
sys.path.insert(0,{str(HERE)!r})
from campaign import run_guard
try:
 with open(sys.argv[1],"w") as out:run_guard(sys.argv[2:],os.environ.copy(),out)
except KeyboardInterrupt:raise SystemExit(130)
''')
    for group in (False,True):
        ready=out/f'dummy_ready_{int(group)}.json';log=out/f'dummy_observer_{int(group)}.log';outer=out/f'dummy_outer_{int(group)}.log'
        p=subprocess.Popen([sys.executable,str(driver),str(outer),sys.executable,str(guard),str(monitor),str(log),str(ready)],start_new_session=True)
        try:
            deadline=time.monotonic()+10
            while not ready.exists():
                assert p.poll() is None and time.monotonic()<deadline;time.sleep(.02)
            while not log.exists() or log.stat().st_size==0:
                assert p.poll() is None and time.monotonic()<deadline;time.sleep(.02)
            observer=json.loads(ready.read_text())['monitor']
            if group:os.killpg(p.pid,signal.SIGINT)
            else:p.send_signal(signal.SIGINT)
            assert p.wait(timeout=15)==130
            try:os.kill(observer,0)
            except ProcessLookupError:pass
            else:raise AssertionError('Owned dummy observer survived controller interruption')
            before=log.stat().st_size;time.sleep(.1);assert log.stat().st_size==before
        finally:
            if p.poll() is None:p.send_signal(signal.SIGINT);p.wait(timeout=15)


def source_lifetime(out):
    source=adapter();erase=source[source.index('    Cost erase('):source.index('    Cost insert(')]
    native=(PARENT/'service.cu').read_text();native=native[native.index('    Cost erase('):native.index('    Cost insert(')]
    stripped=erase.replace('\n        Zone operation("U_DELETE");','').replace('Zone validate("DELETE_VALIDATE");','').replace('validate.close();','')
    stripped=stripped.replace('{Zone owners("DELETE_ROWS");for(int id:ids){','for(int id:ids){').replace('\n        }}','\n        }')
    assert stripped==native, 'Deleting annotation tokens must recover the exact native erase body'
    zone=source[source.index('struct Zone {'):].split('};',1)[0]+'};'
    mock=r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <set>
#include <string>
#include <vector>
static std::vector<std::string> events,stack;
static void nvtxRangePushA(const char* name){events.push_back(std::string("push:")+name);stack.push_back(name);}
static void nvtxRangePop(){assert(!stack.empty());events.push_back("pop:"+stack.back());stack.pop_back();}
static void require(bool value,const char*){assert(value);}
static void ck(int value){assert(!value);}
static int cudaMemcpyAsync(void*,const void*,size_t,int,int){events.push_back("copy");return 0;}
static int cudaStreamSynchronize(int){events.push_back("sync");return 0;}
constexpr int cudaMemcpyDeviceToDevice=0;
struct AuditSet {std::set<int> values;auto insert(int id){return values.insert(id);}~AuditSet(){events.push_back("unique_destroy");}};
struct Cost {double submit=0,tail=0;};
struct Mutation {int kind,id,n,row,last,moved,next,after;};
'''+zone+r'''
struct Store {
    struct Plan {float buffer[3*960]{};float* database=buffer;int n=3,stream=0;}p;
    int next=3;std::vector<int> occurrence{0,1,2},position{0,1,2};std::vector<Mutation> mutations;uint64_t swapped=0;
'''+erase.replace('std::set<int> unique','AuditSet unique')+r'''
};
int main(){Store s;s.erase(std::vector<int>{0,2});
    auto sync=std::find(events.begin(),events.end(),"sync"),destroy=std::find(events.begin(),events.end(),"unique_destroy");
    assert(sync!=events.end()&&destroy!=events.end()&&sync<destroy);
    assert(std::count(events.begin(),events.end(),"copy")==2&&s.p.n==1&&s.mutations.size()==2);
#if TRACE
    auto close=std::find(events.begin(),events.end(),"pop:U_DELETE");assert(close!=events.end()&&destroy<close&&stack.empty());
#endif
}
'''
    (out/'lifetime.cpp').write_text(mock)
    for trace in (0,1):
        binary=out/f'lifetime_{trace}'
        subprocess.run(['g++','-std=c++17','-O2','-DMODE=2',f'-DTRACE={trace}',str(out/'lifetime.cpp'),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)


def negative_accounting():
    def rejects(fn):
        try:fn()
        except AssertionError:return
        raise AssertionError('Corrupted fixture was accepted')
    distance_fields(np.array([0.,1.]),np.array([0.,1.]))
    for d,s in (([-1.],[1.]),([1.],[-1.]),([np.nan],[1.]),([1.],[np.inf])):
        rejects(lambda:distance_fields(np.array(d),np.array(s)))
    fields=('sample','kind','rows','ack_ms','delete_ms','insert_ms','copy_calls','H2D_bytes','D2D_bytes','sync_calls')
    rows=[dict(zip(fields,v)) for v in ((0,0,32,3.,3.,0.,20,0,20*3840,1),(0,1,32,2.,0.,2.,1,32*3840,0,1),(0,2,32,5.1,3.,2.,21,32*3840,20*3840,2))]
    assert operator_group(rows,2,0,32)==rows[:2]
    for row,field,value in ((2,'delete_ms',1.),(2,'insert_ms',1.),(0,'delete_ms',1.),(1,'insert_ms',1.),(0,'insert_ms',1.),(1,'delete_ms',1.),(2,'D2D_bytes',19*3840),(2,'copy_calls',20),(0,'D2D_bytes',-3840),(2,'sync_calls',1)):
        bad=copy.deepcopy(rows);bad[row][field]=value
        if field=='D2D_bytes':bad[row]['copy_calls']=value//3840+int(row!=0)
        rejects(lambda:operator_group(bad,2,0,32))
    return 14


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    assert [len(jobs(s)) for s in ('qualification','primary','timeline')]==[29,84,11]
    assert 'gather_deleted<<<' in adapter() and adapter().count('Zone operation("U_DELETE")')==1
    source_lifetime(a.out);negative_checks=negative_accounting();guard_cleanup(a.out.resolve())
    subprocess.run(['g++','-std=c++17','-O2','-shared','-fPIC',str(HERE/'oracle.cpp'),'-o',str(a.out/'replay.so')],check=True)
    f=ctypes.CDLL(str(a.out/'replay.so')).replay
    f.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p];f.restype=ctypes.c_int
    total=0
    for n,k in ((65,32),(513,256),(4096,2048)):
        for b in (1,32,512):
            for op in (0,1,2):
                victims=np.random.default_rng(2026101501).permutation(n)[:k].astype('<i4');forward=list(range(n));reverse=list(range(n))+[-1]*k;records=[];next_id=n
                def erase(start,count):
                    for id in victims[start:start+count]:
                        id=int(id);size=len(forward);row=reverse[id];last=size-1;moved=forward[-1] if row!=last else -1
                        records.append([0,id,size,row,last,moved,next_id,size-1])
                        if row!=last:forward[row]=moved;reverse[moved]=row
                        forward.pop();reverse[id]=-1
                def insert(count):
                    nonlocal next_id
                    for _ in range(count):
                        size=len(forward);records.append([1,next_id,size,size,-1,-1,next_id+1,size+1]);forward.append(next_id);reverse[next_id]=size;next_id+=1
                if op==0:erase(0,k)
                for start in range(0,k,b):
                    count=min(b,k-start)
                    if op!=0:erase(start,count)
                    if op!=1:insert(count)
                witness=np.array(records,'<i4');physical=np.array(forward,'<i4');positions=np.array(reverse,'<i4');swaps=np.zeros(1,'<u8')
                run=lambda:f(n,victims.ctypes.data,k,b,op,witness.ctypes.data,len(witness),physical.ctypes.data,len(physical),positions.ctypes.data,swaps.ctypes.data)
                assert run()==0;witness[0,1]=-1;assert run()!=0;total+=1
    check();save(a.out/'RECEIPT.json',dict(passed=True,cases=total,negative_mutation_tests=total,negative_field_accounting_tests=negative_checks,
        source_transform=True,native_delete_body_roundtrip=True,unique_destruction_after_sync_both_TRACE=True,owned_guard_observer_cleanup=True,PID_and_process_group_SIGINT=True,GPU_starts=0))
    print('PASS:27 replay cases,27 negative witnesses,14 field/accounting negatives,native-source roundtrip,2 lifetime checks andCPU guard cleanup;124 bounded jobs;0 GPU starts')


if __name__=='__main__':main()
