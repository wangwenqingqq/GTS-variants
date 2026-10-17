"""Independent captured-source binding and CMS-only logical statistics."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import collections
import datetime as dt
import hashlib
import json
import urllib.parse
from pathlib import Path
from capture import BASE, PARAMS, validate
from replay import quantile, save


def analyze(folder):
    receipt = json.loads((folder/'CAPTURE.json').read_text())
    assert receipt['passed'] and receipt['GPU_starts'] == 0
    assert 1 <= receipt['page_count'] <= 20
    events, continuation, page_repeats = [], {}, []
    for i, record in enumerate(receipt['pages']):
        assert record['file'] == f'page_{i:02d}.json'
        body = (folder/record['file']).read_bytes()
        assert len(body) == record['bytes'] and hashlib.sha256(body).hexdigest() == record['sha256']
        assert record['url'] == BASE+'?'+urllib.parse.urlencode({**PARAMS, **continuation})
        page = json.loads(body)
        assert not page.get('error') and not page.get('warnings')
        rows = page['query']['recentchanges']
        assert len(rows) <= 500
        page_repeats.append(len(rows)-len({r['pageid'] for r in rows}))
        events.extend(rows)
        continuation = page.get('continue', {})
        assert continuation or i == len(receipt['pages'])-1
    assert receipt['page_count'] == len(receipt['pages'])
    assert receipt['complete_requested_interval'] == (not continuation)
    assert receipt['truncated_at_registered_cap'] == bool(continuation)
    assert not continuation or len(receipt['pages']) == 20
    assert len(events) == receipt['event_count']
    assert len({r['rcid'] for r in events}) == len(events)
    for i, row in enumerate(events):
        validate(row)
        assert not i or events[i-1]['timestamp'] <= row['timestamp']
    normalized = ''.join(json.dumps(row, sort_keys=True)+'\n' for row in events).encode()
    assert normalized == (folder/'events.jsonl').read_bytes()
    assert len(normalized) == receipt['normalized']['bytes']
    assert hashlib.sha256(normalized).hexdigest() == receipt['normalized']['sha256']
    assert {f.name for f in folder.iterdir()} == {
        'CAPTURE.json', 'events.jsonl', *(r['file'] for r in receipt['pages'])}
    counts, last = collections.Counter(), {}
    gaps, linked, unlinked, backwards_ids = [], 0, 0, 0
    for i, row in enumerate(events):
        page = row['pageid']
        counts[page] += 1
        if page in last:
            prior = last[page]
            linked += row['old_revid'] == prior['revid']
            unlinked += row['old_revid'] != prior['revid']
            gaps.append((dt.datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))-
                         dt.datetime.fromisoformat(prior['timestamp'].replace('Z', '+00:00'))).total_seconds())
        last[page] = row
        backwards_ids += bool(i and row['rcid'] < events[i-1]['rcid'])
    repeat = len(events)-len(counts)
    return dict(passed=True, source_grade='A: observed public CMS revisions',
                vector_service_trace=False, requested_UTC_interval=[PARAMS['rcstart'], PARAMS['rcend']],
                observed_UTC_interval=[events[0]['timestamp'], events[-1]['timestamp']] if events else None,
                complete_requested_interval=not continuation, events=len(events), distinct_pages=len(counts),
                types=dict(collections.Counter(r['type'] for r in events)), repeat_events=repeat,
                repeat_event_fraction=repeat/len(events) if events else None,
                repeated_pages=sum(n > 1 for n in counts.values()),
                events_per_page_p50=quantile(list(counts.values()), .5),
                events_per_page_p90=quantile(list(counts.values()), .9),
                events_per_page_max=max(counts.values(), default=0),
                repeated_page_gap_seconds_p50=quantile(gaps, .5),
                repeated_page_gap_seconds_p90=quantile(gaps, .9),
                within_capture_revision_links=linked, within_capture_revision_discontinuities=unlinked,
                globally_decreasing_rcid_transitions=backwards_ids,
                transport_pages=len(receipt['pages']), transport_page_repeated_targets=sum(page_repeats),
                transport_page_is_ACK=False, vector_client_requests='UNKNOWN', vector_ACK_boundaries='UNKNOWN',
                vector_initial_membership_and_physical_layout='UNKNOWN', queries_and_readers='UNKNOWN',
                M=None, F=None, weighted_elimination=None,
                physical_admission='REJECTED: missing vector mapping, initial storage and request/observer boundaries',
                input_capture_sha256=hashlib.sha256((folder/'CAPTURE.json').read_bytes()).hexdigest(),
                normalized_events_sha256=hashlib.sha256(normalized).hexdigest(), GPU_starts=0)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--capture', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = analyze(a.capture)
    save(a.out, result)
    print('METADATA_PASS', result['events'], result['distinct_pages'],
          'repeat', result['repeat_event_fraction'], 'not vector requests;GPU starts 0')
