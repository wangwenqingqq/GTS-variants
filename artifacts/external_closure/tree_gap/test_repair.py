#!/usr/bin/env python3
"""Regression: an underfilled top-K maximum must not become a pruning bound."""
import heapq
from prepare_repair import repair_text

def retrieve(full_bound):
    candidates=[(0.,0),(0.,1),(.95255,2101),(.96125,374),(.96502,394),(1.,2),(1.1,3),(1.2,4)]
    answer=[];bound=float('inf')
    for distance,occurrence in candidates:
        if distance>bound:continue
        heapq.heappush(answer,(-distance,occurrence))
        if len(answer)>8:heapq.heappop(answer)
        if not full_bound or len(answer)==8:bound=-answer[0][0]
    return answer,bound

def check():
    assert len(retrieve(False)[0])==2
    answer,bound=retrieve(True);assert len(answer)==8 and bound==1.2
    assert {374,394}.issubset(i for _,i in answer)
    source='''#include "config.cuh"
__global__ void searchKnnD(){dis_k = dis_res;}
// Get low bounds
__global__ void getKnnBound(){float dis_k = 99999;dis_k = dis_res;knn_bound[bid] = dis_res;}
// Compute info
'''
    repaired=repair_text(source)
    assert 'isFullPQK(pq_a[idx])' in repaired and 'isFullPQK(pq_a[bid])' in repaired
    assert repaired.count('CUDART_INF_F')==2 and '<math_constants.h>' in repaired
    try:repair_text(repaired)
    except AssertionError:pass
    else:raise AssertionError('must reject already-patched input')
    print('PASS underfilled-heap counterexample, both call-site invariant and patch rejection')
if __name__=='__main__':check()
