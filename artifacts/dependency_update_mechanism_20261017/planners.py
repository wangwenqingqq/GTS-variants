"""CPU row-copy semantics;generic propagation has no descending-tail assumption."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python.')
def generic(commands):
    state={}
    for src,dst in commands:state[dst]=state.get(src,src)
    return {dst:src for dst,src in state.items() if src!=dst}

def tail(commands,n,b):
    end=n-b;origins=list(range(end,n));out={}
    for src,dst in commands:
        assert end<=src<n and 0<=dst<src
        origin=origins[src-end]
        if dst>=end:origins[dst-end]=origin
        else:out[dst]=origin
    out.update({end+i:src for i,src in enumerate(origins) if src!=end+i})
    assert not set(out)&set(out.values())
    return out

def dependencies(commands):
    writes={};depth={};raw=waw=0;levels=[]
    for src,dst in commands:
        raw+=writes.get(src,0);waw+=writes.get(dst,0)
        level=1+max(depth.get(src,-1),depth.get(dst,-1));levels.append(level)
        writes[dst]=writes.get(dst,0)+1;depth[dst]=level
    # Descending source rows can never be a later destination:WAR is impossible.
    return dict(RAW=raw,WAW=waw,WAR=0,levels=max(levels,default=-1)+1)
