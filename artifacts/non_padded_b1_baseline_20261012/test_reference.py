"""CPU regression for reference ownership after deletions and inserted occurrences."""
import csv,tempfile,unittest
from pathlib import Path
import numpy as np
from recover import normalize_reference
class ReferenceOwnership(unittest.TestCase):
    def fixture(self,p,ids):
        trace=p/'trace';ref=p/'ref';trace.with_suffix('.logical').write_text('4 5 960\n1 1\n2 -1\n0 5\n3 -1\n')
        np.array(ids,dtype='<i4').tofile(str(ref)+'.ids.i32')
        np.array([.5,.25],dtype='<f4').tofile(str(ref)+'.dist.f32')
        Path(str(ref)+'.queries.csv').write_text('step,qid,count,offset\n1,0,1,0\n3,0,1,1\n')
        return trace,ref
    def test_logical_not_rank(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);trace,ref=self.fixture(p,[3,5]);out=p/'rank'
            record=normalize_reference(trace,ref,out)
            self.assertTrue(record['all_round_trips_equal'])
            self.assertEqual(np.fromfile(str(out)+'.ids.i32',dtype='<i4').tolist(),[2,4])
            for suffix in ('.dist.f32','.queries.csv'):
                self.assertEqual(Path(str(ref)+suffix).read_bytes(),Path(str(out)+suffix).read_bytes())
    def test_deleted_id_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);trace,ref=self.fixture(p,[1,5])
            with self.assertRaises(AssertionError):normalize_reference(trace,ref,p/'rank')
if __name__=='__main__':unittest.main()
