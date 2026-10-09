#!/usr/bin/env python3
"""Pinned target overlay: prepare/build only until TARGET_CORRECTNESS admits timing."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

if not __debug__:
    raise RuntimeError("Assertions must remain enabled; Python -O is unsupported")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PARENT = HERE.parent / 'unified_search_update'
sys.path.insert(0, str(PARENT))
spec = importlib.util.spec_from_file_location('frozen_unified_run', PARENT / 'run.py')
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def once(text, before, after):
    assert text.count(before) == 1, ('target anchor changed', before)
    return text.replace(before, after, 1)


def function(text, marker, replacement):
    start = text.index(marker)
    body = text.index('{', start)
    depth = 1
    end = body + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[:start] + replacement + text[end:]


def edit(path, transform):
    path.write_text(transform(path.read_text()))


def outside_repo(work):
    work=work.resolve()
    if work==REPO or REPO in work.parents:
        raise RuntimeError("Private build/evidence work must be outside the publication checkout")
    return work


def prepare(work, upstream=None):
    work=outside_repo(work)
    work.mkdir(parents=True, exist_ok=False)
    frozen = work / 'parent'
    frozen.mkdir()
    parent_manifest = parent.prepare(frozen, upstream)
    source = work / 'source'
    shutil.copytree(frozen / 'source', source)
    inc = source / 'include'
    for name in ('input.hpp', 'numeric.cuh', 'knn_live.cuh', 'parallel_range.cuh'):
        shutil.copy2(HERE / name, inc / name)
    edit(inc / 'tree.cuh', lambda s: once(s, '__global__ void getPivotDis', '#include "numeric.cuh"\n\n__global__ void getPivotDis'))
    edit(inc / 'tree.cuh', lambda s: once(s, 'u0i,u0n.pid,u0n.min_dis,u0n.size', 'u0i,u0n.pid,std::isfinite(u0n.min_dis)?u0n.min_dis:0.0f,u0n.size'))
    edit(inc / 'tree.cuh', lambda s: once(s, 'node_list[0].is_leaf = 0;\n\t\tsplit_list[0] = 1;',
                                        'node_list[0].is_leaf = data_info[1]<=MAX_SIZE;\n\t\tsplit_list[0] = data_info[1]>MAX_SIZE;'))
    edit(inc / 'tree.cuh', lambda s: once(s, '\n\tCHECK(cudaMallocManaged((void **)&max_node_num, sizeof(int)));', '\n    MAX_H=uk::tree_height(data_info[1]);\n\tCHECK(cudaMallocManaged((void **)&max_node_num, sizeof(int)));'))
    edit(inc / 'search.cuh', lambda s: function(s, '__global__ void findNextRnn(', (HERE / 'native_numeric.inc').read_text()))
    edit(inc / 'search_naive.cuh', lambda s: function(s, 'void searchNaiveRnn(', (HERE / 'buffer_numeric.inc').read_text()))
    edit(inc / 'update.cuh', lambda s: function(s, '__global__ void leafProcessRnnUpdate(', (HERE / 'leaf_numeric.inc').read_text()))
    def update(s):
        s = s.replace('data_info[1] * data_info[0] * sizeof(short)', 'uk::data_bytes(data_info[1],data_info[0])')
        s = s.replace('is_delete_prefix[tree_size - 1]', '(tree_size?is_delete_prefix[tree_size - 1]:0)')
        s = once(s, 'rex::bridge.refresh(node_list,empty_list,id_list,max_node_num[0],data_info[1],TREE_ORDER);',
                 'target::refresh_bounds(data_d,node_list,empty_list,id_list,max_node_num[0],data_info[1],data_info[0]);\n'
                 '\t\t\t\trex::bridge.refresh(node_list,empty_list,id_list,max_node_num[0],data_info[1],TREE_ORDER);')
        s = once(s, 'if(rex::bridge.mode)rex::bridge.search',
                 'target::require_epoch(data,nodes,info[1],info[0]);\n    if(rex::bridge.mode)rex::bridge.search')
        s = once(s, '\n\tCHECK(cudaMallocManaged((void **)&search_num, sizeof(int)));',
                 '\n    qnum_leaf=std::min(qnum_leaf,qnum);\n\tCHECK(cudaMallocManaged((void **)&search_num, sizeof(int)));')
        # No zero-grid launch when conservative pruning selects no leaves.
        s = once(s, 'leafProcessRnnUpdate<<<search_num[0], THREAD_NUM>>>',
                 'if(search_num[0])leafProcessRnnUpdate<<<search_num[0], THREAD_NUM>>>')
        return s
    edit(inc / 'update.cuh', update)
    def types(s):
        s = once(s, 'QUERY_DIM=128', 'QUERY_DIM=960')
        return once(s, 'int n,node_count,region_count,arity; uint64_t tree_epoch;',
                    'int n,node_count,region_count,arity; uint64_t tree_epoch; int d=128;')
    edit(inc / 'region_types.hpp', types)
    def bridge(s):
        s = once(s, 'info[0]==QUERY_DIM', '(info[0]==128||info[0]==960)')
        s = once(s, 'view.data=data;view.deleted=deleted;view.qids=qids;',
                 'target::require_epoch(data,(TN*)view.nodes,info[1],info[0]);\n'
                 '        require(view.tree_epoch==target::bounds.epoch,"stale PAR epoch");\n'
                 '        view.d=info[0];view.data=data;view.deleted=deleted;view.qids=qids;')
        return once(s, 'arity,++epoch};', 'arity,target::bounds.epoch};epoch=view.tree_epoch;')
    edit(inc / 'region_bridge.cuh', bridge)
    def output(s):
        s = s.replace('float distance=legacy_object_distance(v.data,id,v.qids[0],query);\n            if(distance<=radius)',
                      'float distance;bool keep=target::hit(v.data,v.d,id,query,radius,distance);\n            if(keep)')
        s = s.replace('float distance=legacy_object_distance(v.data,id,v.qids[0],query);\n                if(distance<=radius)',
                      'float distance;bool keep=target::hit(v.data,v.d,id,query,radius,distance);\n                if(keep)')
        s = once(s, 'for(int j=threadIdx.x;j<QUERY_DIM;j+=blockDim.x)query[j]=v.data[v.qids[0]*QUERY_DIM+j];',
                 'for(int j=threadIdx.x;j<v.d;j+=blockDim.x)query[j]=v.data[size_t(v.qids[0])*v.d+j];')
        return s
    edit(inc / 'region_output.cuh', output)
    def observer(s):
        s = once(s, 'if(n!=1000 || q<1', 'if(n<1 || n>1000000 || q<1')
        s = once(s, 'ids.resize(size_t(q)*(n+10)); fields.resize(ids.size());',
                 '// Full output is bounded independently of Q*N. Growth is timed in deliver().')
        s = once(s, 'if(count<0 || size_t(count)>ids.size()-offset)throw std::runtime_error("full-output buffer capacity");',
                 '''constexpr size_t maximum=(size_t(1)<<30)/8;
        if(count<0||size_t(count)>maximum-offset)throw std::runtime_error("full-output 1GiB budget exceeded; reject entire trace");
        size_t needed=offset+size_t(count);
        if(needed>ids.capacity()){size_t capacity=std::min(maximum,std::max(needed,2*ids.capacity()));
            ids.reserve(capacity);fields.reserve(capacity);}
        ids.resize(needed);fields.resize(needed);''')
        s = once(s, '<<ids.size()*8', '<<(ids.capacity()*sizeof(int)+fields.capacity()*sizeof(float))')
        return s
    edit(inc / 'u10_trace.hpp', observer)
    edit(source / 'src/main.cu', lambda s: s[:s.index('int main(int argc,char** argv)')] + (HERE / 'main.inc').read_text())
    sources = {str(p.relative_to(source)): sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
    manifest = dict(base_commit='0033cb2d1934768411ed1806c6729108f412c1e7',
                    parent_sources=parent_manifest['sources'], sources=sources,
                    overlay_files={p.name: sha(p) for p in HERE.iterdir() if p.is_file()})
    (work / 'PREPARED.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def build(work, nvcc):
    work=outside_repo(work)
    manifest=json.loads((work/'PREPARED.json').read_text())
    actual={str(p.relative_to(work/'source')):sha(p) for p in (work/'source').rglob('*') if p.is_file()}
    if actual!=manifest['sources']:
        raise RuntimeError("Prepared source identity changed; reject build")
    for name,digest in manifest['overlay_files'].items():
        if sha(HERE/name)!=digest:
            raise RuntimeError("Overlay identity changed; prepare a new private checkpoint")
    nvcc=shutil.which(nvcc)
    if not nvcc:
        raise RuntimeError("Installed nvcc was not found")
    nvcc=str(Path(nvcc).resolve())
    if (work/'BUILD.log').exists() or (work/'BUILD.json').exists():
        raise RuntimeError("Build checkpoint already exists; never overwrite it")
    (work / 'bin').mkdir(exist_ok=False)
    args = [nvcc, '-std=c++17', '-O3', '-arch=sm_120', '-lineinfo', '-rdc=true',
            '-Xnvlink=--ignore-host-info', '--ptxas-options=-v',
            '-I' + str(work / 'source/include'), work / 'source/src/main.cu', '-o', work / 'bin/target']
    parent.command(args, work / 'BUILD.log')
    manifest = dict(command=list(map(str, args)), binary_sha256=sha(work / 'bin/target'))
    (work / 'BUILD.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=('prepare', 'build'))
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--upstream', type=Path)
    p.add_argument('--nvcc', default='nvcc')
    a = p.parse_args()
    if a.stage == 'prepare':
        prepare(a.work, a.upstream)
    else:
        build(a.work, a.nvcc)
