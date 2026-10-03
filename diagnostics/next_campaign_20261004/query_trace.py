"""Query-scoped coarse CPU/memory observation, outside validation and setup."""
from pathlib import Path
import json
import os
import resource
import time
import cupy as cp

class QueryTrace:
    def __init__(self,out):
        self.out=str(out);self.rows=[];self.next=1000
    @staticmethod
    def cpu():
        r=resource.getrusage(resource.RUSAGE_SELF)
        return r.ru_utime+r.ru_stime
    def point(self,q):
        free,total=cp.cuda.runtime.memGetInfo()
        rss=int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
        return (q,time.perf_counter()-self.start,self.cpu()-self.cpu_start,total-free,rss)
    def begin(self):
        self.start=time.perf_counter();self.cpu_start=self.cpu();self.rows.append(self.point(0))
        self.start=time.perf_counter();self.cpu_start=self.cpu()
    def sample(self,q,total):
        if q>=self.next or q==total:
            self.rows.append(self.point(q));self.next=(q//1000+1)*1000
    def finish(self,total_ms):
        cpu=self.cpu()-self.cpu_start
        Path(self.out+'.windows.csv').write_text('processed,wall_s,cpu_s,device_used_bytes,rss_bytes\n'+''.join(','.join(map(str,r))+'\n' for r in self.rows))
        Path(self.out+'.cpu.json').write_text(json.dumps({'query_cpu_s':cpu,'query_wall_s':total_ms/1000,'busy_core_equivalents':cpu/(total_ms/1000),'scope':'all-thread CPU delta in warm query pass','window_hook':'one post-delivery snapshot near each 1k boundary; included in timer'},indent=2)+'\n')
