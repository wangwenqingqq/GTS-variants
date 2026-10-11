#!/usr/bin/env python3
"""Reuse the frozen scalar exhaustive oracle; only add full score-vector export."""
import argparse,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'certified_navigation_20261010'

def prepare(out):
    original=BASE/'oracle_cpu.cpp';text=original.read_text()
    expected=json.loads((BASE/'evidence/CPU_ORACLE_RECEIPT.json').read_text())['source_sha256']
    if hashlib.sha256(original.read_bytes()).hexdigest()!=expected:raise ValueError('oracle source drift')
    replacements=[('require(argc==5,"oracle_cpu data qids K output.bin");','require(argc==6,"scores data qids K topk.bin all_scores.bin");'),
      ('std::vector<int> outids(q*k);','require(q==8 && n==1000000 && d==960 && k==8,"bounded GIST contract");\n    std::ofstream all(argv[5],std::ios::binary);int ah[4]={n,d,q,k};all.write((char*)ah,16);\n    std::vector<double> all_scores(n);\n    std::vector<int> outids(q*k);'),
      ('std::partial_sort(keys.begin(),keys.begin()+k,keys.end(),less);','for(int row=0;row<n;++row)all_scores[row]=keys[row].score;\n        all.write((char*)all_scores.data(),size_t(n)*8);require(bool(all),"full score export");\n        std::partial_sort(keys.begin(),keys.begin()+k,keys.end(),less);')]
    for a,b in replacements:
        if text.count(a)!=1:raise ValueError('source anchor drift')
        text=text.replace(a,b)
    out.mkdir(parents=True,exist_ok=False);(out/'compute_scores.cpp').write_text(text)
    (out/'SOURCE.json').write_text(json.dumps({'base_oracle_sha256':expected,'generated_sha256':hashlib.sha256(text.encode()).hexdigest(),
      'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'changes':['bounded 8-query shape gate','export ordered per-row FP64 scores before unchanged top-K selection'],'arithmetic_changed':False},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);prepare(p.parse_args().out)
