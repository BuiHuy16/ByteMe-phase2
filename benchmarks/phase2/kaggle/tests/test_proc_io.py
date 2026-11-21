"""Unit fixtures plus real cross-UID Linux /proc acceptance tests."""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "kaggle_runtime.py"
spec = importlib.util.spec_from_file_location("proc_runtime", SOURCE)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class ProcIOTests(unittest.TestCase):
    def test_w1_driver_completes_when_only_io_is_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(temp, temp, "io-unavailable")
            session.processes = {label: mock.Mock(pid=pid, poll=mock.Mock(return_value=None))
                                 for label, pid in (("backend", 101), ("mysql", 102))}
            driver = mock.Mock(pid=103, poll=mock.Mock(return_value=0), wait=mock.Mock(return_value=0))
            with mock.patch.object(session, "_backend_alive"), \
                    mock.patch.object(runtime.subprocess, "Popen", return_value=driver), \
                    mock.patch.object(runtime.ResourceSampler, "_process_details", return_value={"state": "S", "start_time": 999, "ticks": 30, "rss": 43008, "read_bytes": None, "write_bytes": None, "io_reason": "PermissionError"}), \
                    mock.patch.object(runtime.ResourceSampler, "_system_cpu", return_value=(100, 10)), \
                    mock.patch.object(runtime.ResourceSampler, "_available_memory", return_value=100000), \
                    mock.patch.object(runtime.os, "sysconf", return_value=100, create=True), \
                    mock.patch.object(runtime.os, "sysconf_names", {"SC_CLK_TCK": 2}, create=True):
                result = session._run(["k6"], "w1/console.txt", "w1/resources.tsv")
            self.assertTrue(result["cpu_rss_complete"])
            self.assertEqual(result["io_unavailable_rows"], 3)
            driver.terminate.assert_not_called()

    def proc_reader(self, path, *args, **kwargs):
        if path.name == "stat":
            return "123 (mysql process) " + " ".join(
                ["S"] + ["0"] * 10 + ["10", "20"] + ["0"] * 6 + ["999"])
        if path.name == "status":
            return "VmRSS: 42 kB\n"
        if path.name == "io":
            raise PermissionError(13, "Permission denied")
        raise AssertionError(path)

    def test_denied_io_keeps_cpu_rss_without_fake_zero(self):
        with mock.patch.object(pathlib.Path, "read_text", lambda path, *a, **kw: self.proc_reader(path)):
            ticks, rss, read, write, reason = runtime.ResourceSampler._process(123)
        self.assertEqual((ticks, rss), (30, 42 * 1024))
        self.assertIsNone(read)
        self.assertIsNone(write)
        self.assertIn("/proc/123/io", reason)

    def test_normal_io_is_collected(self):
        def reader(path, *args, **kwargs):
            if path.name == "io":
                return "read_bytes: 1234\nwrite_bytes: 5678\n"
            return self.proc_reader(path)
        with mock.patch.object(pathlib.Path, "read_text", reader):
            result = runtime.ResourceSampler._process(123)
        self.assertEqual(result[2:], (1234, 5678, None))

    def test_missing_vmrss_for_active_process_is_mandatory_telemetry_failure(self):
        def reader(path, *args, **kwargs):
            if path.name == "status":
                return "Name:\tmysql\nState:\tS (sleeping)\n"
            return self.proc_reader(path)
        with mock.patch.object(pathlib.Path, "read_text", reader):
            with self.assertRaisesRegex(runtime.ProcessTelemetryUnavailable, "active process"):
                runtime.ResourceSampler._process_details(123)

    def test_status_permission_error_for_alive_process_is_failure(self):
        def reader(path, *args, **kwargs):
            if path.name == "status":
                raise PermissionError(13, "Permission denied")
            return self.proc_reader(path)
        with mock.patch.object(pathlib.Path, "read_text", reader):
            with self.assertRaisesRegex(runtime.ProcessTelemetryUnavailable, "permission denied"):
                runtime.ResourceSampler._process_details(123)

    def test_zombie_and_pid_reuse_are_distinguished(self):
        zombie = {"state": "Z", "ticks": 30, "start_time": 999}
        with mock.patch.object(runtime.ResourceSampler, "_stat", return_value=zombie):
            with self.assertRaises(runtime.ProcessLifecycle) as caught:
                runtime.ResourceSampler._process_details(123)
        self.assertEqual(caught.exception.event, "PROCESS_ZOMBIE")
        active = {"state": "S", "ticks": 30, "start_time": 1000}
        with mock.patch.object(runtime.ResourceSampler, "_stat", return_value=active):
            with self.assertRaises(runtime.ProcessLifecycle) as caught:
                runtime.ResourceSampler._process_details(123, expected_start_time=999)
        self.assertEqual(caught.exception.event, "PID_REUSED")

    def test_exit_race_after_stat_is_lifecycle_not_fake_rss(self):
        active = {"state": "S", "ticks": 30, "start_time": 999}
        with mock.patch.object(runtime.ResourceSampler, "_stat",
                               side_effect=[active, runtime.ProcessLifecycle("PROCESS_EXITED", 123)]), \
                mock.patch.object(pathlib.Path, "read_text", return_value="Name:\tk6\n"):
            with self.assertRaises(runtime.ProcessLifecycle) as caught:
                runtime.ResourceSampler._process_details(123)
        self.assertEqual(caught.exception.event, "PROCESS_EXITED")

    def test_pid_reuse_between_stat_and_status_rejects_sample(self):
        first = {"state": "S", "ticks": 30, "start_time": 999}
        replacement = {"state": "S", "ticks": 1, "start_time": 1000}
        with mock.patch.object(runtime.ResourceSampler, "_stat", side_effect=[first, replacement]), \
                mock.patch.object(pathlib.Path, "read_text", return_value="VmRSS: 42 kB\n"):
            with self.assertRaises(runtime.ProcessLifecycle) as caught:
                runtime.ResourceSampler._process_details(123)
        self.assertEqual(caught.exception.event, "PID_REUSED_DURING_SAMPLE")

    def test_unavailable_io_start_stop_and_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "resources.tsv"
            sampler = runtime.ResourceSampler(path, {"mysql": 123})
            with mock.patch.object(sampler, "_process_details", return_value={"state": "S", "start_time": 999, "ticks": 30, "rss": 43008, "read_bytes": None, "write_bytes": None, "io_reason": "PermissionError /proc/123/io"}), \
                    mock.patch.object(sampler, "_system_cpu", return_value=(100, 10)), \
                    mock.patch.object(sampler, "_available_memory", return_value=100000), \
                    mock.patch.object(runtime.os, "sysconf", return_value=100, create=True), \
                    mock.patch.object(runtime.os, "sysconf_names", {"SC_CLK_TCK": 2}, create=True):
                sampler.start()
                sampler.stop()
            self.assertIsNone(sampler.failure)
            self.assertIn("\t43008\tNA\tNA\n", path.read_text())
            self.assertEqual(runtime.validate_resource_samples(path, {"mysql"})["io_unavailable_rows"], 1)
            notice = json.loads(path.with_suffix(".unavailable.jsonl").read_text())
            self.assertEqual((notice["label"], notice["pid"]), ("mysql", 123))
            original = path.read_text()
            for invalid in (original.replace("43008", "NA"), original.replace("\t0.000\t43008", "\tNaN\t43008")):
                path.write_text(invalid)
                with self.assertRaisesRegex(RuntimeError, "invalid/missing CPU/RSS"):
                    runtime.validate_resource_samples(path, {"mysql"})
            path.write_text(original)
            with self.assertRaisesRegex(RuntimeError, "missing process labels"):
                runtime.validate_resource_samples(path, {"mysql", "backend"})
            path.with_suffix(".unavailable.jsonl").unlink()
            with self.assertRaisesRegex(RuntimeError, "without unavailable evidence"):
                runtime.validate_resource_samples(path, {"mysql"})


@unittest.skipUnless(sys.platform == "linux", "requires real Linux procfs")
class LinuxProcIntegrationTests(unittest.TestCase):
    def test_real_child_zombie_then_reaped_driver_preserves_samples(self):
        with tempfile.TemporaryDirectory() as temp:
            child = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"],
                                     stdin=subprocess.PIPE)
            sampler = runtime.ResourceSampler(pathlib.Path(temp) / "resources.tsv",
                                              {"driver": child}, interval=60,
                                              allowed_exit_labels={"driver"})
            try:
                sampler.start()
                sampler._sample_once()
                child.stdin.close()
                deadline = time.monotonic() + 5
                while runtime.ResourceSampler._stat(child.pid)["state"] != "Z":
                    if time.monotonic() > deadline:
                        self.fail("child did not become zombie")
                    time.sleep(.01)
                with self.assertRaises(runtime.ProcessLifecycle) as caught:
                    runtime.ResourceSampler._process_details(child.pid)
                self.assertEqual(caught.exception.event, "PROCESS_ZOMBIE")
                sampler._sample_once()
                self.assertEqual(child.wait(timeout=5), 0)
                sampler.stop()
                result = runtime.validate_resource_samples(sampler.output, {"driver"}, 2)
                self.assertEqual(result["rows_by_label"]["driver"], 2)
                with self.assertRaises(runtime.ProcessLifecycle):
                    runtime.ResourceSampler._process_details(child.pid)
            finally:
                sampler.stop()
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=5)

    def test_real_current_process_io(self):
        result = runtime.ResourceSampler._process(os.getpid())
        self.assertGreater(result[1], 0)
        self.assertIsInstance(result[2], int)
        self.assertIsInstance(result[3], int)
        self.assertIsNone(result[4])

    @unittest.skipUnless(hasattr(os, "geteuid") and os.geteuid() == 0, "requires root to launch isolated nobody reader")
    def test_real_cross_uid_denial_cpu_rss_and_driver_continuation(self):
        # The root-owned test process stays alive; nobody reads its procfs.
        program = '''import importlib.util, pathlib, tempfile, sys, json
spec=importlib.util.spec_from_file_location("r",sys.argv[1]); r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp)/"resources.tsv"
 s=r.ResourceSampler(p,{"mysql":int(sys.argv[2])})
 s.start(); s.stop(); s.stop()
 assert s.failure is None
 result=r.validate_resource_samples(p,{"mysql"})
 assert result["cpu_rss_complete"] and result["io_unavailable_rows"]>=1, result
 assert "\\tNA\\tNA" in p.read_text()
 print(json.dumps({"real_cross_uid_proc":"PASS","driver_continued":True,**result}))
'''
        proc = subprocess.run([sys.executable, "-c", program, str(SOURCE), str(os.getpid())],
                              user=65534, group=65534, extra_groups=[], capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        print(proc.stdout.strip())


if __name__ == "__main__":
    unittest.main()
