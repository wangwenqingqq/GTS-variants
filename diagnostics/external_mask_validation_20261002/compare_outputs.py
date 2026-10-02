#!/usr/bin/env python3
"""Compare two complete P0-format range output streams, including fields."""
import argparse
import filecmp
import json
import itertools
import os
import numpy as np


def records(path):
    with open(path,'rb') as f:
        while header:=f.read(8):
            if len(header)!=8:raise ValueError('short record header')
            qid,count=np.frombuffer(header,dtype='<i4')
            if count<0:raise ValueError('negative count')
            ids=f.read(int(count)*4)
            values=f.read(int(count)*4)
            if len(ids)!=count*4 or len(values)!=count*4:raise ValueError('short record')
            yield int(qid),np.frombuffer(ids,dtype='<i4'),np.frombuffer(values,dtype='<f4')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('reference')
    p.add_argument('candidate')
    a = p.parse_args()
    if (os.path.getsize(a.reference)==os.path.getsize(a.candidate) and
            filecmp.cmp(a.reference,a.candidate,shallow=False)):
        print(json.dumps({'qualification':'BITWISE_MATCH_ON_TESTED',
                          'false_negatives':0,'false_positives':0,
                          'order_mismatch_queries':0,'bitwise_field_mismatches':0,
                          'tolerance_field_mismatches':0,'nonfinite_fields':0,
                          'max_abs_error':0.0,'max_rel_error':0.0},indent=2))
        return
    first_ref=next(records(a.reference),None)
    first_got=next(records(a.candidate),None)
    if first_ref is None or first_got is None:
        raise ValueError('empty result')
    if first_ref[0] == first_got[0]:
        paired=itertools.zip_longest(records(a.reference),records(a.candidate))
    else:
        ref,got=list(records(a.reference)),list(records(a.candidate))
        if len(ref)!=len(got) or len({r[0] for r in ref})!=len(ref) or len({r[0] for r in got})!=len(got):
            raise ValueError('query count or duplicate IDs mismatch')
        got_by_qid={r[0]:r for r in got}
        if {r[0] for r in ref}!=set(got_by_qid):
            raise ValueError('query IDs mismatch')
        paired=((r,got_by_qid[r[0]]) for r in ref)
    summary = dict(queries=0, reference_hits=0, candidate_hits=0,
                   false_negatives=0, false_positives=0, order_mismatch_queries=0,
                   bitwise_field_mismatches=0, tolerance_field_mismatches=0,
                   nonfinite_fields=0, max_abs_error=0.0, max_rel_error=0.0)
    for left,right in paired:
        if left is None or right is None or left[0]!=right[0]:
            raise ValueError('query ID order or count mismatch')
        _,ir,dr=left
        _,ig,dg=right
        summary['queries']+=1
        summary['reference_hits'] += len(ir)
        summary['candidate_hits'] += len(ig)
        if not np.array_equal(ir,ig):
            summary['order_mismatch_queries']+=1
            if len(np.unique(ir))!=len(ir) or len(np.unique(ig))!=len(ig):
                raise ValueError('duplicate result ID')
            summary['false_negatives']+=len(np.setdiff1d(ir,ig,assume_unique=True))
            summary['false_positives']+=len(np.setdiff1d(ig,ir,assume_unique=True))
            _,r_index,g_index=np.intersect1d(ir,ig,assume_unique=True,return_indices=True)
            dr=dr[r_index];dg=dg[g_index]
        finite=np.isfinite(dg)
        summary['nonfinite_fields']+=int(np.count_nonzero(~finite))
        dr=dr[finite];dg=dg[finite]
        if len(dr):
            error=np.abs(dg.astype(np.float64)-dr.astype(np.float64))
            tol=1e-7+1e-5*np.abs(dr.astype(np.float64))
            summary['bitwise_field_mismatches']+=int(np.count_nonzero(
                dr.view('<u4')!=dg.view('<u4')))
            summary['tolerance_field_mismatches']+=int(np.count_nonzero(error>tol))
            summary['max_abs_error']=max(summary['max_abs_error'],float(error.max()))
            summary['max_rel_error']=max(summary['max_rel_error'],float(
                (error/np.maximum(np.abs(dr.astype(np.float64)),1e-30)).max()))
    summary['qualification'] = ('BITWISE_MATCH_ON_TESTED' if not any(summary[k] for k in
        ('false_negatives', 'false_positives', 'order_mismatch_queries', 'bitwise_field_mismatches', 'nonfinite_fields'))
        else 'MEMBERSHIP_MATCH_FIELDS_WITHIN_FROZEN_TOL_ON_TESTED' if not any(summary[k] for k in
        ('false_negatives', 'false_positives', 'order_mismatch_queries', 'tolerance_field_mismatches', 'nonfinite_fields'))
        else 'CONTRACT_MISMATCH')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
