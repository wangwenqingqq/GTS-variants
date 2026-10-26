"""Local-only Word orchestration checks; no NVML, SSH, GPU, or real signals."""
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import word_campaign as W

HERE = Path(__file__).resolve().parent


class WordRunnerTests(unittest.TestCase):
    def setUp(self):
        self.runtime_tmp = tempfile.TemporaryDirectory(dir=HERE)
        self.runtime_file = Path(self.runtime_tmp.name) / 'cupy_compiler.py'
        self.runtime_file.write_bytes(b'fixed compiler fixture')
        self.tmp = tempfile.TemporaryDirectory(dir=HERE)
        self.root = Path(self.tmp.name)
        self.epoch = self.root / 'runs/word_test'
        self.epoch.mkdir(parents=True)
        (self.root / 'logs').mkdir()
        self.vector = self.root / 'runs/vector'
        self.vector.mkdir()
        (self.vector / 'COMPLETE.json').write_text(json.dumps({'plan_processed': True}))
        (self.vector / 'admission.json').write_text(json.dumps({'index': 6, 'uuid': 'GPU-vector'}))
        (self.root / 'logs/active_epoch.txt').write_text(str(self.vector))
        self.env = patch.dict(os.environ, {'FAISS_PYTHON': '/usr/bin/python3',
                             'E34_SSH_FAILED': '0'}, clear=False)
        self.env.start()
        self.files = {}
        self.paths = {'word_manifest': 'WORD_MANIFEST.json', 'tree_binary': 'word_bin/word_tree',
                      'count_binary': 'word_bin/word_count',
                      'scan_script': 'resume/edit_scan.py', 'audit_script': 'resume/audit_word.py',
                      'oracle_binary': 'word_bin/edit_oracle', 'oracle_source': 'resume/edit_oracle.cpp',
                      'tree_source': 'resume/edit_tree_bench.cu',
                      'source_build_manifest': 'builds/corrected/BUILD_MANIFEST.json',
                      'word_build_manifest': 'resume/WORD_BUILD_RECORD.json'}
        for key, name in self.paths.items():
            if key not in ('word_manifest', 'source_build_manifest', 'word_build_manifest'):
                self.add(name, key.encode())
        self.add('builds/corrected/source_p/include/search_v2.cuh', b'corrected header fixture')
        header_sha = self.files['builds/corrected/source_p/include/search_v2.cuh']['sha256']
        self.add(self.paths['source_build_manifest'], json.dumps({'compiled_sources': {
            'source_p/include/search_v2.cuh': header_sha}}).encode())
        build_files, commands, guard_logs = {}, {}, {}
        sources = {key: self.paths['oracle_source' if key == 'oracle_binary' else 'tree_source']
                   for key in ('tree_binary', 'count_binary', 'oracle_binary')}
        for key, source in sources.items():
            command = ['/usr/bin/c++', '-O3', str(self.root / source), '-o', str(self.root / self.paths[key])]
            if key == 'count_binary':
                command.append('-DINSTRUMENT=1')
            commands[key] = command
            log = f'resume/{key}.guard.jsonl'
            guard_logs[key] = log
            self.add(log, ('\n'.join(json.dumps(e) for e in [
                {'event': 'start', 'cmd': command}, {'event': 'end', 'exit_code': 0}]) + '\n').encode())
            for name in (self.paths[key], source, log):
                build_files[name] = self.files[name]
        self.word_build = {'files': build_files, 'binaries': {key: self.paths[key] for key in sources},
                           'sources': sources, 'commands': commands, 'guard_logs': guard_logs,
                           'toolchain': {'cuda': '13.1.115', 'target_sm': 120, 'cxx': 'fixture c++'}}
        self.add(self.paths['word_build_manifest'], json.dumps(self.word_build).encode())
        data_files = {}
        for name in ('data/word_permutation.npy', 'data/word_base.strb', 'data/word_query.strb'):
            self.add(name, name.encode())
            data_files[name] = self.files[name]
        self.cases = [{'family': 'word', 'N': n, 'D': 109, 'k': 8, 'Q': list(W.QS),
                       'base': 'data/word_base.strb', 'query': 'data/word_query.strb',
                       'oracle': f'data/word_{n}.oracle',
                       'state': 'feasible' if n != 611000 else 'infeasible: insufficient source rows after holdout',
                       'query_isolation': {'isolated': True}}
                      for n in W.NS]
        manifest = {'seed': 20261026, 'query_rows': 1000, 'stride': 109,
                    'maximum_length': 32, 'available_base_rows': 610756,
                    'cases': self.cases, 'files': data_files}
        self.add(self.paths['word_manifest'], json.dumps(manifest).encode())
        oracles = {}
        for c in self.cases[:-1]:
            self.add(c['oracle'], bytes(120000))
            oracles[str(c['N'])] = self.files[c['oracle']]['sha256']
            c['oracle_sha256'] = oracles[str(c['N'])]
        self.proof = {'python_invocation':'/usr/bin/python3','files': self.files, 'paths': self.paths, 'oracle_sha256': oracles,
                      'runtime_files': {str(self.runtime_file): {'bytes': self.runtime_file.stat().st_size,
                                                               'sha256': W.L.sha(self.runtime_file)}}}
        self.proof_file = self.root / 'resume_20261026/WORD_PHASE_FREEZE.json'
        self.proof_file.parent.mkdir()
        self.proof_file.write_text(json.dumps(self.proof))

    def add(self, name, payload):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        self.files[name] = {'bytes': len(payload), 'sha256': W.L.sha(path)}

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()
        self.runtime_tmp.cleanup()

    def test_full_plan_and_alternating_pairs_keep_infeasible_load(self):
        tasks = W.plan(self.cases, self.root, self.epoch)
        self.assertEqual(len([t for t in tasks if t['kind'] == 'sanitize']), 12)
        self.assertEqual(len([t for t in tasks if t['kind'] == 'gate']), 24)
        self.assertEqual(len([t for t in tasks if t['kind'] == 'count']), 12)
        timed = [t for t in tasks if t['kind'] == 'time']
        self.assertEqual(len(timed), 4 * 3 * 2 * 6)
        self.assertEqual([t['arm'] for t in timed[:2]], ['P', 'S'])
        self.assertEqual([t['arm'] for t in timed[24:26]], ['S', 'P'])
        self.assertEqual({t['case']['N'] for t in timed}, set(W.NS))
        self.assertEqual({t['Q'] for t in timed}, set(W.QS))
        self.assertFalse(any(t.get('arm') not in (None, 'P', 'S') for t in tasks))

    def test_frozen_inputs_and_late_mutation(self):
        proof, cases = W.verified_inputs(self.root)
        self.assertEqual(len(cases), 4)
        path = self.root / self.paths['tree_binary']
        path.write_bytes(path.read_bytes()[:-1] + b'!')
        with self.assertRaises(W.L.SafetyStop):
            W.verified_inputs(self.root)

    def test_unfrozen_compiled_header_rejected(self):
        del self.proof['files']['builds/corrected/source_p/include/search_v2.cuh']
        self.proof_file.write_text(json.dumps(self.proof))
        with self.assertRaises(W.L.SafetyStop):
            W.verified_inputs(self.root)

    def replace_manifest(self, mutate):
        manifest = json.loads((self.root / self.paths['word_manifest']).read_text())
        mutate(manifest)
        self.add(self.paths['word_manifest'], json.dumps(manifest).encode())
        self.proof_file.write_text(json.dumps(self.proof))

    def test_case_path_escape_is_rejected(self):
        self.replace_manifest(lambda manifest: manifest['cases'][0].update(base='../outside.strb'))
        with self.assertRaisesRegex(W.L.SafetyStop, 'outside the task root'):
            W.verified_inputs(self.root)
        case = dict(self.cases[0], query=str(self.runtime_file))
        task = {'kind': 'gate', 'case': case, 'arm': 'P', 'Q': 1}
        with self.assertRaisesRegex(W.L.SafetyStop, 'outside the task root'):
            W.command(self.root, self.proof, task)

    def test_case_input_covered_by_only_phase_proof_is_rejected(self):
        self.add('data/unfrozen_case.strb', b'not part of the original Word manifest')
        self.replace_manifest(lambda manifest: manifest['cases'][0].update(base='data/unfrozen_case.strb'))
        with self.assertRaisesRegex(W.L.SafetyStop, 'both manifests'):
            W.verified_inputs(self.root)

    def test_word_build_binary_mapping_mismatch_is_rejected(self):
        self.word_build['binaries']['tree_binary'] = self.paths['count_binary']
        self.add(self.paths['word_build_manifest'], json.dumps(self.word_build).encode())
        self.proof_file.write_text(json.dumps(self.proof))
        with self.assertRaisesRegex(W.L.SafetyStop, 'binary/source binding'):
            W.verified_inputs(self.root)

    def test_word_build_compile_command_and_guard_log_must_match(self):
        self.word_build['commands']['tree_binary'].append('-DUNRECORDED=1')
        self.add(self.paths['word_build_manifest'], json.dumps(self.word_build).encode())
        self.proof_file.write_text(json.dumps(self.proof))
        with self.assertRaisesRegex(W.L.SafetyStop, 'guarded compile evidence'):
            W.verified_inputs(self.root)

    def test_word_timing_build_cannot_enable_instrumentation(self):
        self.word_build['commands']['tree_binary'].append('-DINSTRUMENT=1')
        self.add(self.paths['word_build_manifest'], json.dumps(self.word_build).encode())
        self.proof_file.write_text(json.dumps(self.proof))
        with self.assertRaisesRegex(W.L.SafetyStop, 'instrumentation binding'):
            W.verified_inputs(self.root)

    def test_external_runtime_dependency_mutation_is_rejected(self):
        W.verified_inputs(self.root)
        self.runtime_file.write_bytes(b'changed compiler fixture')
        with self.assertRaisesRegex(W.L.SafetyStop, 'runtime dependency changed'):
            W.verified_inputs(self.root)

    def test_exact_venv_invocation_is_frozen_even_for_same_resolved_executable(self):
        executable = self.root / 'system_python'
        executable.write_bytes(b'executable fixture')
        invocations = [self.root / name / 'bin/python' for name in ('venv_a', 'venv_b')]
        for path in invocations:
            path.parent.mkdir(parents=True)
            path.symlink_to(executable)
        guard = self.root / 'guard.py'
        guard.write_bytes(b'guard fixture')
        original_read = Path.read_text
        def read(path, *args, **kwargs):
            return 'boot-fixture' if str(path) == '/proc/sys/kernel/random/boot_id' else original_read(path, *args, **kwargs)
        identities = []
        with patch.object(W.L, 'GUARD', guard), patch.object(Path, 'read_text', autospec=True, side_effect=read):
            for invocation in invocations:
                self.proof['python_invocation']=str(invocation)
                self.proof_file.write_text(json.dumps(self.proof))
                with patch.dict(os.environ, {'FAISS_PYTHON': str(invocation)}):
                    identities.append(W.identity(self.root))
        self.assertEqual(identities[0]['python'], identities[1]['python'])
        self.assertEqual(identities[0]['python_sha256'], identities[1]['python_sha256'])
        self.assertNotEqual(identities[0]['python_invocation'], identities[1]['python_invocation'])
        self.assertNotEqual(identities[0], identities[1])

    def test_runtime_proof_binds_first_interpreter_invocation(self):
        with patch.dict(os.environ, {'FAISS_PYTHON': '/other/venv/python'}):
            with self.assertRaises(W.L.SafetyStop):
                W.verified_inputs(self.root)

    def test_oracle_full_and_bounded_mutation_rejected(self):
        c = dict(self.cases[0])
        W.verify_oracle(self.root, self.epoch, c)
        (self.root / c['oracle']).write_bytes(b'!' + bytes(119999))
        with self.assertRaises(W.L.SafetyStop):
            W.verify_oracle(self.root, self.epoch, c)
        bounded = dict(c, N=2000, oracle='runs/word_test/bounded.oracle')
        path = self.root / bounded['oracle']
        path.write_bytes(bytes(120000))
        W.L.save(self.epoch / 'word_bounded_oracle_manifest.json',
                 {'path': bounded['oracle'], 'bytes': 120000, 'sha256': W.L.sha(path)})
        W.verify_oracle(self.root, self.epoch, bounded)
        path.write_bytes(b'!' + bytes(119999))
        with self.assertRaises(W.L.SafetyStop):
            W.verify_oracle(self.root, self.epoch, bounded)

    def test_infeasible_611k_never_runs_gpu_or_oracle(self):
        c = self.cases[-1]
        with patch.object(W.C, 'execute') as execute, patch.object(W.L, 'guarded_run') as oracle:
            for arm in 'PS':
                task = {'kind': 'gate', 'case': c, 'arm': arm, 'Q': 1024,
                        'key': 'word_611000_q1024', 'label': 'infeasible_' + arm}
                self.assertFalse(W.requires_gpu(self.epoch, task))
                result = W.run_task(self.root, self.epoch, {}, self.proof, task)
                self.assertTrue(result['quality']['not_run'])
                self.assertIn('infeasible:', result['state'])
            execute.assert_not_called()
            oracle.assert_not_called()

    def test_global_stop_and_local_ssh_stop_refuse_phase(self):
        stop = self.root / 'STOP_CAMPAIGN.json'
        stop.write_text('{}')
        with patch.object(W, 'initialize') as initialize:
            with self.assertRaises(W.L.SafetyStop):
                W.main(self.root, 'init')
            initialize.assert_not_called()
        stop.unlink()
        with patch.dict(os.environ, {'E34_SSH_FAILED': '1'}):
            with self.assertRaises(W.L.SafetyStop):
                W.check_stops(self.root)
        marker = self.root / 'LOCAL_STOP_CAMPAIGN.json'
        marker.write_text('{}')
        with patch.dict(os.environ, {'E34_SSH_STOP_FILE': str(marker)}):
            with self.assertRaises(W.L.SafetyStop):
                W.check_stops(self.root)

    def test_vector_must_be_processed_first(self):
        (self.vector / 'COMPLETE.json').unlink()
        with patch.object(W, 'initialize') as initialize:
            with self.assertRaises(W.L.SafetyStop):
                W.main(self.root, 'init')
            initialize.assert_not_called()

    def test_any_error_latches_and_prevents_new_epoch(self):
        with patch.object(W.L, 'preflight'), \
             patch.object(W, 'initialize', side_effect=W.L.SafetyStop('guard exited 98')) as initialize:
            with self.assertRaises(W.L.SafetyStop):
                W.main(self.root, 'init')
            with self.assertRaises(W.L.SafetyStop):
                W.main(self.root, 'init')
        self.assertEqual(initialize.call_count, 1)
        self.assertEqual(len(list((self.root / 'runs').glob('word_epoch_*'))), 1)
        self.assertTrue((self.root / 'STOP_CAMPAIGN.json').exists())

    def test_command_preserves_repetitions_and_rejects_approx_or_unavailable(self):
        task = {'kind': 'time', 'case': self.cases[0], 'arm': 'P', 'Q': 1024}
        p = W.command(self.root, self.proof, task)
        self.assertEqual(p[-6:], [61000, 1024, 3, 1, '{out}', 'unused_cache_disabled'])
        task['arm'] = 'S'
        s = W.command(self.root, self.proof, task)
        self.assertEqual(s[-5:], [61000, 1024, 3, 1, '{out}'])
        task['arm'] = 'P-approx'
        with self.assertRaises(ValueError):
            W.command(self.root, self.proof, task)
        task.update(case=self.cases[-1], arm='P')
        with self.assertRaises(W.L.SafetyStop):
            W.command(self.root, self.proof, task)

    def test_q1024_requires_exact_complete_row_count(self):
        c = self.cases[0]
        prefix = self.epoch / 'bad/result'
        prefix.parent.mkdir()
        Path(str(prefix) + '.ids').write_bytes(bytes(1000 * 8 * 4))
        task = {'kind': 'gate', 'case': c, 'arm': 'P', 'Q': 1024,
                'key': 'word_61000_q1024', 'label': 'bad'}
        with patch.object(W.C, 'execute', return_value=(prefix, {'valid': True})):
            with self.assertRaisesRegex(W.L.SafetyStop, 'row count'):
                W.run_task(self.root, self.epoch, {'index': 6, 'uuid': 'GPU-test'}, self.proof, task)

    def test_cpu_dependency_guard_has_no_gpu_and_bounded_threads(self):
        with patch.object(W.L, 'guarded_run') as run:
            W.run_task(self.root, self.epoch, {}, self.proof, {'kind': 'dependency', 'label': 'dep'})
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs['timeout_s'], 600)
        self.assertEqual(kwargs['env']['CUDA_VISIBLE_DEVICES'], '')
        self.assertEqual(kwargs['env']['OMP_NUM_THREADS'], '16')
        self.assertFalse(W.requires_gpu(self.epoch, {'kind': 'dependency'}))

    def test_count_process_uses_instrumented_binary_and_full_pass_denominator(self):
        for q in (32, 1024):
            c = self.cases[0]
            task = {'kind': 'count', 'case': c, 'arm': 'P', 'Q': q,
                    'key': f'word_61000_q{q}', 'label': f'count_word_61000_q{q}'}
            W.quality_path(self.epoch, task).write_text(json.dumps({'correct': True}))
            self.assertTrue(W.requires_gpu(self.epoch, task))
            self.assertEqual(W.command(self.root, self.proof, task)[0], self.root / self.paths['count_binary'])
            prefix = self.epoch / task['label'] / 'result'
            prefix.parent.mkdir()
            rows = 1024 if q == 1024 else 1000
            Path(str(prefix) + '.ids').write_bytes(bytes(rows * 8 * 4))
            Path(str(prefix) + '.json').write_text(json.dumps({'instrumented': 1,
                'distance_calls': 100, 'candidate_leaves': 20, 'leaf_distances': 80}))
            auditor = types.SimpleNamespace(audit=lambda *a, **kw: {'correct': True})
            spec = types.SimpleNamespace(loader=types.SimpleNamespace(exec_module=lambda module: None))
            with patch.object(W.C, 'execute', return_value=(prefix, {'valid': True})), \
                 patch.object(W.importlib.util, 'spec_from_file_location', return_value=spec), \
                 patch.object(W.importlib.util, 'module_from_spec', return_value=auditor):
                W.run_task(self.root, self.epoch, {'index': 6, 'uuid': 'GPU-test'}, self.proof, task)
            scope = json.loads((self.epoch / (task['label'] + '.scope.json')).read_text())
            self.assertEqual(scope['queries_in_correctness_pass'], rows)
            self.assertEqual(scope['unique_held_out_queries'], 1000)
            self.assertEqual(scope['raw_counts']['distance_calls'], 100)
            self.assertEqual(scope['ragged_batch_included'], q == 32)
            self.assertEqual(scope['repeated_query_rows'], 24 if q == 1024 else 0)

    def anchor_scan(self, label, receipt):
        number = len(list(self.epoch.glob('STEP_*_DONE.json')))
        W.L.save(self.epoch / f'STEP_{number:04d}_DONE.json',
                 {'task': {'arm': 'S', 'kind': 'gate', 'label': label, 'case': {'state': 'feasible'}},
                  'result': {'state': 'complete', 'jit_manifest': receipt['jit_manifest']}})

    def fake_scan(self, label, artifacts, error=None):
        def execute(*args):
            cache = self.epoch / 'cupy_cache'
            self.assertEqual(os.environ['CUPY_CACHE_DIR'], str(cache))
            self.assertEqual(os.environ['CUPY_CACHE_IN_MEMORY'], '0')
            self.assertEqual(os.environ['CUPY_CACHE_SAVE_CUDA_SOURCE'], '1')
            run = self.epoch / label
            run.mkdir()
            for name, payload in artifacts.items():
                path = cache / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
            if error:
                raise error
            return run / 'result', {'valid': True}
        return execute

    def test_scan_jit_environment_binary_source_hashes_and_restore(self):
        old = {'CUPY_CACHE_DIR': 'prior-cache', 'CUPY_CACHE_IN_MEMORY': '1',
               'CUPY_CACHE_SAVE_CUDA_SOURCE': '0'}
        artifacts = {'edit.cubin': b'compiled-edit-container', 'edit.cubin.cu': b'edit source',
                     'internal/topk.cubin': b'compiled-topk-container'}
        with patch.dict(os.environ, old), \
             patch.object(W.C, 'execute', side_effect=self.fake_scan('scan1', artifacts)):
            _, receipt = W.execute_scan(self.root, self.epoch, {'index': 6, 'uuid': 'GPU-test'}, 'scan1', ['scan'])
            self.anchor_scan('scan1', receipt)
            self.assertEqual({key: os.environ[key] for key in old}, old)
        record = json.loads((self.epoch / 'scan1/jit_manifest.json').read_text())
        self.assertTrue(record['valid'])
        self.assertEqual(set(record['files']), set(artifacts))
        for name, payload in artifacts.items():
            self.assertEqual(record['files'][name]['bytes'], len(payload))
            self.assertEqual(record['files'][name]['sha256'], W.L.sha(self.epoch / 'cupy_cache' / name))
        head, current = W.checked_jit_cache(self.epoch)
        self.assertEqual(head['sequence'], 1)
        self.assertEqual(current, record['files'])

    def test_scan_jit_new_keys_append_to_valid_hash_chain(self):
        for label, artifacts in [('scan1', {'one.cubin': b'one', 'one.cubin.cu': b'source one'}),
                                  ('scan2', {'two.cubin': b'two'})]:
            with patch.object(W.C, 'execute', side_effect=self.fake_scan(label, artifacts)):
                _, receipt = W.execute_scan(self.root, self.epoch, {'index': 6, 'uuid': 'GPU-test'}, label, ['scan'])
                self.anchor_scan(label, receipt)
        record = json.loads((self.epoch / 'scan2/jit_manifest.json').read_text())
        self.assertEqual(record['new_files'], ['two.cubin'])
        self.assertEqual(record['previous']['sha256'], W.L.sha(self.epoch / 'scan1/jit_manifest.json'))
        self.assertEqual(W.checked_jit_cache(self.epoch)[0]['sequence'], 2)

    def test_scan_jit_previously_frozen_binary_mutation_stops_before_next_process(self):
        with patch.object(W.C, 'execute', side_effect=self.fake_scan('scan1', {'one.cubin': b'one'})):
            _, receipt = W.execute_scan(self.root, self.epoch, {'index': 6, 'uuid': 'GPU-test'}, 'scan1', ['scan'])
            self.anchor_scan('scan1', receipt)
        (self.epoch / 'cupy_cache/one.cubin').write_bytes(b'two')
        with patch.object(W.C, 'execute') as execute:
            with self.assertRaises(W.L.SafetyStop):
                W.execute_scan(self.root, self.epoch, {'index': 6, 'uuid': 'GPU-test'}, 'scan2', ['scan'])
            execute.assert_not_called()

    def test_scan_jit_existing_binary_changed_during_process_is_not_promoted(self):
        with patch.object(W.C, 'execute', side_effect=self.fake_scan('scan1', {'one.cubin': b'one'})):
            _, receipt = W.execute_scan(self.root, self.epoch, {'index': 6, 'uuid': 'GPU-test'}, 'scan1', ['scan'])
            self.anchor_scan('scan1', receipt)
        head_before = (self.epoch / 'jit_head.json').read_bytes()
        with patch.object(W.C, 'execute', side_effect=self.fake_scan('scan2', {'one.cubin': b'two'})):
            with self.assertRaises(W.L.SafetyStop):
                W.execute_scan(self.root, self.epoch, {'index': 6, 'uuid': 'GPU-test'}, 'scan2', ['scan'])
        record = json.loads((self.epoch / 'scan2/jit_manifest.json').read_text())
        self.assertFalse(record['valid'])
        self.assertFalse(record['previous_artifacts_unchanged'])
        self.assertEqual((self.epoch / 'jit_head.json').read_bytes(), head_before)

    def test_scan_jit_missing_binary_is_not_promotable(self):
        with patch.object(W.C, 'execute', side_effect=self.fake_scan('source_only', {'only.cu': b'source'})):
            with self.assertRaisesRegex(W.L.SafetyStop, 'compiled-binary provenance'):
                W.execute_scan(self.root, self.epoch, {'index': 6, 'uuid': 'GPU-test'}, 'source_only', ['scan'])
        record = json.loads((self.epoch / 'source_only/jit_manifest.json').read_text())
        self.assertFalse(record['valid'])
        self.assertFalse(record['compiled_binary_present'])
        self.assertFalse((self.epoch / 'jit_head.json').exists())

    def test_scan_jit_failure_restores_environment_and_retains_diagnostics(self):
        old = dict(os.environ)
        with patch.object(W.C, 'execute', side_effect=self.fake_scan('failed_scan', {'partial.cubin': b'partial'},
                                                                   error=W.L.SafetyStop('guard exited 98'))):
            with self.assertRaises(W.L.SafetyStop):
                W.execute_scan(self.root, self.epoch, {'index': 6, 'uuid': 'GPU-test'}, 'failed_scan', ['scan'])
        self.assertEqual(dict(os.environ), old)
        record = json.loads((self.epoch / 'failed_scan/jit_manifest.json').read_text())
        self.assertFalse(record['valid'])
        self.assertIn('partial.cubin', record['files'])
        self.assertFalse((self.epoch / 'jit_head.json').exists())

    def test_scan_jit_self_consistent_rewind_is_rejected_by_completed_step_anchor(self):
        receipts = []
        for label, artifacts in [('scan1', {'one.cubin': b'one'}), ('scan2', {'two.cubin': b'two'})]:
            with patch.object(W.C, 'execute', side_effect=self.fake_scan(label, artifacts)):
                _, receipt = W.execute_scan(self.root, self.epoch, {'index': 6, 'uuid': 'GPU-test'}, label, ['scan'])
                self.anchor_scan(label, receipt)
                receipts.append(receipt)
        (self.epoch / 'scan2/jit_manifest.json').unlink()
        (self.epoch / 'cupy_cache/two.cubin').unlink()
        (self.epoch / 'jit_head.json').write_text(json.dumps(receipts[0]['jit_manifest']))
        with self.assertRaisesRegex(W.L.SafetyStop, 'completed S step anchors'):
            W.checked_jit_cache(self.epoch)

    def test_completed_s_step_without_jit_anchor_is_rejected(self):
        W.L.save(self.epoch / 'STEP_0000_DONE.json',
                 {'task': {'arm': 'S', 'kind': 'gate', 'label': 'scan1', 'case': {'state': 'feasible'}},
                  'result': {'state': 'complete'}})
        with self.assertRaisesRegex(W.L.SafetyStop, 'immutable JIT anchor'):
            W.checked_jit_cache(self.epoch)

    def test_successful_s_task_result_carries_step_bound_jit_anchor(self):
        case = self.cases[0]
        task = {'kind': 'gate', 'case': case, 'arm': 'S', 'Q': 1,
                'key': 'word_61000_q1', 'label': 'scan_task'}
        create = self.fake_scan(task['label'], {'edit.cubin': b'compiled fixture'})
        def execute(*args):
            prefix, receipt = create(*args)
            Path(str(prefix) + '.ids').write_bytes(bytes(1000 * 8 * 4))
            return prefix, receipt
        auditor = types.SimpleNamespace(audit=lambda *a, **kw: {'correct': True})
        spec = types.SimpleNamespace(loader=types.SimpleNamespace(exec_module=lambda module: None))
        with patch.object(W.C, 'execute', side_effect=execute), \
             patch.object(W.importlib.util, 'spec_from_file_location', return_value=spec), \
             patch.object(W.importlib.util, 'module_from_spec', return_value=auditor):
            result = W.run_task(self.root, self.epoch, {'index': 6, 'uuid': 'GPU-test'}, self.proof, task)
        self.assertEqual(result['jit_manifest']['manifest'], 'scan_task/jit_manifest.json')
        W.L.save(self.epoch / 'STEP_0000_DONE.json', {'task': task, 'result': result})
        self.assertEqual(W.checked_jit_cache(self.epoch)[0], result['jit_manifest'])

    def test_scan_jit_manifest_mutation_is_rejected(self):
        with patch.object(W.C, 'execute', side_effect=self.fake_scan('scan1', {'one.cubin': b'one'})):
            _, receipt = W.execute_scan(self.root, self.epoch, {'index': 6, 'uuid': 'GPU-test'}, 'scan1', ['scan'])
            self.anchor_scan('scan1', receipt)
        path = self.epoch / 'scan1/jit_manifest.json'
        path.write_text(path.read_text() + ' ')
        with self.assertRaises(W.L.SafetyStop):
            W.checked_jit_cache(self.epoch)

    def test_scan_bytes_do_not_invent_p_work_measurements(self):
        c = self.cases[0]
        task = {'kind': 'work', 'case': c, 'Q': 32, 'key': 'word_61000_q32', 'label': 'work_test'}
        result = W.run_task(self.root, self.epoch, {}, self.proof, task)
        self.assertNotIn('P_distance_calls', result['work'])
        self.assertIn('separate instrumented process', result['work']['P_count_state'])
        self.assertEqual(result['work']['S_logical_padded_character_bytes_per_batch'], 32 * 61000 * 109)
        self.assertFalse(W.requires_gpu(self.epoch, task))


if __name__ == '__main__':
    unittest.main()
