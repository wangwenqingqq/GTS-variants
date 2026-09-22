#!/usr/bin/env python3
"""Run the predeclared height-adapted GTS scale extension with the same launcher."""
import argparse
import fcntl
import json
from pathlib import Path
import run as base


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root',type=Path);ap.add_argument('--gpu',required=True)
    a=ap.parse_args();root=a.root.resolve();(root/'runs').mkdir(exist_ok=True)
    state=base.snapshot(a.gpu);assert not state['apps'].strip()
    index=state['gpu'].split(',')[0].strip();locks=[]
    for p in [Path(f'/tmp/gtspp_gpu{index}.lock'),root/'run.lock']:
        f=p.open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    meta=json.loads((root/'fixtures/manifest.json').read_text())
    for name,digest in meta['file_sha256'].items():assert base.sha(root/'fixtures'/name)==digest
    pins={str(p.relative_to(root)):base.sha(p) for sub in ['source','bin','fixtures'] for p in sorted((root/sub).rglob('*')) if p.is_file()}
    (root/'SOURCE_BINARY_INPUT_SHA256.json').write_text(json.dumps(pins,indent=2)+'\n')
    expected=meta['cases']['words_65536']
    for kind in ['range','knn','update']:
        if not base.invoke(root,a.gpu,f'smoke_gts_{kind}_65536','gts',kind,65536,False,'smoke',expected):continue
        passed=[base.invoke(root,a.gpu,f'{tool}_gts_{kind}','gts',kind,65536,False,'sanitizer',expected,tool) for tool in ['memcheck','synccheck']]
        if not all(passed):
            print('STOP promotion:',kind,'failed sanitizer',flush=True);continue
        for pair in range(6):
            for blocking in ([False,True] if pair%2==0 else [True,False]):
                assert base.invoke(root,a.gpu,f'pair{pair}_gts_{kind}_b{int(blocking)}','gts',kind,65536,blocking,'paired',expected)
        assert base.invoke(root,a.gpu,f'profile_gts_{kind}','gts',kind,65536,False,'profile',expected)


if __name__=='__main__':main()
