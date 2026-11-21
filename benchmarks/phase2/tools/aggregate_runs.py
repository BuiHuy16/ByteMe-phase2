#!/usr/bin/env python3
"""Build a locked multi-run baseline directly from official evidence ZIPs.

Each run remains an independent statistical unit. Request samples are used only
to calculate per-run, per-operation values; percentiles are never pooled across
runs. Missing telemetry is reported as unavailable rather than converted to 0.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import itertools
import io
import json
import math
import pathlib
import re
import statistics
import zipfile
from collections import defaultdict


ROOT = pathlib.Path(__file__).resolve().parents[3]
COMPARATOR_PATH = ROOT / "benchmarks/phase2/kaggle/compare_manifests.py"
EXPECTED_STATUS = {
    "w1": {"food_list": 200, "food_search": 200, "order_list": 200},
    "w2": {"cart_add": 200, "cart_update": 200, "checkout": 201, "cancel": 200},
}
EXPECTED_W3_SCENARIOS = {
    "same_food_checkout", "same_cart_checkout", "admin_stock_vs_checkout",
}
EXPECTED_PHASE_ORDER = [
    "prepare_standard", "warmup", "w1", "post_w1", "reset_after_w1", "w2",
    "post_w2", "reset_after_w2", "w3", "post_w3", "cooldown", "final_reset",
]
REQUIRED_RESOURCE_LABELS = {"backend", "mysql", "driver"}
MYSQL_STATUS_FIELDS = (
    "Com_delete", "Com_insert", "Com_select", "Com_update", "Connections",
    "Created_tmp_disk_tables", "Created_tmp_tables", "Innodb_buffer_pool_read_requests",
    "Innodb_buffer_pool_reads", "Innodb_row_lock_current_waits", "Innodb_row_lock_time",
    "Innodb_row_lock_waits", "Queries", "Questions", "Slow_queries",
    "Threads_connected", "Threads_running",
)
MYSQL_DIGEST_FIELDS = (
    "count_star", "sum_timer_wait_ms", "sum_rows_affected", "sum_rows_sent",
    "sum_rows_examined", "sum_created_tmp_disk_tables", "sum_no_index_used",
)


class AggregationError(RuntimeError):
    """Evidence cannot enter this aggregation group."""


def load_comparator():
    spec = importlib.util.spec_from_file_location("byteme_compare_manifests", COMPARATOR_PATH)
    if spec is None or spec.loader is None:
        raise AggregationError(f"cannot load comparator: {COMPARATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def finite_number(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise AggregationError(f"invalid numeric value for {label}: {value!r}")
    return float(value)


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(values: list[float | int | None]) -> dict:
    available = [finite_number(value, "summary") for value in values if value is not None]
    if not available:
        return {"available_runs": 0, "missing_runs": len(values), "median": None, "mean": None,
                "min": None, "max": None, "population_stddev": None,
                "coefficient_of_variation": None}
    mean = statistics.fmean(available)
    deviation = statistics.pstdev(available) if len(available) > 1 else 0.0
    return {
        "available_runs": len(available), "missing_runs": len(values) - len(available),
        "median": statistics.median(available), "mean": mean, "min": min(available),
        "max": max(available), "population_stddev": deviation,
        "coefficient_of_variation": deviation / mean if mean else None,
    }


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_member(archive: zipfile.ZipFile, name: str) -> dict:
    try:
        return json.loads(archive.read(name))
    except KeyError as exc:
        raise AggregationError(f"missing evidence member {name}") from exc
    except json.JSONDecodeError as exc:
        raise AggregationError(f"invalid JSON in {name}: {exc}") from exc


def verify_archive(archive: zipfile.ZipFile) -> dict:
    bad_crc = archive.testzip()
    if bad_crc:
        raise AggregationError(f"ZIP CRC failure: {bad_crc}")
    names = set(archive.namelist())
    try:
        checksum_lines = archive.read("SHA256SUMS.txt").decode("utf-8-sig").splitlines()
    except KeyError as exc:
        raise AggregationError("missing SHA256SUMS.txt") from exc
    checked = set()
    for line in checksum_lines:
        match = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.*)$", line)
        if not match:
            continue
        expected, name = match.groups()
        if name not in names:
            raise AggregationError(f"checksum member missing: {name}")
        actual = hashlib.sha256(archive.read(name)).hexdigest()
        if actual.lower() != expected.lower():
            raise AggregationError(f"checksum mismatch: {name}")
        checked.add(name)
    unlisted = names - checked - {"SHA256SUMS.txt"}
    if unlisted:
        raise AggregationError(f"unlisted evidence members: {sorted(unlisted)}")
    if not checked:
        raise AggregationError("SHA256SUMS.txt has no usable entries")
    return {"zip_entries": len(names), "checksums_verified": len(checked), "crc_valid": True}


def validate_official(result: dict, protocol: dict) -> None:
    expected = {
        "status": "PASS", "official_benchmark": True, "requested_official_benchmark": True,
        "profile": "standard", "classification": "VALID_BASELINE_MEASUREMENT",
    }
    for field, value in expected.items():
        if result.get(field) != value:
            raise AggregationError(f"official gate {field}: expected {value!r}, got {result.get(field)!r}")
    if result.get("error") is not None or protocol.get("harness_valid") is not True:
        raise AggregationError("official result has an error or invalid harness")
    if result.get("cleanup", {}).get("success") is not True:
        raise AggregationError("cleanup did not succeed")
    if result.get("secret_scan_violations") != []:
        raise AggregationError("secret scan has violations")
    if result.get("reset_matches_initial") is not True:
        raise AggregationError("dataset reset does not match initial state")
    initial = protocol.get("initial_dataset_sha256")
    resets = protocol.get("reset_dataset_sha256")
    if (not isinstance(initial, str) or not re.fullmatch(r"[0-9a-f]{64}", initial)
            or not isinstance(resets, list) or len(resets) != 3 or resets != [initial] * 3):
        raise AggregationError("protocol dataset reset checksums are incomplete or inconsistent")
    if protocol.get("phase_order") != EXPECTED_PHASE_ORDER:
        raise AggregationError("protocol phase order does not match the locked protocol")
    if protocol.get("warmup_excluded_from_official_metrics") is not True:
        raise AggregationError("protocol does not confirm warmup exclusion")
    if any(value != "CONSISTENT" for value in protocol.get("consistency_outcomes", {}).values()) or set(
        protocol.get("consistency_outcomes", {})
    ) != {"post_w1", "post_w2", "post_w3"}:
        raise AggregationError("dataset consistency checks are incomplete or failed")


def operation_metrics(archive: zipfile.ZipFile, workload: str, duration_ms: float) -> dict:
    durations: dict[str, list[float]] = defaultdict(list)
    requests, errors, business, server = (defaultdict(int) for _ in range(4))
    expected = EXPECTED_STATUS[workload]
    member = f"{workload}/raw.json"
    try:
        stream = archive.open(member)
    except KeyError as exc:
        raise AggregationError(f"missing {member}") from exc
    with stream:
        for raw_line in stream:
            try:
                item = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise AggregationError(f"malformed raw k6 line in {member}") from exc
            if item.get("type") != "Point":
                continue
            data = item.get("data", {})
            tags = data.get("tags", {})
            operation = tags.get("operation")
            if operation not in expected:
                continue
            metric = item.get("metric")
            if metric == "http_req_duration":
                durations[operation].append(finite_number(data.get("value"), f"{member} duration"))
            elif metric == "http_reqs":
                requests[operation] += 1
                try:
                    status = int(tags.get("status", 0))
                except (TypeError, ValueError):
                    status = 0
                if status != expected[operation]:
                    errors[operation] += 1
                if status in (400, 409):
                    business[operation] += 1
                if status == 0 or status >= 500:
                    server[operation] += 1
    result = {}
    seconds = duration_ms / 1000.0
    for operation in expected:
        values, count = durations.get(operation, []), requests.get(operation, 0)
        if not values or count == 0:
            raise AggregationError(f"missing raw operation samples: {workload}.{operation}")
        if len(values) != count:
            raise AggregationError(f"duration/request mismatch: {workload}.{operation}")
        result[operation] = {
            "requests": count, "request_rate_rps": count / seconds,
            "latency_p50_ms": percentile(values, .50), "latency_p95_ms": percentile(values, .95),
            "latency_p99_ms": percentile(values, .99), "errors": errors[operation],
            "error_rate": errors[operation] / count, "business_rejections": business[operation],
            "server_errors": server[operation],
        }
    return result


def parse_resources(archive: zipfile.ZipFile, workload: str) -> dict:
    member = f"{workload}/resources.tsv"
    try:
        text = archive.read(member).decode("utf-8-sig")
    except KeyError as exc:
        raise AggregationError(f"missing {member}") from exc
    by_label: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    row_counts: dict[str, int] = defaultdict(int)
    unavailable_io = 0
    for row in csv.DictReader(io.StringIO(text), delimiter="\t"):
        label = row.get("label")
        if not label:
            continue
        row_counts[label] += 1
        for source, target in (("process_cpu_percent", "cpu_percent"), ("rss_bytes", "rss_bytes")):
            value = row.get(source)
            if value not in (None, "", "NA"):
                try:
                    parsed = float(value)
                except ValueError as exc:
                    raise AggregationError(f"invalid {source} value in {member}: {value!r}") from exc
                if not math.isfinite(parsed):
                    raise AggregationError(f"non-finite {source} value in {member}")
                by_label[label][target].append(parsed)
        if row.get("read_bytes") == "NA" or row.get("write_bytes") == "NA":
            unavailable_io += 1
    if not REQUIRED_RESOURCE_LABELS.issubset(row_counts):
        raise AggregationError(f"incomplete resource labels in {member}: {sorted(row_counts)}")
    result = {"labels": {}, "row_counts": dict(row_counts), "io_unavailable_rows": unavailable_io}
    for label, metrics in sorted(by_label.items()):
        cpu, rss = metrics["cpu_percent"], metrics["rss_bytes"]
        result["labels"][label] = {
            "samples": row_counts[label], "cpu_samples": len(cpu), "rss_samples": len(rss),
            "cpu_mean_percent": statistics.fmean(cpu) if cpu else None,
            "cpu_max_percent": max(cpu) if cpu else None,
            "rss_median_bytes": statistics.median(rss) if rss else None,
            "rss_max_bytes": max(rss) if rss else None,
        }
    return result


def parse_gc(archive: zipfile.ZipFile) -> dict:
    text = archive.read("logs/gc.log").decode("utf-8-sig", errors="replace")
    pauses = [float(match.group(1)) for line in text.splitlines()
              if "[gc          ]" in line and "Pause" in line
              for match in [re.search(r"\s([0-9.]+)ms$", line)] if match]
    return {"pause_count": len(pauses), "pause_total_ms": sum(pauses),
            "pause_max_ms": max(pauses) if pauses else None,
            "pause_p95_ms": percentile(pauses, .95)}


def mysql_status(archive: zipfile.ZipFile, member: str) -> dict[str, int]:
    lines = archive.read(member).decode("utf-8-sig", errors="replace").splitlines()
    result = {}
    for line in lines[3:]:
        fields = line.split("\t")
        if len(fields) != 2:
            break
        if fields[0] in MYSQL_STATUS_FIELDS:
            try:
                result[fields[0]] = int(fields[1])
            except ValueError:
                pass
    return result


def parse_mysql(archive: zipfile.ZipFile) -> dict:
    result = {}
    for workload in ("w1", "w2", "w3"):
        before = mysql_status(archive, f"database/before-{workload}.txt")
        after = mysql_status(archive, f"database/after-{workload}.txt")
        result[workload] = {field: after[field] - before[field]
                            for field in MYSQL_STATUS_FIELDS if field in before and field in after}
    return result


def mysql_digest_snapshot(archive: zipfile.ZipFile, member: str) -> dict:
    lines = archive.read(member).decode("utf-8-sig", errors="replace").splitlines()
    header_index = next((index for index, line in enumerate(lines) if line.startswith("DIGEST\t")), None)
    if header_index is None:
        return {}
    result = {}
    for line in lines[header_index + 1:]:
        fields = line.split("\t")
        if len(fields) != 9:
            continue
        digest, query = fields[:2]
        try:
            values = [float(value) for value in fields[2:]]
        except ValueError:
            continue
        if not all(math.isfinite(value) for value in values):
            continue
        result[digest] = {"query": query, "metrics": dict(zip(MYSQL_DIGEST_FIELDS, values))}
    return result


def parse_mysql_digest_deltas(archive: zipfile.ZipFile, workload: str) -> dict:
    before = mysql_digest_snapshot(archive, f"database/before-{workload}.txt")
    after = mysql_digest_snapshot(archive, f"database/after-{workload}.txt")
    result = {}
    for digest in sorted(set(before) | set(after)):
        before_item, after_item = before.get(digest), after.get(digest)
        metric_delta = {}
        for field in MYSQL_DIGEST_FIELDS:
            # Snapshots contain only the top digests. If a digest is absent from either
            # snapshot, its delta is unknown rather than a fabricated zero.
            metric_delta[field] = (after_item["metrics"][field] - before_item["metrics"][field]
                                   if before_item and after_item else None)
        result[digest] = {"query": (after_item or before_item)["query"], "delta": metric_delta,
                          "present_before": before_item is not None, "present_after": after_item is not None}
    return result


def load_evidence(path: pathlib.Path) -> dict:
    if not path.is_file():
        raise AggregationError(f"evidence ZIP not found: {path}")
    with zipfile.ZipFile(path) as archive:
        integrity = verify_archive(archive)
        manifest = json_member(archive, "manifest/run-manifest.json")
        result = json_member(archive, "official-result.json")
        protocol = json_member(archive, "official/protocol-validation.json")
        validate_official(result, protocol)
        run_id = manifest.get("run_id")
        if not run_id:
            raise AggregationError(f"manifest has no run_id: {path}")
        workloads, resources = {}, {}
        for workload in ("w1", "w2"):
            validation = json_member(archive, f"{workload}/validation.json")
            if validation.get("harness_valid") is not True:
                raise AggregationError(f"{run_id} {workload} harness invalid")
            duration = finite_number(validation.get("actual_duration_ms"), "actual_duration_ms")
            operations = operation_metrics(archive, workload, duration)
            request_count = sum(item["requests"] for item in operations.values())
            rejection_count = sum(item["business_rejections"] for item in operations.values())
            server_error_count = sum(item["server_errors"] for item in operations.values())
            error_count = sum(item["errors"] for item in operations.values())
            if request_count != validation.get("requests"):
                raise AggregationError(f"{run_id} {workload} raw request count mismatch")
            if rejection_count != validation.get("business_rejections"):
                raise AggregationError(f"{run_id} {workload} business rejection count mismatch")
            if server_error_count != validation.get("server_errors"):
                raise AggregationError(f"{run_id} {workload} server error count mismatch")
            if error_count != validation.get("unexpected_responses") or error_count != validation.get("checks_failed"):
                raise AggregationError(f"{run_id} {workload} raw application error count mismatch")
            workloads[workload] = {"validation": validation, "operations": operations}
            resources[workload] = parse_resources(archive, workload)
            validate_resource_coverage(resources[workload], validation, run_id, workload)
        w3_validation = json_member(archive, "w3/validation.json")
        w3_result = json_member(archive, "w3/result.json")
        if w3_validation.get("harness_valid") is not True:
            raise AggregationError(f"{run_id} W3 harness invalid")
        w3, rounds_per_scenario = {}, int(w3_result.get("rounds_per_scenario", 0))
        scenarios = w3_result.get("scenarios", {})
        if rounds_per_scenario != 15 or set(scenarios) != EXPECTED_W3_SCENARIOS:
            raise AggregationError(f"{run_id} W3 scenario/round coverage mismatch")
        if set(w3_validation.get("violation_rounds", {})) != EXPECTED_W3_SCENARIOS or set(
            w3_validation.get("server_error_rounds", {})
        ) != EXPECTED_W3_SCENARIOS:
            raise AggregationError(f"{run_id} W3 validation scenario coverage mismatch")
        for scenario, scenario_result in scenarios.items():
            rounds = scenario_result.get("rounds", [])
            if len(rounds) != rounds_per_scenario or [item.get("round") for item in rounds] != list(
                range(1, rounds_per_scenario + 1)
            ):
                raise AggregationError(f"{run_id} W3 round coverage mismatch: {scenario}")
            violations = [item.get("round") for item in rounds if item.get("violations")]
            if violations != w3_validation["violation_rounds"][scenario]:
                raise AggregationError(f"{run_id} W3 violation rounds disagree: {scenario}")
            server_rounds = w3_validation.get("server_error_rounds", {}).get(scenario, [])
            observed_server_rounds = [
                item["round"] for item in rounds
                if any(int(response.get("http_status", 0) or 0) == 0
                       or int(response.get("http_status", 0) or 0) >= 500
                       for response in item.get("responses", []))
            ]
            if observed_server_rounds != server_rounds:
                raise AggregationError(f"{run_id} W3 server-error rounds disagree: {scenario}")
            w3[scenario] = {
                "rounds": rounds_per_scenario, "violation_rounds": violations,
                "invariant_violations": len(violations),
                "violation_rate": len(violations) / rounds_per_scenario if rounds_per_scenario else None,
                "server_error_rounds": server_rounds, "server_errors": len(server_rounds),
            }
        if protocol.get("w3_violation_rounds") != w3_validation.get("violation_rounds"):
            raise AggregationError(f"{run_id} protocol W3 violations disagree with scenario results")
        official_w3_server = result.get("application_outcome", {}).get("w3_server_error_rounds")
        if official_w3_server != w3_validation.get("server_error_rounds"):
            raise AggregationError(f"{run_id} official W3 server errors disagree with scenario results")
        resources["w3"] = parse_resources(archive, "w3")
        validate_resource_coverage(resources["w3"], w3_validation, run_id, "w3")
        return {
            "run_id": run_id, "evidence_path": str(path), "evidence_sha256": sha256_file(path),
            "integrity": integrity, "manifest": manifest,
            "official": {key: result.get(key) for key in
                         ("status", "official_benchmark", "profile", "classification")},
            "workloads": workloads, "w3": w3, "resources": resources,
            "jvm_gc": parse_gc(archive), "mysql": parse_mysql(archive),
            "mysql_digests": {workload: parse_mysql_digest_deltas(archive, workload)
                              for workload in ("w1", "w2", "w3")},
        }


def validate_resource_coverage(resources: dict, validation: dict, run_id: str, workload: str) -> None:
    coverage = validation.get("resource_validation", {})
    if coverage.get("cpu_rss_complete") is not True:
        raise AggregationError(f"{run_id} {workload} CPU/RSS telemetry incomplete")
    declared = coverage.get("rows_by_label", {})
    for label in REQUIRED_RESOURCE_LABELS:
        actual_rows = resources["row_counts"].get(label, 0)
        if actual_rows != declared.get(label) or actual_rows < coverage.get("minimum_rows_per_label", 1):
            raise AggregationError(f"{run_id} {workload} telemetry row count mismatch: {label}")
        metrics = resources["labels"].get(label, {})
        if metrics.get("cpu_samples") != actual_rows or metrics.get("rss_samples") != actual_rows:
            raise AggregationError(f"{run_id} {workload} CPU/RSS samples incomplete: {label}")


def validate_group(records: list[dict], minimum_runs: int, comparator=None) -> dict:
    if len(records) < minimum_runs:
        raise AggregationError(f"insufficient runs: {len(records)} < minimum_runs={minimum_runs}")
    run_ids = [record.get("run_id") for record in records]
    if None in run_ids or len(set(run_ids)) != len(run_ids):
        raise AggregationError("duplicate run IDs")
    comparator = comparator or load_comparator()
    pairwise = []
    for left, right in itertools.combinations(records, 2):
        comparison = comparator.compare_documents([left["manifest"], right["manifest"]])
        pairwise.append({"run_ids": [left["run_id"], right["run_id"]], **comparison})
    mismatches = [{"run_ids": item["run_ids"], **mismatch}
                  for item in pairwise for mismatch in item["mismatches"]]
    if mismatches:
        raise AggregationError(f"manifest mismatch: {json.dumps(mismatches, ensure_ascii=False)}")
    return {"comparable": True, "mismatches": [], "pairwise_comparisons": pairwise}


def aggregate_operations(records: list[dict]) -> dict:
    result = {}
    for workload in ("w1", "w2"):
        result[workload] = {}
        for operation in sorted(records[0]["workloads"][workload]["operations"]):
            per_run = {record["run_id"]: record["workloads"][workload]["operations"][operation]
                       for record in records}
            metrics = next(iter(per_run.values())).keys()
            result[workload][operation] = {
                "per_run": per_run,
                "across_runs": {metric: summarize([values[metric] for values in per_run.values()])
                                for metric in metrics},
                "percentile_policy": "Percentiles are computed within each run; across-run summaries use per-run percentiles. Requests are not pooled.",
            }
    return result


def aggregate_w3(records: list[dict]) -> dict:
    result = {}
    for scenario in sorted(records[0]["w3"]):
        per_run = {record["run_id"]: record["w3"][scenario] for record in records}
        rounds = sum(item["rounds"] for item in per_run.values())
        violations = sum(item["invariant_violations"] for item in per_run.values())
        result[scenario] = {
            "per_run": per_run, "total_rounds": rounds,
            "total_invariant_violations": violations,
            "total_server_error_rounds": sum(item["server_errors"] for item in per_run.values()),
            "runs_with_invariant_violations": sum(item["invariant_violations"] > 0 for item in per_run.values()),
            "runs_with_server_errors": sum(item["server_errors"] > 0 for item in per_run.values()),
            "violation_rate": violations / rounds if rounds else None,
            "across_runs": {
                "invariant_violations": summarize([item["invariant_violations"] for item in per_run.values()]),
                "violation_rate": summarize([item["violation_rate"] for item in per_run.values()]),
                "server_errors": summarize([item["server_errors"] for item in per_run.values()]),
            },
        }
    return result


def aggregate_resources(records: list[dict]) -> dict:
    result = {}
    for workload in ("w1", "w2", "w3"):
        result[workload] = {}
        for label in sorted(records[0]["resources"][workload]["labels"]):
            per_run = {record["run_id"]: record["resources"][workload]["labels"].get(label, {})
                       for record in records}
            result[workload][label] = {
                "per_run": per_run,
                "across_runs": {metric: summarize([item.get(metric) for item in per_run.values()])
                                for metric in ("cpu_mean_percent", "cpu_max_percent",
                                               "rss_median_bytes", "rss_max_bytes")},
            }
    return result


def aggregate_simple(records: list[dict], key: str) -> dict:
    per_run = {record["run_id"]: record[key] for record in records}
    fields = sorted({field for values in per_run.values() for field in values})
    return {"per_run": per_run,
            "across_runs": {field: summarize([values.get(field) for values in per_run.values()])
                            for field in fields}}


def aggregate_mysql(records: list[dict]) -> dict:
    result = {}
    for workload in ("w1", "w2", "w3"):
        per_run = {record["run_id"]: record["mysql"].get(workload, {}) for record in records}
        fields = sorted({field for values in per_run.values() for field in values})
        result[workload] = {"per_run": per_run,
                            "across_runs": {field: summarize([values.get(field) for values in per_run.values()])
                                            for field in fields}}
    return result


def aggregate_mysql_digests(records: list[dict]) -> dict:
    result = {}
    for workload in ("w1", "w2", "w3"):
        per_run = {record["run_id"]: record["mysql_digests"].get(workload, {}) for record in records}
        digests = sorted({digest for values in per_run.values() for digest in values})
        workload_result = {}
        for digest in digests:
            per_digest = {run_id: values.get(digest) for run_id, values in per_run.items()}
            metrics = {field: summarize([item["delta"].get(field) if item else None
                                         for item in per_digest.values()])
                       for field in MYSQL_DIGEST_FIELDS}
            workload_result[digest] = {"query_by_run": {run_id: item["query"] if item else None
                                                         for run_id, item in per_digest.items()},
                                       "per_run_delta": {run_id: item["delta"] if item else None
                                                          for run_id, item in per_digest.items()},
                                       "across_runs": metrics,
                                       "availability": {run_id: bool(item) for run_id, item in per_digest.items()}}
        result[workload] = workload_result
    return result


def exclusion_record(path: pathlib.Path, reference_manifest: dict, comparator) -> dict:
    record = load_evidence(path)
    manifest = record["manifest"]
    comparison = comparator.compare_documents([reference_manifest, manifest])
    mismatches = comparison.get("mismatches", [])
    reason = ("outside selected Intel comparison group: " + ", ".join(
        sorted({item.get("field", "unknown") for item in mismatches})
    )) if mismatches else "not selected for this baseline"
    return {"run_id": record["run_id"], "evidence_path": str(path),
            "evidence_sha256": record["evidence_sha256"], "integrity": record["integrity"],
            "official": record["official"],
            "selected_fingerprint": {"hardware": manifest["hardware"],
                                     "toolchain": manifest["toolchain"],
                                     "source": manifest["source"], "locks": manifest["locks"]},
            "reason": reason, "comparison": comparison}


def build_report(records: list[dict], exclusions: list[dict], minimum_runs: int, target_runs: int) -> dict:
    comparator = load_comparator()
    comparison = validate_group(records, minimum_runs, comparator)
    reference = records[0]["manifest"]
    return {
        "schema_version": 1,
        "baseline": {"phase": "BEFORE", "status": "LOCKED", "comparison_group": "kaggle-intel-xeon",
                     "valid_runs": len(records), "minimum_runs": minimum_runs,
                     "minimum_runs_met": len(records) >= minimum_runs, "target_runs": target_runs,
                     "target_runs_met": len(records) >= target_runs,
                     "after_requirement": "AFTER runs must pass the same comparator against this Intel fingerprint."},
        "run_traceability": [{**{key: record[key] for key in
                               ("run_id", "evidence_path", "evidence_sha256", "integrity", "official")},
                              "hardware_fingerprint": record["manifest"]["hardware"],
                              "toolchain_fingerprint": record["manifest"]["toolchain"],
                              "source_fingerprint": record["manifest"]["source"],
                              "locks": record["manifest"]["locks"]} for record in records],
        "selected_manifest_fingerprint": {"hardware": reference["hardware"],
                                           "toolchain": reference["toolchain"],
                                           "source": reference["source"], "locks": reference["locks"]},
        "telemetry_coverage": [{
            "run_id": record["run_id"],
            "resources": {workload: {"row_counts": record["resources"][workload]["row_counts"],
                                     "io_unavailable_rows": record["resources"][workload]["io_unavailable_rows"]}
                          for workload in ("w1", "w2", "w3")},
            "mysql_status_fields": {workload: sorted(record["mysql"][workload])
                                    for workload in ("w1", "w2", "w3")},
        } for record in records],
        "comparability": comparison, "excluded_runs": exclusions,
        "w1_w2_operations": aggregate_operations(records), "w3_scenarios": aggregate_w3(records),
        "resources": aggregate_resources(records), "jvm_gc": aggregate_simple(records, "jvm_gc"),
        "mysql": aggregate_mysql(records), "mysql_query_digests": aggregate_mysql_digests(records),
        "missing_telemetry_policy": "Unavailable values remain null with availability counts; they are never converted to zero.",
    }


def number(value, digits=3) -> str:
    return "NA" if value is None else f"{value:.{digits}f}"


def render_markdown(report: dict) -> str:
    baseline = report["baseline"]
    lines = ["# G2.5 Official BEFORE Baseline — Intel Multi-run Aggregation", "",
             f"**Baseline status: `{baseline['status']}`**", "",
             f"Selected group: `{baseline['comparison_group']}`. Valid runs: **{baseline['valid_runs']}**; "
             f"minimum {baseline['minimum_runs']} met: **{str(baseline['minimum_runs_met']).lower()}**; "
             f"target {baseline['target_runs']} met: **{str(baseline['target_runs_met']).lower()}**.", "",
             "Percentiles are calculated per run and then summarized across runs. Request samples are not pooled.", "",
             "## Run traceability", "", "| Run ID | CPU | MemTotal bytes | Evidence SHA-256 | ZIP checksums |",
             "|---|---|---:|---|---:|"]
    for run in report["run_traceability"]:
        cpu = run["hardware_fingerprint"]["cpu_model"]
        memory = run["hardware_fingerprint"]["memory_total_bytes"]
        lines.append(f"| `{run['run_id']}` | `{cpu}` | {memory} | `{run['evidence_sha256']}` | "
                     f"{run['integrity']['checksums_verified']} verified |")
    fingerprint = report["selected_manifest_fingerprint"]
    hardware, locks = fingerprint["hardware"], fingerprint["locks"]
    cgroup, toolchain, source = hardware["cgroup"], fingerprint["toolchain"], fingerprint["source"]
    rows = {
        "CPU model": hardware["cpu_model"], "CPU quota": cgroup["cpu_quota_raw"],
        "cpuset": cgroup["cpuset_effective"], "cgroup memory limit": cgroup["memory_limit_raw"],
        "MemTotal bytes (reference)": hardware["memory_total_bytes"],
        "OS / kernel": f"{hardware['os_id']} {hardware['os_version']} / {hardware['kernel']}",
        "runtime image identity": hardware["runtime_image_identity"],
        "Java": toolchain["java_version"].splitlines()[0],
        "MySQL": toolchain["mysql_version"].split(" Ver ")[-1], "k6": toolchain["k6_version"],
        "application SHA": source["application_sha"], "JAR SHA-256": source["application_jar_sha256"],
        "configuration SHA-256": locks["configuration_sha256"],
        "workload SHA-256": locks["workload_source_sha256"], "dataset SHA-256": locks["dataset_sha256"],
    }
    lines += ["", "## Hardware, toolchain and benchmark locks", "",
              "| Fingerprint | Locked value |", "|---|---|"]
    lines.extend(f"| {key} | `{value}` |" for key, value in rows.items())
    lines += ["", "## Per-run W1/W2 metrics", "",
              "| Run ID | Workload | Operation | Requests | RPS | P50 ms | P95 ms | P99 ms | Errors | Business rejections |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for workload, operations in report["w1_w2_operations"].items():
        for operation, item in operations.items():
            for run_id, metric in item["per_run"].items():
                lines.append(f"| `{run_id}` | {workload.upper()} | `{operation}` | {metric['requests']} | "
                             f"{number(metric['request_rate_rps'])} | {number(metric['latency_p50_ms'])} | "
                             f"{number(metric['latency_p95_ms'])} | {number(metric['latency_p99_ms'])} | "
                             f"{metric['errors']} | {metric['business_rejections']} |")
    lines += ["", "## W1/W2 operation aggregates", "",
              "| Workload | Operation | Metric | Median | Min | Max | CV |", "|---|---|---|---:|---:|---:|---:|"]
    for workload, operations in report["w1_w2_operations"].items():
        for operation, item in operations.items():
            for metric, stats in item["across_runs"].items():
                lines.append(f"| {workload.upper()} | `{operation}` | `{metric}` | {number(stats['median'])} | "
                             f"{number(stats['min'])} | {number(stats['max'])} | "
                             f"{number(stats['coefficient_of_variation'], 4)} |")
    lines += ["", "## W3 scenario aggregates", "",
              "| Scenario | Rounds | Violations | Violation rate | Server-error rounds | Runs with violations | Runs with server errors |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for scenario, item in report["w3_scenarios"].items():
        lines.append(f"| `{scenario}` | {item['total_rounds']} | {item['total_invariant_violations']} | "
                     f"{number(item['violation_rate'], 4)} | {item['total_server_error_rounds']} | "
                     f"{item['runs_with_invariant_violations']} | {item['runs_with_server_errors']} |")
    lines += ["", "## W3 per-run findings", "",
              "| Run ID | Scenario | Rounds | Invariant violations | Violation rate | Server-error rounds |",
              "|---|---|---:|---:|---:|---:|"]
    for scenario, item in report["w3_scenarios"].items():
        for run_id, metric in item["per_run"].items():
            lines.append(f"| `{run_id}` | `{scenario}` | {metric['rounds']} | {metric['invariant_violations']} | "
                         f"{number(metric['violation_rate'], 4)} | {metric['server_errors']} |")
    lines += ["", "## Telemetry coverage", "",
              "CPU/RSS, JVM/GC and MySQL per-run values and across-run summaries are preserved in the JSON report. Missing telemetry remains `null` with availability counts; it is not represented as zero.", "",
              "## Excluded runs", "",
              "| Run ID | Evidence SHA-256 | Official evidence | Comparator mismatch |", "|---|---|---|---|"]
    for item in report["excluded_runs"]:
        mismatches = ", ".join(mismatch.get("field", "unknown") for mismatch in item["comparison"]["mismatches"])
        lines.append(f"| `{item['run_id']}` | `{item['evidence_sha256']}` | `{item['official']['status']}` / "
                     f"`{item['official']['classification']}` | `{mismatches}` |")
    lines += ["", "## Baseline lock", "",
              "The official BEFORE baseline is locked to Runs 02, 04 and 05 in the Intel Xeon comparison group. Runs 01 and 03 remain preserved AMD evidence and are not aggregated. AFTER must use an Intel-compatible manifest and pass the same comparator. The minimum run count is met; the five-run target is not met.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-markdown", required=True)
    parser.add_argument("--minimum-runs", type=int, default=3)
    parser.add_argument("--target-runs", type=int, default=5)
    parser.add_argument("--exclude", action="append", default=[], help="Evidence ZIP retained outside the group")
    parser.add_argument("evidence", nargs="+")
    args = parser.parse_args()
    if args.minimum_runs < 1 or args.target_runs < args.minimum_runs:
        raise SystemExit("invalid run count policy")
    try:
        records = [load_evidence(pathlib.Path(item)) for item in args.evidence]
        comparator = load_comparator()
        validate_group(records, args.minimum_runs, comparator)
        exclusions = [exclusion_record(pathlib.Path(item), records[0]["manifest"], comparator)
                      for item in args.exclude]
        report = build_report(records, exclusions, args.minimum_runs, args.target_runs)
        output_json, output_markdown = pathlib.Path(args.output_json), pathlib.Path(args.output_markdown)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_markdown.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        output_markdown.write_text(render_markdown(report), encoding="utf-8")
    except (AggregationError, zipfile.BadZipFile) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({"status": report["baseline"]["status"],
                      "valid_runs": report["baseline"]["valid_runs"],
                      "minimum_runs_met": report["baseline"]["minimum_runs_met"],
                      "target_runs_met": report["baseline"]["target_runs_met"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
