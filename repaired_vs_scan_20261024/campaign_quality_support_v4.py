"""Locked, monitored, append-only GPU epochs; never mix restarted campaigns."""
import csv,datetime,fcntl,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path

THREE=('ARS','SRA','RAS','SAR','ASR','RSA')
FOUR=('ARSX','XSRA','RAXS','SXAR','ASRX','XRSA')
ELIGIBLE=(5,4,6,7,0,1)
class Contaminated(RuntimeError):pass

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def snapshot(index):
    def q(field):return subprocess.check_output(['nvidia-smi','-i',str(index),field,'--format=csv,noheader,nounits'],text=True,timeout=10)
    gpu=q('--query-gpu=uuid,name,driver_version,memory.used,utilization.gpu,pstate,power.draw,clocks.current.graphics,clocks.current.memory')
    apps=q('--query-compute-apps=pid,process_name,used_memory');row=[x.strip() for x in next(csv.reader([gpu.strip()]))]
    return {'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'index':index,'uuid':row[0],'gpu':gpu,'apps':apps,'idle':not apps.strip() and int(row[3])<=256 and int(row[4])==0}
class IdentityUnavailable(RuntimeError):pass

def proc_identity(pid):
    try:
        text=Path(f'/proc/{pid}/stat').read_text();fields=text[text.rfind(')')+2:].split()
        return int(fields[1]),int(fields[19])
    except OSError as error:
        if error.errno not in (2,3):raise IdentityUnavailable('unreadable process identity') from error
        try:fd=os.pidfd_open(pid,0)
        except ProcessLookupError:return None
        except (OSError,AttributeError) as missing:raise IdentityUnavailable('cannot establish process absence') from missing
        else:os.close(fd);raise IdentityUnavailable('live PID without readable identity')
    except (ValueError,IndexError) as error:raise IdentityUnavailable('malformed process identity') from error

def owned_pid(pid,group,known):
    current=proc_identity(pid)
    if pid in known:
        if current is None:return True
        if known[pid] is not None:return current[1]==known[pid]
    cursor=pid;born=current[1] if current else None
    for _ in range(64):
        identity=proc_identity(cursor)
        if identity is None:return False
        if cursor in known and known[cursor] is not None:
            if identity[1]!=known[cursor]:return False
            known[pid]=born;return True
        if identity[0]<=1:return False
        cursor=identity[0]
    return False

def foreign_apps(state,group,known):
    bad=[]
    for row in csv.reader(state['apps'].splitlines()):
        if not row:continue
        try:owned=owned_pid(int(row[0].strip()),group,known)
        except (ValueError,IdentityUnavailable):owned=False
        if not owned:bad.append(row)
    return bad

def stable_idle(index,seconds=20,group=None,known=None):
    history=[];deadline=time.monotonic()+seconds;stable=0
    while True:
        state=snapshot(index);history.append(state)
        if state['apps'].strip() and (known is None or foreign_apps(state,group,known)):return state,history
        stable=stable+1 if state['idle'] else 0
        if stable>=3 or time.monotonic()>=deadline:return state,history
        time.sleep(.5)

def acquire(root):
    while True:
        for index in ELIGIBLE:
            handle=None
            try:
                handle=open(f'/tmp/gtspp_gpu{index}.lock','r');fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                state=snapshot(index)
                if state['idle']:return index,state,handle
            except (OSError,subprocess.SubprocessError,ValueError,IndexError):pass
            if handle:handle.close()
        print('WAIT no admissible idle card; no foreign processes signaled',flush=True);time.sleep(20)

def remember_target(run,known):
    file=run/'result.pid'
    if file.exists():known.setdefault(int(file.read_text()),None)

def signal_owned(pid,sig,group,known):
    try:fd=os.pidfd_open(pid,0)
    except (ProcessLookupError,PermissionError):return False
    try:
        identity=proc_identity(pid)
        if identity and owned_pid(pid,group,known) and known[pid]==identity[1]:
            try:signal.pidfd_send_signal(fd,sig,None,0);return True
            except ProcessLookupError:return False
        return False
    except IdentityUnavailable:return False
    finally:os.close(fd)

def terminate_owned(p,known):
    # pidfd keeps the signal bound to the verified process across PID reuse.
    for pid in sorted(known,reverse=True):signal_owned(pid,signal.SIGTERM,p.pid,known)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        for pid in sorted(known,reverse=True):signal_owned(pid,signal.SIGKILL,p.pid,known)
        p.wait()

def execute(root,epoch,index,gpu,label,kind,q,k,arm,reps=0,warm=0,dump=False,count=False,tool=None,fixture=False,allow_quality_failure=False):
    run=epoch/label;run.mkdir();binary=root/'bin'/('arborx_count_fast' if count else 'arborx_bench') if arm=='X' else root/'bin'/('bench_count_v4' if count else 'bench_v3')
    folder=root/'bounded' if fixture else root/'fixtures';data=folder/('words.txt' if kind=='words' else 'tloc.f32bin');oracle=folder/(kind+'.oracle')
    cmd=[str(binary),kind,str(data),str(oracle),str(q),arm,str(k),str(reps),str(warm),str(run/'result'),str(int(dump))]
    if tool:cmd=['compute-sanitizer','--tool',tool,'--error-exitcode','90',*cmd]
    before,waiting=stable_idle(index);save(run/'admission_wait.json',waiting);save(run/'before.json',before)
    if not before['idle']:save(run/'invalid.json',{'reason':'occupied_before_process'});raise Contaminated(label)
    rec={'label':label,'arm':arm,'kind':kind,'Q':q,'k':k,'reps':reps,'warmups':warm,'dump':dump,'instrumented':count,'tool':tool,'gpu_uuid':gpu,'command':cmd,'binary_sha256':sha(binary),'runner_sha256':sha(__file__),'oracle_sha256':sha(oracle),'start':time.time()}
    checks=[];problem=None;known={}
    with (run/'stdout.log').open('x') as out,(run/'stderr.log').open('x') as err:
        p=subprocess.Popen(cmd,cwd=root,env={**os.environ,'CUDA_VISIBLE_DEVICES':gpu},start_new_session=True,stdout=out,stderr=err)
        rec['pid']=p.pid;identity=proc_identity(p.pid);known[p.pid]=identity[1] if identity else None
        try:
            while p.poll() is None:
                remember_target(run,known)
                state=snapshot(index)
                remember_target(run,known)
                bad=foreign_apps(state,p.pid,known);checks.append({'time_utc':state['time_utc'],'apps':state['apps'],'foreign':bad,'known_owned_pids':sorted(known),'known_pid_starttimes':dict(known)})
                if bad:raise Contaminated('foreign process during '+label)
                if time.time()-rec['start']>3600:raise TimeoutError(label)
                time.sleep(.35)
        except BaseException as e:
            problem=e
            if p.poll() is None:
                remember_target(run,known);terminate_owned(p,known)
        rec['exit_code']=p.wait();rec['elapsed_s']=time.time()-rec['start']
    remember_target(run,known)
    after=snapshot(index);save(run/'after_initial.json',after)
    if foreign_apps(after,p.pid,known):
        if problem:rec['prior_exception']=type(problem).__name__+': '+str(problem)
        problem=Contaminated('foreign process in after-initial snapshot '+label)
    # A trailing NVML window can rise again briefly after the CUDA process exits.
    time.sleep(1)
    after,settling=stable_idle(index,group=p.pid,known=known)
    save(run/'settling.json',settling);save(run/'after.json',after);save(run/'checks.json',checks)
    rec['valid']=problem is None and after['idle'] and rec['exit_code']==0
    if problem:rec['exception']=type(problem).__name__+': '+str(problem)
    rec['result_files']={p.name:sha(p) for p in run.glob('result*') if p.is_file()}
    save(run/'receipt.json',rec)
    print(label,rec['exit_code'],round(rec['elapsed_s'],2),flush=True)
    if problem:raise problem
    if not after['idle']:raise Contaminated('occupied after '+label)
    if allow_quality_failure and rec['exit_code'] in (20,21):return run
    assert rec['exit_code']==0,(label,rec['exit_code'])
    logs=(run/'stdout.log').read_text()+(run/'stderr.log').read_text()
    if tool:assert 'ERROR SUMMARY: 0 errors' in logs,(label,'sanitizer summary')
    assert 'PASS' in logs and json.loads((run/'result.json').read_text())['correct']
    return run

def cases():
    for kind in ('words','tloc'):
        for k in range(3):
            for q in (1,32,1024):yield kind,k,q

def same_file(a,b):
    with a.open('rb') as x,b.open('rb') as y:
        while True:
            u=x.read(8<<20);v=y.read(8<<20)
            if u!=v:return False
            if not u:return True

def stages(root,epoch,index,state,mode):
    gpu=state['uuid'];save(epoch/'admission.json',state)
    frozen=json.loads((root/'FROZEN_CPU_ORACLE.json').read_text())
    verified={}
    for name,v in frozen['files'].items():
        if name.startswith('fixtures/'):
            assert sha(root/name)==v['sha256'],name
            verified[name]=v['sha256']
    save(epoch/'frozen_inputs_verified.json',verified)
    bins={p.name:sha(p) for p in (root/'bin').iterdir() if p.is_file()};save(epoch/'binaries.json',bins)
    call=lambda label,kind,q,k,arm,**kw:execute(root,epoch,index,gpu,label,kind,q,k,arm,**kw)
    if mode=='smoke':
        for kind in ('words','tloc'):
            for arm in 'ARS':call(f'smoke_{kind}_{arm}',kind,1,0,arm,dump=True)
        return
    for kind,k,q in cases():
        runs={arm:call(f'full_{kind}_k{k}_q{q}_{arm}',kind,q,k,arm,dump=True) for arm in ('ARS' if kind=='words' else 'ARSX')}
        assert same_file(runs['A']/'result.native.bin',runs['R']/'result.native.bin'),('native_order_mismatch',kind,k,q)
    save(epoch/'FULL_PASS.json',{'binary_hashes':bins,'native_A_R_identical':True})
    for kind in ('words','tloc'):
        for arm in ('ARS' if kind=='words' else 'ARSX'):
            for tool in ('memcheck','synccheck'):
                for k in range(3):call(f'gate_{kind}_{arm}_{tool}_k{k}',kind,32,k,arm,tool=tool,fixture=True)
        call(f'stress_{kind}_R',kind,32,1,'R',reps=1)
    save(epoch/'GATES_PASS.json',{'memcheck':True,'synccheck':True,'Graph_replays_changing_IDs':64,'binary_hashes':bins})
    for kind,k,q in cases():
        for arm in ('ARS' if kind=='words' else 'ARSX'):call(f'count_{kind}_k{k}_q{q}_{arm}',kind,q,k,arm,count=True)
    save(epoch/'COUNT_PASS.json',{'binary_hashes':bins})
    schedule=[{'kind':kind,'k':k,'Q':q,'orders':THREE if kind=='words' else FOUR} for kind,k,q in cases()]
    save(epoch/'TIMING_SCHEDULE.json',schedule)
    # A contaminated observation invalidates this entire epoch's timing, never a replacement sample.
    for round_id in range(6):
        for kind,k,q in cases():
            order=(THREE if kind=='words' else FOUR)[round_id]
            for arm in order:call(f'time_g{round_id}_{kind}_k{k}_q{q}_{arm}',kind,q,k,arm,reps=3,warm=3)
        save(epoch/f'ROUND_{round_id}_COMPLETE.json',{'round':round_id,'gpu_uuid':gpu})
    assert bins=={p.name:sha(p) for p in (root/'bin').iterdir() if p.is_file()},'binaries changed during campaign'
    save(epoch/'COMPLETE.json',{'gpu_uuid':gpu,'rounds':6,'all_required_cases':18,'binary_hashes':bins})

def main(root,mode):
    root=Path(root).resolve();assert mode in ('smoke','all')
    task=(root/'campaign.lock').open('a');fcntl.flock(task,fcntl.LOCK_EX|fcntl.LOCK_NB)
    for attempt in range(1000):
        index,state,lock=acquire(root);epoch=root/'runs'/f'{mode}_{time.time_ns()}';epoch.mkdir();(root/'logs/active_epoch.txt').write_text(str(epoch)+'\n');(root/'logs/runner.pid').write_text(str(os.getpid())+'\n')
        try:stages(root,epoch,index,state,mode)
        except Contaminated as e:save(epoch/'INVALID_EPOCH.json',{'reason':str(e),'all_timing_ineligible':True});print('RESTART entire epoch',e,flush=True);lock.close();time.sleep(5);continue
        except BaseException as e:save(epoch/'FAILED.json',{'reason':type(e).__name__+': '+str(e)});lock.close();raise
        lock.close();print('COMPLETE',epoch,flush=True);return
    raise RuntimeError('too many contaminated epochs')
if __name__=='__main__':main(*sys.argv[1:])
