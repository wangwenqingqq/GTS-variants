"""CPU-only prospective gate checks, including explicitly retained gray regions."""
import csv,tempfile,unittest
from pathlib import Path
from analyze import classify,geometric,percentile,metric_record
class Gates(unittest.TestCase):
    def test_gate_boundaries(self):
        self.assertEqual(classify(1.5,.70,1.15,1),'BASELINE_FIXED_MEMORY_LIMIT')
        self.assertEqual(classify(1.5,.5,1.25,1),'BASELINE_FIXED_RESIDUAL_COMPUTE')
        self.assertEqual(classify(2.001,.8,1.,1),'BASELINE_NOT_FIXED')
        self.assertEqual(classify(1.,.299,1.,1),'BASELINE_NOT_FIXED')
        self.assertEqual(classify(1.5,.69,1.15,1),'UNCLASSIFIED')
        self.assertEqual(classify(2.,.3,1.2,1),'UNCLASSIFIED')
        self.assertEqual(classify(1.,float('nan'),1.,1),'UNCLASSIFIED')
    def test_estimators(self):
        self.assertAlmostEqual(geometric([.5,2]),1.)
        self.assertAlmostEqual(percentile([1,2,3,4,5,6],.5),3.5)
        self.assertAlmostEqual(percentile([1,2,3,4,5,6],.1),1.5)
    def test_NCU_units_and_enums(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'metrics.csv'
            metrics={'Kernel Name':('','squared_l2_b1'),'gpu__time_duration.avg':('ns','1000000'),
                'dram__bytes.sum':('byte','1000000000'),'dram__bytes_op_read.sum':('byte','999000000'),
                'dram__bytes_op_write.sum':('byte','1000000'),
                'smsp__sass_thread_inst_executed_op_fadd_pred_on.sum':('inst','1'),
                'smsp__sass_thread_inst_executed_op_fmul_pred_on.sum':('inst','2'),
                'smsp__sass_thread_inst_executed_op_ffma_pred_on.sum':('inst','3'),
                'launch__cluster_scheduling_policy':('','PolicySpread')}
            with p.open('w') as f:w=csv.writer(f);w.writerow(metrics);w.writerow([v[0] for v in metrics.values()]);w.writerow([v[1] for v in metrics.values()])
            r=metric_record(p);self.assertAlmostEqual(r['kernel_ms'],1.);self.assertAlmostEqual(r['DRAM_GBs'],1000.)
            self.assertEqual(r['executed_FP32_proxy'],9.);self.assertEqual(r['metrics']['launch__cluster_scheduling_policy']['value'],'PolicySpread')
if __name__=='__main__':unittest.main()
