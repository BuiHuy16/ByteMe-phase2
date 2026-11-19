#!/usr/bin/env python3
"""Aggregate comparable k6 summary JSON files without merging different platforms/workloads."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics


FIELDS = {
    "latency_p50_ms": ("http_req_duration", "p(50)"),
    "latency_p95_ms": ("http_req_duration", "p(95)"),
    "latency_p99_ms": ("http_req_duration", "p(99)"),
    "request_rate_rps": ("http_reqs", "rate"),
    "http_failure_rate": ("http_req_failed", "rate"),
}


def summarize(values: list[float]) -> dict:
    mean = statistics.fmean(values)
    deviation = statistics.pstdev(values) if len(values) > 1 else 0.0
    return {
        "runs": len(values), "median": statistics.median(values), "mean": mean,
        "min": min(values), "max": max(values), "population_stddev": deviation,
        "coefficient_of_variation": deviation / mean if mean else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--configuration-sha256", required=True)
    parser.add_argument("--dataset-sha256", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("summaries", nargs="+")
    args = parser.parse_args()
    records = []
    rejected = []
    for item in args.summaries:
        path = pathlib.Path(item)
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            values = {}
            for name, (metric, key) in FIELDS.items():
                value = data["metrics"][metric]["values"][key]
                if not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError(f"invalid {metric}.{key}")
                values[name] = float(value)
            records.append({"path": str(path), "values": values})
        except Exception as exc:
            rejected.append({"path": str(path), "reason": str(exc)})
    if not records:
        raise SystemExit("No valid summaries")
    aggregate = {name: summarize([record["values"][name] for record in records]) for name in FIELDS}
    result = {"workload": args.workload, "platform": args.platform,
              "configuration_sha256": args.configuration_sha256,
              "dataset_sha256": args.dataset_sha256,
              "valid_runs": len(records), "rejected_runs": rejected,
              "per_run": records, "aggregate": aggregate,
              "note": "The caller must supply summaries whose workload, dataset and configuration match these locked identities."}
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"valid_runs": len(records), "rejected_runs": len(rejected)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
