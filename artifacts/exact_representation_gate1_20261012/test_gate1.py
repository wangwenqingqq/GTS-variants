"""Small CPU numerical, ownership, threshold and frozen-gate regression checks."""
import os,unittest
from pathlib import Path
import numpy as np
from analyze import classify,histogram_stats,percentile
from run import score_function,query_record
class Contract(unittest.TestCase):
    def test_gates(self):
        self.assertEqual(classify(384,480),'GO_BYTE_REDUCTION')
        self.assertEqual(classify(384,480.01),'UNCLASSIFIED')
        self.assertEqual(classify(384.01,720),'CONDITIONAL_BYTE_REDUCTION')
        self.assertEqual(classify(576,720),'CONDITIONAL_BYTE_REDUCTION')
        self.assertEqual(classify(576.01,480),'NO_GO_BYTE_REDUCTION')
        self.assertEqual(classify(500,720.01),'NO_GO_BYTE_REDUCTION')
        self.assertEqual(classify(300,720.01),'NO_GO_BYTE_REDUCTION')
        self.assertEqual(classify(float('nan'),300),'UNCLASSIFIED')
    def test_histogram_quantiles(self):
        values=[1,1,2,960];h=np.bincount(values,minlength=961).tolist();v=histogram_stats(h)
        for k,p in [('median',.5),('p10',.1),('p90',.9),('p95',.95),('p99',.99)]:self.assertEqual(v[k],percentile(values,p))
        self.assertEqual(v['mean'],241.)
        self.assertIsNone(histogram_stats([0]*961)['mean'])
    @unittest.skipUnless(os.environ.get('GATE1_TEST_LIBRARY'),'Supply the precompiled CPU library for numerical qualification')
    def test_ordered_bits_and_crossings(self):
        score=score_function(Path(os.environ['GATE1_TEST_LIBRARY']))
        rng=np.random.default_rng(2026101218);x=rng.random((257,960),dtype=np.float32);x[1]=x[0];q=x[0].copy();threshold=.497906721377376
        full=np.zeros(len(x));required=np.full(len(x),960,dtype=np.uint16);seen=np.zeros(len(x),bool)
        for j in range(960):
            delta=x[:,j].astype(np.float64)-float(q[j]);full=full+delta*delta
            new=(~seen)&(full>threshold);required[new]=j+1;seen|=new
        observed,dims,before,at=score(x,q,threshold)
        self.assertEqual(observed.tobytes(),full.tobytes());np.testing.assert_array_equal(dims,required)
        record=query_record(0,observed,dims,before,at,full,threshold,960)
        self.assertEqual(record['hits'],2);self.assertEqual(record['false_rejections'],0)
        x=np.zeros((6,960),np.float32);q=np.zeros(960,np.float32)
        x[1,0]=1;x[2,0]=np.nextafter(np.float32(1),np.float32(0));x[3,0]=np.nextafter(np.float32(1),np.float32(2));x[4,959]=2;x[5,0]=2
        full,dims,before,at=score(x,q,1.)
        np.testing.assert_array_equal(dims,[960,960,960,1,960,1])
        np.testing.assert_array_equal(full<=1.,[True,True,True,False,False,False])
        self.assertEqual(query_record(0,full,dims,before,at,full,1.,960)['hard_nonhits_at_D'],1)
        x[0,0]=np.nan
        with self.assertRaises(ValueError):score(x,q,1.)
if __name__=='__main__':unittest.main()
