"""Read-only reuse of the established NSYS interval/correlation parser."""
import argparse,csv,io
from pathlib import Path
from bind import require_closed
from protocol import REPO,VARIANTS,load,save,sha,module
from quality import table
def parse(path,variant):
    legacy=module('frozen_update_timeline',REPO/'artifacts/dynamic_update_critical_path_20261015_recovery_01/timeline.py')
    legacy.PHASES=legacy.PHASES|{'PLAN_BUILD','UPDATE_EXECUTE'};legacy.BOOKKEEPING=legacy.BOOKKEEPING|{'PLAN_BUILD'}
    if variant!='NATIVE':legacy.EXPECTED_PHASES['D']={'DELETE_VALIDATE':1,'PLAN_BUILD':1,'UPDATE_EXECUTE':1}
    def check_api(op,names):
        if op in ('D','I'):assert names.get('cudaStreamSynchronize_v3020')==1,('ACK wait count',op,names)
    legacy.check_update_api=check_api
    legacy.sampled_metrics=lambda *args:dict(status='UNKNOWN',reason='Device-wide sampled metrics not requested;activities and per-kernel counters retained separately')
    result=legacy.parse(path);result['source_sha256']=sha(path)
    result['scope']='Profiled NVTX function scopes,not unprofiled complete Host-return ACK;destructor/ledger boundary caveat applies. Exclusive Host spans are wall spans,not active CPU cycles;device time is overlaid,not added.'
    return result
def bind(trace,updates,ops):
    assert len(trace['ranges'])==len(ops);at=0
    for actual,op in zip(trace['ranges'],ops):
        kind=int(op['kind']);assert actual['operator']==('D','I','Q')[kind]
        if kind==2:continue
        if kind==0:
            row=updates[at];at+=1;copies=int(row['copy_APIs']);kernels=int(row['kernels']);h2d=int(row['metadata']);d2d=int(row['payload']) if kernels==0 else 0
        else:copies=1;kernels=0;h2d=int(op['rows'])*3840;d2d=0
        assert actual['copy_API_calls']==copies and actual['kernels']==actual['launch_API_calls']==kernels and actual['sync_API_calls']==1,('API/kernel binding',actual['index'],actual,row if kind==0 else op)
        assert actual['H2D_activity_bytes']==h2d and actual['D2D_activity_bytes']==d2d and actual['other_copy_activity_bytes']==0,('transfer binding',actual['index'])
    assert at==len(updates);trace['per_ACK_physical_binding']=dict(passed=True,delete_ACKs=at,insert_ACKs=at,query_scopes=160,scope='Chronological APIs,kernels and DMA bytes bound to the validated executor ledger;kernel payload is not memcpy activity or DRAM')
def ncu(path):
    rows=list(csv.reader(io.StringIO(path.read_text())));index=next(i for i,r in enumerate(rows) if 'Metric Name' in r and 'Metric Value' in r);header=rows[index];records=[]
    for r in rows[index+1:]:
        if len(r)!=len(header):continue
        row=dict(zip(header,r))
        if row['Metric Name'] not in ('dram__bytes_read.sum','dram__bytes_write.sum','lts__t_sectors_op_read.sum','lts__t_sectors_op_write.sum'):continue
        value=row['Metric Value'].replace(',','');row['parsed_value']=None if value.lower() in ('n/a','nan','-','') else float(value);records.append(row)
    assert records and len({r['ID'] for r in records})==1 and {r['Metric Name'] for r in records}=={'dram__bytes_read.sum','dram__bytes_write.sum','lts__t_sectors_op_read.sum','lts__t_sectors_op_write.sum'}
    return dict(selected_launches=1,records=records,source_sha256=sha(path),scope='First matching update kernel only,not whole ACK or service;unavailable values null,never zero',whole_service_DRAM='UNKNOWN',whole_service_L2='UNKNOWN')
def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();w=a.work;require_closed(w);assert load(w/'profile/RESULTS.json')['complete'];a.out.mkdir();results={}
    for j in load(w/'REGISTERED.json')['schedule']['profile']:
        label=j['label'];base=w/'profile/reports'/label
        if j['tool']=='nsys':
            result=parse(Path(str(base)+'.sqlite'),j['variant']);prefix=w/'profile/outputs'/label;bind(result,table(str(prefix)+'.updates.csv'),table(str(prefix)+'.ops.csv'));save(a.out/(label+'.json'),result)
            results[label]={k:v for k,v in result.items() if k!='ranges'}
        else:results[label]=ncu(Path(str(base)+'.csv'))
    save(a.out/'SUMMARY.json',dict(passed=True,records=results,scope='Diagnostic attribution,never replacement for primary latency'))
    print('PROFILE_AUDIT_PASS',len(results),'captures',flush=True)
if __name__=='__main__':main()
