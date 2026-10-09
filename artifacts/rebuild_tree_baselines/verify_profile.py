#!/usr/bin/env python3
"""Check fresh profile outputs against the admitted exhaustive parent's exact prefix."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def rows(p):
    with p.open() as f: return list(csv.DictReader(f))


def normalize_dump(text):
    """Reproduce the frozen all-function CUDA13.1 dump hash, retaining its headers."""
    result=[]
    for line in text.splitlines():
        fn=re.match(r'\s*Function\s*:\s*(\S+)',line)
        instruction=re.match(r'\s*/\*[0-9a-fA-F]+\*/\s*(.*)',line)
        if fn:result.append('Function: '+fn.group(1))
        elif instruction:
            value=re.sub(r'\s*/\*\s*0x[0-9a-fA-F]+\s*\*/\s*$','',instruction.group(1)).strip()
            if value:result.append(re.sub(r'\s+',' ',value))
        elif line.strip().startswith(('code version =','host =','compile_size =')):result.append(line.strip())
    return '\n'.join(result)+'\n'


def bind_parent(parent, proof, method):
    assert proof['passed'] and proof['ordered_full_outputs']
    prefix='outputs/round_1_'+method
    hashes={k:v for k,v in proof['evidence_binding']['output_hashes'].items() if k.startswith(prefix+'.')}
    required={prefix+s for s in ('.queries.csv','.ids.i32','.dist.f32','.ops.csv',
                                '.warmup.queries.csv','.warmup.ids.i32','.warmup.dist.f32')}
    assert required <= set(hashes), 'unbound parent payload'
    for name,digest in hashes.items():assert sha(parent/name)==digest, ('changed admitted parent',name)
    return hashes


def verify(raw, parent, parent_quality, normalized, output):
    registration = read(raw/'PROFILE_REGISTERED.json')
    assert registration['instrumentation_sha256'] == sha(HERE/'profile.py')
    assert registration['contract_sha256'] == sha(HERE/'CONTRACT.json')
    assert registration['prefix_sha256'] == sha(HERE/'REBUILD_PREFIX.txt')
    assert registration['binary_sha256'] == read(raw/'profile_build_clean/BUILD.json')['binary_sha256']
    normalized_hash = sha(normalized)
    assert normalized_hash == '7d0ff1767e79a2dbc1f8ea18e52d29015d3d5a99ce4491dab8836d75b5f40948'
    lines = normalized.read_text().splitlines()
    assert sum(x.startswith('Function:') for x in lines) == 112
    assert sum(x.endswith(';') for x in lines) == 74144
    assert sha(parent_quality) == 'b03505ad24615549011c31a17c7838e14c8fe55344309e8b0187be9ab3ba3f18'
    proof=read(parent_quality)
    assert sha(parent/'REGISTERED.json')==proof['evidence_binding']['registered_sha256']
    assert sha(parent/'RAW_ROWS.json')==proof['evidence_binding']['raw_rows_sha256']
    for name,digest in proof['evidence_binding']['guard_hashes'].items():
        if name.startswith('guard/round_1/'):assert sha(parent/name)==digest
    report = []
    for method in ('A','B'):
        parent_hashes=bind_parent(parent,proof,method)
        folder = raw/'profiles'/method; receipt = read(folder/'guard/receipt.json')
        assert receipt['exit_code'] == 0 and receipt['runtime_valid'] and receipt['stop_reason'] is None
        assert not any(x['foreign'] for x in read(folder/'guard/checks.json'))
        assert not read(folder/'guard/before.json')['apps'] and not read(folder/'guard/after.json')['apps']
        fresh = folder/'out'; old = parent/'outputs'/('round_1_'+method)
        queries = rows(Path(str(fresh)+'.queries.csv')); old_queries = rows(Path(str(old)+'.queries.csv'))
        assert len(queries) == 31 and queries == old_queries[:31]
        total = sum(int(r['count']) for r in queries)
        for suffix in ('.ids.i32','.dist.f32'):
            a = Path(str(fresh)+suffix).read_bytes(); b = Path(str(old)+suffix).read_bytes()
            assert len(a) == total*4 and len(b) == sum(int(r['count']) for r in old_queries)*4
            assert a == b[:total*4]
        for suffix in ('.queries.csv','.ids.i32','.dist.f32'):
            assert Path(str(fresh)+'.warmup'+suffix).read_bytes() == Path(str(old)+'.warmup'+suffix).read_bytes()
        fresh_states = rows(Path(str(fresh)+'.ops.csv')); old_states = rows(Path(str(old)+'.ops.csv'))
        assert len(fresh_states) == 51
        columns = ('step','flag','base_before','buffer_before','base_after','buffer_after')
        assert [{k:r[k] for k in columns} for r in fresh_states] == [{k:r[k] for k in columns} for r in old_states[:51]]
        report.append(dict(method=method,prefix_queries=31,prefix_output_items=total,
            complete_prefix_and_warmup_byte_identity_to_admitted_parent=True,
            parent_exhaustive_quality_sha256=sha(parent_quality),
            parent_output_hashes_checked=parent_hashes,analyst_sha256=sha(Path(__file__)),
            fresh_output_sha256={p.name:sha(p) for p in folder.glob('out.*')}))
    assert not output.exists()
    output.write_text(json.dumps(report,indent=2)+'\n')
    print('PASS guards, complete prefix/warmup/state identity and all normalized GPU functions')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','parent','parent-quality','normalized','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--raw-sass',type=Path)
    a=p.parse_args();assert __debug__
    if a.raw_sass:
        value=normalize_dump(a.raw_sass.read_text())
        if a.normalized.exists():assert a.normalized.read_text()==value
        else:a.normalized.write_text(value)
    verify(a.raw,a.parent,a.parent_quality,a.normalized,a.output)
