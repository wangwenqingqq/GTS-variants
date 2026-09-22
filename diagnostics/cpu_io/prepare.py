#!/usr/bin/env python3
"""Create an instrumented COPY of the pinned archive; never edit its source."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Expected one anchor, found {text.count(old)}: {old[:80]!r}")
    return text.replace(old, new, 1)


def function_scope(text, name, label, expected=1):
    pattern = re.compile(r"(?m)^(?:void|int|static inline void) " + name + r"\([^;{}]*\)\s*\{")
    matches = list(pattern.finditer(text))
    if len(matches) != expected:
        raise ValueError(f"{name}: expected {expected} definitions, got {len(matches)}")
    return pattern.sub(lambda m: m.group(0) + f'\n\tGTS_DIAG_SCOPE("{label}");', text)


def prepare(out):
    pins = json.loads((HERE / "SOURCE_PINS.json").read_text())
    for name, digest in pins["sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Source drift: {name}; re-audit before instrumenting")
    if out.exists():
        raise FileExistsError(f"Refusing to replace {out}")
    # Transform everything in memory first, so anchor failures leave no partial copy.
    edits = {}
    groups = {
        "include/file.cuh": [("load", "input.load", 1)],
        "include/tree.cuh": [("indexConstru", "index.total", 1)],
        "include/incremental_insert.cuh": [
            ("initIncrementalInsert", "update.init_mirrors", 1),
            ("findTargetLeaf", "update.cpu_route", 1),
            ("incrementalInsert", "update.insert_total", 1),
            ("deleteIncrementalInsert", "update.delete_direct", 1)],
        "include/update.cuh": [
            ("updateIndexRnn", "update.total", 1),
            ("searchIndexRnnUpdate", "update.query", 1),
            ("ensureDeletePrefixValid", "update.delete_prefix", 1)],
        "include/search_v2.cuh": [
            ("searchIndexKnnV2", "query.knn", 4),
            ("searchIndexRnnV2", "query.range", 1)],
    }
    for name, funcs in groups.items():
        t = (ROOT / name).read_text()
        for func, label, count in funcs:
            t = function_scope(t, func, label, count)
        edits[name] = t
    t = edits["include/tree.cuh"]
    t = replace_once(t, "\t\tTN *h_nl =", '\t\tGTS_DIAG_SCOPE("index.fix_leaf_flags");\n\t\tTN *h_nl =')
    t = replace_once(t, "\t\t// Step 1: Copy node_list", '\t\tGTS_DIAG_SCOPE("index.padding_total");\n\t\t// Step 1: Copy node_list')
    t = replace_once(t, "\t\t\t\tTN *_sort_nodes =", '\t\t\t\tGTS_DIAG_SCOPE("index.cpu_leaf_sort");\n\t\t\t\tTN *_sort_nodes =')
    edits["include/tree.cuh"] = t
    t = (ROOT / "src/main.cu").read_text()
    t = '#include "gts_cpu_io_profile.hpp"\n' + t
    t = replace_once(t, "\tfile = argv[1];", '''\tgts_diag_configure();
\tGtsDiagDump gts_diag_dump;
\tGTS_DIAG_SCOPE("main.total");
\tfile = argv[1];''')
    t = replace_once(t, "\t\t// Copy data to CPU for initialization", '\t\t{ GTS_DIAG_SCOPE("knn.unused_full_d2h");\n\t\t// Copy data to CPU for initialization')
    t = replace_once(t, "\t\tdelete[] node_list_h;", "\t\tdelete[] node_list_h;\n\t\t}")
    t = replace_once(t, "\t\tauto calib_begin =", '\t\t{ GTS_DIAG_SCOPE("knn.calibration");\n\t\tauto calib_begin =')
    t = replace_once(t, '\t\tfprintf(fcost, "Time of calibration: %f\\n", time_calibration);', '\t\tfprintf(fcost, "Time of calibration: %f\\n", time_calibration);\n\t\t}')
    t = replace_once(t, '\t\t\tsaveK((char *)"result_ids.txt"', '\t\t\t{ GTS_DIAG_SCOPE("knn.save_results");\n\t\t\tsaveK((char *)"result_ids.txt"')
    t = replace_once(t, '(char *)"result_dists.txt", res_ids, res_dis, k, qnum);', '(char *)"result_dists.txt", res_ids, res_dis, k, qnum);\n\t\t\t}')
    edits["src/main.cu"] = t
    t = (ROOT / "include/gpu_timer.cuh").read_text()
    if t.count("cudaEventCreate(") != 4:
        raise ValueError("Timer event creation changed")
    edits["include/gpu_timer.cuh"] = t.replace("cudaEventCreate(", "gts_diag_event_create(")
    out.mkdir(parents=True)
    for name in pins["sha256"]:
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    shutil.copy2(HERE / "profile.hpp", out / "include/gts_cpu_io_profile.hpp")
    for name, text in edits.items():
        (out / name).write_text(text)
    manifest = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(out.rglob("*")) if p.is_file()}
    (out / "INSTRUMENTED_SHA256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared diagnostic-only source: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, help="New scratch directory (must not exist)")
    prepare(parser.parse_args().out.resolve())
