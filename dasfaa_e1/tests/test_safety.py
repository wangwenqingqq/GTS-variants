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
    def test_pre_pidfile_cleanup_keeps_watchdog_alive(self):
        calls=[]
        class Watchdog:
            pid=100
            def wait(self,timeout):
                calls.append(('reap_watchdog',timeout))
                return -9
        def owned(pid,group,known):
            known[pid]=pid*10
            return True
        with patch.object(g,'descendants',return_value=[100,101,102]),patch.object(g,'proc_identity',side_effect=lambda p:(100,p*10)),patch.object(g,'owned_pid',side_effect=owned),patch.object(g,'signal_owned',side_effect=lambda pid,sig,*args:calls.append((pid,sig)) or True):
            self.assertTrue(g.terminate_guarded(Watchdog(),{100:1000}))
        self.assertNotIn(100,[c[0] for c in calls])
        self.assertLess(calls.index((101,g.signal.SIGSTOP)),calls.index((102,g.signal.SIGSTOP)))
        self.assertLess(calls.index((102,g.signal.SIGKILL)),calls.index((101,g.signal.SIGKILL)))
        self.assertEqual(calls[-1],('reap_watchdog',5))
    def test_guard_exit_is_latched_before_summary_parse(self):
        source=Path(r.__file__).read_text()
        latch=source.index("if not problem and receipt['exit_code'] in (3,97,98):")
        self.assertLess(latch,source.index("json.loads(result.read_text())"))
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
