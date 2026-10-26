"""Fail if the compiled append path can mutate native tree metadata."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parent

def body(text, marker):
    start=text.index(marker); lo=text.index('{',start); hi=lo+1; depth=1
    while depth:
        depth+=(text[hi]=='{')-(text[hi]=='}');hi+=1
    return text[lo:hi]

def check(text):
    append=body(text,'void append(')
    forbidden=('node_list','nodes','min_dis','max_dis','LEAF_PAD_SLOTS','interval','indexConstru','rebuild','searchIndex','tree')
    for token in forbidden: assert token not in append, ('tree mutation/routing in append',token)
    calls=set(re.findall(r'\b([A-Za-z_]\w*)\s*\(',append))
    assert calls <= {'require','if','cudaMemcpy','ck','size_t','sp','xp'},calls
    return True

if __name__=='__main__':
    text=(ROOT/'dynamic.cu').read_text();assert check(text)
    for arm in ('g','p'):
        code=(ROOT/f'native_{arm}/update.cuh').read_text()
        for marker in ('LEAF_PAD_SLOTS','incremental_insert','updateIndexRnn(', 'getNewData('):assert marker not in code
        static=(ROOT/f'native_{arm}/search_v2.cuh').read_text()
        assert 'int le = qe + 1' not in static
        assert 'update_disk = false; // FIX1' in static and '// FIX2:' in static and 'FAILFAST:' in static
    assert 'source_p/' not in text and 'source_g/' not in text, 'unadapted archival include in executable'
    try:check(text.replace('void append(int uid,int payload){','void append(int uid,int payload){ nodes[0].min_dis=0;'))
    except AssertionError:pass
    else:raise AssertionError('mutation test was not rejected')
    print('PASS: append call graph restricted; historical insertion paths not compiled; mutation rejected')
