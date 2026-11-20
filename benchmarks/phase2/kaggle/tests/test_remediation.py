from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import tarfile
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[4]


def load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


runtime = load("g24k_runtime", "benchmarks/phase2/kaggle/kaggle_runtime.py")
dataset = load("g24k_dataset", "benchmarks/phase2/prepare_dataset.py")
comparator = load("g24k_compare", "benchmarks/phase2/kaggle/compare_manifests.py")


def metric(values: dict) -> dict:
    return {"type": "counter", "contains": "default", "values": values}


def summary(workload: str) -> dict:
    if workload == "W1":
        checks, requests, error_metric = 6, 6, "application_error_rate"
    else:
        checks, requests, error_metric = 8, 8, "write_error_rate"
    return {"metrics": {
        "checks": metric({"passes": checks, "fails": 0, "rate": 1}),
        "http_reqs": metric({"count": requests, "rate": 1}),
        "http_req_failed": metric({"rate": 0, "passes": 0, "fails": requests}),
        error_metric: metric({"rate": 0, "passes": 0, "fails": requests}),
    }}


def full_manifest(application_sha: str = "a" * 40) -> dict:
    return {
        "source": {"protocol_baseline_sha": runtime.BASELINE_SHA, "repository_sha": "b" * 40,
                   "application_sha": application_sha, "application_jar_sha256": "c" * 64},
        "hardware": {"cpu_model": "CPU", "logical_cores": 4, "memory_total_bytes": 32_000,
                     "os_id": "ubuntu", "os_version": "24.04", "kernel": "6.1",
                     "runtime_image_identity": "d" * 64,
                     "cgroup": {"version": "v2", "cpu_quota_raw": "400000 100000",
                                "cpu_period_us": 100000, "cpuset_effective": "0-3",
                                "cpuset_cpu_count": 4, "memory_limit_raw": "32000",
                                "resolved_cpu_limit": 4.0, "resolved_memory_limit_bytes": 32000,
                                "quota_evidence_complete": True}},
        "toolchain": {"java_version": "21.0.13", "mysql_version": "8.4.13", "k6_version": "v0.55.2",
                      "java_executable_sha256": "e", "mysqld_executable_sha256": "f",
                      "k6_executable_sha256": "g"},
        "locks": {"configuration_sha256": "h", "workload_source_sha256": "i", "dataset_sha256": "j"},
    }


class DatasetSemanticsTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"categories": 3, "read_foods": 60, "read_orders": 20, "items_per_order": 2,
                        "write_actors": 2, "contention_actors": 4, "shared_stock": 10}
        self.counts = {"users": 8, "categories": 3, "foods": 63, "carts": 2,
                       "cart_items": 0, "orders": 22, "order_items": 42}
        self.kwargs = dict(read_orders=20, read_order_items=40, shared_stock=10,
                           orphan_order_items=0, orphan_cart_items=0, negative_food_stock=0,
                           invalid_cart_quantities=0, invalid_order_quantities=0)

    def test_post_workload_valid_mutation_passes(self):
        result = dataset.evaluate_invariants(self.profile, self.counts,
                                             validation_phase="post_workload", **self.kwargs)
        self.assertTrue(all(result.values()), result)

    def test_same_mutation_is_not_valid_initial_state(self):
        result = dataset.evaluate_invariants(self.profile, self.counts,
                                             validation_phase="initial", **self.kwargs)
        self.assertFalse(all(result.values()))
        self.assertFalse(result["initial_carts_empty"])

    def test_post_workload_still_rejects_orphan(self):
        values = {**self.kwargs, "orphan_order_items": 1}
        result = dataset.evaluate_invariants(self.profile, self.counts,
                                             validation_phase="post_workload", **values)
        self.assertFalse(result["no_orphan_order_items"])


class SmokeValidationTests(unittest.TestCase):
    def write_summary(self, directory: pathlib.Path, workload: str, document: dict | None = None) -> pathlib.Path:
        path = directory / "summary.json"
        path.write_text(json.dumps(document or summary(workload)), encoding="utf-8")
        return path

    def test_valid_k6_summaries_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            self.assertEqual(runtime.validate_k6_smoke_summary(self.write_summary(root, "W1"), "W1")["checks"], 6)
            self.assertEqual(runtime.validate_k6_smoke_summary(self.write_summary(root, "W2"), "W2")["checks"], 8)

    def test_k6_exit_zero_but_failed_check_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            document = summary("W1")
            document["metrics"]["checks"]["values"] = {"passes": 5, "fails": 1, "rate": 5 / 6}
            with self.assertRaisesRegex(RuntimeError, "check mismatch"):
                runtime.validate_k6_smoke_summary(self.write_summary(pathlib.Path(temp), "W1", document), "W1")

    def test_unexpected_and_transport_failures_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            document = summary("W2")
            document["metrics"]["unexpected_responses"] = metric({"count": 1, "rate": 1})
            with self.assertRaisesRegex(RuntimeError, "unexpected responses"):
                runtime.validate_k6_smoke_summary(self.write_summary(pathlib.Path(temp), "W2", document), "W2")

    def test_request_count_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            document = summary("W1")
            document["metrics"]["http_reqs"]["values"]["count"] = 5
            with self.assertRaisesRegex(RuntimeError, "request-count mismatch"):
                runtime.validate_k6_smoke_summary(self.write_summary(pathlib.Path(temp), "W1", document), "W1")
            document = summary("W2")
            document["metrics"]["http_req_failed"]["values"]["rate"] = 0.125
            with self.assertRaisesRegex(RuntimeError, "HTTP/workload errors"):
                runtime.validate_k6_smoke_summary(self.write_summary(pathlib.Path(temp), "W2", document), "W2")

    def test_header_only_resource_telemetry_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "resources.tsv"
            path.write_text("timestamp_utc\tlabel\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "no samples"):
                runtime.validate_resource_samples(path, {"backend", "mysql", "driver"})

    def test_w3_baseline_defects_do_not_fail_valid_harness(self):
        scenarios = {}
        for name in ("same_food_checkout", "same_cart_checkout", "admin_stock_vs_checkout"):
            rounds = [{"round": number, "responses": [{"http_status": 201}, {"http_status": 500}],
                       "after": {"orders": 1}, "violations": ["BASELINE_DEFECT"]} for number in (1, 2)]
            scenarios[name] = {"rounds": rounds, "violation_rounds": [1, 2], "server_error_rounds": [1, 2]}
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "w3.json"
            path.write_text(json.dumps({"rounds_per_scenario": 2, "scenarios": scenarios}), encoding="utf-8")
            self.assertTrue(runtime.validate_w3_smoke_result(path, 2)["harness_valid"])


class ReliabilityTests(unittest.TestCase):
    def test_failure_still_creates_zip_and_cleanup_failure_forces_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="failure-evidence")
            session.probe()
            probe_path = session.evidence / "environment/hardware-runtime.json"
            probe = json.loads(probe_path.read_text(encoding="utf-8"))
            probe["is_kaggle"] = True
            probe_path.write_text(json.dumps(probe), encoding="utf-8")
            with mock.patch.object(session, "resolve_bundle", side_effect=RuntimeError("adversarial failure")), \
                    mock.patch.object(session, "cleanup", return_value={"success": False, "errors": ["cleanup failed"]}):
                result = session.run_smoke()
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("cleanup failed", result["error"])
            self.assertTrue(pathlib.Path(result["evidence_zip"]).is_file())

    def test_cleanup_error_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="cleanup")
            session.probe()
            with mock.patch.object(runtime.shutil, "rmtree", side_effect=OSError("denied")):
                result = session.cleanup()
            self.assertFalse(result["success"])
            self.assertIn("runtime-secret cleanup", result["errors"][0])

    def test_reset_checksum_failure_forces_smoke_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="reset-failure")
            session.probe()
            probe_path = session.evidence / "environment/hardware-runtime.json"
            probe = json.loads(probe_path.read_text(encoding="utf-8"))
            probe["is_kaggle"] = True
            probe_path.write_text(json.dumps(probe), encoding="utf-8")
            cleanup = {"success": True, "backend_stopped": True, "mysql_stopped": True,
                       "runtime_secret_removed": True, "errors": []}
            with mock.patch.object(session, "resolve_bundle"), mock.patch.object(session, "setup_toolchain"), \
                    mock.patch.object(session, "start_mysql"), mock.patch.object(session, "start_backend"), \
                    mock.patch.object(session, "run_workloads", side_effect=RuntimeError("reset checksum mismatch")), \
                    mock.patch.object(session, "cleanup", return_value=cleanup), \
                    mock.patch.object(session, "write_run_manifest"):
                result = session.run_smoke()
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("reset checksum mismatch", result["error"])

    def test_secret_scan_detects_jwt_and_private_key(self):
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="secret")
            session.probe()
            (session.evidence / "leak.txt").write_text(
                "-----BEGIN PRIVATE KEY-----\neyJ" + "A" * 24 + "." + "B" * 12 + "." + "C" * 12,
                encoding="utf-8")
            self.assertEqual(session.scan_evidence_secrets(), ["leak.txt"])


class ArchiveSafetyTests(unittest.TestCase):
    def make_tar(self, path: pathlib.Path, member: tarfile.TarInfo, data: bytes = b""):
        with tarfile.open(path, "w") as archive:
            archive.addfile(member, io.BytesIO(data) if member.isfile() else None)

    def test_regular_directory_is_extracted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archive = root / "directory.tar"
            member = tarfile.TarInfo("mysql-8.4.13-linux-glibc2.28-x86_64/bin")
            member.type = tarfile.DIRTYPE
            self.make_tar(archive, member)
            runtime.safe_extract(archive, root / "out")
            self.assertTrue((root / "out" / member.name).is_dir())

    def test_duplicate_directory_entries_are_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archive = root / "duplicate-directory.tar"
            name = "mysql-8.4.13-linux-glibc2.28-x86_64/bin"
            with tarfile.open(archive, "w") as bundle:
                for _ in range(2):
                    member = tarfile.TarInfo(name)
                    member.type = tarfile.DIRTYPE
                    bundle.addfile(member)
            runtime.safe_extract(archive, root / "out")
            self.assertTrue((root / "out" / name).is_dir())

    def test_regular_file_is_extracted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archive = root / "file.tar"
            content = b"mysql binary placeholder"
            member = tarfile.TarInfo("mysql-8.4.13-linux-glibc2.28-x86_64/bin/mysqld")
            member.size = len(content)
            self.make_tar(archive, member, content)
            runtime.safe_extract(archive, root / "out")
            self.assertEqual((root / "out" / member.name).read_bytes(), content)

    def test_directory_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archive = root / "bad-directory.tar"
            member = tarfile.TarInfo("../escape")
            member.type = tarfile.DIRTYPE
            self.make_tar(archive, member)
            with self.assertRaisesRegex(RuntimeError, "unsafe archive member"):
                runtime.safe_extract(archive, root / "out")

    def test_duplicate_regular_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archive = root / "duplicate-file.tar"
            name = "inside/file"
            with tarfile.open(archive, "w") as bundle:
                for content in (b"first", b"second"):
                    member = tarfile.TarInfo(name)
                    member.size = len(content)
                    bundle.addfile(member, io.BytesIO(content))
            with self.assertRaisesRegex(RuntimeError, "duplicate archive member"):
                runtime.safe_extract(archive, root / "out")

    def test_path_escape_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archive = root / "bad.tar"
            member = tarfile.TarInfo("inside/link")
            member.type, member.linkname = tarfile.SYMTYPE, "../../escape"
            self.make_tar(archive, member)
            with self.assertRaisesRegex(RuntimeError, "unsafe symlink"):
                runtime.safe_extract(archive, root / "out")

    def test_path_escape_hardlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archive = root / "bad-hard.tar"
            member = tarfile.TarInfo("inside/link")
            member.type, member.linkname = tarfile.LNKTYPE, "../escape"
            self.make_tar(archive, member)
            with self.assertRaisesRegex(RuntimeError, "unsafe hardlink"):
                runtime.safe_extract(archive, root / "out")

    def test_safe_hardlink_is_extracted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archive = root / "hardlink.tar"
            content = b"library"
            target = tarfile.TarInfo("inside/libmysqlclient.so.24")
            target.size = len(content)
            link = tarfile.TarInfo("inside/libmysqlclient.so")
            link.type, link.linkname = tarfile.LNKTYPE, target.name
            with tarfile.open(archive, "w") as bundle:
                bundle.addfile(target, io.BytesIO(content))
                bundle.addfile(link)
            runtime.safe_extract(archive, root / "out")
            self.assertEqual((root / "out" / link.name).read_bytes(), content)

    def test_special_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archive = root / "fifo.tar"
            member = tarfile.TarInfo("inside/fifo")
            member.type = tarfile.FIFOTYPE
            self.make_tar(archive, member)
            with self.assertRaisesRegex(RuntimeError, "unsupported archive member type"):
                runtime.safe_extract(archive, root / "out")


class HardwareComparatorTests(unittest.TestCase):
    def test_cgroup_v2_limits_are_resolved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "cgroup"
            root.mkdir()
            (root / "cgroup.controllers").write_text("cpu cpuset memory", encoding="utf-8")
            (root / "cpu.max").write_text("200000 100000", encoding="utf-8")
            (root / "cpuset.cpus.effective").write_text("0-1", encoding="utf-8")
            (root / "memory.max").write_text("1073741824", encoding="utf-8")
            proc = pathlib.Path(temp) / "proc-cgroup"
            proc.write_text("0::/\n", encoding="utf-8")
            result = runtime.resolve_cgroup_limits(root, proc)
            self.assertTrue(result["quota_evidence_complete"])
            self.assertEqual(result["resolved_cpu_limit"], 2.0)
            self.assertEqual(result["resolved_memory_limit_bytes"], 1073741824)

    def test_different_treatment_sha_is_allowed_but_hardware_difference_is_not(self):
        first, second = full_manifest("a" * 40), full_manifest("z" * 40)
        self.assertTrue(comparator.compare_documents([first, second])["comparable"])
        second["hardware"]["cgroup"]["cpuset_effective"] = "0-2"
        self.assertFalse(comparator.compare_documents([first, second])["comparable"])

    def test_missing_quota_evidence_is_rejected(self):
        first, second = full_manifest(), full_manifest()
        del second["hardware"]["cgroup"]["memory_limit_raw"]
        result = comparator.compare_documents([first, second])
        self.assertFalse(result["comparable"])
        self.assertTrue(any(item["reason"] == "missing" for item in result["mismatches"]))


if __name__ == "__main__":
    unittest.main()
