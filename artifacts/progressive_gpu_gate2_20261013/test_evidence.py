"""Fail-closed scalar curation regression checks; no GPU launches."""
import csv,tempfile,unittest
from pathlib import Path
from curate import traffic,KEYS,phase
class EvidenceTests(unittest.TestCase):
    def fixture(self,path,mode,queries=32):
        header=['ID','Kernel Name',*KEYS]
        units=['','', 'nsecond','byte','byte','byte','byte','%','%']
        data=[]
        for _ in range(queries):
            names=['squared_l2_b1','cub::DeviceSelectKernel','flags_kernel','fields_kernel'] if mode=='B1' else [n for s in (128,256,512,960) for n in (f'void progressive_stage<{0 if s==128 else 128 if s==256 else 256 if s==512 else 512}, {s}>(...)','cub::DeviceSelectKernel')]+['progressive_fields']
            for name in names:data.append([len(data),name,1000,300,200,100,400,50,25])
        with path.open('w') as f:csv.writer(f).writerows([header,units,*data])
        return data
    def test_all_queries_and_kernels(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'raw.csv'
            for mode,launches in (('B1',128),('P1',288)):
                self.fixture(p,mode);r=traffic(p,mode,list(range(32)))
                self.assertEqual(r['launches'],launches)
                self.assertEqual(sum(f['mean_DRAM_bytes_per_query'] for f in r['families']),r['means']['DRAM_bytes'])
            self.fixture(p,'P1',31)
            with self.assertRaises(AssertionError):traffic(p,'P1',list(range(32)))
    def test_unknown_kernel_fails(self):
        with self.assertRaises(AssertionError):phase('unregistered_distance_kernel','P1',1)
    def test_duration_unit_alias(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'raw.csv';self.fixture(p,'B1');first=traffic(p,'B1',list(range(32)))
            with p.open() as f:rows=list(csv.reader(f))
            rows[1][2]='ns'
            with p.open('w') as f:csv.writer(f).writerows(rows)
            second=traffic(p,'B1',list(range(32)))
            self.assertEqual(first['means'],second['means'])
if __name__=='__main__':unittest.main()
