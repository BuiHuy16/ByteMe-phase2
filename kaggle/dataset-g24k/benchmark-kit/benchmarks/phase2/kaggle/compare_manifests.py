#!/usr/bin/env python3
"""Reject aggregation when Kaggle hardware/toolchain/configuration differs."""

from __future__ import annotations

import argparse
import json
import pathlib


COMPARISON_FIELDS = (
    "hardware.cpu_model",
    "hardware.logical_cores",
    "hardware.memory_total_bytes",
    "hardware.os_id",
    "hardware.os_version",
    "hardware.kernel",
    "hardware.runtime_image_identity",
    "hardware.cgroup.version",
    "hardware.cgroup.cpu_quota_raw",
    "hardware.cgroup.cpu_period_us",
    "hardware.cgroup.cpuset_effective",
    "hardware.cgroup.cpuset_cpu_count",
    "hardware.cgroup.memory_limit_raw",
    "hardware.cgroup.resolved_cpu_limit",
    "hardware.cgroup.resolved_memory_limit_bytes",
    "hardware.cgroup.quota_evidence_complete",
    "toolchain.java_version",
    "toolchain.mysql_version",
    "toolchain.k6_version",
    "toolchain.java_executable_sha256",
    "toolchain.mysqld_executable_sha256",
    "toolchain.k6_executable_sha256",
    "locks.configuration_sha256",
    "locks.workload_source_sha256",
    "locks.dataset_sha256",
)

PROVENANCE_FIELDS = (
    "source.protocol_baseline_sha",
    "source.repository_sha",
    "source.application_sha",
    "source.application_jar_sha256",
)


def value(document: dict, path: str):
    current = document
    for part in path.split("."):
        current = current[part]
    return current


def compare_documents(documents: list[dict]) -> dict:
    reference = documents[0]
    mismatches = []
    for index, document in enumerate(documents, 1):
        for field in (*PROVENANCE_FIELDS, *COMPARISON_FIELDS):
            try:
                actual = value(document, field)
            except (KeyError, TypeError):
                mismatches.append({"manifest": index, "field": field, "reason": "missing"})
                continue
            if actual is None or actual == "" or (field.endswith("quota_evidence_complete") and actual is not True):
                mismatches.append({"manifest": index, "field": field, "reason": "insufficient_evidence",
                                   "actual": actual})
    for index, document in enumerate(documents[1:], 2):
        for field in COMPARISON_FIELDS:
            try:
                expected, actual = value(reference, field), value(document, field)
            except (KeyError, TypeError):
                continue
            if actual != expected:
                mismatches.append({"manifest": index, "field": field,
                                   "reference": expected, "actual": actual})
    return {"comparable": not mismatches,
            "treatment_application_shas": [document.get("source", {}).get("application_sha") for document in documents],
            "mismatches": mismatches}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifests", nargs="+")
    args = parser.parse_args()
    if len(args.manifests) < 2:
        parser.error("at least two run manifests are required")
    documents = [json.loads(pathlib.Path(item).read_text(encoding="utf-8-sig")) for item in args.manifests]
    result = {"manifests": args.manifests, **compare_documents(documents)}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not mismatches else 2


if __name__ == "__main__":
    raise SystemExit(main())
