"""Logical age/cancellation stress;selection never uses physical-copy dependencies."""
import argparse,csv,json,hashlib,collections
from pathlib import Path
import numpy as np
from planners import generic,tail,dependencies

FIELDS=['batch','phase','before','rows','moves','assignments','eliminated','RAW','WAW','WAR','levels','fresh_victims','distinct_destinations']

def generate(n,family,seed,out):
    assert not out.exists();out.mkdir();k=n//2;b=512
    rng=np.random.default_rng(seed);original=np.random.default_rng(2026101501).permutation(n)[:k]
    owner=list(range(n));pos=list(range(n))+[-1]*k;labels=list(range(n));next_id=n;before=0
    victims=[];records=[];queries=[];bounds=[0,n//20,n//5,n*35//100,n//2]
    for phase,stop in enumerate(bounds):
        while before<stop:
            count=min(b,stop-before)
            if family=='W2_ORIGINAL':ids=list(map(int,original[before:before+count]))
            else:
                recent=0 if family=='UNIFORM_LIVE' else count//2 if family=='MIX_RECENT8' else count
                window=8*b if family=='MIX_RECENT8' else 4*b
                pool=[v for v in range(max(0,next_id-window),next_id) if pos[v]>=0]
                ids=list(map(int,rng.choice(pool,recent,replace=False))) if recent else []
                selected=set(ids)
                while len(ids)<count:
                    # Uniform live sampling;no weighting by row or future copy plan.
                    v=owner[int(rng.integers(n))]
                    if v not in selected:ids.append(v);selected.add(v)
                rng.shuffle(ids)
            assert len(set(ids))==count and all(pos[v]>=0 for v in ids)
            commands=[];entry={};fresh=sum(v>=n for v in ids)
            for v in ids:
                row=pos[v];last=len(owner)-1
                if row!=last:
                    for r in (last,row):
                        if r not in entry:entry[r]=labels[r]
                    commands.append((last,row));labels[row]=labels[last]
                    moved=owner[-1];owner[row]=moved;pos[moved]=row
                owner.pop();pos[v]=-1
            net=generic(commands);tp=tail(commands,n,count);assert net==tp
            # All affected capacity rows,not just the surviving logical prefix.
            assert all(labels[r]==entry[net.get(r,r)] for r in entry)
            assert not set(net)&set(net.values())
            record=dict(batch=len(records),phase=phase,before=before,rows=count,moves=len(commands),assignments=len(net),eliminated=len(commands)-len(net),fresh_victims=fresh,distinct_destinations=len(set(d for s,d in commands)),**dependencies(commands));records.append(record)
            victims.extend(ids)
            for _ in ids:
                row=len(owner);owner.append(next_id);pos[next_id]=row;labels[row]=next_id;next_id+=1
            before+=count
        queries.append(dict(phase=phase,mutation=before))
    assert len(victims)==k and len(owner)==n and next_id==n+k
    np.asarray(victims,dtype='<i4').tofile(out/'victims.i32')
    np.asarray(owner,dtype='<i4').tofile(out/'final_owner.i32');np.asarray(labels,dtype='<i4').tofile(out/'final_capacity_labels.i32')
    with (out/'batches.csv').open('x') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,lineterminator='\n');w.writeheader();w.writerows(records)
    moves=sum(r['moves'] for r in records);assignments=sum(r['assignments'] for r in records)
    ratios=[r['eliminated']/r['moves'] if r['moves'] else 0 for r in records]
    result=dict(N=n,batch=b,seed=seed,family=family,replacements=k,batches=len(records),query_windows=queries,native_moves=moves,final_assignments=assignments,elimination_ratio=1-assignments/moves if moves else 0,
        per_batch_elimination_quantiles={str(q):float(np.quantile(ratios,q)) for q in (0,.1,.5,.9,1)},RAW=sum(r['RAW'] for r in records),WAW=sum(r['WAW'] for r in records),WAR=0,
        level_distribution=dict(collections.Counter(r['levels'] for r in records)),batches_with_elimination=sum(r['eliminated']>0 for r in records),fresh_occurrence_deletions=sum(r['fresh_victims'] for r in records),
        generic_tail_plan_mismatches=0,entire_capacity_per_batch_provenance=True,selection_uses_physical_plan=False,real_application_trace=False,
        files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in out.iterdir() if p.is_file()},GPU_starts=0)
    with (out/'RESULT.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);a=p.parse_args();assert not a.work.exists();a.work.mkdir()
    contract=json.loads((Path(__file__).parent/'CONTRACT.json').read_text())['cpu_gate0'];records=[]
    for n in contract['N']:
        for seed in contract['seeds']:
            for family in contract['families']:
                record=generate(n,family,seed,a.work/f'N{n}_{family}_{seed}');records.append(record)
                print('STRUCTURE',n,family,seed,'elimination',record['elimination_ratio'],'RAW',record['RAW'],'fresh',record['fresh_occurrence_deletions'],flush=True)
    with (a.work/'RESULTS.json').open('x') as f:json.dump(dict(passed=True,records=records,GPU_starts=0),f,indent=2);f.write('\n')

if __name__=='__main__':main()
