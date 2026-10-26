"""Derive range adapters and separately retain pinned, patched static kNN provenance."""
import hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent
SEARCH_PINS = {
    'p': ('2268650537923903819c84245ca0b05050636cab59508d114a4033e952cce278',
          'gtspp_search_v2_fixes.patch',
          'ccb0b634e06b0c4d2ab302144f0fd3fe17eef8b75ba9d2da90a5cb3af418100d'),
    'g': ('b7a9c719c9fcd67ffdda8e4583da02341d0bbaa0038121f418873629466cddaf',
          'gts_original_search_v2_fixes.patch',
          '1e129c1539df9c9180dbb76603f7db9ade7aa27d0a0bda9e09e46a9ad2e04a40'),
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def apply_exact_patch(original, patch):
    """Apply unified hunks only at their exact original offsets, without fuzz."""
    lines = original.splitlines(keepends=True)
    out = []; cursor = 0; hunks = 0
    diff = patch.splitlines(keepends=True); i = 0
    while i < len(diff):
        match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', diff[i])
        if not match:
            i += 1; continue
        lo = int(match.group(1)) - 1
        assert lo >= cursor, 'overlapping/reordered patch hunk'
        out.extend(lines[cursor:lo]); cursor = lo; i += 1; hunks += 1
        removed = added = 0
        while i < len(diff) and not diff[i].startswith('@@ '):
            line = diff[i]
            assert line and line[0] in ' +-', 'unsupported patch line'
            payload = line[1:]
            if line[0] in ' -':
                assert cursor < len(lines) and lines[cursor] == payload, ('patch context mismatch', cursor + 1)
                cursor += 1; removed += 1
            if line[0] in ' +':
                out.append(payload); added += 1
            i += 1
        assert removed == int(match.group(2) or 1), 'old hunk length mismatch'
        assert added == int(match.group(4) or 1), 'new hunk length mismatch'
    assert hunks, 'empty patch'
    out.extend(lines[cursor:])
    return ''.join(out)

def patch_static_search(name):
    expected_source, patch_name, expected_patch = SEARCH_PINS[name]
    source = ROOT/f'source_{name}'/'include'/'search_v2.cuh'
    patch = ROOT/'patches'/patch_name
    original = source.read_bytes(); delta = patch.read_bytes()
    assert sha(original) == expected_source, ('unapproved static kNN source', name)
    assert sha(delta) == expected_patch, ('unapproved correctness patch', name)
    fixed = apply_exact_patch(original.decode(), delta.decode())
    assert 'int le = qe + 1' not in fixed
    assert 'update_disk = false; // FIX1' in fixed and '// FIX2:' in fixed and 'FAILFAST:' in fixed
    target = ROOT/f'native_{name}'/'search_v2.cuh'
    target.parent.mkdir(exist_ok=True)
    target.write_text(fixed)
    return dict(source_sha256=sha(original), patch_sha256=sha(delta),
                patched_sha256=sha(fixed.encode()), executed=False,
                reason='The dynamic adapter executes searchIndexRnnUpdate, not static searchIndexKnnV2.')


def adapt(name):
    src = ROOT/f'source_{name}'/'include'; dst = ROOT/f'native_{name}'; dst.mkdir(exist_ok=True)
    tree = (src/'tree.cuh').read_text()
    search = (src/'search.cuh').read_text()
    update = (src/'update.cuh').read_text()
    update = update[update.index('__global__ void leafProcessRnnUpdate'):update.index('void updateIndexRnn(')]
    update = update.replace('if (is_delete[data_id] == 0)', 'if (is_delete[e1_stable_ids[data_id]] == 0)')
    def add_tanimoto(code):
        at = 0
        while True:
            hit = re.search(r'else if \(data_info\[2\] == 6\)', code[at:])
            if not hit: break
            start = at + hit.start(); brace = code.index('{', start); end = brace+1; depth=1
            while depth:
                depth += (code[end]=='{') - (code[end]=='}'); end+=1
            block = code[brace:end]
            left = re.search(r'int n = size_s\[(.*?)\];', block).group(1)
            right = re.search(r'int m = size_s\[(.*?)\];', block).group(1)
            result = re.search(r'(\w+) = table\[n\]\[m\]', block).group(1)
            branch = f"\nelse if (data_info[2] == 8) {{ {result} = e1_tanimoto(data_d + size_t({left})*data_info[0], data_d + size_t({right})*data_info[0], data_info[0]); }}\n"
            code=code[:end]+branch+code[end:]; at=end+len(branch)
        return code
    tree=add_tanimoto(tree);search=add_tanimoto(search);update=add_tanimoto(update)
    if name == 'p':
        old = re.search(r'\tMAX_H = computeMaxHeight\(TREE_ORDER, data_info\[1\]\);', tree)
        assert old
        tree = tree[:old.start()] + '''
    MAX_H = 1;
    for (int worst = data_info[1]; worst > MAX_SIZE;
         worst -= (TREE_ORDER-1)*(worst/TREE_ORDER)) ++MAX_H;
''' + tree[old.end():]
    # Historical insert/rebuild functions are intentionally not compiled.
    prefix = '#pragma once\n#include "search.cuh"\nint *is_delete = nullptr;\n__device__ int *e1_stable_ids;\n'
    if name == 'p':
        prefix += '''int update_ws_qnum_cap=0, update_ws_qnum_leaf_cap=0;
int update_ws_max_node_cap=0, update_ws_max_search_num_cap=0;
int *update_result_id_ws=nullptr;
float *update_result_dis_ws=nullptr;
int update_result_ws_cap=0;
'''
    for file, content in [('tree.cuh',tree),('search.cuh',search),('update.cuh',prefix+update)]:
        (dst/file).write_text(content)
    for file in ('config.cuh','file.cuh'):(dst/file).write_bytes((src/file).read_bytes())
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dst.iterdir())}

if __name__ == '__main__':
    static = {name:patch_static_search(name) for name in ('g','p')}
    result = {name:adapt(name) for name in ('g','p')}
    (ROOT/'evidence/native_source_hashes.json').write_text(json.dumps(result, indent=2)+'\n')
    (ROOT/'evidence/static_knn_patch_provenance.json').write_text(json.dumps(static, indent=2)+'\n')
