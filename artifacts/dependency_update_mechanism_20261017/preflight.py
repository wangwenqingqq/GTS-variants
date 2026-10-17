"""Reproduction-only packaging of this campaign's pre-target identity checks."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python.')
import datetime,os,subprocess
from pathlib import Path
from protocol import HERE,sha,load,save
def capture(w,restore,reg,ready):
    assert not (w/'STARTS.jsonl').exists(),'Preflight must precede every target'
    nvcc=reg['commands']['0'][0];commands=dict(host=['hostname'],CPU=['lscpu','-J'],GPU=['nvidia-smi','-q','-i',reg['gpu']],processes=['nvidia-smi','--query-compute-apps=gpu_uuid,pid,process_name','--format=csv,noheader'],nvcc=[nvcc,'--version'],nsys=['/usr/local/bin/nsys','--version'],ncu=['/usr/local/bin/ncu','--version'],disk=['df','-B1',str(w)])
    now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
    save(w/'HOST_BEFORE_GPU.json',dict(verified_UTC=now(),GPU_starts=0,commands={k:dict(command=v,output=subprocess.check_output(v,text=True)) for k,v in commands.items()}))
    environment={**os.environ,**reg['environment']};libraries={}
    for trace in ready['binaries']:
        text=subprocess.check_output(['ldd',str(w/'build'/trace/'service')],env=environment,text=True);assert 'not found' not in text
        for line in text.splitlines():
            fields=line.split()
            if '=>' in fields and len(fields)>2 and fields[2].startswith('/'):libraries[fields[2]]=sha(fields[2])
    cccl=Path(nvcc).resolve().parent.parent/'targets/x86_64-linux/include/cccl';assert cccl.is_dir()
    headers={str(p):sha(p) for p in cccl.rglob('*') if p.is_file()};assert headers
    save(w/'DEPENDENCIES_BEFORE_GPU.json',dict(passed=True,GPU_starts=0,verified_UTC=now(),ready_sha256=sha(w/'READY.json'),linked_libraries=libraries,CCCL_header_hashes=headers,scope='Live linked resolutions and installed headers;not per-process maps'))
    save(w/'POSTPROCESSOR_SOURCE.json',dict(before_primary=True,files={n:sha(HERE/n) for n in ('profile.py','plot.py')}))
    records=load(restore/'receipts/RESTORED_INPUT_PATH_MAP.json')['files'];expected={str(Path(r['path']).resolve()):r for r in records.values()};verified=[]
    for name,h in reg['inputs'].items():
        path=Path(name).resolve()
        if str(path) in expected:
            r=expected[str(path)];assert h==r['sha256'] and path.stat().st_size==r['bytes'];verified.append(r['portable_key'])
    for n in (4096,1000000):assert sha(w/'cpu/traces'/f'N{n}_W2_ORIGINAL_2026101701'/'victims.i32')==sha(restore/'rebuild/derived_parent/inputs'/f'N{n}_W2.victims.i32')
    save(w/'INPUT_REUSE_AUDIT.json',dict(passed=True,verified_UTC=now(),registered_reused_inputs_checked=len(verified),original_hashes_all_exact=True,W2_victims_match_original_at_both_scales=True,portable_input_keys=verified))
