# ByteMe Phase 2 reproducible benchmark kit

This directory prepares the common before/after protocol. It does **not** contain an official result. G2.5 must run the same committed workload and locked configuration against each treatment SHA.

## Platform

Primary platform: local Windows + Docker Desktop Compose. k6 runs from the pinned container tag in `K6_IMAGE`; the application and MySQL run in a dedicated Compose project. The load generator shares the Docker VM/host, so its CPU/memory use is collected and treated as a confounder. Kaggle remains a fallback only; local and Kaggle results must never be compared directly.

## Files

- `compose.benchmark.yaml`: benchmark-only runtime/resource lock layered over the baseline Compose file.
- `profiles.json`: deterministic smoke and standard dataset cardinalities.
- `prepare_dataset.py`: safety-checked isolated reset, fixture generation, logical checksums and temporary actor-token file.
- `workloads/w1_read.js`: food list, food search and authenticated order-list reads with operation tags.
- `workloads/w2_write.js`: isolated per-actor cart add/update, checkout and cancellation.
- `workloads/w3_contention.py`: barrier-based correctness rounds for same-food checkout, same-cart checkout and admin-stock-vs-checkout.
- `tools/collect_environment.ps1`: source/toolchain/image/runtime configuration manifest.
- `tools/collect_resources.ps1`: timestamped Docker CPU/RAM samples.
- `tools/collect_db_telemetry.ps1`: read-only MySQL status and Performance Schema digest snapshots for before/after deltas.
- `tools/new_manifest.ps1`: SHA-256 artifact manifest.
- `tools/aggregate_runs.py`: median/min/max/CV aggregation for comparable k6 summaries; rejects malformed runs.
- `tools/run_smoke.ps1`: small preparation smoke test only.

## Dataset profiles

`smoke` exists only to validate the kit. `standard` is the proposed G2.5 starting profile and must be frozen before the first official run.

| Partition | Smoke | Standard |
|---|---:|---:|
| Search/menu foods | 60 | 5,000 |
| Read actor orders | 20 | 500 |
| Items per read order | 2 | 2 |
| Dedicated write actors/foods | 2 | 20 |
| Contention actors | 4 | 4 |
| Shared-stock initial quantity | 10 | 10 |

Users, categories, foods, orders and order items are regenerated from the profile. Logical checksums deliberately exclude password hashes, JWTs and generated timestamps. Temporary actor tokens stay under `.local/phase2-benchmark/` and must never be archived.

## Official G2.5 protocol (not run by G2.4)

1. Create a new unique run ID and a new dedicated Compose project/volume.
2. Build the selected source SHA and record image/base-image IDs.
3. Prepare `standard`; archive cardinality and logical checksums.
4. Readiness, then 60 s low-rate warm-up. Discard warm-up metrics.
5. Run W1 for 180 s using constant arrival rates: food list 10 RPS, search 5 RPS, order list 5 RPS. Lock page size (proposed 20; add a separate diagnostic run for 50).
6. Reset and verify the dataset.
7. Run W2 for 180 s with 10 constant VUs, not exceeding the 20 dedicated actors.
8. Reset and verify the dataset.
9. Run W3 separately for 15 correctness rounds/scenario; never mix it into throughput percentiles.
10. Cool down 30 s, collect logs/metrics, reset and verify again, then remove only the run's project resources.
11. Repeat independent measurement runs at least 3 times (target 5), alternating before/after order where practical. A failed run is retained and classified, never silently rerun.

For each metric report per-run p50/p95/p99/RPS/error rate, then median across valid runs plus min/max and coefficient of variation. Do not treat historical p95/p99 thresholds as accepted SLOs. Business 409s, HTTP 500s and transport errors are separate counters.

Take DB telemetry snapshots immediately before and after each measured workload and compare `COUNT_STAR` by digest; never enable MySQL general logging during throughput measurement. Hikari configuration is locked, while runtime pool gauges are unavailable through the current actuator exposure and must be reported as a limitation rather than inferred.

The aggregator requires the frozen configuration and dataset SHA-256 values on every invocation. Review each candidate run's manifests before passing its summary; the tool deliberately does not infer comparability from filenames.

## Configuration lock

The benchmark override explicitly locks G1 heap, Hikari 10/10, Tomcat 200/10, MySQL isolation/max connections/buffer pool, CPU/memory limits, GC logging and the MySQL digest. k6 is run with a pinned tag and its resolved digest is recorded. Any later configuration change is either prohibited or declared as a separate treatment.

## Smoke test

From PowerShell at repository root:

```powershell
$env:BENCH_ACTOR_PASSWORD = '<ephemeral strong value>'
./benchmarks/phase2/tools/run_smoke.ps1 -EvidenceDir 'docs/phase2/evidence/g2.4/YYYY-MM-DD/smoke'
```

The script uses project `byteme-g24-smoke`, ports 13308/18082, runs only a few iterations/rounds, resets to the initial checksum, writes evidence, and removes the project volume/containers/network/image plus temporary secrets. It is not an official baseline benchmark.

## Artifact layout for every official run

```text
<run-id>/
  manifest/environment.json
  manifest/configuration-lock.md
  dataset/initial.json
  dataset/post-run.json
  workload/source-checksums.txt
  k6/raw.json
  k6/summary.json
  resources/docker-stats.tsv
  logs/backend.log
  logs/mysql.log
  database/status-before.txt
  database/status-after.txt
  consistency/result.json
  exit-codes/
  SHA256SUMS.txt
```

Never archive runtime env files, passwords, private keys, JWTs or Authorization headers.
