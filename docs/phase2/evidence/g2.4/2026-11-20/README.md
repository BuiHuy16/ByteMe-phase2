# G2.4 evidence — 2026-11-20 (Asia/Saigon)

This directory records benchmark preparation only. No G2.5 official before/after run was executed. Runtime timestamps are UTC on 2026-11-19; the evidence directory uses the local project date.

## Outcome

- Primary platform: local Windows + Docker Desktop, dedicated Compose project and volume.
- Fallback: Kaggle CPU only if local becomes unavailable; results from different platforms must not be compared.
- Baseline application source: `510f6415b6af535ceec77213f0b0c7d5082123f7`, with executable diff exit `0` during the successful smoke.
- Final validation: `smoke-attempt-6`, status `PASS`, not an official benchmark.
- Initial and post-reset logical dataset checksum: `1563f0bc27189c805d600347a497830593289542cfc3543d3b73d29117961e50`.
- W1: 6/6 checks passed; W2: 8/8 checks passed. The tiny iteration counts make their latency/RPS unsuitable as baseline results.
- W3 intentionally reproduced known concurrency behavior: same-food invariant violations in 2/2 rounds, same-cart HTTP 500 in round 2, and admin-stock final-state violation in round 2. These are correctness signals, not throughput percentiles.
- MySQL status and Performance Schema digest snapshots exist before/after W1, W2 and W3; Docker CPU/RAM samples exist for all three workloads.
- Cleanup removed the dedicated containers, network, volume, backend image, listeners and temporary credentials/keys. Shared Docker resources were not modified.

## Preserved attempts

| Attempt | Result | Reason / validation value |
|---|---|---|
| `smoke-attempt-1` | FAIL | Environment collector treated Java informational stderr as failure; cleanup passed. |
| `smoke-attempt-2` | FAIL | W3 Python name collision; W1/W2 passed; cleanup passed. |
| `smoke-attempt-3` | FAIL | Second W3 local-name collision; W1/W2 passed; cleanup passed. |
| `smoke-attempt-4` | PASS | First end-to-end pass with deterministic reset and cleanup. |
| `smoke-attempt-5` | FAIL | Application DB user correctly lacked Performance Schema privilege; collector failed closed; cleanup passed. |
| `smoke-attempt-6` | PASS | Final kit: stable environment capture, read-only root telemetry, W1/W2/W3 resource samples, reset and cleanup. |

Failures are retained and were not hidden by reruns. Each attempt has its own raw output and checksum manifest.

## Artifact map

- `platform-decision.md`: local/Kaggle comparison and selection.
- `configuration-lock.md`: frozen toolchain/runtime/dataset/workload controls.
- `smoke-summary.md`: final smoke interpretation and limitations.
- `smoke-attempt-*/`: build, startup, environment, dataset, workload, DB/resource telemetry, logs, exit codes and cleanup evidence.
- `benchmark-source-SHA256SUMS.txt`: hashes of the versioned benchmark kit.
- `SHA256SUMS.txt`: evidence-tree manifest, excluding itself.

Runtime passwords, JWTs, Authorization headers and RSA key material are deliberately absent. The token file lived only under `.local/phase2-benchmark/` and was deleted during cleanup.
