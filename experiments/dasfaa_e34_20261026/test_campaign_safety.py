"""CPU-only safety regressions; never access NVML, SSH, GPUs, or real signals."""
import json
from pathlib import Path
import signal
import struct
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

import campaign as C
import lock_support as L

HERE = Path(__file__).resolve().parent
IDLE = {'idle': True, 'apps': '', 'uuid': 'GPU-test', 'time_utc': 'test'}


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=HERE)
        self.root = Path(self.tmp.name)
        self.epoch = self.root / 'epoch'
        self.epoch.mkdir()
        (self.root / 'logs').mkdir()
        (self.root / 'data').mkdir()
        L._last_snapshot = None
        L._fatal_telemetry = None
        L.configure(self.epoch / 'telemetry')

    def tearDown(self):
        self.tmp.cleanup()

    def test_guard_limits_and_tree_upper_bound(self):
        cmd = L.guarded_command(self.root / 'guard', ['program', 'argument'])
        self.assertEqual(cmd[cmd.index('--rss-max-gb') + 1], '16')
        self.assertEqual(cmd[cmd.index('--mem-available-min-gb') + 1], '48')
        self.assertEqual(cmd[cmd.index('--timeout-s') + 1], '900')
        self.assertEqual(cmd[-3:], ['--', 'program', 'argument'])
        with self.assertRaises(ValueError):
            L.guarded_command('log', ['x'], timeout=901)
        case = {'N': 30_000_000, 'family': 'tloc'}
        self.assertIn('infeasible', C.tree_infeasible(self.root, case))
        with self.assertRaises(L.SafetyStop):
            C.command(self.root, case, 1, 'P')
        case = {'N': 1_000_000, 'family': 'deep', 'tree_h': 8}
        self.assertIn('tree_h=8', C.tree_infeasible(self.root, case))

    def test_timeout_reads_meminfo_then_latches_without_further_nvml(self):
        events = []
        def failed(*args, **kwargs):
            events.append('nvml')
            return types.SimpleNamespace(returncode=124, stderr='timeout', stdout='')
        with patch.object(L, 'preflight'), patch.object(L.subprocess, 'run', side_effect=failed) as run, \
             patch.object(L, 'meminfo', side_effect=lambda: events.append('meminfo') or 'memory'):
            with self.assertRaises(L.SafetyStop):
                L.snapshot(0)
            self.assertEqual(events, ['nvml', 'meminfo'])
            with self.assertRaises(L.SafetyStop):
                L.snapshot(0)
            self.assertEqual(run.call_count, 1)
        stop = list((self.epoch / 'telemetry').glob('NVML_STOP*'))
        self.assertEqual(len(stop), 1)
        self.assertEqual(json.loads(stop[0].read_text())['meminfo'], 'memory')

    def test_snapshot_uses_guard_timeout10_and_thirty_second_cadence(self):
        clock = [100.0]
        calls = []
        def run(cmd, **kwargs):
            calls.append(cmd)
            field = next(x for x in cmd if x.startswith('--query-'))
            text = 'GPU-test, GPU, driver, 0, 0, P0, 10, 100, 100\n' if 'query-gpu' in field else ''
            return types.SimpleNamespace(returncode=0, stderr='', stdout=text)
        with patch.object(L, 'preflight'), patch.object(L.subprocess, 'run', side_effect=run), \
             patch.object(L.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(L.time, 'sleep', side_effect=lambda s: clock.__setitem__(0, clock[0] + s)):
            self.assertTrue(L.snapshot(0)['idle'])
            self.assertTrue(L.snapshot(0)['idle'])
        self.assertEqual(clock[0], 130.0)
        for cmd in calls:
            k = cmd.index('--')
            self.assertEqual(cmd[k + 1:k + 4], ['timeout', '10', 'nvidia-smi'])
            self.assertIn('--log', cmd)

    def test_cadence_survives_fresh_step_process_state(self):
        clock = [100.0]
        with patch.object(L, 'preflight'), \
             patch.object(L.subprocess, 'run', side_effect=[
                 types.SimpleNamespace(returncode=0, stderr='', stdout='GPU-test, GPU, driver, 0, 0, P0, 10, 100, 100\n'),
                 types.SimpleNamespace(returncode=0, stderr='', stdout='')]*2), \
             patch.object(L.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(L.time, 'sleep', side_effect=lambda s: clock.__setitem__(0, clock[0] + s)):
            L.snapshot(0)
            L._last_snapshot = None
            L.configure(self.epoch / 'telemetry')
            L.snapshot(0)
        self.assertEqual(clock[0], 130.0)

    def test_query_isolation_failure_skips_both_gpu_arms(self):
        c = {'family': 'deep', 'N': 1_000_000,
             'input_gate': 'not-run: query-isolation-failed', 'matching_base_rows': 16}
        with patch.object(C, 'execute') as execute:
            for arm in 'PS':
                task = {'kind': 'gate', 'case': c, 'arm': arm, 'Q': 1,
                        'key': 'deep_1000000_q1', 'label': f'gate_deep_{arm}'}
                got = C.run_task(self.root, self.epoch, 0, 'GPU-test', task)
                self.assertEqual(got['state'], 'not-run: query-isolation-failed')
                self.assertFalse(got['quality']['correct'])
            execute.assert_not_called()

    def test_terminal_process_codes_do_not_query_nvml_again(self):
        for code in (3, 97, 98):
            class Process:
                pid = 100
                returncode = code
                def poll(self):
                    return code
                def wait(self, timeout=None):
                    return code
            with patch.object(L, 'stable_idle', return_value=(IDLE, [IDLE])) as idle, \
                 patch.object(L, 'preflight'), patch.object(L, 'proc_identity', return_value=(1, 1000)), \
                 patch.object(C.subprocess, 'Popen', return_value=Process()) as popen:
                with self.assertRaises(L.SafetyStop):
                    C.execute(self.root, self.epoch, 0, 'GPU-test', f'code_{code}', ['binary'])
            self.assertEqual(idle.call_count, 1)
            cmd = popen.call_args.args[0]
            self.assertIn(str(L.GUARD), cmd)
            rec = json.loads((self.epoch / f'code_{code}/receipt.json').read_text())
            self.assertEqual(rec['exit_code'], code)
            self.assertFalse(rec['valid'])

    def test_main_never_retries_or_creates_second_epoch(self):
        with patch.object(L, 'preflight'), \
             patch.object(C, 'initialize', side_effect=L.SafetyStop('guard exited 98')) as initialize:
            with self.assertRaises(L.SafetyStop):
                C.main(self.root, 'init')
            with self.assertRaises(L.SafetyStop):
                C.main(self.root, 'init')
        self.assertEqual(initialize.call_count, 1)
        self.assertEqual(len(list((self.root / 'runs').iterdir())), 1)
        self.assertTrue((self.root / 'STOP_CAMPAIGN.json').exists())

    def test_plan_preserves_every_load_and_round(self):
        cases = json.loads((HERE / 'DATA_MANIFEST.json').read_text())['cases']
        tasks = C.plan(cases, self.root / 'runs/epoch', self.root)
        gates = [t for t in tasks if t['kind'] == 'gate']
        times = [t for t in tasks if t['kind'] == 'time']
        self.assertEqual(len(gates), len(cases) * 3 * 2)
        self.assertEqual(len(times), len(cases) * 3 * 2 * 6)
        self.assertEqual(len([t for t in tasks if t['kind'] == 'sanitize']), 24)
        self.assertEqual([t['arm'] for t in times[:2]], ['P', 'S'])
        self.assertEqual([t['arm'] for t in times[len(cases)*6:len(cases)*6+2]], ['S', 'P'])

    def test_pid_reuse_and_guard_child_termination_order(self):
        identities = {100: (1, 1000), 123: (100, 1230), 456: (1, 4560)}
        known = {100: 1000}
        with patch.object(L, 'proc_identity', side_effect=lambda p: identities.get(p)):
            self.assertTrue(L.owned_pid(123, 100, known))
            identities[123] = (1, 9990)
            self.assertFalse(L.owned_pid(123, 100, known))
            self.assertTrue(L.foreign_apps({'apps': '456, foreign, 10'}, 100, known))
        events = []
        class Process:
            pid = 100
            def wait(self, timeout=None):
                return 0
        with patch.object(L, 'remember_descendants'), \
             patch.object(L, 'signal_owned', side_effect=lambda p, s, g, k: events.append((p, s))):
            L.terminate_owned(Process(), {100: 1000, 123: 1230})
        self.assertEqual(events, [(123, signal.SIGTERM), (123, signal.SIGKILL)])
        self.assertFalse(any(p == 100 for p, _ in events))
        with patch.object(L.os, 'pidfd_open', return_value=99, create=True), \
             patch.object(L.os, 'close'), \
             patch.object(L.signal, 'pidfd_send_signal', create=True) as send, \
             patch.object(L, 'proc_identity', return_value=(1, 9990)):
            self.assertFalse(L.signal_owned(123, signal.SIGTERM, 100, {100: 1000, 123: 1230}))
            send.assert_not_called()

    def test_skipped_workloads_do_not_need_gpu(self):
        case = {'family': 'tloc', 'N': 30_000_000, 'input_gate': 'pass'}
        task = {'case': case, 'kind': 'gate', 'arm': 'P'}
        self.assertFalse(C.requires_gpu(self.root, self.epoch, task))
        task['arm'] = 'S'
        self.assertTrue(C.requires_gpu(self.root, self.epoch, task))
        task['kind'] = 'oracle'
        self.assertFalse(C.requires_gpu(self.root, self.epoch, task))
        case['input_gate'] = 'not-run: query-isolation-failed'
        task['kind'] = 'gate'
        self.assertFalse(C.requires_gpu(self.root, self.epoch, task))
        case['input_gate'] = 'pass'
        task.update(kind='time', key='tloc_30000000_q1')
        (self.epoch / 'quality_tloc_30000000_q1_S.json').write_text(json.dumps({'correct': False}))
        self.assertFalse(C.requires_gpu(self.root, self.epoch, task))

    def test_oracle_mutation_is_rejected_before_use(self):
        oracle = self.root / 'full.oracle'
        oracle.write_bytes(bytes(120000))
        case = {'N': 1_000_000, 'family': 'tloc', 'oracle': 'full.oracle',
                'oracle_sha256': L.sha(oracle)}
        C.verify_oracle(self.root, self.epoch, case)
        oracle.write_bytes(bytes([1]) + bytes(119999))
        with self.assertRaises(L.SafetyStop):
            C.verify_oracle(self.root, self.epoch, case)
        case.update(N=2000, oracle=str(oracle.relative_to(self.root)))
        L.save(self.epoch / 'tloc_bounded_oracle_manifest.json',
               {'path': case['oracle'], 'bytes': 120000, 'sha256': L.sha(oracle)})
        C.verify_oracle(self.root, self.epoch, case)
        oracle.write_bytes(bytes(120000))
        with self.assertRaises(L.SafetyStop):
            C.verify_oracle(self.root, self.epoch, case)

    def test_guarded_cpu_process_and_preflight_limit(self):
        with patch.object(L, 'preflight'), \
             patch.object(L.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0)) as run:
            L.guarded_run(self.root / 'oracle.guard.jsonl', ['oracle'], check=False)
        self.assertIn(str(L.GUARD), run.call_args.args[0])
        with patch.object(L, 'meminfo', return_value='MemAvailable: 67108863 kB\n'):
            with self.assertRaises(L.SafetyStop):
                L.preflight()


if __name__ == '__main__':
    unittest.main()
