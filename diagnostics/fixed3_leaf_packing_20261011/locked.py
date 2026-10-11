#!/usr/bin/env python3
"""Reuse the owned-process runner while retaining the parent's shared GPU locks."""
import fcntl,importlib.util,os,subprocess
from pathlib import Path
def snapshot(gpu):
    def query(field):
        return subprocess.check_output(['nvidia-smi','-i',gpu,field,'--format=csv,noheader'],text=True,timeout=10).strip()
    return {'device':query('--query-gpu=index,uuid,name,memory.used,utilization.gpu'),
            'apps':query('--query-compute-apps=pid,process_name,used_memory')}
def adopt_locks(stack,paths):
    fds=list(map(int,os.environ['GTS_CAMPAIGN_LOCK_FDS'].split(',')))
    inherited={(os.fstat(fd).st_dev,os.fstat(fd).st_ino):fd for fd in fds}
    assert len(inherited)==2,'exactly two shared GPU lock descriptors required'
    for i,path in enumerate(paths):
        if not path.exists():
            assert i>=2;continue
        st=path.stat();key=(st.st_dev,st.st_ino)
        assert key in inherited,('unowned lock path',path)
        # Same open-file description: acquire succeeds without releasing the parent.
        fcntl.flock(inherited[key],fcntl.LOCK_EX|fcntl.LOCK_NB)
if __name__=='__main__':
    spec=importlib.util.spec_from_file_location('preserved_runner',Path(__file__).parent/'helpers/run_locked.py')
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    runner.snapshot=snapshot;runner.acquire_locks=adopt_locks;runner.main()
