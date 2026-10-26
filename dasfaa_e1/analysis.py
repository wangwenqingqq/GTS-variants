"""Frozen buffer recipe and six-process paired estimator; no automatic promotion."""
import math, statistics

def predict_buffer(inserts,queries,rebuild_s,scan_s_per_object):
    if not (inserts>0 and queries>0 and rebuild_s>0 and scan_s_per_object>0):
        raise ValueError('positive measured calibration inputs required')
    return max(1,math.ceil(min(inserts,math.sqrt(2*inserts*rebuild_s/(queries*scan_s_per_object)))))

def paired_ratio(baseline_s,candidate_s):
    if len(baseline_s)!=6 or len(candidate_s)!=6:
        raise ValueError('exactly six paired processes required; no sample replacement')
    if any(not(math.isfinite(v) and v>0) for v in [*baseline_s,*candidate_s]):
        raise ValueError('invalid time')
    logs=[math.log(b/c) for b,c in zip(baseline_s,candidate_s)]
    mu=statistics.mean(logs);half=2.570581835636305*statistics.stdev(logs)/math.sqrt(6)
    return dict(ratio=math.exp(mu),ci95=[math.exp(mu-half),math.exp(mu+half)],
                pairs=6,process_wins=sum(v>0 for v in logs),paired_logs=logs)

if __name__=='__main__':
    assert predict_buffer(40000,20000,1,.000001)==2000
    assert predict_buffer(4,2,1,.00000001)==4
    got=paired_ratio([2]*6,[1]*6);assert got['ratio']==2 and got['ci95']==[2,2]
    try:paired_ratio([1]*5,[1]*5)
    except ValueError:pass
    else:raise AssertionError('incomplete pairs accepted')
    print('PASS: buffer recipe and frozen paired estimator')
