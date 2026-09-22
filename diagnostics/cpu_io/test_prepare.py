#!/usr/bin/env python3
"""CPU-only regression check for the copy/instrumentation boundary."""
import hashlib
import json
from pathlib import Path
import re
import tempfile
from prepare import HERE, ROOT, function_scope, prepare, replace_once


def main():
    pins = json.loads((HERE / "SOURCE_PINS.json").read_text())["sha256"]
    assert "#define short float" in (ROOT / "include/config.cuh").read_text()
    tuner = (ROOT / "include/residual_tuner.cuh").read_text()
    method = re.search(r"void AutoTuneAndUpload\([^)]*\)\s*\{(.*?)\n    \}", tuner, re.S)
    assert method
    body = re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*', '', method.group(1))
    for unused in ("node_list", "num_nodes", "data_h", "id_list_h", "dim", "n", "metric_type"):
        assert not re.search(r"\b" + unused + r"\b", body), unused
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "copy"
        prepare(out)
        main = (out / "src/main.cu").read_text()
        assert main.index("gts_diag_configure();") < main.index("load(file,")
        assert main.count('GTS_DIAG_SCOPE("knn.unused_full_d2h")') == 1
        assert (out / "include/search_v2.cuh").read_text().count('GTS_DIAG_SCOPE("query.knn")') == 4
        assert (out / "include/gpu_timer.cuh").read_text().count("gts_diag_event_create(") == 4
        manifest = json.loads((out / "INSTRUMENTED_SHA256.json").read_text())
        assert all(hashlib.sha256((out / p).read_bytes()).hexdigest() == h for p, h in manifest.items())
        try:
            prepare(out)
        except FileExistsError:
            pass
        else:
            raise AssertionError("Existing output was not protected")
    for operation in (lambda: replace_once("x x", "x", "y"),
                      lambda: function_scope("void f() {}", "missing", "x")):
        try:
            operation()
        except ValueError:
            pass
        else:
            raise AssertionError("Ambiguous or missing anchor was accepted")
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in pins.items())
    print("PASS: pinned source unchanged, exact anchors, four overloads, protected output, generated hashes")


if __name__ == "__main__":
    main()
