from __future__ import annotations

import copy
import importlib.util
import pathlib
import tempfile
import unittest
import zipfile
import json


ROOT = pathlib.Path(__file__).resolve().parents[4]


def load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


aggregate = load("phase2_aggregate", "benchmarks/phase2/tools/aggregate_runs.py")
comparator = load("phase2_compare", "benchmarks/phase2/kaggle/compare_manifests.py")


def manifest(cpu="Intel(R) Xeon(R) CPU @ 2.20GHz", configuration="config"):
    return {
        "source": {"protocol_baseline_sha": "a", "repository_sha": "b",
                   "application_sha": "c", "application_jar_sha256": "d"},
        "hardware": {
            "cpu_model": cpu, "logical_cores": 4, "memory_total_bytes": 33_658_155_008,
            "os_id": "ubuntu", "os_version": "24.04", "kernel": "6.18.55+",
            "runtime_image_identity": "image",
            "cgroup": {"version": "v2", "cpu_quota_raw": "400000 100000",
                       "cpu_period_us": 100000, "cpuset_effective": "0-3",
                       "cpuset_cpu_count": 4, "memory_limit_raw": "32212254720",
                       "resolved_cpu_limit": 4.0, "resolved_memory_limit_bytes": 32212254720,
                       "quota_evidence_complete": True},
        },
        "toolchain": {"java_version": "java", "mysql_version": "/run/a/mysqld Ver mysql",
                      "k6_version": "k6", "java_executable_sha256": "java-sha",
                      "mysqld_executable_sha256": "mysql-sha", "k6_executable_sha256": "k6-sha",
                      "libaio_package_version": "libaio", "libaio_package_sha256": "package-sha",
                      "libaio_library_sha256": "library-sha", "libaio_library_soname": "libaio.so.1t64",
                      "libaio_compatibility_soname": "libaio.so.1"},
        "locks": {"configuration_sha256": configuration, "workload_source_sha256": "workload",
                  "dataset_sha256": "dataset"},
    }


def records(count=3):
    return [{"run_id": f"run-{index}", "manifest": copy.deepcopy(manifest())}
            for index in range(1, count + 1)]


class AggregationPolicyTests(unittest.TestCase):
    def test_accepts_three_comparable_runs(self):
        result = aggregate.validate_group(records(), 3, comparator)
        self.assertTrue(result["comparable"])
        self.assertEqual(result["mismatches"], [])

    def test_rejects_mixed_cpu(self):
        selected = records()
        selected[2]["manifest"]["hardware"]["cpu_model"] = "AMD EPYC 7B12"
        with self.assertRaisesRegex(aggregate.AggregationError, "hardware.cpu_model"):
            aggregate.validate_group(selected, 3, comparator)

    def test_rejects_insufficient_runs(self):
        with self.assertRaisesRegex(aggregate.AggregationError, "insufficient runs"):
            aggregate.validate_group(records(2), 3, comparator)

    def test_rejects_manifest_lock_mismatch(self):
        selected = records()
        selected[1]["manifest"]["locks"]["configuration_sha256"] = "different"
        with self.assertRaisesRegex(aggregate.AggregationError, "locks.configuration_sha256"):
            aggregate.validate_group(selected, 3, comparator)

    def test_memtotal_policy_is_applied_by_comparator(self):
        selected = records()
        selected[1]["manifest"]["hardware"]["memory_total_bytes"] += 4096
        self.assertTrue(aggregate.validate_group(selected, 3, comparator)["comparable"])

    def test_rejects_memtotal_outside_tolerance(self):
        selected = records()
        selected[1]["manifest"]["hardware"]["memory_total_bytes"] += 1024 * 1024 + 1
        with self.assertRaisesRegex(aggregate.AggregationError, "hardware.memory_total_bytes"):
            aggregate.validate_group(selected, 3, comparator)

    def test_group_requires_pairwise_memtotal_comparability(self):
        selected = records()
        base = selected[0]["manifest"]["hardware"]["memory_total_bytes"]
        selected[1]["manifest"]["hardware"]["memory_total_bytes"] = base + 800_000
        selected[2]["manifest"]["hardware"]["memory_total_bytes"] = base + 1_600_000
        with self.assertRaisesRegex(aggregate.AggregationError, "hardware.memory_total_bytes"):
            aggregate.validate_group(selected, 3, comparator)

    def test_rejects_duplicate_run_ids(self):
        selected = records()
        selected[1]["run_id"] = selected[0]["run_id"]
        with self.assertRaisesRegex(aggregate.AggregationError, "duplicate run IDs"):
            aggregate.validate_group(selected, 3, comparator)

    def test_missing_telemetry_is_not_zero(self):
        result = aggregate.summarize([10.0, None, 20.0])
        self.assertEqual(result["available_runs"], 2)
        self.assertEqual(result["missing_runs"], 1)
        self.assertEqual(result["median"], 15.0)

    def test_percentile_interpolates_within_one_run(self):
        self.assertEqual(aggregate.percentile([1.0, 2.0, 3.0, 4.0], .50), 2.5)
        self.assertAlmostEqual(aggregate.percentile([1.0, 2.0, 3.0, 4.0], .95), 3.85)

    def test_operation_metrics_uses_per_operation_points_and_statuses(self):
        lines = [
            {"type": "Point", "metric": "http_req_duration", "data": {"value": value,
             "tags": {"operation": "food_list"}}}
            for value in (10, 20, 30, 40)
        ]
        lines += [
            {"type": "Point", "metric": "http_reqs", "data": {"value": 1,
             "tags": {"operation": "food_list", "status": status}}}
            for status in (200, 200, 500, 409)
        ]
        for operation in ("food_search", "order_list"):
            lines.extend([
                {"type": "Point", "metric": "http_req_duration", "data": {"value": 5,
                 "tags": {"operation": operation}}},
                {"type": "Point", "metric": "http_reqs", "data": {"value": 1,
                 "tags": {"operation": operation, "status": 200}}},
            ])
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "raw.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("w1/raw.json", "\n".join(json.dumps(line) for line in lines))
            with zipfile.ZipFile(path) as archive:
                result = aggregate.operation_metrics(archive, "w1", 2000)
        food = result["food_list"]
        self.assertEqual(food["requests"], 4)
        self.assertEqual(food["request_rate_rps"], 2)
        self.assertEqual(food["latency_p50_ms"], 25)
        self.assertEqual(food["errors"], 2)
        self.assertEqual(food["business_rejections"], 1)
        self.assertEqual(food["server_errors"], 1)

    def test_official_gate_rejects_incomplete_dataset_reset_evidence(self):
        protocol = {
            "harness_valid": True, "profile": "standard",
            "phase_order": aggregate.EXPECTED_PHASE_ORDER,
            "initial_dataset_sha256": "a" * 64,
            "reset_dataset_sha256": ["a" * 64, "a" * 64],
            "warmup_excluded_from_official_metrics": True,
            "consistency_outcomes": {"post_w1": "CONSISTENT", "post_w2": "CONSISTENT",
                                     "post_w3": "CONSISTENT"},
        }
        result = {"status": "PASS", "official_benchmark": True,
                  "requested_official_benchmark": True, "profile": "standard",
                  "classification": "VALID_BASELINE_MEASUREMENT", "error": None,
                  "cleanup": {"success": True}, "secret_scan_violations": [],
                  "reset_matches_initial": True}
        with self.assertRaisesRegex(aggregate.AggregationError, "reset checksums"):
            aggregate.validate_official(result, protocol)

    def test_rejects_evidence_checksum_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "bad-checksum.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("payload.json", "{}")
                archive.writestr("SHA256SUMS.txt", f"{'0' * 64}  payload.json\n")
            with zipfile.ZipFile(path) as archive:
                with self.assertRaisesRegex(aggregate.AggregationError, "checksum mismatch"):
                    aggregate.verify_archive(archive)

    def test_mysql_digest_delta_preserves_missing_as_unavailable(self):
        header = ("DIGEST\tDIGEST_TEXT\tCOUNT_STAR\tTIMER_MS\tROWS_AFFECTED\tROWS_SENT\t"
                  "ROWS_EXAMINED\tTMP_DISK\tNO_INDEX\n")
        before = header + "abc\tSELECT 1\t2\t4.0\t0\t2\t2\t0\t0\n"
        after = header + "abc\tSELECT 1\t5\t9.5\t1\t8\t12\t0\t0\n"
        after += "def\tSELECT 2\t1\t1.0\t0\t0\t0\t0\t0\n"
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "mysql.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("database/before-w1.txt", before)
                archive.writestr("database/after-w1.txt", after)
            with zipfile.ZipFile(path) as archive:
                result = aggregate.parse_mysql_digest_deltas(archive, "w1")
        self.assertEqual(result["abc"]["delta"]["count_star"], 3)
        self.assertEqual(result["abc"]["delta"]["sum_timer_wait_ms"], 5.5)
        self.assertIsNone(result["def"]["delta"]["count_star"])


if __name__ == "__main__":
    unittest.main()
