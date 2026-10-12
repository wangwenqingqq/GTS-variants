#!/usr/bin/env python3
"""Normalize profiler-exported PC columns and ASLR-relative control targets only."""
import argparse,csv,hashlib,json,re
from pathlib import Path
from collections import Counter

def selected(text):
 assert re.search(r'^Kernel Name\s+pairwise_matrix_kernel\s*$',text,re.M)
 rows=[(int(m.group(1),16),m.group(2)) for l in text.splitlines() if (m:=re.match(r'^0x([0-9a-f]+)\s+(.+?)\s*$',l))]
 assert len(rows)>100 and all(b[0]-a[0]==16 for a,b in zip(rows,rows[1:]))
 base,last=rows[0][0],rows[-1][0];out=[];opcodes=Counter()
 for pc,inst in rows:
  inst=re.sub(r'\s+',' ',inst.strip());bare=re.sub(r'^@!?P\d+\s+','',inst);op=bare.split()[0];opcodes[op]+=1
  if op.startswith(('BRA','BSSY','CALL','RET')):
   def relative(m):
    n=int(m.group(0),16);assert base<=n<=last and (n-base)%16==0
    return hex(n-base)
   inst=re.sub(r'0x[0-9a-f]+',relative,inst)
  out.append(inst+';')
 normal='Function: pairwise_matrix_kernel\n'+'\n'.join(out)+'\n'
 return normal,dict(instructions=len(out),opcodes=dict(sorted(opcodes.items())),normalized_sha256=hashlib.sha256(normal.encode()).hexdigest(),normalization='Nsight-PC-ASLR-control-relative-v3; all predicates/mnemonics/other operands retained',relative_control_targets_only=True)

def metrics(p):
 rows=list(csv.reader(Path(p).read_text().splitlines()));assert len(rows)==3
 headers,units,values=rows;assert len(headers)==len(units)==len(values);v={k:dict(value=z,unit=u) for k,u,z in zip(headers,units,values)}
 number=lambda k:float(v[k]['value'].replace(',',''))
 seconds=number('gpu__time_duration.avg');assert v['gpu__time_duration.avg']['unit'] in ('ns','nsecond');seconds/=1e9
 bytes_=number('dram__bytes.sum');assert v['dram__bytes.sum']['unit']=='byte'
 add,mul,fma=[number('smsp__sass_thread_inst_executed_op_'+op+'_pred_on.sum') for op in ('fadd','fmul','ffma')];flops=add+mul+2*fma
 return dict(kernel=v['Kernel Name']['value'],block=v['Block Size']['value'],grid=v['Grid Size']['value'],duration_s=seconds,DRAM_bytes=bytes_,DRAM_read_bytes=number('dram__bytes_op_read.sum'),DRAM_write_bytes=number('dram__bytes_op_write.sum'),L2_bytes=number('lts__t_bytes.sum'),global_load_sectors=number('l1tex__t_sectors_pipe_lsu_mem_global_op_ld.sum'),global_store_sectors=number('l1tex__t_sectors_pipe_lsu_mem_global_op_st.sum'),FP32_pred_on_add=add,FP32_pred_on_mul=mul,FP32_pred_on_fma=fma,FP32_executed_flop_proxy=flops,FP64_pred_on=[number('smsp__sass_thread_inst_executed_op_'+op+'_pred_on.sum') for op in ('dadd','dmul','dfma')],DRAM_GBs=bytes_/seconds/1e9,FP32_executed_TFLOPs=flops/seconds/1e12,executed_intensity=flops/bytes_,DRAM_percent_of_peak=number('dram__throughput.avg.pct_of_peak_sustained_elapsed'),SM_throughput_percent=number('sm__throughput.avg.pct_of_peak_sustained_elapsed'),occupancy_percent=number('sm__warps_active.avg.pct_of_peak_sustained_active'),threads_per_warp_instruction=number('smsp__thread_inst_executed_per_inst_executed.ratio'),raw_metrics=v,scope='one first measured query selected main kernel; NCU10-pass diagnostic only; FMA counted2, not useful-work proxy or Host denominator')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('output',type=Path);a=p.parse_args();v={}
 for name in ('full','distance'):
  raw=a.directory/(name+'_selected.sass.txt');normal,meta=selected(raw.read_text());(a.directory/(name+'_relative_v3.normalized.sass')).write_text(normal);v[name]=dict(raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),**meta)
 assert v['full']['normalized_sha256']==v['distance']['normalized_sha256']
 # A true opcode change must survive normalization.
 raw=(a.directory/'full_selected.sass.txt').read_text();mutated=raw.replace('FFMA','FMUL',1);assert selected(raw)[1]['normalized_sha256']!=selected(mutated)[1]['normalized_sha256']
 v['metrics']={name:metrics(a.directory/(name+'_base.csv')) for name in ('read','distance','full')};v['raw_vendor_code_publication']='excluded; publish hashes, resource and numerical ledgers only';v['full_module_image_hash']='unavailable; library ELF and NCU report container hashes retained, not asserted to be a full JIT cubin hash'
 assert not a.output.exists();a.output.write_text(json.dumps(v,indent=2)+'\n')
