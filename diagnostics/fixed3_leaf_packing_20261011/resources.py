#!/usr/bin/env python3
"""Pin the selected leaf function and review baseline-relative static resources."""
import argparse,collections,hashlib,json,re
from pathlib import Path
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def review(root):
    result={}
    for mode in ('G0','G1','G2'):
        text=(root/(mode+'.sass.txt')).read_text()
        parts=[x for x in text.split('Function : ') if x.splitlines()[0].startswith('_Z14dataProcessKnn')]
        assert len(parts)==1;part=parts[0];name=part.splitlines()[0].strip();lines=[]
        for line in part.splitlines()[1:]:
            if re.match(r'\s*/\*[0-9a-f]+\*/',line):
                code=re.sub(r'/\*.*?\*/','',line).strip()
                if code:lines.append(code)
        normalized='\n'.join(lines)+'\n'
        ops=collections.Counter(re.sub(r'^@!?P\d+\s+','',x).split()[0].split('.')[0] for x in lines)
        dump=(root/(mode+'.resources.txt')).read_text().split('Function '+name+':',1)[1].splitlines()[1].strip()
        resource={k:int(v) for k,v in re.findall(r'(REG|STACK|SHARED|LOCAL):(\d+)',dump)}
        props=(root/(mode+'.build.log')).read_text().split('Function properties for '+name+'\n',1)[1].splitlines()[0]
        stack,stores,loads=map(int,re.findall(r'\d+',props));assert stores==loads==0 and stack==resource['STACK']
        result[mode]={'binary_sha256':sha(root/(mode+'.bench')),'function':name,
            'normalized_sass_sha256':hashlib.sha256(normalized.encode()).hexdigest(),
            'normalization':'Instruction lines only; address/encoding comments stripped; opcode and operands retained',
            'resources':resource,'ptxas_spill_store_bytes':stores,'ptxas_spill_load_bytes':loads,
            'instruction_count':len(lines),'opcode_counts':dict(ops),
            'resource_dump_sha256':sha(root/(mode+'.resources.txt')),'sass_dump_sha256':sha(root/(mode+'.sass.txt')),
            'build_log_sha256':sha(root/(mode+'.build.log'))}
    assert result['G0']['normalized_sass_sha256']==result['G1']['normalized_sass_sha256']
    assert result['G0']['resources']==result['G1']['resources']
    for key in ('STACK','LOCAL','SHARED'):assert result['G2']['resources'][key]==result['G0']['resources'][key]
    return {'pass':True,'scope':'Static source/SASS admission only; no dynamic spill/occupancy or performance claim',
        'admission':'G0/G1 leaf SASS and resources identical; no additional stack/local/shared allocation; zero ptxas spills; G2 register increment retained for performance attribution',
        'modes':result}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args()
    with (a.root/'RESOURCE_GATE.json').open('x') as f:json.dump(review(a.root),f,indent=2);f.write('\n')
    print('PASS selected leaf static resource gate')
