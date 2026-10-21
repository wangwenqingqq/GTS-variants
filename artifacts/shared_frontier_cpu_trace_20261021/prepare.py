"""Provision a real-genome-derived DNA population and frozen CPU trace inputs."""
if not __debug__:raise SystemExit('Assertions required')
import argparse,array,gzip,hashlib,json,random,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent

def identity(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return dict(bytes=p.stat().st_size,sha256=h.hexdigest())
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
def main(words,tloc,chr1,out):
 assert not out.resolve().is_relative_to(HERE.parent.parent.resolve())
 out.mkdir();c=json.loads((HERE/'CONTRACT.json').read_text());N=c['sample']['N'];extra=c['sample']['incoming'];sources={}
 with gzip.open(chr1,'rb') as f:
  assert f.readline().strip()==b'>chr1'
  seq=b''.join(line.strip().upper() for line in f)
 offsets=array.array('I',(i for i in range(0,len(seq)-107,108) if not seq[i:i+108].translate(None,b'ACGT')))
 assert len(offsets)>=1000000
 chosen=sorted(random.Random(2026102100).sample(range(len(offsets)),1000000))
 dna=out/'DNA_GRCh38_chr1_108.txt';positions=array.array('I')
 with dna.open('xb') as f:
  f.write(b'108 1000000 6\n')
  for i in chosen:
   o=offsets[i];f.write(seq[o:o+108]+b'\n');positions.append(o)
 assert positions.itemsize==4
 with (out/'DNA_GENOMIC_OFFSETS.u32').open('xb') as f:positions.tofile(f)
 save(out/'DNA_PROVENANCE.json',dict(source_url=c['data']['DNA_GRCh38_chr1_108']['source_url'],compressed_source=identity(chr1),reference='UCSC hg38 GRCh38 chr1,not original GTS DNA',reference_bases=len(seq),eligible_nonoverlapping_ACGT_windows=len(offsets),population=identity(dna),offsets=identity(out/'DNA_GENOMIC_OFFSETS.u32'),seed=2026102100,original_GTS_DNA=False))
 del seq,offsets,chosen,positions
 for name,src in [('Words',words),('DNA_GRCh38_chr1_108',dna),('TLoc',tloc)]:
  total=c['data'][name]['source_N'];seed=c['sample']['seeds'][name]
  selected=sorted(random.Random(seed).sample(range(total),N+extra));selection=set(selected)
  dst=out/(name+'.trace');picked=0;maxlen=0
  with src.open('rb') as f,dst.open('xb') as g:
   header=f.readline().split();assert int(header[1])==total
   assert int(header[2])==(2 if name=='TLoc' else 6)
   g.write(f'{name} {N+extra} {0 if name=="TLoc" else 1}\n'.encode())
   rows=0
   for i,line in enumerate(f):
    rows+=1
    if i in selection:
     text=line[:-1] if line.endswith(b'\n') else line
     if name!='TLoc':assert 0<len(text)<=128;maxlen=max(maxlen,len(text))
     else:assert len(text.split())==2
     g.write(str(i).encode()+b'\t'+text+b'\n');picked+=1
  assert rows==total and picked==N+extra
  qsets={str(s):random.Random(s).sample(range(N),c['sample']['B']) for s in c['sample']['query_seeds']}
  queries=set(q for qs in qsets.values() for q in qs)
  deleted=random.Random(2026102121).sample([i for i in range(N) if i not in queries],extra)
  save(out/(name+'.selection.json'),dict(dataset=name,source=identity(src),source_header=[int(x) for x in header],source_N=total,source_rows=selected,trace_input=identity(dst),queries=qsets,deleted=deleted,incoming=list(range(N,N+extra)),initial_N=N,max_string_bytes=maxlen,source_sample_seed=seed))
  for s,qs in qsets.items():
   with (out/(name+'.'+s+'.qid')).open('x') as f:f.write('\n'.join(map(str,qs))+'\n')
  with (out/(name+'.delete')).open('x') as f:f.write('\n'.join(map(str,deleted))+'\n')
  sources[name]=dict(source_N=total,source=identity(src),trace_input=identity(dst),selection=identity(out/(name+'.selection.json')))
 save(out/'INPUTS.json',dict(passed=True,contract=identity(HERE/'CONTRACT.json'),preparer=identity(HERE/'prepare.py'),sources=sources,GPU_starts=0,protected_GIST_heldout_accesses=0))
 print('INPUT_PREPARATION_PASS:Words,DNA-derived,TLoc;65536+32 rows each;no query-distance selection;0GPU',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--words',type=Path,required=True);p.add_argument('--tloc',type=Path,required=True);p.add_argument('--chr1',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.words,a.tloc,a.chr1,a.out)
