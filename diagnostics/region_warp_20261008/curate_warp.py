#!/usr/bin/env python3
"""Whitelist public receipts; preserve distinct raw and portable file hashes."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'region_exec_20261008'))
from audit_closure import read,sha

QUALIFICATION=('SOURCE.json','VALIDATION.json','FULL_WORK.json','FULL_WORK_ROWS.json',
               'LEAF_DISTRIBUTION.json','MICRO.json','ADMISSION.json','REGISTERED.json',
               'QUALIFICATION_AUDIT.json')
RESULTS=('RESULTS.json','FORMAL_ROWS.json','FORMAL_TIMER.json','COST_ROWS.json',
         'COST_QUALIFICATION.json','COMPLETE.json','INDEPENDENT_AUDIT.json')


def curate(raw,output,phase):
    source=read(raw/'SOURCE.json'); run=Path(source['build'][-1]).parent.parent
    code=Path(next(s for s in source['test_warp_build'] if s.endswith('test_warp.cu'))).parents[2]
    prefixes=((str(run),'$REGION_RUN'),(str(code),'$FROZEN_CODE'),
              (str(run.parents[2]),'$CAMPAIGN_ROOT'))
    def portable(value):
        if isinstance(value,dict):return {k:portable(v) for k,v in value.items()}
        if isinstance(value,list):return [portable(v) for v in value]
        if isinstance(value,str):
            for prefix,marker in prefixes:value=value.replace(prefix,marker)
        return value
    names=QUALIFICATION if phase=='qualification' else RESULTS
    output.mkdir(parents=True,exist_ok=True); manifest={}
    for name in names:
        content=json.dumps(portable(read(raw/name)),indent=2)+'\n'; target=output/name
        assert not target.exists() or target.read_text()==content, 'never replace changed prior evidence'
        target.write_text(content)
        manifest[name]=dict(raw_sha256=sha(raw/name),curated_sha256=sha(target))
    if phase=='qualification':
        target=output/'RESOURCES.txt'
        content='\n'.join(x.rstrip() for x in portable((raw/target.name).read_text()).splitlines())+'\n'
        assert not target.exists() or target.read_text()==content
        target.write_text(content)
        manifest[target.name]=dict(raw_sha256=sha(raw/target.name),curated_sha256=sha(target))
    receipt=output/('PUBLICATION_'+phase.upper()+'.json'); assert not receipt.exists()
    derived={name:dict(curated_sha256=sha(output/name),
                      provenance='Derived receipt; individual raw constituent hashes are recorded inside, not a substituted aggregate')
             for name in ('OPPORTUNITY.json','PRELIMINARY_ATTEMPT.json')
             if phase=='qualification' and (output/name).exists()}
    receipt.write_text(json.dumps(dict(files=manifest,derived_receipts=derived,
        primary_scope='one fixed N1000/D128/radius0 mixed trace; 30 formal processes',
        raw_evidence='Retained external task-owned storage; raw hashes are not portable hashes',
        exclusions=['raw inputs','full binary outputs','GPU identifiers','process identifiers',
                    'device configuration','private paths']),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raw',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--phase',choices=('qualification','results'),required=True)
    a=p.parse_args();curate(a.raw,a.output,a.phase)
