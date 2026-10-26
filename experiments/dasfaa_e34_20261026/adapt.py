"""Strictly apply the approved correctness patch, then WORK-only instrumentation."""
import hashlib
import re
from pathlib import Path

ORIGINAL_SHA = {
    'P': '2268650537923903819c84245ca0b05050636cab59508d114a4033e952cce278',
    'G': 'b7a9c719c9fcd67ffdda8e4583da02341d0bbaa0038121f418873629466cddaf',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def apply_unified(source, patch):
    """No offsets/fuzz: every removed/context line must match the archived file."""
    lines = source.splitlines(keepends=True)
    out, cursor = [], 0
    hunks = re.split(r'^@@ .*? @@.*\n', patch, flags=re.M)
    headers = list(re.finditer(r'^@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@.*\n', patch, re.M))
    assert headers and len(hunks) == len(headers) + 1, 'unsupported unified diff'
    for header, hunk in zip(headers, hunks[1:]):
        start = int(header.group(1)) - 1
        assert start >= cursor
        out.extend(lines[cursor:start])
        old, new = [], []
        for line in hunk.splitlines(keepends=True):
            assert line[:1] in (' ', '+', '-'), 'unsupported patch line'
            if line[0] in ' -': old.append(line[1:])
            if line[0] in ' +': new.append(line[1:])
        assert lines[start:start + len(old)] == old, f'patch context at line {start + 1}'
        out.extend(new)
        cursor = start + len(old)
    out.extend(lines[cursor:])
    return ''.join(out)


def instrument_p(source):
    # These statements disappear completely in the timed build.
    source = source.replace('TN node = node_list[nid];\n\n\t\t\tdis_q = 0;',
                            'TN node = node_list[nid];\n\t\t\tWORK(0,1);\n\t\t\tdis_q = 0;')
    source = source.replace('data_id = id_list[node.lid + did]; // Data idx in dataset.',
                            'data_id = id_list[node.lid + did]; WORK(0,1); WORK(2,1); // Data idx in dataset.')
    source = source.replace('data_id = id_list[node.lid + did];\n',
                            'data_id = id_list[node.lid + did]; WORK(0,1); WORK(2,1);\n')
    source = source.replace('for (int did = tid; did < MAX_SIZE; did += THREAD_NUM)',
                            'if(tid==0) WORK(1,1);\n\tfor (int did = tid; did < MAX_SIZE; did += THREAD_NUM)')
    return source


def g_output_adapter(source):
    """Observe the existing sorted payload; change neither distances nor pruning."""
    kernel = r'''
// Output-only observer: native sorted payload is a leaf-slot index, not an ID.
int *audit_result_ids = nullptr;
__global__ void auditMergeKnnIds(int ls, int le, double *p, int off, int *sizes,
                                int level, int nup, TN *nodes, int *ids, int *out, int k) {
    int tid = blockDim.x * blockIdx.x + threadIdx.x;
    for (int i = tid; i < le-ls; i += gridDim.x * blockDim.x) {
        int slots = sizes[level] / (MAX_SIZE * 3 + 3);
        int first_leaf = (int)p[off + i*nup];
        int start = off + slots*3 + first_leaf*MAX_SIZE;
        int qid = (int)p[off + slots*2 + first_leaf];
        for (int j = 0; j < k; ++j) {
            int slot = (int)p[start+j];
            int leaf = slot / MAX_SIZE, within = slot % MAX_SIZE;
            int nid = (int)p[off+slots+leaf];
            TN node = nodes[nid];
            out[qid*k+j] = within < node.size && node.is_leaf ? ids[node.lid+within] : -1;
        }
    }
}
'''
    anchor = 'void searchIndexKnnV2(short *data_d'
    assert source.count(anchor) == 1
    source = source.replace(anchor, kernel + '\n' + anchor)
    anchor = 'mergeResKnn<<<block_num, THREAD_NUM>>>(ls, le, p_list_k, offset_p, size_list, cur_level, nnum_up, res_dis, k);'
    assert source.count(anchor) == 1
    source = source.replace(anchor, anchor + '\n\t\t\tif (audit_result_ids) auditMergeKnnIds<<<block_num, THREAD_NUM>>>(ls, le, p_list_k, offset_p, size_list, cur_level, nnum_up, node_list, id_list, audit_result_ids, k);')
    return source


def corrected(original, patch, arm, instrument=False):
    assert arm in ORIGINAL_SHA
    assert hashlib.sha256(original).hexdigest() == ORIGINAL_SHA[arm], f'wrong {arm} archive'
    result = apply_unified(original.decode(), patch)
    assert 'int le = qe + 1' not in result
    if arm == 'P' and instrument:
        result = instrument_p(result)
    if arm == 'G':
        result = g_output_adapter(result)
    return result
