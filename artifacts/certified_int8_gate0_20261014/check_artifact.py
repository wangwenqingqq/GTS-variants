#!/usr/bin/env python3
"""Local admission/schema and exact-rational witnesses; never quantize or scan."""
import argparse
from fractions import Fraction as F
import hashlib
import json
from math import isqrt
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parent


def require(ok,message):
    if not ok:raise AssertionError(message)


def read(p):return json.loads(Path(p).read_text())


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dot(a,b):return sum((F(x)*F(y) for x,y in zip(a,b)),F(0))


def norm(a):
    v=dot(a,a);p=isqrt(v.numerator);q=isqrt(v.denominator)
    require(p*p==v.numerator and q*q==v.denominator,'witness norm not rational')
    return F(p,q)


def interval(center,eq,ex):return max(F(0),center-eq-ex),center+eq+ex


def classify(lower,upper,r):
    if lower>r:return 'CERT_REJECT'
    return 'CERT_ACCEPT' if upper<=r else 'AMBIGUOUS_FALLBACK'


def algebra():
    witnesses=[];qt=(4,0);xt=(0,0);center=norm(tuple(a-b for a,b in zip(qt,xt)))
    lower,upper=interval(center,F(1),F(1))
    for q,x in [((3,0),(1,0)),((5,0),(-1,0))]:
        distance=norm(tuple(a-b for a,b in zip(q,x)))
        require(lower<=distance<=upper,'triangle witness failed')
        for radius in map(F,(0,1,2,4,6,7)):
            label=classify(lower,upper,radius)
            require(not(label=='CERT_REJECT' and distance<=radius),'reject equality/false rejection')
            require(not(label=='CERT_ACCEPT' and distance>radius),'accept equality/false acceptance')
            witnesses.append({'q':list(q),'x':list(x),'r':str(radius),'lower':str(lower),'upper':str(upper),'exact_distance':str(distance),'decision':label})
    require(classify(F(0),F(0),F(0))=='CERT_ACCEPT','zero/equality witness')
    # Mathematical IP-to-L2 relation only. This is not a floating reduction identity.
    q=(1,0);x=(3,4);qt=(1,0);xt=(3,0)
    eq=norm(tuple(a-b for a,b in zip(q,qt)));ex=norm(tuple(a-b for a,b in zip(x,xt)))
    b=eq*norm(x)+norm(qt)*ex;c=dot(qt,xt);a=dot(q,q)+dot(x,x)
    actual=dot(q,x);d2=dot(tuple(u-v for u,v in zip(q,x)),tuple(u-v for u,v in zip(q,x)))
    require(c-b<=actual<=c+b and a-2*(c+b)<=d2<=a-2*(c-b) and d2==a-2*actual,'IP/L2 witness failed')
    n2=960*127*127;diff2=960*254*254
    require(n2==15483840 and 2*n2==30967680 and diff2==61935360 and diff2<2**31,'INT32 bound differs')
    return {'status':'EXACT_RATIONAL_LOGICAL_CHECK_ONLY','triangle_cases':witnesses,'zero_equality_checked':True,'IP_to_L2_witness':{'A':str(a),'center_IP':str(c),'error_bound':str(b),'original_IP':str(actual),'original_L2_squared':str(d2),'L2_squared_lower':str(a-2*(c+b)),'L2_squared_upper':str(a-2*(c-b))},'INT32_limits':{'max_norm2':n2,'abs_dot_max':n2,'abs_twice_dot_max':2*n2,'max_integer_difference_squared':diff2,'fits_INT32':True},'quantizer_implemented':False,'residual_bound_fixture_validated':False,'dataset_pairs':0,'GPU_starts':0}


def check(repo):
    c=read(ROOT/'CONTRACT.json');w=c['workload'];closure=read(ROOT/'evidence/EXECUTION_CLOSURE.json')
    for p,digest in c['parent_files'].items():require(sha(repo/p)==digest,'frozen parent differs: '+p)
    identity=read(repo/'artifacts/progressive_gpu_gate2_20261013/evidence/INPUT_IDENTITY.json')
    require(w['N']==1000000 and w['D']==960 and w['planned_pairs']==32000000 and len(set(w['query_ids']))==32 and w['query_ids']==identity['query_ids'] and w['data_sha256']==identity['data_sha256'],'frozen workload differs')
    radius=struct.unpack('<f',struct.pack('<I',int(w['radius_bits'],16)))[0]
    require(radius*radius==float.fromhex(w['cutoff_hex']),'radius/squared cutoff differs')
    require(c['declared_parent_commit']=='1f71ad70b5dbf839ff6bf2360b0a1197aecc8006' and c['declared_parent_is_ancestor'] and c['parent_inputs_identical_to_declared_parent'],'parent scope differs')
    a=read(ROOT/'evidence/ADMISSION.json');require(a['verdict']==closure['final']=='SUBSUMED_PRIOR_ART','prior-art stop differs')
    require(a['PRIOR_ART_sha256']==sha(ROOT/'PRIOR_ART.md') and a['source_identities_sha256']==sha(ROOT/'evidence/SOURCE_IDENTITIES.json'),'admission identities differ')
    require(a['primary_direct_source']=='PVS_EAHR_2608_07152v1' and a['scope']=='broad core thesis, not identical ordered-FP64 L2 implementation','source scope overstated')
    for key in ('database_rows_quantized','population_pairs','remote_process_starts','GPU_starts','NCU_starts','NSYS_starts','Tensor_Core_starts'):
        require(c['execution'][key]==closure[key]==0,'unadmitted execution: '+key)
    require(not c['execution']['quantizer_implemented'] and closure['numerical_experiment_status']=='NOT_RUN','numerical success implied')
    require(read(ROOT/'evidence/ALGEBRA_WITNESSES.json')==algebra(),'logical witness receipt differs')
    for p in ('quantization/QUANTIZER.json','quantization/RESIDUAL_BOUNDS.json','quality/BOUND_QUALITY.json','quality/EXACTNESS.json','certificate/CLASSIFICATION.json','certificate/QUERY_DISTRIBUTIONS.json','certificate/MARGIN_BUCKETS.json'):
        require(read(ROOT/p)['status']=='NOT_RUN','unexecuted stage disguised: '+p)
    q=read(ROOT/'quality/EXACTNESS.json');require(q['FN'] is q['FP'] is q['bound_violations'] is None,'untested quality reported as zero')
    storage=read(ROOT/'cost/STORAGE.json');update=read(ROOT/'cost/UPDATE_BYTES.json');cost=read(ROOT/'cost/MODELED_BYTES.json')
    require(storage['INT8_sidecar_bytes']==968000000 and storage['FP32_keeper_bytes']==3840000000 and storage['total_vector_payload_bytes']==4808000000 and F(storage['storage_ratio_exact'])==F(601,480),'storage payload model differs')
    require(update['extra_maintained_payload_bytes_per_vector']==968 and update['raw_plus_sidecar_payload_bytes_per_insert']==4808 and not update['dynamic_trace_run'],'update claim differs')
    require(cost['status']=='NOT_MEASURED' and cost['mean_modeled_bytes'] is cost['fallback_count'] is None and cost['sidecar_source_floor_bytes']==968000000,'unmeasured cost implied')
    old=read(repo/'artifacts/exact_representation_gate1_20261012/bytes/STAGE_ACCOUNTING.json');strong=sum(x['coordinate_bytes'] for x in old['rows'])//32
    require(strong==1014828776==cost['historical_progressive_source_model_bytes'] and F(cost['maximum_source_byte_saving_vs_progressive_floor_exact'])==F(strong-968000000,strong),'source-model denominator differs')
    m=ROOT/'PUBLICATION_SET.json'
    if m.exists():
        manifest=read(m)
        for p,r in manifest['files'].items():require((ROOT/p).stat().st_size==r['bytes'] and sha(ROOT/p)==r['sha256'],'publication content differs: '+p)
        actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='PUBLICATION_SET.json'}
        require(actual==set(manifest['files']),'publication whitelist differs')
    print(json.dumps({'passed':True,'final':'SUBSUMED_PRIOR_ART','checks':'schema, frozen identities, rational witnesses, exact storage arithmetic; not a quantizer or GIST quality gate','population_pairs':0,'GPU_starts':0}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=ROOT.parent.parent);check(p.parse_args().repo)
