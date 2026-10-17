"""CPU-only fixture for the reproduction receipt helper;no actual tool runs."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python.')
import argparse,json
from pathlib import Path
from unittest.mock import patch
import preflight
from protocol import load,save,sha
def run(root):
    root.mkdir();w=root/'work';r=root/'restore';w.mkdir();r.mkdir()
    nvcc=root/'toolkit/bin/nvcc';nvcc.parent.mkdir(parents=True);nvcc.write_text('fixture')
    cccl=root/'toolkit/targets/x86_64-linux/include/cccl';cccl.mkdir(parents=True);(cccl/'fixture.h').write_text('fixture header')
    lib=root/'libfixture.so';lib.write_bytes(b'library')
    (w/'build/0').mkdir(parents=True);(w/'build/0/service').write_bytes(b'not executable')
    for n in (4096,1000000):
        a=w/'cpu/traces'/f'N{n}_W2_ORIGINAL_2026101701'/'victims.i32';a.parent.mkdir(parents=True);a.write_bytes(b'victims')
        b=r/'rebuild/derived_parent/inputs'/f'N{n}_W2.victims.i32';b.parent.mkdir(parents=True,exist_ok=True);b.write_bytes(a.read_bytes())
    (r/'receipts').mkdir();payload=r/'payload';payload.write_bytes(b'input')
    save(r/'receipts/RESTORED_INPUT_PATH_MAP.json',{'files':{'fixture':dict(path=str(payload),sha256=sha(payload),bytes=5,portable_key='fixture')}})
    ready={'binaries':{'0':'unused fixture digest'}};save(w/'READY.json',ready)
    reg=dict(commands={'0':[str(nvcc)]},gpu='0',environment={},inputs={str(payload):sha(payload)})
    calls=[]
    def command(cmd,**kwargs):
        calls.append(cmd)
        return 'libfixture.so => '+str(lib)+' (0x0)\n' if cmd[0]=='ldd' else 'fixture output\n'
    with patch.object(preflight.subprocess,'check_output',side_effect=command):
        preflight.capture(w,r,reg,ready)
    deps=load(w/'DEPENDENCIES_BEFORE_GPU.json')
    assert deps['GPU_starts']==0 and deps['ready_sha256']==sha(w/'READY.json')
    assert deps['linked_libraries']=={str(lib):sha(lib)} and deps['CCCL_header_hashes']=={str(cccl/'fixture.h'):sha(cccl/'fixture.h')}
    audit=load(w/'INPUT_REUSE_AUDIT.json');assert audit['registered_reused_inputs_checked']==1 and audit['original_hashes_all_exact']
    assert load(w/'POSTPROCESSOR_SOURCE.json')['before_primary'] and len(calls)==9
    (w/'STARTS.jsonl').write_text('fixture target already admitted\n')
    with patch.object(preflight.subprocess,'check_output',side_effect=AssertionError('Must not run a tool')):
        try:preflight.capture(w,r,reg,ready)
        except AssertionError as error:assert 'Preflight must precede every target' in str(error)
        else:raise AssertionError('Late preflight was admitted')
    return dict(passed=True,GPU_starts=0,fixture_only=True,receipt_and_late_capture_checks=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.work),sort_keys=True))
