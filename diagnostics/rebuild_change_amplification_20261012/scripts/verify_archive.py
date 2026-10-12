#!/usr/bin/env python3
"""Verify the small private archive; never pretend host-only pack bytes are local."""
import argparse,hashlib,json,tarfile
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def verify(archive,manifest):
    files=json.loads(Path(manifest).read_text());small={k:v for k,v in files.items() if v['storage']=='small_archive'};large={k:v for k,v in files.items() if v['storage']=='host_only_large'}
    assert len(large)==4 and all(k.startswith('snapshots/') and k.endswith('/packed.f32') and v['bytes']==3840000000 for k,v in large.items())
    with tarfile.open(archive,'r:gz') as t:
        members=t.getmembers();assert len(members)==len(small) and {m.name for m in members}==set(small)
        for m in members:
            assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
            assert m.size==small[m.name]['bytes'];h=hashlib.sha256();f=t.extractfile(m)
            for b in iter(lambda:f.read(8<<20),b''):h.update(b)
            assert h.hexdigest()==small[m.name]['sha256'],m.name
        def j(n):return json.load(t.extractfile(n))
        def bound(n,h):assert files[n]['sha256']==h,n
        c=j('FINAL_CLOSURE.json');assert c['passed'] and c['target_GPU_processes']==1 and not c['optional_GPU_repeat_used']
        for n,k in [('CONTRACT.json','contract_sha256'),('REGISTERED.json','registered_sha256'),('QUALITY.json','quality_sha256'),('summary_v2/RESULT.json','final_result_sha256'),('summary_v2/SNAPSHOT_MANIFEST.json','snapshot_manifest_sha256')]:bound(n,c[k])
        bound('analysis_v1/CLOSURE.json',c['original_closure_sha256'])
        for n,h in c['post_close_file_bindings'].items():bound(n,h)
        for n,h in c['preregistered_observer_source_and_case'].items():
            if n.startswith('observer_source/'):bound(n,h)
        bound('observer',c['preregistered_observer_binary'])
        q=j('QUALITY.json');assert q['passed'] and q['rebuild_trigger_steps_zero_based']==[48,216]
        for suffix,h in q['payload_hashes'].items():bound('outputs/observer'+suffix,h)
        bound('summary_v2_repeat/RESULT.json',c['final_result_sha256'])
        snapshots=j('summary_v2/SNAPSHOT_MANIFEST.json')
        for x in snapshots:bound('snapshots/'+x['file'],x['sha256'])
    return {'passed':True,'archive_sha256':sha(archive),'archive_bytes':Path(archive).stat().st_size,'manifest_sha256':sha(manifest),
      'small_files_locally_verified':len(small),'small_uncompressed_bytes':sum(v['bytes'] for v in small.values()),'host_only_large_files':len(large),'host_only_large_bytes':sum(v['bytes'] for v in large.values()),
      'complete_payload_bindings':len(q['payload_hashes']),'snapshot_manifest_files':len(snapshots),'scope':'Every small archive member byte and closure/output/source binding verified locally. Four complete packed files bound by host-rehashed snapshot manifest, NOT locally re-read.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('manifest',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    r=verify(a.archive,a.manifest);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
