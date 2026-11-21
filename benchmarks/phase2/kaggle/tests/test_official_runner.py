from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[4]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


runtime = load("g25_runtime", "benchmarks/phase2/kaggle/kaggle_runtime.py")
comparator = load("g25_compare", "benchmarks/phase2/kaggle/compare_manifests.py")


def metric(values: dict) -> dict:
    return {"type": "counter", "contains": "default", "values": values}


def official_summary(workload: str, errors: bool = False) -> dict:
    error_metric = "write_error_rate" if workload == "W2" else "application_error_rate"
    return {"state": {"testRunDurationMs": 180_100}, "metrics": {
        "http_reqs": metric({"count": 100, "rate": 1}),
        "iterations": metric({"count": 25, "rate": 1}),
        "checks": metric({"passes": 99 if errors else 100, "fails": 1 if errors else 0, "rate": .99}),
        "http_req_failed": metric({"rate": .01 if errors else 0}),
        error_metric: metric({"rate": .01 if errors else 0}),
    }}


def full_manifest() -> dict:
    return {
        "source": {"protocol_baseline_sha": runtime.BASELINE_SHA, "repository_sha": "b" * 40,
                   "application_sha": runtime.BASELINE_SHA, "application_jar_sha256": "c" * 64},
        "hardware": {"cpu_model": "CPU", "logical_cores": 4, "memory_total_bytes": 32000,
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
                      "libaio_package_sha256": "h", "libaio_library_sha256": "i",
                      "libaio_library_soname": "libaio.so.1t64",
                      "libaio_compatibility_soname": "libaio.so.1"},
        "locks": {"configuration_sha256": "j", "workload_source_sha256": "k", "dataset_sha256": "l"},
    }


class OfficialSummaryTests(unittest.TestCase):
    def test_http_failures_are_retained_as_baseline_outcome(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "summary.json"
            path.write_text(json.dumps(official_summary("W1", errors=True)), encoding="utf-8")
            result = runtime.validate_k6_official_summary(path, "W1", 180, {"rates": [10, 5, 5]})
            self.assertTrue(result["harness_valid"])
            self.assertEqual(result["outcome"], "HTTP_OR_PERFORMANCE_FAILURE")

    def test_structurally_empty_or_interrupted_measurement_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "summary.json"
            document = official_summary("W2")
            document["metrics"]["http_reqs"]["values"]["count"] = 0
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "no requests"):
                runtime.validate_k6_official_summary(path, "W2", 180, {"vus": 10})
            document = official_summary("W2")
            document["state"]["testRunDurationMs"] = 10_000
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "duration"):
                runtime.validate_k6_official_summary(path, "W2", 180, {"vus": 10})


class OfficialOrchestrationTests(unittest.TestCase):
    def config(self) -> dict:
        return {"runtime": {"backend_port": 18083}, "workloads": {
            "warmup_seconds": 60, "warmup_food_list_rps": 2, "warmup_food_search_rps": 1,
            "warmup_order_list_rps": 1, "measurement_seconds": 180, "w1_food_list_rps": 10,
            "w1_food_search_rps": 5, "w1_order_list_rps": 5, "w1_order_page_size": 20,
            "w2_vus": 10, "w3_rounds": 15, "cooldown_seconds": 30},
            "official_validation": {"minimum_resource_samples_per_label": 2,
                                    "k6_duration_tolerance_seconds": 60}}

    def test_phase_order_standard_parameters_resets_and_warmup_separation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="official-order")
            session.evidence.mkdir(parents=True)
            session.runtime.mkdir(parents=True)
            session.config = self.config()
            benchmark = root / "benchmarks/phase2"
            (benchmark / "workloads").mkdir(parents=True)
            calls = []

            def dataset(phase, mode, output, expected_sha=None):
                calls.append(phase)
                return {"overall_sha256": "fixture-sha", "consistency_outcome": "CONSISTENT"}

            def k6(phase, workload, script, duration, environment, expected_load):
                calls.append(phase)
                return {"outcome": "COMPLETED_WITHOUT_OBSERVED_ERRORS", "environment": environment,
                        "duration": duration, "load": expected_load}

            with mock.patch.object(session, "_benchmark_root", return_value=benchmark), \
                    mock.patch.object(session, "_official_dataset", side_effect=dataset), \
                    mock.patch.object(session, "_preflight_official_w3",
                                      side_effect=lambda *_: calls.append("w3_preflight")), \
                    mock.patch.object(session, "_official_k6", side_effect=k6) as run_k6, \
                    mock.patch.object(session, "_db_telemetry"), \
                    mock.patch.object(session, "_official_w3", side_effect=lambda *_: calls.append("w3") or {
                        "violation_rounds": {}, "server_error_rounds": {}}), \
                    mock.patch.object(session, "_official_cooldown", side_effect=lambda *_: calls.append("cooldown")):
                result = session.run_official_workloads()

            self.assertEqual(calls, ["prepare_standard", "w3_preflight", "warmup", "w1", "post_w1", "reset_after_w1",
                                     "w2", "post_w2", "reset_after_w2", "w3", "post_w3", "cooldown",
                                     "final_reset"])
            warmup, w1, w2 = run_k6.call_args_list
            self.assertEqual(warmup.args[3], 60)
            self.assertEqual([warmup.args[4][key] for key in
                              ("FOOD_LIST_RPS", "FOOD_SEARCH_RPS", "ORDER_LIST_RPS")], ["2", "1", "1"])
            self.assertEqual(w1.args[3], 180)
            self.assertEqual([w1.args[4][key] for key in
                              ("FOOD_LIST_RPS", "FOOD_SEARCH_RPS", "ORDER_LIST_RPS")], ["10", "5", "5"])
            self.assertEqual(w2.args[4]["WRITE_VUS"], "10")
            self.assertEqual(result["reset_sha256"], ["fixture-sha"] * 3)
            self.assertIn("warmup", result)
            self.assertNotEqual(result["warmup"], result["w1"])


class OfficialOrchestrationAndW3GuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w3 = load("g25_w3_guard", "benchmarks/phase2/workloads/w3_contention.py")

    def config(self) -> dict:
        return OfficialOrchestrationTests.config(self)

    def session_with_real_bundle_layout(self, temp: str) -> tuple:
        root = pathlib.Path(temp)
        bundle = root / "staged-input/dataset-g25/benchmark-kit"
        benchmark = bundle / "benchmarks/phase2"
        workloads = benchmark / "workloads"
        workloads.mkdir(parents=True)
        shutil.copy2(ROOT / "benchmarks/phase2/workloads/w3_contention.py",
                     workloads / "w3_contention.py")
        for name in ("w1_read.js", "w2_write.js"):
            (workloads / name).write_text("// fixture\n", encoding="utf-8")
        (benchmark / "profiles.json").write_text("{}\n", encoding="utf-8")
        (benchmark / "prepare_dataset.py").write_text("# fixture\n", encoding="utf-8")
        (bundle / "schema.sql").write_text("-- fixture\n", encoding="utf-8")
        session = runtime.KaggleSession(input_root=str(root / "staged-input"),
                                        working_root=str(root / "working"), run_id="w3-layout")
        session.evidence.mkdir(parents=True)
        session.runtime.mkdir(parents=True)
        session.bundle_root = bundle
        session.db_password = "fixture-password"
        session.tools["mysql"] = pathlib.Path("/portable/mysql")
        session.config = {
            "runtime": {"mysql_host": "127.0.0.1", "mysql_port": 3307, "backend_port": 18083,
                        "database_user": "bench", "database": "byteme"},
            "workloads": {"w3_rounds": 15},
        }
        actors = session.runtime / "actors.json"
        actors.write_text("{}\n", encoding="utf-8")
        return session, actors, root

    def test_established_smoke_and_official_projects_are_accepted(self):
        self.assertEqual(self.w3.require_benchmark_project(runtime.SMOKE_PROJECT), runtime.SMOKE_PROJECT)
        self.assertEqual(self.w3.require_benchmark_project(runtime.OFFICIAL_PROJECT), runtime.OFFICIAL_PROJECT)

    def test_non_benchmark_and_missing_projects_remain_rejected(self):
        for project in (None, "", "byteme-g25-kaggle", "production"):
            with self.subTest(project=project), self.assertRaisesRegex(SystemExit, "Refusing non-benchmark project"):
                self.w3.require_benchmark_project(project)

    def test_dataset_and_w3_commands_use_profile_specific_project_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            session, actors, _ = self.session_with_real_bundle_layout(temp)
            smoke = session._dataset_command("prepare", "smoke", session.evidence / "smoke.json")
            standard = session._dataset_command("prepare", "standard", session.evidence / "standard.json")
            smoke_w3 = session._w3_command(runtime.SMOKE_PROJECT, actors, "http://127.0.0.1:18083",
                                           2, session.evidence / "smoke-w3/result.json")
            official = session._w3_command(runtime.OFFICIAL_PROJECT, actors, "http://127.0.0.1:18083",
                                           15, session.evidence / "w3/result.json")
            self.assertEqual(smoke[smoke.index("--project") + 1], runtime.SMOKE_PROJECT)
            self.assertEqual(standard[standard.index("--project") + 1], runtime.OFFICIAL_PROJECT)
            self.assertEqual(smoke_w3[smoke_w3.index("--project") + 1], runtime.SMOKE_PROJECT)
            self.assertEqual(smoke_w3[smoke_w3.index("--rounds") + 1], "2")
            self.assertEqual(official[official.index("--project") + 1], runtime.OFFICIAL_PROJECT)
            self.assertEqual(official[official.index("--mysql-password-env") + 1], "BENCH_DB_PASSWORD")

    def test_real_bundle_layout_preflight_is_independent_of_kaggle_working_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            session, actors, root = self.session_with_real_bundle_layout(temp)
            kaggle_working = root / "kaggle/working"
            kaggle_working.mkdir(parents=True)
            previous = pathlib.Path.cwd()
            try:
                os.chdir(kaggle_working)
                session._preflight_benchmark_files()
                session._preflight_w3_project_guards()
                result = session._preflight_official_w3(actors, "http://127.0.0.1:18083")
            finally:
                os.chdir(previous)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["project"], runtime.OFFICIAL_PROJECT)
            self.assertEqual(result["checked_before"], "warmup")
            self.assertTrue((session.evidence / "environment/w3-project-guard-preflight.json").is_file())
            self.assertTrue((session.evidence / "official/w3-preflight.json").is_file())

    def test_official_preflight_fails_closed_for_missing_actor_or_password(self):
        with tempfile.TemporaryDirectory() as temp:
            session, actors, _ = self.session_with_real_bundle_layout(temp)
            actors.unlink()
            with self.assertRaisesRegex(RuntimeError, "actors fixture missing before warm-up"):
                session._preflight_official_w3(actors, "http://127.0.0.1:18083")
            actors.write_text("{}\n", encoding="utf-8")
            session.db_password = ""
            with self.assertRaisesRegex(RuntimeError, "password environment source is absent"):
                session._preflight_official_w3(actors, "http://127.0.0.1:18083")

    def test_bundled_source_without_guard_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            session, _, _ = self.session_with_real_bundle_layout(temp)
            (session._benchmark_root() / "workloads/w3_contention.py").write_text(
                "VALUE = 'missing guard'\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "guard is absent"):
                session._preflight_w3_project_guards()

    def test_post_workload_business_invariant_is_recorded_without_harness_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="business-defect")
            session.evidence.mkdir(parents=True)
            session.runtime.mkdir(parents=True)
            session.config = self.config()

            def write_snapshot(*_args, **_kwargs):
                output = session.evidence / "dataset/post-w3.json"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps({"profile": "standard", "validation_phase": "post_workload",
                                              "all_invariants_pass": False, "overall_sha256": "mutated"}),
                                  encoding="utf-8")

            with mock.patch.object(session, "_dataset_command", return_value=["python"]), \
                    mock.patch.object(session, "_run", side_effect=write_snapshot) as command:
                result = session._official_dataset("post_w3", "snapshot", "dataset/post-w3.json")
            self.assertEqual(result["consistency_outcome"], "BUSINESS_INVARIANT_VIOLATION")
            self.assertEqual(command.call_args.kwargs["allowed_exit_codes"], {0, 2})

    def test_full_official_evidence_protocol_is_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="protocol")
            session.evidence.mkdir(parents=True)
            session.runtime.mkdir(parents=True)
            session.config = self.config()
            benchmark = root / "benchmark"
            benchmark.mkdir()
            standard = {"categories": 10, "read_foods": 5000, "read_orders": 500,
                        "items_per_order": 2, "write_actors": 20, "contention_actors": 4,
                        "write_stock": 1000000, "shared_stock": 10}
            (benchmark / "profiles.json").write_text(json.dumps({"standard": standard}), encoding="utf-8")
            order = ["prepare_standard", "warmup", "w1", "post_w1", "reset_after_w1", "w2",
                     "post_w2", "reset_after_w2", "w3", "post_w3", "cooldown", "final_reset"]
            plan = {"profile": "standard", "phase_order": order,
                    "warmup": {"duration_seconds": 60, "food_list_rps": 2,
                               "food_search_rps": 1, "order_list_rps": 1},
                    "w1": {"duration_seconds": 180, "food_list_rps": 10,
                           "food_search_rps": 5, "order_list_rps": 5, "order_page_size": 20},
                    "w2": {"duration_seconds": 180, "vus": 10},
                    "w3": {"rounds_per_scenario": 15}, "cooldown_seconds": 30}
            required = [
                "official/execution-plan.json", "official/phase-events.json", "official/w3-preflight.json",
                "environment/w3-project-guard-preflight.json", "dataset/initial.json",
                "dataset/post-w1.json", "dataset/after-reset-w1.json", "dataset/post-w2.json",
                "dataset/after-reset-w2.json", "dataset/post-w3.json", "dataset/after-final-reset.json",
                "warmup/raw.json", "warmup/summary.json", "warmup/validation.json", "warmup/resources.tsv",
                "w1/raw.json", "w1/summary.json", "w1/validation.json", "w1/resources.tsv",
                "w2/raw.json", "w2/summary.json", "w2/validation.json", "w2/resources.tsv",
                "w3/result.json", "w3/validation.json", "w3/resources.tsv", "database/before-w1.txt",
                "database/after-w1.txt", "database/before-w2.txt", "database/after-w2.txt",
                "database/before-w3.txt", "database/after-w3.txt"]
            for relative in required:
                path = session.evidence / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            (session.evidence / "official/execution-plan.json").write_text(json.dumps(plan), encoding="utf-8")
            (session.evidence / "official/w3-preflight.json").write_text(json.dumps({
                "status": "PASS", "project": runtime.OFFICIAL_PROJECT, "checked_before": "warmup"
            }), encoding="utf-8")
            (session.evidence / "official/phase-events.json").write_text(json.dumps([
                {"phase": phase, "state": "completed"} for phase in order]), encoding="utf-8")
            initial_auth = {"token_strategy": "initial_login", "actor_count": 26,
                            "login_requests": 26, "reused_tokens": 0, "live_token_validations": 0}
            reuse_auth = {"token_strategy": "reuse_initial_tokens", "actor_count": 26,
                          "login_requests": 0, "reused_tokens": 26, "live_token_validations": 26}
            (session.evidence / "dataset/initial.json").write_text(json.dumps({
                "profile": "standard", "profile_parameters": standard,
                "preparation_authentication": initial_auth}), encoding="utf-8")
            for relative in ("dataset/after-reset-w1.json", "dataset/after-reset-w2.json",
                             "dataset/after-final-reset.json"):
                (session.evidence / relative).write_text(json.dumps({
                    "preparation_authentication": reuse_auth}), encoding="utf-8")
            execution = {"plan": plan, "initial_sha256": "sha", "reset_sha256": ["sha"] * 3,
                         "w1": {"outcome": "HTTP_OR_PERFORMANCE_FAILURE"},
                         "w2": {"outcome": "COMPLETED_WITHOUT_OBSERVED_ERRORS"},
                         "w3": {"violation_rounds": {"scenario": [1]}},
                         "consistency_outcomes": {"post_w1": "CONSISTENT", "post_w2": "CONSISTENT",
                                                  "post_w3": "BUSINESS_INVARIANT_VIOLATION"}}
            with mock.patch.object(session, "_benchmark_root", return_value=benchmark):
                validation = session.validate_official_execution(execution)
            self.assertTrue(validation["harness_valid"])
            self.assertTrue(validation["warmup_excluded_from_official_metrics"])
            self.assertEqual(validation["dataset_authentication"]["final_reset"], reuse_auth)
            mismatched = {**execution, "reset_sha256": ["sha", "different", "sha"]}
            with mock.patch.object(session, "_benchmark_root", return_value=benchmark):
                with self.assertRaisesRegex(RuntimeError, "resets do not all match"):
                    session.validate_official_execution(mismatched)
            (session.evidence / "w2/raw.json").unlink()
            with mock.patch.object(session, "_benchmark_root", return_value=benchmark):
                with self.assertRaisesRegex(RuntimeError, "missing or empty"):
                    session.validate_official_execution(execution)

    def test_application_defects_do_not_fail_official_but_harness_exception_does(self):
        execution = {"initial_sha256": "sha", "reset_sha256": ["sha"] * 3,
                     "w1": {"outcome": "HTTP_OR_PERFORMANCE_FAILURE"},
                     "w2": {"outcome": "COMPLETED_WITHOUT_OBSERVED_ERRORS"},
                     "w3": {"violation_rounds": {"scenario": [1]}, "server_error_rounds": {}},
                     "consistency_outcomes": {"post_w1": "CONSISTENT", "post_w2": "CONSISTENT",
                                              "post_w3": "BUSINESS_INVARIANT_VIOLATION"}, "plan": {}}
        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="application-outcome")
            session.evidence.mkdir(parents=True)
            session.runtime.mkdir(parents=True)
            (session.evidence / "environment").mkdir()
            (session.evidence / "environment/hardware-runtime.json").write_text(
                json.dumps({"is_kaggle": True}), encoding="utf-8")
            session.application_sha = runtime.BASELINE_SHA
            with mock.patch.object(session, "resolve_bundle"), mock.patch.object(session, "setup_toolchain"), \
                    mock.patch.object(session, "start_mysql"), mock.patch.object(session, "start_backend"), \
                    mock.patch.object(session, "run_official_workloads", return_value=execution), \
                    mock.patch.object(session, "validate_official_execution", return_value={"harness_valid": True}), \
                    mock.patch.object(session, "cleanup", return_value={"success": True}), \
                    mock.patch.object(session, "write_run_manifest"), \
                    mock.patch.object(session, "scan_evidence_secrets", return_value=[]):
                result = session.run_official()
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["official_benchmark"])
            self.assertEqual(result["application_outcome"]["w1"], "HTTP_OR_PERFORMANCE_FAILURE")

        with tempfile.TemporaryDirectory() as temp:
            session = runtime.KaggleSession(input_root=temp, working_root=temp, run_id="interrupted")
            session.evidence.mkdir(parents=True)
            session.runtime.mkdir(parents=True)
            (session.evidence / "environment").mkdir()
            (session.evidence / "environment/hardware-runtime.json").write_text(
                json.dumps({"is_kaggle": True}), encoding="utf-8")
            session.application_sha = runtime.BASELINE_SHA
            cleanup = mock.Mock(return_value={"success": True})
            with mock.patch.object(session, "resolve_bundle"), mock.patch.object(session, "setup_toolchain"), \
                    mock.patch.object(session, "start_mysql"), mock.patch.object(session, "start_backend"), \
                    mock.patch.object(session, "run_official_workloads", side_effect=RuntimeError("interrupted")), \
                    mock.patch.object(session, "cleanup", cleanup), mock.patch.object(session, "write_run_manifest"), \
                    mock.patch.object(session, "scan_evidence_secrets", return_value=[]):
                result = session.run_official()
            self.assertEqual(result["status"], "FAIL")
            self.assertFalse(result["official_benchmark"])
            cleanup.assert_called_once()
            self.assertTrue((session.evidence / "logs/official-failure-traceback.txt").is_file())


class NotebookAndComparatorTests(unittest.TestCase):
    def test_official_notebook_bootstrap_and_single_run_order(self):
        notebook = json.loads((ROOT / "kaggle/script/byteme_phase2_g25_official.ipynb").read_text(encoding="utf-8"))
        code = ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"]
        joined = "\n".join(code)
        self.assertEqual(joined.count("session.run_official("), 1)
        self.assertLess(joined.index("prepare_kaggle_input("), joined.index("KaggleSession("))
        self.assertLess(joined.index("KaggleSession("), joined.index("session.probe()"))
        self.assertLess(joined.index("session.probe()"), joined.index("session.run_official("))
        self.assertNotIn("session.run_smoke()", joined)

    def test_comparator_cli_returns_zero_and_two_without_name_error(self):
        with tempfile.TemporaryDirectory() as temp:
            first, second = pathlib.Path(temp) / "first.json", pathlib.Path(temp) / "second.json"
            first.write_text(json.dumps(full_manifest()), encoding="utf-8")
            second.write_text(json.dumps(full_manifest()), encoding="utf-8")
            with mock.patch.object(sys, "argv", ["compare", str(first), str(second)]), redirect_stdout(io.StringIO()):
                self.assertEqual(comparator.main(), 0)
            changed = full_manifest()
            changed["hardware"]["cpu_model"] = "different"
            second.write_text(json.dumps(changed), encoding="utf-8")
            with mock.patch.object(sys, "argv", ["compare", str(first), str(second)]), redirect_stdout(io.StringIO()):
                self.assertEqual(comparator.main(), 2)


if __name__ == "__main__":
    unittest.main()
