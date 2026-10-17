"""Bounded public CMS metadata capture, not a vector-service transaction trace."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import datetime as dt
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

FIELDS = {'rcid', 'pageid', 'revid', 'old_revid', 'timestamp', 'type'}
PARAMS = dict(action='query', format='json', formatversion='2', list='recentchanges',
              rcprop='ids|timestamp', rctype='edit|new', rcnamespace='0',
              rcstart='2026-10-16T00:00:00Z', rcend='2026-10-16T01:00:00Z',
              rcdir='newer', rclimit='500', maxlag='5')
BASE = 'https://en.wikipedia.org/w/api.php'


def sha(body):
    return hashlib.sha256(body).hexdigest()


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write('\n')


def validate(row):
    assert set(row) == FIELDS, 'Unexpected metadata fields; do not retain actors/text'
    assert row['type'] in ('edit', 'new')
    for key in ('rcid', 'pageid', 'revid', 'old_revid'):
        assert type(row[key]) is int and row[key] >= (0 if key == 'old_revid' else 1)
    assert PARAMS['rcstart'] <= row['timestamp'] <= PARAMS['rcend']
    assert row['type'] != 'new' or row['old_revid'] == 0


def capture(out, first=None):
    out.mkdir()
    records, events, seen, continuation = [], [], set(), {}
    for page in range(20):
        params = {**PARAMS, **continuation}
        url = BASE + '?' + urllib.parse.urlencode(params)
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        if page == 0 and first:
            body = first.read_bytes()
            transport = 'Retained pre-registration reachability probe'
        else:
            request = urllib.request.Request(url, headers={
                'User-Agent': 'GTSPP-Dependency-Opportunity-Research/1.0 '
                              '(https://github.com/wangwenqingqq/GTS-variants)'})
            with urllib.request.urlopen(request, timeout=30) as response:
                assert response.status == 200
                body = response.read(1_000_001)
            transport = 'Read-only HTTPS API'
        assert len(body) <= 1_000_000
        obj = json.loads(body)
        assert not obj.get('error') and not obj.get('warnings'), obj
        rows = obj['query']['recentchanges']
        assert len(rows) <= 500
        for row in rows:
            validate(row)
            assert row['rcid'] not in seen, 'Duplicate source event; do not silently deduplicate'
            assert not events or events[-1]['timestamp'] <= row['timestamp']
            seen.add(row['rcid'])
            events.append(row)
        filename = f'page_{page:02d}.json'
        with (out / filename).open('xb') as f:
            f.write(body)
        records.append(dict(file=filename, url=url, retrieved_UTC=started,
                            transport=transport, bytes=len(body), sha256=sha(body)))
        continuation = obj.get('continue', {})
        if not continuation:
            break
    with (out / 'events.jsonl').open('x') as f:
        for row in events:
            f.write(json.dumps(row, sort_keys=True) + '\n')
    receipt = dict(passed=True, source_grade='A: upstream public CMS observations only',
                   vector_service_trace=False, complete_requested_interval=not continuation,
                   truncated_at_registered_cap=bool(continuation), page_count=len(records),
                   event_count=len(events), retained_fields=sorted(FIELDS), pages=records,
                   normalized=dict(file='events.jsonl', bytes=(out/'events.jsonl').stat().st_size,
                                   sha256=sha((out/'events.jsonl').read_bytes())), GPU_starts=0)
    save(out / 'CAPTURE.json', receipt)
    return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--first', type=Path)
    a = p.parse_args()
    result = capture(a.out, a.first)
    print('CAPTURE_PASS', result['event_count'], result['page_count'],
          'complete', result['complete_requested_interval'], 'GPU starts 0')
