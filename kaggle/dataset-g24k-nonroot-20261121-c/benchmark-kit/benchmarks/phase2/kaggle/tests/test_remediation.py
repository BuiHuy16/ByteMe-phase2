from __future__ import annotations

import importlib.util
import hashlib
import io
import json
import os
import pathlib
import sys
import tarfile
import tempfile
import types
import unittest
import zipfile
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
                      "k6_executable_sha256": "g", "libaio_package_version": "0.3.113-6build1.1",
                      "libaio_package_sha256": "k", "libaio_library_sha256": "l",
                      "libaio_library_soname": "libaio.so.1t64",
                      "libaio_compatibility_soname": "libaio.so.1"},
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
    def test_root_mysql_identity_drops_privileges_and_records_uid_gid(self):
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="root-identity")
            account = mock.Mock(pw_uid=65534, pw_gid=65534, pw_name="nobody")
            pwd_api = types.SimpleNamespace(getpwnam=mock.Mock(return_value=account))
            with mock.patch.object(runtime.os, "geteuid", return_value=0, create=True), \
                    mock.patch.object(runtime, "pwd", pwd_api):
                identity = session._mysql_identity()
            self.assertEqual(identity, (65534, 65534, "nobody"))
            demote = session._drop_mysql_privileges(identity[0], identity[1])
            with mock.patch.object(runtime.os, "setgid", create=True) as setgid, \
                    mock.patch.object(runtime.os, "setuid", create=True) as setuid:
                demote()
            setgid.assert_called_once_with(65534)
            setuid.assert_called_once_with(65534)

    def test_nonroot_mysql_identity_keeps_current_uid_gid(self):
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="user-identity")
            with mock.patch.object(runtime.os, "geteuid", return_value=1000, create=True), \
                    mock.patch.object(runtime.os, "getegid", return_value=1001, create=True):
                self.assertEqual(session._mysql_identity(), (1000, 1001, "current-user"))

    def test_mysql_startup_root_failure_regression_runs_init_and_server_demoted(self):
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="root-regression")
            session.config = {"runtime": {"mysql_port": 13309, "mysql_transaction_isolation": "REPEATABLE-READ",
                                           "mysql_max_connections": 100, "mysql_innodb_buffer_pool_size": 536870912,
                                           "database": "testdb", "database_user": "tester"}}
            session.tools = {"mysqld": pathlib.Path(temp) / "mysql/bin/mysqld"}
            session.tools["mysqld"].parent.mkdir(parents=True)
            session.evidence.mkdir(parents=True)
            session.evidence.joinpath("logs").mkdir()
            schema = pathlib.Path(temp) / "schema.sql"
            schema.write_text("SELECT 1;", encoding="utf-8")
            session._mysql_identity = lambda: (65534, 65534, "nobody")
            calls = []
            def run(*args, **kwargs):
                calls.append(kwargs.get("preexec_fn"))
                return runtime.subprocess.CompletedProcess(args[0], 0, "", "")
            class Process:
                def poll(self): return None
            def popen(*args, **kwargs):
                calls.append(kwargs.get("preexec_fn"))
                return Process()
            pings = iter([runtime.subprocess.CompletedProcess([], 0, "", "")])
            session.tools.update({"mysqladmin": pathlib.Path(temp) / "mysql/bin/mysqladmin"})
            with mock.patch.object(session, "_drop_mysql_privileges", return_value=lambda: None), \
                    mock.patch.object(runtime.os, "geteuid", return_value=0, create=True), \
                    mock.patch.object(runtime.os, "chown", create=True), \
                    mock.patch.object(session, "_mysql"), mock.patch.object(session, "_find_single", return_value=schema), \
                    mock.patch.object(runtime.subprocess, "run", side_effect=lambda *a, **kw: next(pings) if "mysqladmin" in str(a[0][0]) else run(*a, **kw)), \
                    mock.patch.object(runtime.subprocess, "Popen", side_effect=popen), \
                    mock.patch.object(session, "_prepare_mysql_writable_paths"):
                session.start_mysql()
            self.assertEqual(len(calls), 2)
            self.assertTrue(all(call is not None for call in calls))
            self.assertEqual(session.mysql_process_identity["uid"], 65534)

    def test_mysql_early_exit_diagnostics_survive_cleanup_and_zip(self):
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="mysql-exit")
            session.probe()
            probe_path = session.evidence / "environment/hardware-runtime.json"
            probe = json.loads(probe_path.read_text(encoding="utf-8"))
            probe["is_kaggle"] = True
            probe_path.write_text(json.dumps(probe), encoding="utf-8")
            session.config = {"runtime": {"mysql_host": "127.0.0.1", "mysql_port": 13309,
                                          "mysql_transaction_isolation": "REPEATABLE-READ",
                                          "mysql_max_connections": 100,
                                          "mysql_innodb_buffer_pool_size": 536870912}}
            session.tools = {"mysqld": pathlib.Path(temp) / "mysql/bin/mysqld"}
            def fake_run(*args, **kwargs):
                (session.evidence / "logs/mysql.log").write_text(
                    "MySQL Server Initialization - end\n", encoding="utf-8")
                return runtime.subprocess.CompletedProcess(args[0], 0, "", "")
            class ExitedProcess:
                def poll(self):
                    return -9
            def fake_popen(*args, **kwargs):
                kwargs["stdout"].write(b"startup stdout\n")
                kwargs["stderr"].write(b"startup stderr\n")
                return ExitedProcess()
            with mock.patch.object(session, "resolve_bundle"), \
                    mock.patch.object(session, "setup_toolchain"), \
                    mock.patch.object(session, "write_run_manifest"), \
                    mock.patch.object(runtime.subprocess, "run", side_effect=fake_run), \
                    mock.patch.object(runtime.subprocess, "Popen", side_effect=fake_popen):
                result = session.run_smoke()
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("environment/mysql-startup-failure.json", result["error"])
            with zipfile.ZipFile(result["evidence_zip"]) as evidence:
                names = set(evidence.namelist())
                self.assertTrue({"logs/mysql-startup.stdout.log", "logs/mysql-startup.stderr.log",
                                 "logs/mysql.log", "environment/mysql-startup-failure.json"} <= names)
                details = json.loads(evidence.read("environment/mysql-startup-failure.json"))
                self.assertEqual(details["exit_code"], -9)
                self.assertEqual(details["signal"], 9)
                self.assertEqual(evidence.read("logs/mysql-startup.stderr.log"), b"startup stderr\n")
                self.assertNotIn(session.db_password.encode(), evidence.read("logs/mysql-startup.stderr.log"))

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


class OfflineDependencyTests(unittest.TestCase):
    def elf_fixture(self, machine: int = 62, markers: tuple[str, ...] =
                    ("libaio.so.1t64", "LIBAIO_0.1", "LIBAIO_0.4", "LIBAIO_0.5", "LIBAIO_0.6")) -> bytes:
        data = bytearray(20)
        data[:4] = b"\x7fELF"
        data[4], data[5], data[7] = 2, 1, 0
        data[18:20] = machine.to_bytes(2, "little")
        for marker in markers:
            data.extend(marker.encode() + b"\0")
        return bytes(data)

    def lock_for(self, data: bytes) -> dict:
        return {"library_sha256": hashlib.sha256(data).hexdigest(),
                "elf": {"class": 2, "data": 1, "osabi": 0, "machine": 62,
                        "soname": "libaio.so.1t64",
                        "required_symbol_versions": ["LIBAIO_0.1", "LIBAIO_0.4", "LIBAIO_0.5", "LIBAIO_0.6"]}}

    def test_locked_libaio_elf_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            data = self.elf_fixture()
            path = pathlib.Path(temp) / "libaio.so.1t64.0.2"
            path.write_bytes(data)
            result = runtime.inspect_elf_library(path, self.lock_for(data))
            self.assertEqual(result["machine"], 62)
            self.assertEqual(result["soname"], "libaio.so.1t64")

    def test_wrong_elf_architecture_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            data = self.elf_fixture(machine=183)
            path = pathlib.Path(temp) / "libaio.so.1t64.0.2"
            path.write_bytes(data)
            with self.assertRaisesRegex(RuntimeError, "ELF mismatch"):
                runtime.inspect_elf_library(path, self.lock_for(data))

    def test_missing_libaio_abi_marker_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            data = self.elf_fixture(markers=("libaio.so.1t64", "LIBAIO_0.1"))
            path = pathlib.Path(temp) / "libaio.so.1t64.0.2"
            path.write_bytes(data)
            with self.assertRaisesRegex(RuntimeError, "ABI markers missing"):
                runtime.inspect_elf_library(path, self.lock_for(data))

    def test_ldd_preflight_reports_missing_libraries_and_uses_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="ldd")
            completed = runtime.subprocess.CompletedProcess(
                ["ldd", "mysqld"], 0, "libaio.so.1 => not found\nlibc.so.6 => /lib/libc.so.6\n", "")
            env = {"LD_LIBRARY_PATH": "/tmp/locked-libaio"}
            with mock.patch.object(runtime.shutil, "which", return_value="/usr/bin/ldd"), \
                    mock.patch.object(runtime.subprocess, "run", return_value=completed) as execute:
                report = session._dynamic_dependencies(pathlib.Path("/tmp/mysqld"), env)
            self.assertEqual(report["missing"], ["libaio.so.1"])
            self.assertIs(execute.call_args.kwargs["env"], env)


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

    @unittest.skipIf(sys.platform == "win32", "os.link requires elevated privileges on Windows")
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

    def test_different_libaio_hash_is_not_comparable(self):
        first, second = full_manifest(), full_manifest()
        second["toolchain"]["libaio_package_sha256"] = "different"
        result = comparator.compare_documents([first, second])
        self.assertFalse(result["comparable"])
        self.assertTrue(any(item["field"] == "toolchain.libaio_package_sha256"
                            for item in result["mismatches"]))


class PrepareKaggleInputTests(unittest.TestCase):
    """Acceptance tests for prepare_kaggle_input() covering all G2.4-K acceptance gates."""

    # --- helpers ---

    JAVA_VERSION_STRING = "openjdk version \"21.0.13\" 2024-01-16 LTS"
    K6_VERSION_STRING = "k6 v0.55.2 (go1.22.0, linux/amd64)"

    BASELINE_SHA = runtime.BASELINE_SHA
    LOCK_VERSION = "0.3.113-6build1.1"

    def _make_config_lock(self, root: pathlib.Path) -> pathlib.Path:
        lock = {
            "schema_version": 2,
            "platform": "kaggle-cpu",
            "baseline_sha": self.BASELINE_SHA,
            "expected_versions": {
                "java_contains": "21.0.13",
                "mysql_contains": "8.4.13",
                "k6_contains": "v0.55.2",
            },
            "offline_dependencies": {
                "libaio": {
                    "package": "libaio1t64",
                    "version": self.LOCK_VERSION,
                    "architecture": "amd64",
                    "filename": "libaio1t64_0.3.113-6build1.1_amd64.deb",
                    "source_url": "https://example.com/libaio.deb",
                    "package_sha256": "aa" * 32,
                    "library_path": "usr/lib/x86_64-linux-gnu/libaio.so.1t64.0.2",
                    "library_sha256": "bb" * 32,
                    "compatibility_soname": "libaio.so.1",
                    "elf": {
                        "class": 2, "data": 1, "osabi": 0, "machine": 62,
                        "soname": "libaio.so.1t64",
                        "required_symbol_versions": ["LIBAIO_0.1", "LIBAIO_0.4"],
                    },
                }
            },
            "runtime": {
                "mysql_host": "127.0.0.1",
                "mysql_port": 13309,
                "mysql_transaction_isolation": "REPEATABLE-READ",
                "mysql_max_connections": 100,
                "mysql_innodb_buffer_pool_size": 536870912,
            },
        }
        path = root / "configuration-lock.json"
        path.write_text(json.dumps(lock), encoding="utf-8")
        return path

    def _make_bundle_root(self, root: pathlib.Path) -> pathlib.Path:
        bundle = root / "bundle"
        bundle.mkdir()
        app = bundle / "application.jar"
        app.write_bytes(b"fake jar")
        schema = bundle / "schema.sql"
        schema_data = b"-- schema"
        schema.write_bytes(schema_data)
        lock_path = bundle / "benchmark-kit" / "benchmarks" / "phase2" / "kaggle"
        lock_path.mkdir(parents=True)
        self._make_config_lock(lock_path)
        manifest = {
            "schema_version": 1,
            "protocol_baseline_sha": self.BASELINE_SHA,
            "files": [
                {"path": "application.jar", "sha256": hashlib.sha256(b"fake jar").hexdigest()},
                {"path": "schema.sql", "sha256": hashlib.sha256(schema_data).hexdigest()},
            ],
        }
        (bundle / "bundle-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return bundle

    def _make_mysql_archive(self, root: pathlib.Path) -> pathlib.Path:
        archive_path = root / "mysql-8.4.13-linux-glibc2.28-x86_64.tar.xz"
        with tarfile.open(archive_path, "w:xz") as tar:
            info = tarfile.TarInfo("mysql-8.4.13/bin/mysqld")
            info.size = 4
            tar.addfile(info, io.BytesIO(b"fake"))
        return archive_path

    def _make_libaio_deb(self, root: pathlib.Path) -> pathlib.Path:
        """Create a fake libaio .deb whose sha256 matches the lock."""
        fake_data = b"fake-deb-data"
        path = root / "libaio1t64_0.3.113-6build1.1_amd64.deb"
        path.write_bytes(fake_data)
        return path, hashlib.sha256(fake_data).hexdigest()

    def _make_java_archive(self, root: pathlib.Path) -> pathlib.Path:
        archive_path = root / "jdk-21.0.13_linux-x64_bin.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            d = tarfile.TarInfo("jdk-21.0.13/bin")
            d.type = tarfile.DIRTYPE
            tar.addfile(d)
            info = tarfile.TarInfo("jdk-21.0.13/bin/java")
            info.size = 4
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(b"fake"))
        return archive_path

    def _make_k6_archive(self, root: pathlib.Path) -> pathlib.Path:
        archive_path = root / "k6-v0.55.2-linux-amd64.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            d = tarfile.TarInfo("k6-v0.55.2-linux-amd64")
            d.type = tarfile.DIRTYPE
            tar.addfile(d)
            info = tarfile.TarInfo("k6-v0.55.2-linux-amd64/k6")
            info.size = 4
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(b"fake"))
        return archive_path

    def _make_extracted_java(self, root: pathlib.Path) -> pathlib.Path:
        """Simulate Kaggle auto-extracting Java JRE directory."""
        java_root = root / "jdk-21.0.13"
        bin_dir = java_root / "bin"
        bin_dir.mkdir(parents=True)
        java_bin = bin_dir / "java"
        java_bin.write_bytes(b"fake")
        java_bin.chmod(0o755)
        return java_bin

    def _make_extracted_k6(self, root: pathlib.Path) -> pathlib.Path:
        """Simulate Kaggle auto-extracting k6 directory."""
        k6_root = root / "k6-v0.55.2-linux-amd64"
        k6_root.mkdir(parents=True)
        k6_bin = k6_root / "k6"
        k6_bin.write_bytes(b"fake")
        k6_bin.chmod(0o755)
        return k6_bin

    def _update_lock_libaio_sha(self, bundle_root: pathlib.Path, deb_sha: str) -> None:
        """Update the libaio package_sha256 in the lock file to match the fake deb."""
        lock_path = list(bundle_root.rglob("configuration-lock.json"))[0]
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock["offline_dependencies"]["libaio"]["package_sha256"] = deb_sha
        lock_path.write_text(json.dumps(lock), encoding="utf-8")

    def _fake_version_runner(self, component, executable, args):
        return self.JAVA_VERSION_STRING if component == "java" else self.K6_VERSION_STRING

    # ----- Regression test: reproduces the original "no exact java 21.0.13; archives=[]" bug -----

    def test_regression_extracted_java_no_longer_raises_no_exact_java(self):
        """Regression: prepare_kaggle_input must accept Kaggle auto-extracted Java (no archive)."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle_root = self._make_bundle_root(root)
            self._make_mysql_archive(root)
            deb_path, deb_sha = self._make_libaio_deb(root)
            self._update_lock_libaio_sha(bundle_root, deb_sha)
            # Simulate Kaggle auto-extracted Java (no archive)
            self._make_extracted_java(root)
            self._make_k6_archive(root)
            # Must NOT raise "no exact java 21.0.13; archives=[]"
            prepared = runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)
            self.assertTrue((prepared / "bootstrap-manifest.json").is_file())
            manifest = json.loads((prepared / "bootstrap-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["components"]["java"]["source_kind"], "extracted")

    def test_java_archive_is_accepted(self):
        """Java archive is extracted, executable found, version verified."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle_root = self._make_bundle_root(root)
            self._make_mysql_archive(root)
            deb_path, deb_sha = self._make_libaio_deb(root)
            self._update_lock_libaio_sha(bundle_root, deb_sha)
            self._make_java_archive(root)
            self._make_k6_archive(root)
            prepared = runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)
            manifest = json.loads((prepared / "bootstrap-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["components"]["java"]["source_kind"], "archive")
            self.assertIn("21.0.13", manifest["components"]["java"]["version"])

    def test_k6_extracted_is_accepted(self):
        """Kaggle auto-extracted k6 (no archive) is accepted."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle_root = self._make_bundle_root(root)
            self._make_mysql_archive(root)
            deb_path, deb_sha = self._make_libaio_deb(root)
            self._update_lock_libaio_sha(bundle_root, deb_sha)
            self._make_java_archive(root)
            self._make_extracted_k6(root)
            prepared = runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)
            manifest = json.loads((prepared / "bootstrap-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["components"]["k6"]["source_kind"], "extracted")

    def test_both_extracted_java_and_k6_accepted(self):
        """Both Java and k6 auto-extracted (no archives) works in combination."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle_root = self._make_bundle_root(root)
            self._make_mysql_archive(root)
            deb_path, deb_sha = self._make_libaio_deb(root)
            self._update_lock_libaio_sha(bundle_root, deb_sha)
            self._make_extracted_java(root)
            self._make_extracted_k6(root)
            prepared = runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)
            manifest = json.loads((prepared / "bootstrap-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["components"]["java"]["source_kind"], "extracted")
            self.assertEqual(manifest["components"]["k6"]["source_kind"], "extracted")

    def test_missing_java_raises(self):
        """No Java source (archive or extracted) raises RuntimeError."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle_root = self._make_bundle_root(root)
            self._make_mysql_archive(root)
            deb_path, deb_sha = self._make_libaio_deb(root)
            self._update_lock_libaio_sha(bundle_root, deb_sha)
            self._make_k6_archive(root)
            # No Java at all
            with self.assertRaisesRegex(RuntimeError, "java"):
                runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)

    def test_duplicate_java_sources_raises(self):
        """Both archive and extracted Java present raises RuntimeError (ambiguous)."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle_root = self._make_bundle_root(root)
            self._make_mysql_archive(root)
            deb_path, deb_sha = self._make_libaio_deb(root)
            self._update_lock_libaio_sha(bundle_root, deb_sha)
            self._make_java_archive(root)
            self._make_extracted_java(root)  # duplicate
            self._make_k6_archive(root)
            with self.assertRaisesRegex(RuntimeError, "java"):
                runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)

    def test_wrong_java_version_raises(self):
        """Java executable reporting wrong version is rejected."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle_root = self._make_bundle_root(root)
            self._make_mysql_archive(root)
            deb_path, deb_sha = self._make_libaio_deb(root)
            self._update_lock_libaio_sha(bundle_root, deb_sha)
            self._make_java_archive(root)
            self._make_k6_archive(root)
            wrong_runner = lambda comp, exe, args: "openjdk version \"21.0.12.1\"" if comp == "java" else self.K6_VERSION_STRING
            with self.assertRaisesRegex(RuntimeError, "version mismatch|21.0.13"):
                runtime.prepare_kaggle_input(root, working, version_runner=wrong_runner)

    def test_libaio_package_checksum_mismatch_raises(self):
        """libaio .deb with wrong SHA-256 is rejected."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle_root = self._make_bundle_root(root)
            self._make_mysql_archive(root)
            deb_path, _ = self._make_libaio_deb(root)
            # Do NOT update the lock sha — intentional mismatch
            self._make_java_archive(root)
            self._make_k6_archive(root)
            with self.assertRaisesRegex(RuntimeError, "libaio package checksum mismatch"):
                runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)

    def test_missing_bundle_manifest_raises(self):
        """No bundle-manifest.json raises RuntimeError."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            with self.assertRaisesRegex(RuntimeError, "bundle-manifest.json"):
                runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)

    def test_prepare_is_idempotent(self):
        """Calling prepare_kaggle_input twice with same inputs returns same directory."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle_root = self._make_bundle_root(root)
            self._make_mysql_archive(root)
            deb_path, deb_sha = self._make_libaio_deb(root)
            self._update_lock_libaio_sha(bundle_root, deb_sha)
            self._make_extracted_java(root)
            self._make_extracted_k6(root)
            first = runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)
            second = runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)
            self.assertEqual(first, second)

    def test_kaggle_session_preserves_prepared_input_root(self):
        """KaggleSession(input_root=prepared) must not reset to /kaggle/input."""
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="root-check")
            self.assertEqual(session.input_root, pathlib.Path(temp).resolve())

    def test_session_input_root_matches_prepare_output(self):
        """session.input_root must equal the resolved prepared path from prepare_kaggle_input."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle_root = self._make_bundle_root(root)
            self._make_mysql_archive(root)
            deb_path, deb_sha = self._make_libaio_deb(root)
            self._update_lock_libaio_sha(bundle_root, deb_sha)
            self._make_extracted_java(root)
            self._make_extracted_k6(root)
            prepared = runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)
            session = runtime.KaggleSession(input_root=prepared, working_root=temp, run_id="root-match")
            self.assertEqual(session.input_root, prepared.resolve())

    def test_bundle_baseline_sha_mismatch_raises(self):
        """bundle-manifest.json with wrong protocol_baseline_sha is rejected."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle = root / "bundle"
            bundle.mkdir()
            bad_manifest = {"schema_version": 1, "protocol_baseline_sha": "wrong" * 8, "files": []}
            (bundle / "bundle-manifest.json").write_text(json.dumps(bad_manifest), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "baseline"):
                runtime.prepare_kaggle_input(root, working)

    def test_missing_mysql_archive_raises(self):
        """No MySQL archive raises RuntimeError."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle_root = self._make_bundle_root(root)
            deb_path, deb_sha = self._make_libaio_deb(root)
            self._update_lock_libaio_sha(bundle_root, deb_sha)
            self._make_extracted_java(root)
            self._make_extracted_k6(root)
            with self.assertRaisesRegex(RuntimeError, "MySQL"):
                runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)

    def test_missing_libaio_deb_raises(self):
        """No libaio .deb raises RuntimeError."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle_root = self._make_bundle_root(root)
            self._make_mysql_archive(root)
            self._make_extracted_java(root)
            self._make_extracted_k6(root)
            # No libaio deb
            with self.assertRaisesRegex(RuntimeError, "libaio"):
                runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)

    def test_bootstrap_does_not_modify_kaggle_input_root(self):
        """prepare_kaggle_input must not write into the source input root."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            bundle_root = self._make_bundle_root(root)
            self._make_mysql_archive(root)
            deb_path, deb_sha = self._make_libaio_deb(root)
            self._update_lock_libaio_sha(bundle_root, deb_sha)
            self._make_extracted_java(root)
            self._make_extracted_k6(root)
            before = {str(p): p.stat().st_mtime for p in root.rglob("*") if p.is_file()}
            runtime.prepare_kaggle_input(root, working, version_runner=self._fake_version_runner)
            after = {str(p): p.stat().st_mtime for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after, "prepare_kaggle_input must not modify the source input root")

    def test_preflight_fail_does_not_start_mysql(self):
        """run_smoke fails at preflight (before MySQL) when probe.is_kaggle is False."""
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="preflight-block")
            session.probe()
            # probe leaves is_kaggle=False on non-Kaggle host; run_smoke must FAIL before MySQL
            with mock.patch.object(session, "start_mysql") as mock_mysql:
                result = session.run_smoke()
            self.assertEqual(result["status"], "FAIL")
            mock_mysql.assert_not_called()

    def test_prepare_kaggle_input_cleans_up_on_error(self):
        """If prepare fails mid-way, no partial .tmp- directory is left in working root."""
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "input"
            root.mkdir()
            working = pathlib.Path(temp) / "working"
            working.mkdir()
            bundle_root = self._make_bundle_root(root)
            self._make_mysql_archive(root)
            deb_path, deb_sha = self._make_libaio_deb(root)
            self._update_lock_libaio_sha(bundle_root, deb_sha)
            self._make_java_archive(root)
            self._make_k6_archive(root)
            # version_runner raises to trigger cleanup
            def boom(component, executable, args):
                raise RuntimeError("simulated version check failure")
            with self.assertRaises(RuntimeError):
                runtime.prepare_kaggle_input(root, working, version_runner=boom)
            leftovers = [p for p in working.iterdir() if p.name.startswith(".")]
            self.assertEqual(leftovers, [], f"temp directories not cleaned up: {leftovers}")

    def test_no_stale_staging_from_previous_session(self):
        """prepare_kaggle_input fingerprints inputs; different inputs produce a different dir."""
        with tempfile.TemporaryDirectory() as temp:
            root_a = pathlib.Path(temp) / "input-a"
            root_a.mkdir()
            root_b = pathlib.Path(temp) / "input-b"
            root_b.mkdir()
            working = pathlib.Path(temp) / "working"
            for root in (root_a, root_b):
                bundle_root = self._make_bundle_root(root)
                self._make_mysql_archive(root)
                deb_path, deb_sha = self._make_libaio_deb(root)
                self._update_lock_libaio_sha(bundle_root, deb_sha)
                self._make_extracted_java(root)
                self._make_extracted_k6(root)
            # Modify k6 in root_b to create a different fingerprint
            k6_bin = list(root_b.rglob("k6"))[0]
            k6_bin.write_bytes(b"different-k6-binary")
            first = runtime.prepare_kaggle_input(root_a, working, version_runner=self._fake_version_runner)
            second = runtime.prepare_kaggle_input(root_b, working, version_runner=self._fake_version_runner)
            self.assertNotEqual(first, second, "Different inputs must produce different prepared directories")


if __name__ == "__main__":
    unittest.main()
