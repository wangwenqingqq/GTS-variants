"""Small runnable checks for the trace/input gate and insertion audit."""
import json, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit_inputs import capacity
from make_smoke import make_events
from check_no_direct_insert import check

class ContractTests(unittest.TestCase):
    def test_fresh_capacity(self):
        self.assertEqual(capacity(50000,5000,100000,'4:4:2')['status'],'contract-infeasible')
        self.assertIn('final_active_cardinality_below_k',capacity(52799,5279,100000,'1:8:1')['reasons'])
        self.assertEqual(capacity(1000000,100000,100000,'8:1:1')['status'],'capacity-feasible')
    def test_active_snapshots(self):
        for seed in (20261026,20261027,20261028):
            active=set(range(10000));seen=active.copy();snapshot=0
            events=make_events(10000,2000,1000,seed)
            self.assertEqual(len(events),5000)
            for e in events:
                if e['op']=='insert':
                    self.assertNotIn(e['id'],seen);seen.add(e['id']);active.add(e['id']);snapshot+=1
                elif e['op']=='delete':self.assertIn(e['id'],active);active.remove(e['id']);snapshot+=1
                self.assertEqual(e['required_snapshot'],snapshot)
                self.assertEqual(e['active_size'],len(active))
    def test_no_metadata_insertion(self):
        source=(Path(__file__).resolve().parents[1]/'dynamic.cu').read_text()
        self.assertTrue(check(source))
        with self.assertRaises(AssertionError):check(source.replace('void append(int uid,int payload){','void append(int uid,int payload){ nodes[0].min_dis=0;'))
    def test_input_matrix_preserved(self):
        source=Path(__file__).resolve().parents[1]/'evidence/input_audit.json'
        data=json.loads(source.read_text());self.assertEqual(len(data['datasets']),7)
        self.assertEqual(sum(len(d['loads']) for d in data['datasets'].values()),132)
        self.assertEqual([k for k,v in data['datasets'].items() if v['input_status']=='input-pass'],['sift'])
if __name__=='__main__':unittest.main()
