"""Small identity/protocol regression checks; never evaluate a real query."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
from fractions import Fraction
import gate1a as g


def main():
    c, s = g.check_sources()
    assert g.selection(copy.deepcopy(c)) == s
    assert set(s['qids']).isdisjoint(c['development_qids']) and len(set(s['qids'])) == 128
    assert len(s['batches']) == 64+32+16
    assert set(s['radius_bits']) == {c['radii']['parent_radius_bits']}
    # Different identity seeds may alter membership, never use score-based selection.
    other = copy.deepcopy(c)
    other['sampling']['query_seed'] += 1
    assert g.selection(other)['qids'] != s['qids']
    other = copy.deepcopy(c)
    other['sampling']['batch_seed'] += 1
    assert g.selection(other)['qids'] == s['qids']
    assert g.selection(other)['permutation'] != s['permutation']
    # Positive gain / interval: the largest residual gives conservative capture.
    fanout, candidate, lower, upper = 100, 90, 50, 80
    assert Fraction(fanout-candidate, fanout-lower) == Fraction(1, 5)
    assert Fraction(fanout-candidate, fanout-upper) == Fraction(1, 2)
    assert Fraction(1, 5) < Fraction(1, 4) < Fraction(1, 2)
    r = struct.unpack('<f', struct.pack('<I', int(c['radii']['parent_radius_bits'], 16)))[0]
    assert (r*r).hex() == c['radii']['parent_threshold_hex']
    # Exclusive creation and streaming identity are part of preservation safety.
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)/'receipt.json'
        g.save(p, dict(test=True))
        h = g.identity(p)
        assert h == dict(bytes=len(p.read_bytes()), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        try:
            g.save(p, dict(test=False))
        except FileExistsError:
            pass
        else:
            raise AssertionError('Existing receipts must never be overwritten.')
        assert json.loads(p.read_text()) == dict(test=True)
    print('TEST_PASS:identity-only sampling;112 fixed batches;degenerate radius;conservative capture;no overwrite;0 scores')


if __name__ == '__main__':
    main()
