#!/usr/bin/env python3
"""Small synthetic SQLite regression for scope, overlap and API ownership."""
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('analysis',HERE/'analyze.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
(HERE/'local').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=HERE/'local') as tmp:
    p=Path(tmp)/'trace.sqlite';c=sqlite3.connect(p)
    c.executescript('''CREATE TABLE StringIds(id,value); INSERT INTO StringIds VALUES(1,'leaf'),(2,'cudaDeviceSynchronize');
CREATE TABLE NVTX_EVENTS(start,end,text,textId,globalTid);
CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(start,end,shortName,gridX,gridY,gridZ,blockX,blockY,blockZ,registersPerThread);
CREATE TABLE CUPTI_ACTIVITY_KIND_RUNTIME(start,end,nameId,globalTid);
CREATE TABLE CUPTI_ACTIVITY_KIND_MEMCPY(start,end,copyKind,bytes);
CREATE TABLE ENUM_CUDA_MEMCPY_OPER(id,name,label); INSERT INTO ENUM_CUDA_MEMCPY_OPER VALUES(1,'htod','HtoD');''')
    for i in range(3):
        t=i*1000
        c.executemany('INSERT INTO NVTX_EVENTS VALUES(?,?,?,?,?)',[(t,t+100,f'measured.query.{i}',None,9),(t+10,t+90,'stage.leaf_distance',None,9)])
        c.execute('INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES(?,?,?,?,?,?,?,?,?,?)',(t+20,t+70,1,2,1,1,32,1,1,20))
        c.executemany('INSERT INTO CUPTI_ACTIVITY_KIND_RUNTIME VALUES(?,?,?,?)',[(t+15,t+85,2,9),(t+95,t+96,2,9)])
        c.execute('INSERT INTO CUPTI_ACTIVITY_KIND_MEMCPY VALUES(?,?,?,?)',(t+40,t+80,1,128))
    c.commit();c.close();r=a.trace(p)
    for q in r['queries']:
        assert abs(q['gpu_temporal_fraction']-.6)<1e-12
        assert q['cuda_api']['cudaDeviceSynchronize']['calls']==2
        assert q['cuda_api_by_stage']['stage.leaf_distance']['cudaDeviceSynchronize']['calls']==1
        assert q['cuda_api_by_stage']['unattributed']['cudaDeviceSynchronize']['calls']==1
        assert q['gpu_um_fault_count'] is None and q['cpu_um_fault_events'] is None
        assert q['copies']['HtoD']['bytes']==128
print('PASS: three query scopes, GPU interval union, same-thread API attribution, uncollected UM remains unknown')
