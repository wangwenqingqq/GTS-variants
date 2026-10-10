#!/usr/bin/env python3
"""CPU-only replay and request-map regressions; no GPU qualification claim."""
import json,subprocess,tempfile,sys
from pathlib import Path
import numpy as np
from pe_trace import replay,warm_events,freeze
from pe_check import check
from qualify import cpu
from pe_costs import collect
from pe_binding import validate_target
from common import outside_repo
HERE=Path(__file__).resolve().parent

def main():
    validate_target(HERE.parent/'unified_target_workflow/phase_b/SHORT_EVENTS.txt')
    rows,final=replay(4,[(0,0),(0,0),(1,4),(1,0),(2,0),(3,1)])
    assert rows==[(0,4,0),(0,5,0),(1,4,-1),(1,0,-1),(2,-1,0),(3,-1,1)]
    assert final.tolist()==[1,2,3,5]
    rows,final=replay(255,warm_events());assert len(rows)==19 and len(final)==264 and 0 not in final
    assert rows[-2:]==[(2,-1,1),(3,-1,1)]
    for ops in ([(1,4)],[(0,4)],[(2,4)]):
        try:replay(4,ops)
        except (AssertionError,IndexError):pass
        else:raise AssertionError('invalid event accepted')
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'truncated.events';path.write_text('2\n2 0\n3 0\n')
        try:validate_target(path)
        except AssertionError:pass
        else:raise AssertionError('truncated target promoted')
    # Insert and delete before any query: output equality alone cannot prove the
    # inserted request vector was frozen correctly. Exercise that boundary too.
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);p=root/'case'
        cpu.validate.case(np.array([[0,0],[1,0],[0,1],[0,0]],np.float32),p,[(0,0),(1,4),(2,0),(3,0)])
        freeze(p/'data.f32bin',p/'events.txt',p/'trace');out=p/'out'
        np.array([0,3,0,3,1,2,-1,-1,-1,-1],'<i4').tofile(str(out)+'.ids.i32')
        values=[0,0,0,0,1,1,np.inf,np.inf,np.inf,np.inf]
        np.array(values,'<f4').tofile(str(out)+'.dist.f32');np.array(values,'<f8').tofile(str(out)+'.native_squared.f64')
        np.arange(4,dtype='<i4').tofile(str(out)+'.final.i32')
        Path(str(out)+'.queries.csv').write_text('step,flag,count,offset\n2,2,2,0\n3,3,8,2\n')
        Path(str(out)+'.ops.csv').write_text('step,flag,n_before,n_after,ack_ms,rebuild_ms\n0,0,4,5,1,0\n1,1,5,4,1,0\n2,2,4,4,1,0\n3,3,4,4,1,0\n')
        assert check(p/'data.f32bin',p/'events.txt',p/'trace',out,'E')['passed']
        vectors=np.fromfile(p/'trace.vectors.f32',dtype='<f4');vectors[0]=123;vectors.tofile(p/'trace.vectors.f32')
        try:check(p/'data.f32bin',p/'events.txt',p/'trace',out,'E')
        except AssertionError as error:assert 'insertion vector' in str(error)
        else:raise AssertionError('incorrect inserted request admitted')
    try:outside_repo(HERE/'must-not-write')
    except (AssertionError,RuntimeError,ValueError):pass
    else:raise AssertionError('repository output admitted')
    for module in ('pe_check','pe_campaign','pe_prepare','pe_trace','pe_results','pe_diagnostic','pe_binding'):
        result=subprocess.run([sys.executable,'-O','-c','import '+module],cwd=HERE,capture_output=True,text=True)
        assert result.returncode!=0 and 'assert' in result.stderr.lower(),module
    c=collect();assert len(c['trace_ms'])==6 and c['radius_upper_calls'].startswith('unknown')
    with tempfile.TemporaryDirectory() as t:
        p=Path(t);src=p/'check.cpp';src.write_text('''#include "pe_common.hpp"
#include <cassert>
int main(){pe::Ranks r;r.init(4,10);assert(r.erase(0)==0);r.insert(4);assert(r.erase(4)==3);r.insert(5);
int expected[]={1,2,3,5};for(int i=0;i<4;i++)assert(r.select(i)==expected[i]);r.release();
pe::Ranks s;s.init(1000,300);std::vector<int> v(1000);for(int i=0;i<1000;i++)v[i]=i;
for(int i=0;i<200;i++){int k=(i*73)%v.size(),id=v[k];assert(s.erase(id)==k);v.erase(v.begin()+k);s.insert(1000+i);v.push_back(1000+i);for(int j=0;j<int(v.size());j++)assert(s.select(j)==v[j]);}
assert(s.final()==v);}
''')
        subprocess.run(['c++','-std=c++17','-O2','-I'+str(HERE),str(src),'-o',str(p/'check')],check=True);subprocess.run([str(p/'check')],check=True)
    print('PASS replay duplicates/deleted coordinates/rebuilds, invalid events, rank insertion/deletion/select, existing cost accounting, frozen insertion bytes, full-output padding, truncated trace/private-output/-O rejection')

if __name__=='__main__':main()
