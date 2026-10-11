#!/usr/bin/env python3
"""CPU-only proof: child adoption preserves parent locks across process gaps."""
import fcntl,os,subprocess,sys,tempfile
from pathlib import Path
here=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
    paths=[Path(tmp)/name for name in ('a','b')];files=[p.open('a+') for p in paths]
    for f in files:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    fds=tuple(f.fileno() for f in files)
    child="import sys;sys.path.insert(0,sys.argv[1]);from locked import adopt_locks;from pathlib import Path;adopt_locks(None,[Path(x) for x in sys.argv[2:]])"
    subprocess.run([sys.executable,'-c',child,str(here),*map(str,paths)],check=True,pass_fds=fds,
        env={**os.environ,'GTS_CAMPAIGN_LOCK_FDS':','.join(map(str,fds))})
    contender="import fcntl,sys;f=open(sys.argv[1]);\ntry:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)\nexcept BlockingIOError:sys.exit(7)"
    assert subprocess.run([sys.executable,'-c',contender,str(paths[0])]).returncode==7
    for f in files:f.close()
    subprocess.run([sys.executable,'-c',contender,str(paths[0])],check=True)
print('PASS inherited shared locks survive child exit and release only with controller')
