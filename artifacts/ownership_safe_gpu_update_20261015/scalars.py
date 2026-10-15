"""Compact process metrics;the complete per-ACK observations remain in hashed private raw files."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import analyze
SERVICE_FIELDS=('service_ms','events_ms','release_ms','query_ms','update_ms_including_statistics','other_ms','device_owned_peak_bytes')

def compact(job,checked):
    if job['kind']=='micro':return dict(job=job,micro=analyze.micro(checked,job))
    return dict(job=job,parent_quality=dict(metadata={k:checked['parent_quality']['metadata'][k] for k in SERVICE_FIELDS}))

def run(records):
    original=analyze.micro
    try:
        analyze.micro=lambda checked,job:checked['micro']
        return analyze.run([dict(job=r['job'],checked=r) for r in records])
    finally:analyze.micro=original
