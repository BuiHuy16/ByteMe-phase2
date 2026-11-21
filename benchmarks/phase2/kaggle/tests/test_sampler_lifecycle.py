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
    @staticmethod
    def details(pid=415, start=999):
        return {"state": "S", "ticks": 30, "start_time": start, "rss": 43008,
                "read_bytes": 123, "write_bytes": 456, "io_reason": None}

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

    def test_driver_normal_exit_and_zombie_are_lifecycle_events(self):
        for event, state in (("PROCESS_EXITED_DURING_SAMPLE", None), ("PROCESS_ZOMBIE", "Z")):
            with self.subTest(event=event), tempfile.TemporaryDirectory() as temp:
                path = pathlib.Path(temp) / "resources.tsv"
                driver = mock.Mock(pid=415, poll=mock.Mock(return_value=0))
                sampler = runtime.ResourceSampler(path, {"driver": driver}, interval=60,
                                                  allowed_exit_labels={"driver"})
                lifecycle = runtime.ProcessLifecycle(event, 415, state, 999, 999)
                with mock.patch.object(sampler, "_process_details",
                                       side_effect=[self.details(), lifecycle]), \
                        mock.patch.object(sampler, "_system_cpu", return_value=(100, 10)), \
                        mock.patch.object(sampler, "_available_memory", return_value=100000), \
                        mock.patch.object(runtime.os, "sysconf", return_value=100, create=True), \
                        mock.patch.object(runtime.os, "sysconf_names", {"SC_CLK_TCK": 2}, create=True):
                    sampler.start()
                    sampler._sample_once()
                    sampler.stop()
                self.assertIsNone(sampler.failure)
                validation = runtime.validate_resource_samples(path, {"driver"})
                self.assertEqual(validation["rows_by_label"]["driver"], 1)
                self.assertEqual(validation["lifecycle_events"][0]["event"], event)

    def test_required_service_exit_and_pid_reuse_fail_closed(self):
        for label, event in (("backend", "PROCESS_EXITED"), ("mysql", "PID_REUSED")):
            with self.subTest(label=label, event=event), tempfile.TemporaryDirectory() as temp:
                process = mock.Mock(pid=222, poll=mock.Mock(return_value=9 if event == "PROCESS_EXITED" else None))
                sampler = runtime.ResourceSampler(pathlib.Path(temp) / "resources.tsv", {label: process})
                sampler.output.parent.mkdir(parents=True, exist_ok=True)
                sampler.output.write_text("header\n", encoding="utf-8")
                lifecycle = runtime.ProcessLifecycle(event, 222, "S", 999, 1000)
                with mock.patch.object(sampler, "_process_details", side_effect=lifecycle), \
                        mock.patch.object(sampler, "_system_cpu", return_value=(100, 10)), \
                        mock.patch.object(runtime.os, "sysconf", return_value=100, create=True), \
                        mock.patch.object(runtime.os, "sysconf_names", {"SC_CLK_TCK": 2}, create=True):
                    with self.assertRaisesRegex(RuntimeError, "required process lifecycle failure"):
                        sampler._sample_once()
                event_doc = json.loads(sampler.output.with_suffix(".lifecycle.jsonl").read_text())
                self.assertEqual((event_doc["label"], event_doc["event"]), (label, event))

    def test_alive_process_telemetry_denial_fails_and_records_label(self):
        with tempfile.TemporaryDirectory() as temp:
            process = mock.Mock(pid=333, poll=mock.Mock(return_value=None))
            sampler = runtime.ResourceSampler(pathlib.Path(temp) / "resources.tsv", {"mysql": process})
            sampler.output.parent.mkdir(parents=True, exist_ok=True)
            sampler.output.write_text("header\n", encoding="utf-8")
            with mock.patch.object(sampler, "_process_details",
                                   side_effect=runtime.ProcessTelemetryUnavailable("VmRSS denied")), \
                    mock.patch.object(sampler, "_system_cpu", return_value=(100, 10)), \
                    mock.patch.object(runtime.os, "sysconf", return_value=100, create=True), \
                    mock.patch.object(runtime.os, "sysconf_names", {"SC_CLK_TCK": 2}, create=True):
                with self.assertRaisesRegex(runtime.ProcessTelemetryUnavailable, "VmRSS denied"):
                    sampler._sample_once()
            event_doc = json.loads(sampler.output.with_suffix(".lifecycle.jsonl").read_text())
            self.assertEqual((event_doc["label"], event_doc["event"]), ("mysql", "TELEMETRY_UNAVAILABLE"))

    def test_later_service_failure_preserves_earlier_valid_sample(self):
        with tempfile.TemporaryDirectory() as temp:
            sampler = runtime.ResourceSampler(pathlib.Path(temp) / "resources.tsv",
                                              {"backend": 1, "mysql": 2})
            with mock.patch.object(sampler, "_process_details", side_effect=[
                    self.details(), runtime.ProcessLifecycle("PROCESS_EXITED", 2)]), \
                    mock.patch.object(sampler, "_system_cpu", return_value=(100, 10)), \
                    mock.patch.object(sampler, "_available_memory", return_value=10000), \
                    mock.patch.object(runtime.os, "sysconf", return_value=100, create=True), \
                    mock.patch.object(runtime.os, "sysconf_names", {"SC_CLK_TCK": 2}, create=True):
                with self.assertRaisesRegex(RuntimeError, "required process lifecycle failure"):
                    sampler.start()
            self.assertIn("\tbackend\t1\t", sampler.output.read_text())
            self.assertNotIn("\tmysql\t2\t", sampler.output.read_text())

    def test_official_validator_requires_samples_and_rejects_service_lifecycle(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "resources.tsv"
            header = "timestamp_utc\tsystem_cpu_percent\tmemory_total_bytes\tmemory_available_bytes\tlabel\tpid\tprocess_cpu_percent\trss_bytes\tread_bytes\twrite_bytes\n"
            row = "now\t1\t100\t50\t{label}\t{pid}\t1\t42\t1\t2\n"
            path.write_text(header + "".join(row.format(label=label, pid=index) for index, label in
                                              enumerate(("backend", "mysql", "driver"), 1)), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "insufficient rows"):
                runtime.validate_resource_samples(path, {"backend", "mysql", "driver"}, 2)
            with path.open("a", encoding="utf-8") as stream:
                stream.write("".join(row.format(label=label, pid=index) for index, label in
                                     enumerate(("backend", "mysql", "driver"), 1)))
            driver_event = {"label": "driver", "pid": 3, "event": "PROCESS_EXITED",
                            "exit_code": 0, "reason": "normal"}
            path.with_suffix(".lifecycle.jsonl").write_text(json.dumps(driver_event) + "\n", encoding="utf-8")
            self.assertTrue(runtime.validate_resource_samples(
                path, {"backend", "mysql", "driver"}, 2)["cpu_rss_complete"])
            path.write_text(path.read_text().replace("now", "2026-11-21T00:00:00+00:00"))
            with self.assertRaisesRegex(RuntimeError, "duration insufficient"):
                runtime.validate_resource_samples(path, {"backend", "mysql", "driver"}, 2,
                                                  minimum_span_seconds=171)
            backend_event = {"label": "backend", "pid": 1, "event": "PROCESS_EXITED",
                             "exit_code": 1, "reason": "unexpected"}
            with path.with_suffix(".lifecycle.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(backend_event) + "\n")
            with self.assertRaisesRegex(RuntimeError, "invalid process lifecycle"):
                runtime.validate_resource_samples(path, {"backend", "mysql", "driver"}, 2)


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
