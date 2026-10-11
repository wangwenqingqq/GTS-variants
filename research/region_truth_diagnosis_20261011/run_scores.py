#!/usr/bin/env python3
"""Bounded CPU-only score scan and private validation-vector extraction."""
import argparse,hashlib,json,os,resource,struct,subprocess,time
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser()
    for name in ['data','index','manifest','samples','queries','source','oracle','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    m=json.loads(a.manifest.read_text())
    for path,key in [(a.data,'data_sha256'),(a.index,'tree_sha256'),(a.queries,'query_sha256'),(a.oracle,'oracle8_sha256')]:
        if sha(path)!=m[key]:raise ValueError('input drift '+key)
    binary=a.out/'compute_scores';build=['/usr/bin/g++','-O3','-std=c++17','-fno-fast-math','-ffp-contract=off',str(a.source),'-o',str(binary)]
    with (a.out/'build.log').open('w') as f:subprocess.run(build,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=60)
    command=['/usr/bin/numactl','--physcpubind=48','--membind=3','/usr/bin/nice','-n','10',str(binary),str(a.data),str(a.queries),'8',str(a.out/'topk.bin'),str(a.out/'all_scores.bin')]
    (a.out/'command.json').write_text(json.dumps({'build':build,'run':command},indent=2)+'\n')
    start=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
    with (a.out/'stdout.log').open('w') as o,(a.out/'stderr.log').open('w') as e:
        r=subprocess.run(command,env={**os.environ,'CUDA_VISIBLE_DEVICES':''},stdout=o,stderr=e,timeout=180)
    after=resource.getrusage(resource.RUSAGE_CHILDREN);wall=time.monotonic()-start
    receipt={'exit_code':r.returncode,'wall_seconds':wall,'CPU_user_seconds':after.ru_utime-before.ru_utime,
        'CPU_system_seconds':after.ru_stime-before.ru_stime,'child_peak_RSS_KiB':after.ru_maxrss,
        'scope':'offline exhaustive truth diagnostic; not deployable latency','GPU_used':False,
        'compiler':subprocess.check_output(['/usr/bin/g++','--version'],text=True).splitlines()[0],
        'source_sha256':sha(a.source),'binary_sha256':sha(binary),'query_sha256':sha(a.queries),
        'data_sha256':m['data_sha256'],'tree_sha256':m['tree_sha256']}
    (a.out/'SCAN_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if r.returncode:raise RuntimeError('scan failed')
    if (a.out/'topk.bin').read_bytes()!=a.oracle.read_bytes():raise ValueError('frozen independent oracle mismatch')
    if (a.out/'all_scores.bin').stat().st_size!=16+8*1000000*8:raise ValueError('score export length')
    rows=set(m['queries'])
    for sample in json.loads(a.samples.read_text())['samples']:rows.update(sample['object_ids'])
    rows=sorted(rows)
    with a.data.open('rb') as src,(a.out/'sample_vectors.bin').open('wb') as dst:
        d,n,metric=struct.unpack('<3i',src.read(12));assert (d,n,metric)==(960,1000000,2)
        dst.write(struct.pack('<2i',len(rows),d));dst.write(struct.pack('<'+str(len(rows))+'i',*rows))
        for row in rows:
            src.seek(12+row*d*4);b=src.read(d*4);assert len(b)==d*4;dst.write(b)
    (a.out/'OUTPUT_MANIFEST.json').write_text(json.dumps({x:sha(a.out/x) for x in ['topk.bin','all_scores.bin','sample_vectors.bin','SCAN_RECEIPT.json']},indent=2)+'\n')
    print('PASS 8-query CPU scan and frozen full-output oracle match; no GPU used')

if __name__=='__main__':main()
