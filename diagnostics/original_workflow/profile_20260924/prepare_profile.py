#!/usr/bin/env python3
"""Pinned reset baseline, bounded repeated workloads, and host-only NVTX scopes."""
import argparse
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import prepare as original
import repair
spec = importlib.util.spec_from_file_location('cpu_helper', HERE.parent.parent/'cpu_io/prepare.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
once = helper.replace_once


def wrap(text, first, last, label):
    assert text.count(first) == 1 and text.count(last) == 1, label
    a = text.index(first); b = text.index(last, a)+len(last)
    return text[:a]+'{ GTS_DIAG_SCOPE("'+label+'");\n'+text[a:b]+'\n}\n'+text[b:]


def kernels(texts):
    result = {}
    for name, text in texts.items():
        for m in re.finditer(r'__global__\s+void\s+(\w+)\s*\(', text):
            a = text.index('{', m.end()); depth = 1; b = a+1
            while depth:
                depth += (text[b] == '{')-(text[b] == '}'); b += 1
            result[name+'::'+m[1]] = hashlib.sha256(text[m.start():b].encode()).hexdigest()
    return result


def prepare(source, out):
    manifest = original.prepare(source, out)
    repair.repair(out)
    data = (out/'fixtures/data.txt').read_text().splitlines()
    rows = [list(map(int, x.split())) for x in data[1:]]
    query_ops = [(2, 0)]*128
    cycle = [(2, 0),(0, 0),(2, 0),(1, original.N),(2, 0)]
    cycle += [(0, 0)]*10+[(2, 0)]+[(1, original.N)]*10+[(2, 0)]
    mixed_ops = cycle*16
    for name, ops, counts in [('query128', query_ops, [1]*128),
                              ('mixed16', mixed_ops, [1,2,1,11,1]*16)]:
        expected = original.oracle(rows, ops, 0)
        assert expected == counts
        f = out/'fixtures'/(name+'.updates')
        f.write_text(str(len(ops))+'\n'+''.join(f'{flag} {idx}\n' for flag, idx in ops))
        manifest['cases'][name] = {'radius': 0, 'operations': len(ops), 'expected_counts': expected,
                                  'updates_sha256': original.sha(f)}
    manifest['scope'] = 'Synthetic count-validated workflow diagnostics; no representative performance claim.'
    manifest['continuation'] = 'query128 plus mixed16; row0 retained, peak live/physical tree rows 1010; CPU multiset oracle.'
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    baseline = out/'variants/rnum_reset'
    before = {name: (baseline/name).read_text() for name in manifest['source_sha256']}
    after = dict(before)
    for name, functions in {
        'include/file.cuh': [('load','input.load')],
        'include/tree.cuh': [('indexConstru','build.total')],
        'include/update.cuh': [('loadUpdate','input.updates'),('updateIndexRnn','update.total'),('searchIndexRnnUpdate','tree.query')],
        'include/search_naive.cuh': [('searchNaiveRnn','buffer.query')],
    }.items():
        for function, label in functions:
            after[name] = helper.function_scope(after[name], function, label)
    t = after['include/tree.cuh']
    sort = 'thrust::sort_by_key(thrust::device, dis_list, dis_list + data_info[1], id_list);'
    t = once(t, sort, '{ GTS_DIAG_SCOPE("build.sort"); '+sort+' }')
    after['include/tree.cuh'] = t
    t = after['include/update.cuh']
    for anchor, label in [
        ('if (update_list[i].update_flag == 0)\n\t\t{','operation.insert'),
        ('if (in_size == MAX_IN_SIZE)\n\t\t\t{','operation.rebuild'),
        ('else if (update_list[i].update_flag == 1)\n\t\t{','operation.delete'),
        ('\t\telse\n\t\t{\n\t\t\tcount_update_s++;','operation.query'),
        ('\t\t\telse\n\t\t\t{\n\t\t\t\tCHECK(cudaMemset(is_delete_in, 0, in_size * sizeof(int)));','delete.buffer_compaction'),
    ]:
        pos = anchor.index('{')+1
        t = once(t, anchor, anchor[:pos]+'\n GTS_DIAG_SCOPE("'+label+'");'+anchor[pos:])
    a = t.index('\twhile ((cur_level < tree_h))'); b = t.index('\tfor (int i = 0; i < qnum;', a)
    t = t[:a]+'\t{ GTS_DIAG_SCOPE("tree.traverse");\n'+t[a:b]+'\t}\n'+t[b:]
    a = t.index('\t\tleafProcessRnnUpdate<<<'); b = t.index('\t\tcudaDeviceSynchronize();', a)+len('\t\tcudaDeviceSynchronize();')
    t = t[:a]+'\t\t{ GTS_DIAG_SCOPE("tree.leaf");\n'+t[a:b]+'\n\t\t}\n'+t[b:]
    t = wrap(t, '\t\tresult_num[0] = thrust::reduce', '\t\tcudaFree(query_qid);', 'tree.result_assembly')
    t = wrap(t, '\t\t\ttotal_result_num = qresult_count[0] + rnum[0];', '\t\t\tCHECK(cudaFree(result_dis));', 'query.final_assembly')
    after['include/update.cuh'] = t
    t = '#include "gts_cpu_io_profile.hpp"\n'+after['src/main.cu']
    anchor = 'int main(int argc, char **argv)\n{'
    t = once(t, anchor, anchor+'''
    if (argc < 6) return 64;
    GtsDiagDump gts_dump;
    GTS_DIAG_SCOPE("main.total");
    { GTS_DIAG_SCOPE("runtime.init");
      gts_diag_configure();
      if (cudaFree(nullptr) != cudaSuccess) return 65;
      unsigned flags=0;
      if (cudaGetDeviceFlags(&flags) != cudaSuccess) return 66;
      std::fprintf(stderr,"GTS_FLAGS,%u\\n",flags);
    }
''')
    after['src/main.cu'] = t
    assert kernels(before) == kernels(after), 'GPU kernel source must remain unchanged'
    dest = out/'variants/profile'
    for name, text in after.items():
        f = dest/name; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(text)
    shutil.copy2(HERE.parent.parent/'cpu_io/profile.hpp', dest/'include/gts_cpu_io_profile.hpp')
    diff = ''.join(''.join(difflib.unified_diff(before[n].splitlines(True), after[n].splitlines(True),
                                              fromfile='rnum_reset/'+n, tofile='profile/'+n)) for n in before)
    (dest/'PATCH.diff').write_text(diff)
    record = {'variant': 'profile', 'base_variant': 'rnum_reset',
              'source_sha256': {str(f.relative_to(dest)): original.sha(f) for f in sorted(dest.rglob('*')) if f.is_file() and f.name != 'PATCH.diff'},
              'kernel_source_sha256': kernels(after), 'kernel_source_unchanged': True,
              'patch_sha256': original.sha(dest/'PATCH.diff'),
              'scope': 'Host timing/NVTX only; nested inclusive ranges must not be summed; existing synchronization retained.'}
    (dest/'VARIANT.json').write_text(json.dumps(record, indent=2)+'\n')
    print('Prepared',len(kernels(after)),'unchanged GPU kernel bodies;',len(mixed_ops),'mixed operations, 80 exact query counts')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path); p.add_argument('out', type=Path)
    a = p.parse_args(); prepare(a.source.resolve(), a.out.resolve())
