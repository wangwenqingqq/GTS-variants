"""No NVML/SSH/GPU is touched by these fail-stop regressions."""
import importlib.util
import subprocess
import sys
import unittest
import tempfile
import struct
import shutil
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gpu_guard as g
import run_smoke as r

class SafetyTests(unittest.TestCase):
    def setUp(self):
        g._FATAL=None
        g._LAST_SNAPSHOT=None
        g.STOP_ROOT=None
        self.guard_path=patch.object(r,'RESOURCE_GUARD','/authoritative/guard.py')
        self.guard_path.start()
    def tearDown(self):
        self.guard_path.stop()
        g._FATAL=None
        g._LAST_SNAPSHOT=None
    def test_guard_command_limits(self):
        cmd=r.guarded_command(['binary'],'test.jsonl')
        self.assertIn('--log',cmd)
        self.assertEqual(cmd[cmd.index('--rss-max-gb')+1],'16')
        self.assertEqual(cmd[cmd.index('--timeout-s')+1],'900')
        with self.assertRaises(AssertionError):r.guarded_command([], '',901)
    def test_fatal_exit_never_retried(self):
        for code in (3,97,98):
            with patch.object(g,'host_memory',return_value={'MemAvailable':100*(1024**3)}):
                with self.assertRaises(g.FatalStop):r.check_exit(code,'fixture')
                self.assertIsNotNone(g._FATAL)
            g._FATAL=None
    def test_nvml_timeout_reads_memory_and_latches(self):
        order=[]
        def timeout(*args,**kwargs):
            order.append('nvml')
            self.assertEqual(args[0][:3],['timeout','10','nvidia-smi'])
            raise subprocess.CalledProcessError(124,args[0])
        with patch.object(g.subprocess,'check_output',side_effect=timeout),patch.object(g,'host_memory',side_effect=lambda:order.append('meminfo') or {'MemAvailable':0}):
            with self.assertRaises(g.FatalStop):g.snapshot(6)
            with self.assertRaises(g.FatalStop):g.snapshot(7)
        self.assertEqual(order,['nvml','meminfo'])
    def test_remote_launch_stays_blocked_without_linux_regression(self):
        self.assertFalse(r.REMOTE_LAUNCH_READY)
        source=Path(r.__file__).read_text()
        self.assertLess(source.index('if not REMOTE_LAUNCH_READY:'),source.index('guard.acquire(a.out)'))
        self.assertIn('pass_fds=lock_fds',source)
    def test_poll_interval(self):
        self.assertGreaterEqual(g.POLL_SECONDS,30)
    def test_failed_stop_is_not_a_cleanup_pass(self):
        class Watchdog:
            pid=100
            def poll(self):return None
        with patch.object(g,'freeze_owned',return_value=False):
            self.assertFalse(g.terminate_guarded(Watchdog(),{100:1000}))

    def test_all_threads_must_be_stopped(self):
        with patch.object(g,'proc_identity',return_value=(100,1000)),patch.object(g,'owned_pid',return_value=True),patch.object(g,'thread_states',return_value=['T','R']),patch.object(g,'signal_owned',return_value=True):
            self.assertFalse(g.freeze_owned(101,100,{101:1000},g.time.monotonic()+.01))

    def test_incomplete_cleanup_cannot_unwind_to_unlock(self):
        source=Path(r.__file__).read_text()
        self.assertIn('guard.hold_failed_cleanup(p,known,folder/',source)
        self.assertIn('guard.enable_subreaper()',source)
        self.assertIn('known=guard.job_known()',source)
        self.assertNotIn('guard.remember_target(folder,known)',source)
        self.assertLess(source.index("        try:\n            identity=guard.proc_identity(p.pid)"),source.index('known[p.pid]=identity[1]'))
        self.assertLess(source.index('guard.enable_subreaper()'),source.index('guard.acquire(a.out)'))

    def test_guard_exit_is_latched_before_summary_parse(self):
        source=Path(r.__file__).read_text()
        latch=source.index("if receipt['exit_code'] in (3,97,98):")
        self.assertLess(latch,source.index("json.loads(result.read_text())"))
    def test_mandatory_code_latches_even_with_post_launch_identity_failure(self):
        for code in (3,97,98):
            class Watchdog:
                pid=100
                def poll(self):return code
                def wait(self,timeout=None):return code
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);case=root/'case';case.mkdir();epoch=root/'epoch';epoch.mkdir()
                patches=[patch.object(g,'ensure_launch_memory'),
                         patch.object(g,'snapshot',return_value={'idle':True,'apps':''}),
                         patch.object(g,'job_known',return_value={42:420}),
                         patch.object(g,'sha',return_value='fixture'),
                         patch.object(g.subprocess,'Popen',return_value=Watchdog()),
                         patch.object(g,'proc_identity',side_effect=g.IdentityUnavailable('fixture')),
                         patch.object(g,'terminate_guarded',return_value=True),
                         patch.object(g,'host_memory',return_value={'MemAvailable':100*(1024**3)})]
                for item in patches:item.start()
                try:
                    with self.assertRaises(g.FatalStop):
                        r.run(root,epoch,6,'fixture-uuid',case,'D',300,lock_fds=(10,11))
                    self.assertEqual(g._FATAL['detail']['code'],code)
                    receipt=__import__('json').loads((epoch/'case_D/receipt.json').read_text())
                    self.assertTrue(receipt['cleanup_complete'])
                    self.assertEqual(receipt['exit_code'],code)
                finally:
                    for item in reversed(patches):item.stop()
                    g._FATAL=None

    def test_quarantine_does_not_unlock_on_logging_or_proc_errors(self):
        class Watchdog:
            pid=100
            def poll(self):return 0
        with patch.object(g,'save',side_effect=OSError('fixture')),patch.object(g,'signal_owned',return_value=True),patch.object(g,'reap_adopted'),patch.object(g,'owned_children',side_effect=[g.IdentityUnavailable('fixture'),[]]):
            g.hold_failed_cleanup(Watchdog(),{g.os.getpid():42},Path('unused'))

    def test_case_header_limits_before_allocation(self):
        root=Path(__file__).resolve().parents[1]
        tmp_root=root/'bin_test_tmp'
        tmp_root.mkdir(exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(dir=tmp_root) as folder:
                folder=Path(folder)
                cpp=folder/'parse.cpp'
                cpp.write_text('#include "case.hpp"\nint main(int n,char**v){try{Case c(v[1]);return 0;}catch(const std::exception&e){std::cerr<<e.what();return 2;}}\n')
                exe=folder/'parse'
                compiler=shutil.which('c++')
                self.assertIsNotNone(compiler)
                subprocess.run([compiler,'-std=c++17','-I',str(root),str(cpp),'-o',str(exe)],check=True)
                cases=[(b'E1CASE1\0','truncated case header'),
                       (b'E1CASE1\0'+struct.pack('<7i',2,128,10000001,0,1,8,0),'10M ceiling'),
                       (b'E1CASE1\0'+struct.pack('<7i',2,4096,1000000,0,1,8,0),'int32 payload')]
                for raw,message in cases:
                    file=folder/'case.bin'
                    file.write_bytes(raw)
                    proc=subprocess.run([str(exe),str(file)],capture_output=True,text=True)
                    self.assertEqual(proc.returncode,2)
                    self.assertIn(message,proc.stderr)
        finally:
            tmp_root.rmdir()
    def test_serial_and_no_epoch_retry(self):
        source=Path(r.__file__).read_text()
        self.assertNotIn('range(100)',source)
        self.assertNotIn('ThreadPool',source)
        self.assertIn("check_exit(receipt['exit_code'],label)",source)

if __name__=='__main__':unittest.main()
