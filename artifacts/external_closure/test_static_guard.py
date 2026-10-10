#!/usr/bin/env python3
"""CPU-only regression for the observed descendant-exit race; not historical proof."""
from static_guard import classify_apps

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
if __name__=='__main__':check()
