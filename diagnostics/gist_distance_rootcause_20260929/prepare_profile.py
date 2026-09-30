#!/usr/bin/env python3
"""Generate a query-only Nsight Systems driver for the four modes."""
import argparse
from pathlib import Path
import subprocess
import sys

from prepare_rootcause import once


def main():
    p = argparse.ArgumentParser()
    p.add_argument('out', type=Path)
    a = p.parse_args()
    subprocess.run([sys.executable, str(Path(__file__).with_name('prepare_rootcause.py')),
                    str(a.out)], check=True)
    path = a.out / 'graph_bench.cu'
    s = path.read_text()
    s = once(s, '#include <cstdlib>', '#include <cstdlib>\n#include <cuda_profiler_api.h>')
    s = once(s, '    double cpu_start=cpu_time();auto loop=Clock::now();',
             '    ck(cudaProfilerStart());\n    double cpu_start=cpu_time();auto loop=Clock::now();')
    s = once(s, '    double loop_s=seconds(loop),cpu_s=cpu_time()-cpu_start;',
             '    double loop_s=seconds(loop),cpu_s=cpu_time()-cpu_start;\n    ck(cudaProfilerStop());')
    path.write_text(s)
    runner = a.out / 'run.py'
    script = runner.read_text()
    script = once(script, "['--cuda-graph-trace=node'] if tool=='nsys-node' else []",
                  "['--cuda-graph-trace=node','--capture-range=cudaProfilerApi','--capture-range-end=stop'] if tool=='nsys-range' else (['--cuda-graph-trace=node'] if tool=='nsys-node' else [])")
    script = once(script, "'nsys','nsys-node','memcheck'", "'nsys','nsys-node','nsys-range','memcheck'")
    runner.write_text(script)


if __name__ == '__main__':
    main()
