#!/usr/bin/env python3
"""Generate a diagnostic TILE_E runner with the P0 graph launch replaced by stream launches."""
from pathlib import Path
import sys

if len(sys.argv)!=3:
    raise SystemExit('usage: make_stream_scan.py source_batch_bench.cu output.cu')
source=Path(sys.argv[1]).read_text()
old='ck(cudaGraphLaunch(graph_exec,stream));'
assert source.count(old)==1
new='''if(mode!="TILE_E"||qt!=2)throw std::runtime_error("stream diagnostic requires TILE_E Q_T=2");
        ck(cudaMemcpyAsync(query_ids,host_query_ids,b*sizeof(int),cudaMemcpyHostToDevice,stream));
        ck(cudaMemcpyAsync(query_radii,host_query_radii,b*sizeof(float),cudaMemcpyHostToDevice,stream));
        launch<2>(true,dim3(blocks,(b+1)/2),0);
        collect(flags);'''
Path(sys.argv[2]).write_text(source.replace(old,new))
