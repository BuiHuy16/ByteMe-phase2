"""Lifecycle acceptance tests; subprocess/Linux boundaries are mocked on Windows."""
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest
import zipfile
from unittest import mock

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "kaggle_runtime.py"
spec = importlib.util.spec_from_file_location("lifecycle_runtime", SOURCE)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class SamplerTests(unittest.TestCase):
    def test_stop_before_start_and_repeated_stop(self):
        sampler = runtime.ResourceSampler(pathlib.Path("unused"), {})
        sampler.stop()
        sampler.stop()
        self.assertIsNone(sampler.thread.ident)

    def test_normal_start_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            sampler = runtime.ResourceSampler(pathlib.Path(temp) / "resources.tsv", {})
            with mock.patch.object(sampler, "_sample_once") as sample:
                sampler.start()
                sampler.stop()
                sampler.stop()
            sample.assert_called_once()
            self.assertFalse(sampler.thread.is_alive())

    def test_initial_sample_failure_survives_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            sampler = runtime.ResourceSampler(pathlib.Path(temp) / "resources.tsv", {})
            with mock.patch.object(sampler, "_sample_once", side_effect=PermissionError("proc access")):
                with self.assertRaisesRegex(PermissionError, "proc access"):
                    try:
                        sampler.start()
                    finally:
                        sampler.stop()

    def test_background_exception_is_observable(self):
        sampler = runtime.ResourceSampler(pathlib.Path("unused"), {}, interval=0)
        with mock.patch.object(sampler, "_sample_once", side_effect=OSError("sample failed")):
            sampler._run()
        self.assertIn("OSError: sample failed", sampler.failure)


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.session = runtime.KaggleSession(self.temp.name, self.temp.name, "test")

    def test_sampler_failure_reaps_driver_preserves_primary_and_services(self):
        process = mock.Mock(pid=123)
        process.poll.return_value = None
        sampler = mock.Mock(failure=None)
        sampler.start.side_effect = PermissionError("primary proc failure")
        sampler.stop.side_effect = RuntimeError("secondary stop failure")
        with mock.patch.object(self.session, "_backend_alive"), \
                mock.patch.object(runtime.subprocess, "Popen", return_value=process), \
                mock.patch.object(runtime, "ResourceSampler", return_value=sampler):
            with self.assertRaisesRegex(PermissionError, "primary proc failure") as caught:
                self.session._run(["k6"], "w1/console.txt", "w1/resources.tsv")
        self.assertIn("secondary stop failure", str(caught.exception.__notes__))
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=10)
        self.assertIsNone(self.session.active_driver)

    def test_workload_wait_exception_reaps_driver(self):
        process = mock.Mock(pid=123)
        process.poll.return_value = None
        process.wait.side_effect = [OSError("wait failed"), 0]
        with mock.patch.object(runtime.subprocess, "Popen", return_value=process):
            with self.assertRaisesRegex(OSError, "wait failed"):
                self.session._run(["driver"], "console.txt")
        process.terminate.assert_called_once()

    def test_backend_dead_before_workload_records_evidence_and_no_launch(self):
        self.session.processes["backend"] = mock.Mock(pid=111, poll=mock.Mock(return_value=9))
        with mock.patch.object(runtime.subprocess, "Popen") as launch:
            with self.assertRaisesRegex(RuntimeError, "exit_code=9"):
                self.session._run(["k6"], "w1/console.txt", "w1/resources.tsv")
        launch.assert_not_called()
        evidence = json.loads((self.session.evidence / "environment/backend-lifecycle.json").read_text())
        self.assertEqual(evidence["pid"], 111)

    def test_backend_dies_during_workload_driver_stopped_first(self):
        driver = mock.Mock(pid=222, poll=mock.Mock(return_value=None))
        backend = mock.Mock(pid=111, poll=mock.Mock(return_value=1))
        self.session.processes["backend"] = backend
        with mock.patch.object(self.session, "_backend_alive", side_effect=[None, RuntimeError("backend exited")]), \
                mock.patch.object(runtime.subprocess, "Popen", return_value=driver), \
                mock.patch.object(runtime, "ResourceSampler", return_value=mock.Mock(failure=None)):
            with self.assertRaisesRegex(RuntimeError, "backend exited"):
                self.session._run(["k6"], "w1/console.txt", "w1/resources.tsv")
        driver.terminate.assert_called_once()
        backend.terminate.assert_not_called()

    def test_cleanup_does_not_stop_services_when_driver_cannot_be_reaped(self):
        backend = mock.Mock()
        self.session.processes["backend"] = backend
        with mock.patch.object(self.session, "_stop_driver", side_effect=OSError("cannot reap")):
            result = self.session.cleanup()
        self.assertFalse(result["success"])
        backend.terminate.assert_not_called()

    def test_smoke_traceback_in_zip_and_secret_redacted(self):
        self.session.probe()
        probe = self.session.evidence / "environment/hardware-runtime.json"
        data = json.loads(probe.read_text())
        data["is_kaggle"] = True
        probe.write_text(json.dumps(data))
        with mock.patch.object(self.session, "resolve_bundle", side_effect=RuntimeError(self.session.db_password)):
            result = self.session.run_smoke()
        self.assertEqual(result["status"], "FAIL")
        with zipfile.ZipFile(result["evidence_zip"]) as archive:
            trace = archive.read("logs/smoke-failure-traceback.txt").decode()
        self.assertIn("Traceback", trace)
        self.assertNotIn(self.session.db_password, trace)

    def test_all_http_checks_failed_despite_zero_k6_exit(self):
        path = pathlib.Path(self.temp.name) / "summary.json"
        path.write_text(json.dumps({"metrics": {
            "checks": {"values": {"passes": 0, "fails": 6}},
            "http_reqs": {"values": {"count": 6}},
            "http_req_failed": {"values": {"rate": 1}},
            "application_error_rate": {"values": {"rate": 1}},
        }}))
        with self.assertRaisesRegex(RuntimeError, "check mismatch"):
            runtime.validate_k6_smoke_summary(path, "W1")


if __name__ == "__main__":
    unittest.main()
