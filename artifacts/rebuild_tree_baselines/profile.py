#!/usr/bin/env python3
"""Host-only NVTX attribution of one registered rebuild; no new synchronization."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / 'unified_target_workflow/phase_b'
sys.path.insert(0, str(PARENT))
spec = importlib.util.spec_from_file_location('phase_b_prepare', PARENT / 'run.py')
parent = importlib.util.module_from_spec(spec); spec.loader.exec_module(parent)

HEADER = r'''#pragma once
#include <cuda_profiler_api.h>
namespace rb {
static bool enabled=false,active=false,seen=false;
inline void push(const std::string& name){if(active)nvtxRangePushA(name.c_str());}
inline void pop(){if(active)nvtxRangePop();}
inline void begin(int step){if(enabled){
    if(step!=48||seen)throw std::runtime_error("outside registered rebuild capture");
    seen=true;u10_ck(cudaProfilerStart());active=true;push("rb.event48");}}
inline void end(){if(active){pop();active=false;u10_ck(cudaProfilerStop());}}
}
'''


def once(text, old, new):
    assert text.count(old) == 1, ('changed source anchor', old)
    return text.replace(old, new, 1)


def prepare(work, upstream):
    manifest = parent.prepare(work, upstream)
    source = work / 'source'; inc = source / 'include'
    (inc / 'trace_rb.hpp').write_text(HEADER)
    p = source / 'src/main.cu'; s = p.read_text()
    s = once(s, '#include "u10_trace.hpp"', '#include "u10_trace.hpp"\n#include "trace_rb.hpp"')
    s = once(s, 'reset_service();if(warm)', 'reset_service();rb::enabled=!warm;if(warm)')
    p.write_text(s)
    p = inc / 'tree.cuh'; s = p.read_text()
    start = s.index('void indexConstru('); a, body = s[:start], s[start:]
    body = once(body, '    MAX_H=uk::tree_height', '    rb::push("rb.alloc_init");\n    MAX_H=uk::tree_height')
    body = once(body, '\twhile ((cur_level', '\trb::pop();\n\twhile ((cur_level')
    body = once(body, '\t\tgetPivotDis<<<', '\t\trb::push("rb.pivot[level="+std::to_string(cur_level)+",slots="+std::to_string(block_num)+",n="+std::to_string(data_info[1])+"]");\n\t\tgetPivotDis<<<')
    body = once(body, '\t\tthrust::sort_by_key', '\t\trb::pop();rb::push("rb.sort[level="+std::to_string(cur_level)+"]");\n\t\tthrust::sort_by_key')
    body = once(body, '\t\tnodeSplit<<<', '\t\trb::pop();rb::push("rb.split[level="+std::to_string(cur_level)+"]");\n\t\tnodeSplit<<<')
    body = once(body, '\t\tstart_idx +=', '\t\trb::pop();\n\t\tstart_idx +=')
    body = once(body, '\t\tsplit_num[0] = thrust::reduce', '\t\trb::push("rb.reduce[level="+std::to_string(cur_level-1)+"]");\n\t\tsplit_num[0] = thrust::reduce')
    body = once(body, 'max_node_num[0], 0);\n\t}', 'max_node_num[0], 0);rb::pop();\n\t}')
    body = once(body, '\tcudaFree(dis_list);', '\trb::push("rb.build_release");\n\tcudaFree(dis_list);')
    body = once(body, '\tcudaFree(pid_list);', '\tcudaFree(pid_list);rb::pop();')
    p.write_text(a + body)
    p = inc / 'update.cuh'; s = p.read_text()
    s = once(s, 'u10.begin_op(i,', 'if(rb::enabled&&i==48)rb::begin(i);u10.begin_op(i,')
    s = once(s, '\t\t\t\ttarget::refresh_bounds(data_d,', '\t\t\t\trb::push("rb.safe_refit");target::refresh_bounds(data_d,')
    s = once(s, '\t\t\t\trex::bridge.refresh(node_list,', '\t\t\t\trb::pop();rb::push("rb.PAR_refresh");rex::bridge.refresh(node_list,')
    s = once(s, '\t\t\t\tuk::live.refresh(data_d,', '\t\t\t\trb::pop();rb::push("rb.mirror_repack");uk::live.refresh(data_d,')
    s = once(s, 'u10.end_rebuild();', 'rb::pop();u10.end_rebuild();')
    s = once(s, 'u10.end_op(tree_size,in_size);', 'rb::push("rb.publish_ACK");u10.end_op(tree_size,in_size);if(rb::active){rb::pop();rb::end();}')
    p.write_text(s)
    # CUDA launch expressions and explicit synchronization count are unchanged.
    baseline = manifest['sources']
    manifest['profile_sources'] = {str(p.relative_to(source)): parent.sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
    manifest['baseline_sources'] = baseline
    manifest['sources'] = manifest['profile_sources']
    manifest['contract_sha256'] = parent.sha(HERE / 'CONTRACT.json')
    manifest['instrumentation_sha256'] = parent.sha(Path(__file__))
    (work / 'PROFILE_PREPARED.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (work / 'PREPARED.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--upstream', type=Path)
    parser.add_argument('--nvcc')
    a = parser.parse_args(); a.work = parent.base.outside_repo(a.work)
    prepare(a.work, a.upstream)
    if a.nvcc: parent.base.build(a.work, a.nvcc)
