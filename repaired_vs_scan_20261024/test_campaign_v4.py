"""CPU-only regressions for foreign snapshots, PID reuse and receipt identities."""
import json,signal,tempfile
from pathlib import Path
from unittest.mock import patch
import campaign_quality_support_v4 as m
import quality_campaign_v4 as planner
from analyze_campaign import paired

def main():
    known={100:1000};identities={100:(1,1000),123:(100,1230),456:(1,4560)}
    with patch.object(m,'proc_identity',side_effect=lambda pid:identities.get(pid)):
        assert m.owned_pid(123,100,known) and known[123]==1230
        identities[123]=(1,9990);assert not m.owned_pid(123,100,known)
        del identities[123];assert m.owned_pid(123,100,known)
        assert m.foreign_apps({'apps':'456, foreign, 10'},100,known)
        known[789]=None;identities[789]=(1,7890);assert not m.owned_pid(789,100,known)
        identities[789]=(100,7890);assert m.owned_pid(789,100,known)
    with patch('pathlib.Path.read_text',side_effect=PermissionError('denied')):
        assert m.foreign_apps({'apps':'123, unreadable, 10'},100,{100:1000,123:1230})
    with patch.object(m.os,'pidfd_open',return_value=99,create=True),patch.object(m.os,'close'),patch.object(m.signal,'pidfd_send_signal',create=True) as send,patch.object(m,'proc_identity',return_value=(1,9990)):
        assert not m.signal_owned(123,signal.SIGTERM,100,{123:1230})
        send.assert_not_called()
    with patch.object(m.os,'pidfd_open',return_value=99,create=True),patch.object(m.os,'close'),patch.object(m.signal,'pidfd_send_signal',create=True) as send,patch.object(m,'proc_identity',return_value=(1,1230)):
        assert m.signal_owned(123,signal.SIGTERM,100,{123:1230})
        send.assert_called_once_with(99,signal.SIGTERM,None,0)
    for orders,arms in [(m.THREE,'ARS'),(m.FOUR,'ARSX')]:
        for a in arms:
            for b in arms:
                if a!=b:assert sum(s.index(a)<s.index(b) for s in orders)==3
    assert paired([2.]*6,[1.]*6)['CI95']==[2.,2.]
    idle={'idle':True,'apps':'','uuid':'GPU-test'};foreign={'idle':False,'apps':'666, foreign, 80000','uuid':'GPU-test'}
    class Process:
        pid=100
        def poll(self):return 0
        def wait(self,timeout=None):return 0
    with tempfile.TemporaryDirectory(prefix='monitor_test_',dir=Path(__file__).resolve().parent) as t:
        root=Path(t);(root/'bin').mkdir();(root/'fixtures').mkdir();(root/'epoch').mkdir();(root/'bin/bench_v3').write_bytes(b'binary');(root/'fixtures/words.oracle').write_bytes(b'oracle')
        with patch.object(m,'stable_idle',side_effect=[(idle,[idle]),(idle,[idle])]),patch.object(m,'snapshot',return_value=foreign),patch.object(m,'proc_identity',side_effect=lambda pid:{100:(1,1000),666:(1,6660)}.get(pid)),patch.object(m.subprocess,'Popen',return_value=Process()),patch.object(m.time,'sleep'):
            try:m.execute(root,root/'epoch',5,'GPU-test','observed_foreign','words',1,0,'A')
            except m.Contaminated:pass
            else:raise AssertionError('observed foreign snapshot was incorrectly accepted')
        rec=json.loads((root/'epoch/observed_foreign/receipt.json').read_text());assert not rec['valid'] and 'after-initial' in rec['exception']
        wrong=root/'wrong';wrong.mkdir();(wrong/'receipt.json').write_text(json.dumps({'gpu_uuid':'GPU-test','kind':'tloc','Q':1024,'k':2,'arm':'A','tool':None,'instrumented':False,'reps':0,'warmups':0,'dump':True}))
        try:planner.verify_run(wrong,root,'GPU-test','words',1,0,'A',dump=True)
        except AssertionError:pass
        else:raise AssertionError('wrong-workload receipt was accepted')
    print('PASS post-exit foreign snapshot rejection, live PID-reuse rejection, stale-owned PID handling, receipt identity rejection, paired statistics; no GPU calls')
if __name__=='__main__':main()
