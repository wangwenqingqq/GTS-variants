"""CPU-only source-derived replay; never loads a CUDA library or executes a kernel."""
import argparse
import concurrent.futures
import hashlib
import json
import math
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.parent / "query_tile_padding_20261012"
BATCHES = (1, 2, 4, 8, 16, 32, 64, 128)


def replay(batch):
    if type(batch) is not int or batch not in BATCHES:
        raise ValueError("outside the frozen batch sweep")
    # Policy4x4<float,4>: Kblk=32, rpt=cpt=4, tr=tc=16.
    mblk = nblk = 4 * 16
    nthreads = 16 * 16
    shared = 2 * (mblk + nblk) * (32 + 4) * 4
    query_tiles = math.ceil(batch / mblk)
    # Occupancy budget is inferred from the existing B1 launch, not a new API query.
    budget = 376
    y = min(query_tiles, budget)
    x = 1 if y == budget else min(math.ceil(1_000_000 / nblk), math.ceil(budget / y))
    scalar_pairs_coordinates = query_tiles * mblk * 1_000_000 * 960
    useful = batch * 1_000_000 * (3 * 960 - 1)
    return {
        "B": batch,
        "query_tiles": query_tiles,
        "padded_query_rows": query_tiles * mblk,
        "Mblk": mblk,
        "Nblk": nblk,
        "Kblk": 32,
        "block": [nthreads, 1, 1],
        "grid": [x, y, 1],
        "dynamic_shared_bytes": shared,
        "FP32_FADD": scalar_pairs_coordinates,
        "FP32_FFMA": scalar_pairs_coordinates,
        "FP32_FMUL": 0,
        "executed_FP32_proxy": 3 * scalar_pairs_coordinates,
        "useful_ops": useful,
        "inflation": 3 * scalar_pairs_coordinates / useful,
    }


def source_checks():
    index = json.loads((ROOT / "SOURCES.json").read_text())

    def read(row):
        with urllib.request.urlopen(row["url"], timeout=90) as response:
            raw = response.read()
        assert hashlib.sha256(raw).hexdigest() == row["sha256"], row["path"]
        if "git_blob" in row:
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            assert blob == row["git_blob"], row["path"]
        return (row["repository"], row["path"]), raw.decode()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        texts = dict(pool.map(read, index["files"]))
    cuvs = "NVIDIA/cuvs"
    base = "cpp/src/distance/detail/"
    dispatch = texts[cuvs, base + "pairwise_matrix/dispatch-inl.cuh"]
    jit = texts[cuvs, base + "pairwise_matrix/jit_lto_kernels/pairwise_matrix_jit.cuh"]
    kernel = texts[cuvs, base + "pairwise_matrix/jit_lto_kernels/pairwise_matrix_kernel.cu.in"]
    op = texts[cuvs, base + "distance_ops/l2_unexp.cuh"]
    accumulation = texts[cuvs, base + "pairwise_distance_base.cuh"]
    policy = texts["NVIDIA/raft", "cpp/include/raft/linalg/contractions.cuh"]
    loads = texts["NVIDIA/raft", "cpp/include/raft/linalg/detail/contractions.cuh"]
    assert "cutlass_op_unavailable = !ops::has_cutlass_op<OpT>::value" in dispatch
    assert "if constexpr (cutlass_op_unavailable)" in dispatch
    assert "get_cutlass_op" not in op and "const auto diff = x - y" in op
    assert "acc += diff * diff" in op and "use_norms = false" in op
    assert "Policy4x4<DataT, veclen>::Policy" in jit
    assert "pairwise_matrix_kernel" in kernel and "policies_t::@policy_type@" in kernel
    assert re.search(r"Policy4x4<float, _veclen>\s*\{\s*typedef KernelPolicy<float, _veclen, 32, 4, 4, 16, 16>", policy)
    core = accumulation.split("DI void accumulate_reg_tile", 1)[1].split("DI void accumulate()", 1)[0]
    assert "compute_distance<OpT, DataT, AccT, IdxT>" in core
    assert "this->m" not in core and "this->n" not in core
    assert "if (rowId < this->m && colId < this->n)" in accumulation
    assert "numBlocksPerSm" in accumulation and "P::Mblk" in accumulation
    assert "ldgDataX[i][j] = Zero()" in loads
    return len(texts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-sources", action="store_true", help="hash-check immutable upstream files in memory")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "PUBLIC_MANIFEST.json").read_text())["files"]
    actual = {str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.name != "PUBLIC_MANIFEST.json"}
    assert actual == set(manifest), "publication whitelist mismatch"
    for name, sha in manifest.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, name
    provenance = json.loads((ROOT / "SOURCE_PROVENANCE.json").read_text())
    for name, sha in provenance["prior_input_hashes"].items():
        assert hashlib.sha256((PRIOR / name).read_bytes()).hexdigest() == sha, name
    contract = json.loads((ROOT / "CONTRACT.json").read_text())
    assert contract["new_GPU_launch_budget"] == 0
    assert provenance["new_GPU_launches"] == 0 and not provenance["runtime_module_bytes_acquired"]
    assert provenance["original_campaign_verdict"] == "PARTIAL_PADDING"
    raw = json.loads((PRIOR / "counters/EXECUTED_WORK.json").read_text())
    stored = json.loads((ROOT / "CPU_REPLAY.json").read_text())
    assert stored["rows"] == [replay(b) for b in BATCHES]
    for b in BATCHES:
        expected, measured = replay(b), raw[str(b)]
        for key in ("FP32_FADD", "FP32_FFMA", "FP32_FMUL", "executed_FP32_proxy", "useful_ops", "inflation"):
            assert expected[key] == measured[key], (b, key)
        for key in ("grid", "block"):
            assert expected[key] == measured["geometry"][key], (b, key)
        assert expected["dynamic_shared_bytes"] == measured["geometry"]["shared_dynamic_bytes"]
    assert replay(64)["grid"] == [376, 1, 1] and replay(128)["grid"] == [188, 2, 1]
    for invalid in (0, 3, 256, True, 1.0):
        try:
            replay(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid batch accepted")
    if args.fetch_sources:
        print("PASS: immutable source hashes and route/policy assertions", source_checks())
    print("PASS: whitelist, frozen inputs, eight CPU replays; original PARTIAL gate retained; zero new GPU launches")


if __name__ == "__main__":
    main()
