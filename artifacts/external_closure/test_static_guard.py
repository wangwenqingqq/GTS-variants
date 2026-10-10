#!/usr/bin/env python3
"""CPU-only regression for the observed descendant-exit race; not historical proof."""
from static_guard import classify_apps

def live_linux_check():
    import subprocess,sys
    from static_guard import owned_identities,proc_identity
    if not sys.platform.startswith('linux'):return
    code="import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import sys;sys.stdin.read(1)']); print(p.pid,flush=True); p.wait()"
    process=subprocess.Popen([sys.executable,'-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    try:
        child=int(process.stdout.readline());before=owned_identities(process.pid)
        assert process.pid in before and child in before and before[child]==proc_identity(child)
        process.stdin.close();process.wait(timeout=5);after=owned_identities(process.pid)
        assert proc_identity(child) is None and proc_identity(process.pid) is None
        assert classify_apps(f'{child}, [No data], 552 MiB',before,after,{child:None})[0]==[]
    finally:
        if not process.stdin.closed:process.stdin.close()
        if process.poll() is None:process.wait(timeout=5)
    print('PASS live Linux descendant starttime and exit-window ownership; no GPU use')

def check():
    app='21, [No data], 552 MiB'
    # GPU snapshot starts with an owned descendant alive; it exits before /proc re-read.
    assert classify_apps(app,{10:1,21:7},{10:1},{21:None})[0]==[]
    assert classify_apps(app,{10:1},{10:1,21:7},{21:7})[0]==[]
    # Unknown, vanished or reused PIDs remain foreign, regardless of process_name.
    assert classify_apps(app,{10:1},{10:1},{21:None})[0]==[app]
    assert classify_apps(app,{10:1,21:7},{10:1},{21:8})[0]==[app]
    assert classify_apps(app,{10:1,21:7},{10:1,21:8},{21:8})[0]==[app]
    assert classify_apps(app,{10:1},{10:1},{21:7})[0]==[app]
    assert classify_apps('',{}, {},{})==( [], [])
    assert classify_apps(app+'\n22, foreign, 10 MiB',{21:7},{21:7},{21:7,22:9})[0]==['22, foreign, 10 MiB']
    from static_second_stop import structure,c
    jobs=c.jobs('recovery');reg={'jobs':jobs};rows={j['label']:{} for j in jobs[:44]};labels={j['label'] for j in jobs[:45]}
    structure(reg,rows,labels,False)
    for bad_rows,bad_labels,complete in [(dict(list(rows.items())[:-1]),labels,False),(rows,set(rows),False),(rows,labels,True)]:
        try:structure(reg,bad_rows,bad_labels,complete)
        except AssertionError:pass
        else:raise AssertionError('incomplete/forged recovery accepted')
    print('PASS snapshot-exit, new child, unknown exit, PID reuse, mixed foreign cases')
    live_linux_check()
if __name__=='__main__':check()
