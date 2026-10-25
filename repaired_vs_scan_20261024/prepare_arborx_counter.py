"""Count only native query work, not contended instrumentation during BVH build."""
import sys
from pathlib import Path

def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main(source,out):
    s=Path(source).read_text()
    s=once(s,'Kokkos::atomic_add(count,1ull);','if(count[2])Kokkos::atomic_add(count,1ull);')
    s=once(s,'counter("getter_calls",2);','counter("getter_calls",3);Kokkos::deep_copy(counter,0ull);')
    s=once(s,'log.build=millis(t);','log.build=millis(t);Kokkos::deep_copy(Kokkos::subview(counter,2),1ull);')
    s=once(s,'#if INSTRUMENT\n  Kokkos::deep_copy(counter,0ull);','#if INSTRUMENT\n  Kokkos::deep_copy(Kokkos::subview(counter,Kokkos::pair<int,int>(0,2)),0ull);')
    Path(out).write_text(s)
if __name__=='__main__':main(*sys.argv[1:])
