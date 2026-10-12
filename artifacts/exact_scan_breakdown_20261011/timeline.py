#!/usr/bin/env python3
"""Exclusive GPU interval attribution; runtime API waits remain overlapping evidence."""
import argparse,csv,json,sqlite3
from pathlib import Path
from collections import defaultdict

def merged(v):
 out=[]
 for a,b in sorted(v):
  if b<=a:continue
  if out and a<=out[-1][1]:out[-1][1]=max(b,out[-1][1])
  else:out.append([a,b])
 return out

def length(v):return sum(b-a for a,b in merged(v))
def clip(v,a,b):return [(max(a,x),min(b,y)) for x,y in v if x<b and y>a]
def category(name):
 if name=='pairwise_matrix_kernel':return 'distance_fused_read_arithmetic'
 if name.startswith('flags_kernel'):return 'predicate'
 if name.startswith('fields_kernel'):return 'output_fields_and_observer'
 if 'DeviceCompactInitKernel' in name or 'DeviceSelectSweepKernel' in name:return 'compaction'
 return 'other_GPU_kernel'
def analyze(path,kind):
 c=sqlite3.connect(path);c.row_factory=sqlite3.Row;strings={r['id']:r['value'] for r in c.execute('select * from StringIds')}
 ranges=[dict(r) for r in c.execute('select * from NVTX_EVENTS where end is not null')]
 for r in ranges:r['label']=r['text'] if r['text'] is not None else strings.get(r['textId'],'')
 top=[r for r in ranges if r['label'].startswith('query_' if kind=='static' else 'op_')]
 assert len(top)==(32 if kind=='static' else 336)
 kernels=[dict(r) for r in c.execute('select * from CUPTI_ACTIVITY_KIND_KERNEL')];copies=[dict(r) for r in c.execute('select * from CUPTI_ACTIVITY_KIND_MEMCPY')];runtime=[dict(r) for r in c.execute('select * from CUPTI_ACTIVITY_KIND_RUNTIME')]
 enums={r['id']:r['label'] for r in c.execute('select * from ENUM_CUDA_MEMCPY_OPER')};rows=[];resources={}
 for k in kernels:
  name=strings[k['demangledName']];resources[name]={key:k[key] for key in ('gridX','gridY','gridZ','blockX','blockY','blockZ','registersPerThread','staticSharedMemory','dynamicSharedMemory','localMemoryPerThread','localMemoryTotal')}
 for q in sorted(top,key=lambda x:x['start']):
  a,b=q['start'],q['end'];by=defaultdict(list);counts=defaultdict(int);bytes_=defaultdict(int);apis=defaultdict(list);api_counts=defaultdict(int)
  for k in kernels:
   if k['start']<b and k['end']>a:
    name=strings[k['demangledName']];key=category(name);by[key].append((max(a,k['start']),min(b,k['end'])));counts[name]+=1
  for k in copies:
   if k['start']<b and k['end']>a:
    key='copy_'+enums[k['copyKind']];by[key].append((max(a,k['start']),min(b,k['end'])));bytes_[key]+=k['bytes']
  for r in runtime:
   if r['start']<b and r['end']>a:
    name=strings[r['nameId']];apis[name].append((max(a,r['start']),min(b,r['end'])));api_counts[name]+=1
  union=merged([x for intervals in by.values() for x in intervals]);active=length(union);sum_component=sum(length(v) for v in by.values());assert abs(sum_component-active)<=1,'unexpected GPU overlap; need exclusive interval sweep'
  row=dict(label=q['label'],host_span_ms=(b-a)/1e6,GPU_active_ms=active/1e6,exposed_Host_gap_ms=((b-a)-active)/1e6,GPU_components_ms={k:length(v)/1e6 for k,v in by.items()},copy_bytes=dict(bytes_),kernel_counts=dict(counts),API_inclusive_ms={k:length(v)/1e6 for k,v in apis.items()},API_counts=dict(api_counts),API_GPU_overlap_ms={k:sum(length(clip(union,x,y)) for x,y in merged(v))/1e6 for k,v in apis.items()})
  rows.append(row)
 components=defaultdict(float);copybytes=defaultdict(int);API=defaultdict(float);overlap=defaultdict(float);APIcounts=defaultdict(int)
 for row in rows:
  for key,value in row['GPU_components_ms'].items():components[key]+=value
  for key,value in row['copy_bytes'].items():copybytes[key]+=value
  for key,value in row['API_inclusive_ms'].items():API[key]+=value
  for key,value in row['API_GPU_overlap_ms'].items():overlap[key]+=value
  for key,value in row['API_counts'].items():APIcounts[key]+=value
 H=sum(r['host_span_ms'] for r in rows);G=sum(r['GPU_active_ms'] for r in rows)
 nested=[]
 if kind=='dynamic':
  for tag in ('insert.vector_H2D','insert.norm','delete.swap_last','delete.bookkeeping'):
   v=[r for r in ranges if r['label']==tag];nested.append(dict(label=tag,count=len(v),Host_inclusive_ms=sum((r['end']-r['start'])/1e6 for r in v),scope='inclusive enqueue/bookkeeping NVTX span, not completion ACK or additive with operation'))
 return dict(scope='diagnostic NSYS NVTX query/op spans, GPU activity union clipped per range; no profiler latency promotion',rows=rows,aggregate=dict(host_span_ms=H,GPU_active_ms=G,exposed_Host_gap_ms=H-G,GPU_active_fraction=G/H,components_ms=dict(components),copy_bytes=dict(copybytes),API_inclusive_ms=dict(API),API_GPU_overlap_ms=dict(overlap),API_counts=dict(APIcounts),allocation_API_calls=sum(v for k,v in APIcounts.items() if 'Alloc' in k or 'Free' in k or 'Malloc' in k)),resources=resources,nested=nested)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('sqlite',type=Path);p.add_argument('kind',choices=['static','dynamic']);p.add_argument('output',type=Path);a=p.parse_args();v=analyze(a.sqlite,a.kind);assert not a.output.exists();a.output.write_text(json.dumps(v,indent=2)+'\n')
