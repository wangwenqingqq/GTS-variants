#!/usr/bin/env python3
"""Portable process-lifetime resource record; not a query timer."""
import json,resource,subprocess,sys,time
from pathlib import Path
assert len(sys.argv)>4 and sys.argv[1]=='--record' and sys.argv[3]=='--'
p=Path(sys.argv[2]);assert not p.exists() and Path(sys.argv[4]).is_file()
t=time.monotonic();rc=subprocess.run(sys.argv[4:]).returncode;r=resource.getrusage(resource.RUSAGE_CHILDREN)
p.write_text(json.dumps(dict(returncode=rc,wall_s=time.monotonic()-t,cpu_user_s=r.ru_utime,cpu_system_s=r.ru_stime,max_rss_bytes=r.ru_maxrss*1024,scope='Linux child process lifetime including setup/warmup/serialization; not the query denominator'),indent=2)+'\n')
sys.exit(rc)
