"""Small CPU-only check for schedule, membership/field parser and retained stop gates."""
import csv,json,tempfile,unittest
from pathlib import Path
import numpy as np
from campaign import jobs,quality
from prepare import HERE,read

class Contract(unittest.TestCase):
    def test_schedule(self):
        c=read(HERE/'CONTRACT.json')
        self.assertEqual([len(jobs(s)) for s in ('qualification','primary','ncu')],[8,18,3])
        self.assertEqual(c['budget']['max_top_level_GPU_starts'],31)
        self.assertEqual(c['workload']['radius_bits'],'0x3f34a3d8')
        self.assertIn('UNCLASSIFIED',c['gates']['uncovered'])
        for r in range(1,7):self.assertEqual([j['mode'] for j in jobs('primary') if j['round']==r],c['measurement']['round_orders'][r-1])

    def test_quality_and_rejections(self):
        with tempfile.TemporaryDirectory() as t:
            w=Path(t);ref=w/'reference';ref.mkdir();prefix=w/'test';qs=list(range(32));v=np.ones(4096);v[:2]=.125
            for q in qs:v.tofile(ref/f'{q}.f64')
            reg=dict(reference=str(ref),q32=qs,radius=.75,read_sums={'4096':1.})
            rows=[dict(invocation=i,query_in_batch=0,qid=qs[i if i<8 else i-8],warmup=int(i<8),count=2,offset=2*i) for i in range(40)]
            inv=[dict(invocation=i,warmup=int(i<8),B=1,ack_ms=1.) for i in range(40)]
            def write():
                for name,data in [('.rows.csv',rows),('.invocations.csv',inv)]:
                    with Path(str(prefix)+name).open('w') as f:writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
            write();Path(str(prefix)+'.meta.json').write_text(json.dumps(dict(N=4096,D=960,B=1,diagnostic=False,squared_bytes=16384,query_bytes=3840,measured_pass_ms=32.)))
            ids=np.tile(np.array([0,1],'<i4'),40);ids.tofile(str(prefix)+'.ids.i32')
            np.full(80,np.sqrt(np.float32(.125)),'<f4').tofile(str(prefix)+'.dist.f32')
            np.full(80,.125,'<f8').tofile(str(prefix)+'.native_squared.f64')
            job=dict(mode='N1',N=4096,label='fixture')
            self.assertTrue(quality(prefix,job,w,reg)['passed'])
            ids[1]=0;ids.tofile(str(prefix)+'.ids.i32')
            with self.assertRaises(AssertionError):quality(prefix,job,w,reg)
            ids[1]=1;ids.tofile(str(prefix)+'.ids.i32')
            np.ones(80,'<f8').tofile(str(prefix)+'.native_squared.f64')
            with self.assertRaises(AssertionError):quality(prefix,job,w,reg)
            np.full(80,.125,'<f8').tofile(str(prefix)+'.native_squared.f64')
            rows[8]['qid']=31;write()
            with self.assertRaises(AssertionError):quality(prefix,job,w,reg)

if __name__=='__main__':unittest.main()
