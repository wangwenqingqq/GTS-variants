#!/usr/bin/env python3
"""Choose each external chunk from development totals only."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
source=ROOT/'chunk_screen.csv'
scores=defaultdict(float)
coverage=defaultdict(set)
for row in csv.DictReader(source.open()):
    key=(row['dataset'],int(row['B']),row['mode'],int(row['chunk_n']))
    scores[key]+=float(row['host_total_ms'])
    coverage[key].add(row['radius'])
grouped=defaultdict(list)
for (dataset,b,mode,chunk),total in scores.items():
    expected={'half','normal'} if dataset=='GIST' else {'normal'}
    assert coverage[dataset,b,mode,chunk]==expected
    grouped[dataset,b,mode].append((total,chunk))
assert len(grouped)==12
chosen={f'{dataset}:{b}:{mode}':min(options)[1]
        for (dataset,b,mode),options in grouped.items()}
(ROOT/'frozen_external.json').write_text(json.dumps(chosen,indent=2,sort_keys=True)+'\n')
(ROOT/'external_selection.json').write_text(json.dumps({
    'criterion':'minimum sum of Host-ready milliseconds over fixed development radii',
    'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'scores':{f'{dataset}:{b}:{mode}':[
        {'chunk_n':chunk,'host_total_ms':total} for total,chunk in sorted(options)]
        for (dataset,b,mode),options in grouped.items()},
    'chosen':chosen},indent=2,sort_keys=True)+'\n')
print(json.dumps(chosen,sort_keys=True))
