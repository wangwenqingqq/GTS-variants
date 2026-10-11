#!/usr/bin/env python3
"""CPU-only raw archive, phase/receipt and complete payload closure, no extraction."""
import argparse,hashlib,json,tarfile
from pathlib import Path
from prepare import read,save,sha

def verify(archive,manifest):
    files=read(manifest)
    with tarfile.open(archive,'r:gz') as t:
        members=t.getmembers();assert len(members)==len(files) and {x.name for x in members}==set(files)
        assert all(x.isfile() and not Path(x.name).is_absolute() and '..' not in Path(x.name).parts for x in members)
        for m in members:
            assert m.size==files[m.name]['bytes'];h=hashlib.sha256()
            f=t.extractfile(m)
            for b in iter(lambda:f.read(8<<20),b''):h.update(b)
            assert h.hexdigest()==files[m.name]['sha256'],m.name
        def j(n):return json.load(t.extractfile(n))
        def bound(n,h):assert files[n]['sha256']==h,(n,h)
        c=j('CONTRACT.json');reg=j('INPUTS.json');closure=j('CLOSURE.json');assert closure['passed'] and closure['processes']==26
        assert c['primary']['processes']==12 and c['qualification']['processes']==12 and c['diagnostic']['processes']==2
        for n,h in reg['inputs'].items():bound(n,h)
        bound('INPUTS.json',closure['inputs_sha256']);bound('REGISTERED.json',closure['registration_sha256']);bound('CONTRACT.json',closure['contract_sha256'])
        payloads=0;rows=[]
        for phase,count in [('qualification',12),('primary',12),('diagnostic',2)]:
            gate=j(phase+'/GATE.json');assert gate['passed'] and len(gate['rows'])==count
            assert len({x['label'] for x in gate['rows']})==count
            for n,h in gate['files'].items():bound(phase+'/'+n,h)
            for row in gate['rows']:
                label=row['label'];receipt=j(f'{phase}/runs/{label}/receipt.json');assert receipt['runtime_valid'] and not receipt['stop_reason'] and receipt['exit_code']==0
                assert all(not x['foreign'] for x in j(f'{phase}/runs/{label}/checks.json'))
                bound(f'{phase}/runs/{label}/receipt.json',row['receipt_sha256']);bound(f'{phase}/outputs/{label}.quality.json',row['quality_sha256'])
                quality=j(f'{phase}/outputs/{label}.quality.json')
                for suffix,q in quality.items():
                    assert q['passed'];prefix=f'{phase}/outputs/{label}'+('.warmup' if suffix=='.warmup' else '')
                    for s,h in q['payload_hashes'].items():bound(prefix+s,h);payloads+=1
                rows.append(dict(phase=phase,label=label,method=row['method'],case=row['case'],sanitizer=row['tool'],passed=True,receipt_sha256=row['receipt_sha256'],quality_sha256=row['quality_sha256'],main_queries=quality['measured']['queries'],main_final_live=quality['measured']['final_live'],warmup_queries=quality['.warmup']['queries']))
        assert payloads==156
    return dict(passed=True,files=len(files),uncompressed_file_bytes=sum(x['bytes'] for x in files.values()),archive_sha256=sha(archive),archive_bytes=Path(archive).stat().st_size,manifest_sha256=sha(manifest),immutable_inputs=len(reg['inputs']),processes=26,qualified_payload_files=payloads,rows=rows,scope='Every archived byte hash and all phase gates, receipts, full quality payload hashes independently rebound locally. Library/data/reference live hashes were reverified at remote close; not locally re-read from unavailable remote paths.')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('archive','manifest','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();j=verify(a.archive,a.manifest);save(a.out,j);print('PASS: every archived file; 26 receipts; 156 full payload bindings')
