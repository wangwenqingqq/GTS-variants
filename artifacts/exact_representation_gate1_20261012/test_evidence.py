"""Post-measurement aggregation checks; no data, compiler, CUDA or GPU required."""
import copy,unittest
from pathlib import Path
from analyze import analyze,load
class Evidence(unittest.TestCase):
    def fixture(self):
        c=load(Path(__file__).with_name('CONTRACT.json'));N=c['workload']['N'];D=c['workload']['D'];rows=[]
        for i,q in enumerate(c['workload']['qids']):
            h=[0]*(D+1);h[100]=N-1;h[D]=1;nh=h.copy();nh[D]=0
            groups={k:dict(count=0,histogram=[0]*(D+1)) for k in ('near','medium','far')};groups['far']=dict(count=N-1,histogram=nh.copy())
            rows.append(dict(query_index=i,qid=q,N=N,D=D,hits=1,nonhits=N-1,histogram=h,nonhit_histogram=nh,margin_groups=groups,hard_nonhits_at_D=0,full960_bit_mismatches=0,false_rejections=0))
        return c,rows
    def test_full_population_and_hit_denominator(self):
        c,rows=self.fixture();a=analyze(rows,c)
        self.assertEqual(a['pairs'],32000000);self.assertEqual(a['hits'],32)
        self.assertAlmostEqual(a['all_objects']['mean'],100.00086)
        self.assertEqual(a['decision'],'GO_BYTE_REDUCTION')
        self.assertEqual(a['checkpoint_rejection'][-1]['unresolved'],32)
        self.assertEqual(a['total_histogram'][960],32)
        self.assertLess(a['checkpoint_rejection'][-1]['rejected_fraction'],1)
    def test_bad_ownership_or_counts_rejected(self):
        c,rows=self.fixture();bad=copy.deepcopy(rows);bad[0]['qid']=rows[1]['qid']
        with self.assertRaises(AssertionError):analyze(bad,c)
        bad=copy.deepcopy(rows);bad[0]['histogram'][100]-=1
        with self.assertRaises(AssertionError):analyze(bad,c)
        bad=copy.deepcopy(rows);bad[0]['false_rejections']=1
        with self.assertRaises(AssertionError):analyze(bad,c)
if __name__=='__main__':unittest.main()
