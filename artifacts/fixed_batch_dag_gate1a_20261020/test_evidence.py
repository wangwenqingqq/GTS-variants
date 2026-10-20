"""Reject counterfactual tampering on private copies, without scoring any query."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python.')
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import check_evidence as checker
import gate1a as g


def run(work, anchors_path, out):
    anchors = g.load(anchors_path)
    checker.validate_raw(work,anchors)
    out.mkdir()
    def change_json(path, update):
        value = g.load(path)
        update(value)
        path.write_bytes(g.encoded(value))
    def payload_and_receipt(root):
        path = root/'run/heldout/HELDOUT_QUERIES.f32'
        b = bytearray(path.read_bytes());b[0] ^= 1;path.write_bytes(b)
        def update(value):
            value['vectors'] = g.identity(path)
            value['records'][0]['vector_sha256'] = hashlib.sha256(b[:3840]).hexdigest()
        change_json(root/'run/heldout/INPUT_MANIFEST.json',update)
    def binary_and_receipt(root):
        path = root/'run/dev_campaign/build/solver'
        b = bytearray(path.read_bytes());b[-1] ^= 1;path.write_bytes(b)
        change_json(root/'run/dev_campaign/BUILD.json',lambda x:x.update(binary_sha256=g.sha(path)))
    mutations = [
        ('payload_and_receipt_synchronous',payload_and_receipt),
        ('empty_source_dictionary',lambda r:change_json(r/'run/dev_campaign/REGISTERED.json',lambda x:x.update(source_sha256={}))),
        ('missing_qualification',lambda r:(r/'run/dev_campaign/qualification/TESTS.json').unlink()),
        ('extra_attempt',lambda r:(r/'DRIVER_R2.stdout').write_text('counterfactual test only\n')),
        ('extra_feature_outside_heldout_folder',lambda r:(r/'run/counterfactual_feature.bin').write_bytes(b'test-only-not-a-real-feature')),
        ('missing_command',lambda r:(r/'run/dev_campaign/receipts/b2_g00.command.json').unlink()),
        ('modified_log',lambda r:(r/'run/dev_campaign/receipts/b2_g00.stdout').write_text('modified\n')),
        ('binary_and_receipt_synchronous',binary_and_receipt)]
    rejected = []
    for name, mutate in mutations:
        with tempfile.TemporaryDirectory(prefix='counterfactual-',dir=out) as tmp:
            root = Path(tmp)
            # Copy, never hard-link: mutations must not touch the sealed originals.
            for n in anchors['raw_files']:
                target = root/n
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(work/n,target)
            checker.validate_raw(root,anchors)
            mutate(root)
            try:
                checker.validate_raw(root,anchors)
            except AssertionError:
                rejected.append(name)
            else:
                raise AssertionError('Counterfactual mutation was admitted: '+name)
    assert len(rejected) == 8
    checker.validate_raw(work,anchors)
    result = dict(passed=True,counterfactual_mutations_rejected=rejected,
                  sealed_originals_unchanged=True,raw_anchors_sha256=g.sha(anchors_path),
                  heldout_evaluations=0,GPU_starts=0)
    g.save(out/'TESTS.json',result)
    print('EVIDENCE_TEST_PASS:8 tampering counterfactuals rejected;sealed originals unchanged;0 query scores')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--anchors',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    run(a.work.resolve(),a.anchors.resolve(),a.out.resolve())
