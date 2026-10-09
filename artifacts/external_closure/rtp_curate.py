#!/usr/bin/env python3
"""Whitelist public internal-workflow evidence; keep runtime receipts private."""
import argparse,hashlib,json
from pathlib import Path

def main(a):
    data=a.input.read_bytes();x=json.loads(data)
    assert x['status']=='MEASURED_FIXED_SHORT_RTP' and len(x['rows'])==18
    assert len(x['binding']['bridge']['rows'])==5 and len(x['binding']['primary']['rows'])==18
    allowed=('status','shape','events','binary_sha256','contract_sha256','rows','comparisons','distributions',
        'new_primary_processes','new_GPU_qualifiers','cumulative_GPU_qualifiers','external_static_processes','limits',
        'checker_sha256','executed_driver_sha256','verification_helper_sha256')
    out={k:x[k] for k in allowed}
    out['complete_private_proof_sha256']=hashlib.sha256(data).hexdigest()
    out['binding']={stage:{k:v for k,v in proof.items() if k!='rows'} for stage,proof in x['binding'].items()}
    out['bridge_checks']=[{k:v for k,v in row.items() if k not in ('trace_ms','setup_plus_trace_ms','initial_setup_ms','warmup_ms','final_release_ms')}
                          for row in x['binding']['bridge']['rows']]
    assert not a.output.exists();a.output.write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
