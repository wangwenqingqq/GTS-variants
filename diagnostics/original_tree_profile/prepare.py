#!/usr/bin/env python3
"""Instrument pinned original source copies; do not optimize algorithms."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('archive_prepare', HERE.parent/'cpu_io/prepare.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
once = helper.replace_once
scope = helper.function_scope

EXPORT = r'''
    {
        GTS_DIAG_SCOPE("validation.export");
        int count = qnum_counter_prefix[qnum-1] + qnum_counter[qnum-1];
        if (count < 0 || count > qnum * (data_info[1] / 500 + PNUM + 1)) {
            std::fprintf(stderr, "AUDIT_INVALID_CANDIDATE_COUNT,%d\n", count); std::exit(91);
        }
        if (search_type == 1) {
            std::vector<int> counts(count);
            if (cudaMemcpy(counts.data(), result_counter, count*sizeof(int), cudaMemcpyDeviceToHost) != cudaSuccess) std::exit(92);
            for (int q=0; q<qnum; ++q) {
                long sum=0;
                for (int j=0;j<qnum_counter[q];++j) sum += counts.at(qnum_counter_prefix[q]+j);
                std::printf("GTS_AUDIT_RESULT,range,%d,%ld\n",q,sum);
            }
        } else {
            std::vector<float> distances(size_t(count)*k);
            if (cudaMemcpy(distances.data(), dis_knn, size_t(count)*k*sizeof(float), cudaMemcpyDeviceToHost) != cudaSuccess) std::exit(93);
            for (int q=0; q<qnum; ++q) {
                if (!qnum_counter[q]) { std::fprintf(stderr,"AUDIT_EMPTY_KNN,%d\n",q); std::exit(94); }
                std::printf("GTS_AUDIT_RESULT,knn,%d,%.9g\n", q, distances.at(size_t(qnum_counter_prefix[q])*k+k-1));
            }
        }
    }
'''


def prepare(source, out):
    pins = json.loads((HERE.parent/'original_tree_redundancy/SOURCE_PINS.json').read_text())['sha256']
    texts = {}
    for name, digest in pins.items():
        data = (source/name).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f'Source drift: {name}')
        texts[name] = data.decode()
    if out.exists():
        raise FileExistsError(out)
    groups = {
        'GTS/include/file.cuh': [('load','input.load'),('loadQuery','input.queries')],
        'GTS/include/tree.cuh': [('indexConstru','index.total')],
        'GTS/include/search_v2.cuh': [('searchIndexRnnV2','query.range'),('searchIndexKnnV2','query.knn')],
        'GTS/include/update.cuh': [('loadUpdate','input.updates'),('updateIndexRnn','update.total'),('searchIndexRnnUpdate','update.query')],
        'GPU-Tree/include/file.cuh': [('load','input.load'),('loadQuery','input.queries')],
        'GPU-Tree/include/pivot.cuh': [('getPivot','index.pivots')],
        'GPU-Tree/include/partition.cuh': [('getPartition','index.partition')],
        'GPU-Tree/include/bplus_tree.cuh': [('getIndex','index.nodes')],
        'GPU-Tree/include/search.cuh': [('search','query.total')],
    }
    for name, funcs in groups.items():
        for func, label in funcs:
            texts[name] = scope(texts[name],func,label)
    name = 'GTS/include/search_v2.cuh'
    assert texts[name].count('avail = avail / 2;') == 2
    texts[name] = texts[name].replace('avail = avail / 2;', 'avail = 256ULL * 1024 * 1024; // Diagnostic resource contract, see CONTRACT.md.')
    name = 'GPU-Tree/include/pivot.cuh'
    texts[name] = once(texts[name], 'srand(time(nullptr));', 'srand(0); // Fixed diagnostic seed, not an algorithm change.')
    name = 'GPU-Tree/include/bplus_tree.cuh'
    anchor = '\tfor (int i = 0; i < total_node_num; i++)\n\t{\n\t\tCHECK(cudaMalloc((void **)&(T[i]), sizeof(BPlusNode)));\n\t}'
    texts[name] = once(texts[name], anchor, '\t{ GTS_DIAG_SCOPE("index.node_allocations");\n'+anchor+'\n\t}')
    for variant in ['GTS','GPU-Tree']:
        name = variant+'/src/main.cu'
        t = '#include "gts_cpu_io_profile.hpp"\n'+texts[name]
        anchor = 'int main(int argc, char **argv)\n{'
        t = once(t, anchor, anchor+'\n\tif (argc < 6) return 64;\n\tGtsDiagDump gts_diag_dump;\n\tGTS_DIAG_SCOPE("main.total");\n\t{ GTS_DIAG_SCOPE("runtime.init"); gts_diag_configure(); if (cudaFree(nullptr) != cudaSuccess) return 65; }')
        if variant == 'GPU-Tree':
            # The original frees mode-inactive uninitialized local pointers.
            t = re.sub(r'(?m)^(\t(?:int|float|short|char|BPlusNode)\s+\*+\w+);',r'\1 = nullptr;',t)
            t = re.sub(r'(?m)^(\tObj \w+);',r'\1{};',t)
            t = once(t, '\ttime_search += diff.count();', '\ttime_search += diff.count();\n'+EXPORT)
        texts[name] = t
    for name, text in texts.items():
        dest = out/name; dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
    for variant in ['GTS','GPU-Tree']:
        shutil.copy2(HERE.parent/'cpu_io/profile.hpp',out/variant/'include/gts_cpu_io_profile.hpp')
    manifest = {str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(out.rglob('*')) if p.is_file()}
    (out/'INSTRUMENTED_SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source',type=Path);ap.add_argument('out',type=Path)
    args=ap.parse_args(); print(json.dumps(prepare(args.source,args.out),indent=2))
