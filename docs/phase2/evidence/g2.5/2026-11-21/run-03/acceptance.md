# G2.5 Official BEFORE Run 03 — Independent Acceptance

**Verdict: `ACCEPTED`**  
**Comparison with Run 01: `COMPARABLE`**

Run 03 is a valid official standard measurement and matches Run 01's hardware, toolchain, source, configuration, workload, and dataset comparison fields. W2 business rejections and W3 concurrency invariant findings are recorded application outcomes; the corresponding harness validations pass.

## 1. Evidence identity and integrity

| Property | Run 03 | Run 01 reference |
|---|---|---|
| Evidence ZIP | `g25-before-20261121T144102Z-evidence.zip` | `g25-before-20261121T081712Z-evidence.zip` |
| Run ID | `g25-before-20261121T144102Z` | `g25-before-20261121T081712Z` |
| ZIP size | 10,411,901 bytes | 9,334,843 bytes |
| ZIP SHA-256 | `ed49c58fe9585661d1187385550db18292d5f1e69363194dec9b043f177fad77` | `f38404aa04d631a8312a0570cb1a9584288ecbf1f6a0e0c26130125c444ad38d` |
| Run interval (UTC) | 2026-11-21 14:41:02–14:50:41 | 2026-11-21 08:17:12–08:26:51 |

Run 03 archive: `docs/phase2/evidence/g2.5/2026-11-21/g25-before-20261121T144102Z-evidence.zip`.

- ZIP contains 63 entries; archive CRC validation passed (`testzip()` returned no bad entry).
- `SHA256SUMS.txt` lists 62 payload files. All 62 digests were recomputed from the ZIP contents and matched. No payload entry is missing, mismatched, or unlisted; the checksum file does not checksum itself.

## 2. Official status, provenance, and protocol

`official-result.json` reports `status=PASS`, `official_benchmark=true`, `requested_official_benchmark=true`, `profile=standard`, `classification=VALID_BASELINE_MEASUREMENT`, and `error=null`. `official/protocol-validation.json` reports `harness_valid=true`.

The evidence contains all 24 start/completion phase events, in the locked order: `prepare_standard → warmup → w1 → post_w1 → reset_after_w1 → w2 → post_w2 → reset_after_w2 → w3 → post_w3 → cooldown → final_reset`. Warmup is explicitly excluded from official metrics. W1 and W2 durations are approximately 180 seconds, W3 has 15 rounds per scenario, and cooldown is 30 seconds.

| Provenance or lock | Run 03 value | Comparison |
|---|---|---|
| Application / protocol baseline SHA | `510f6415b6af535ceec77213f0b0c7d5082123f7` | Matches Run 01 |
| Repository SHA | `4418a8dd76192f6da3437968d9d8a31a4566e72b` | Matches Run 01 |
| Application JAR SHA-256 | `f802904a9a47cc14e8745dd7c39a1fb24b6219ef8be60be3805be4cf9af8cd98` | Matches Run 01 and bundle manifest |
| Configuration lock SHA-256 | `e257ab3d71b73377d40cc85612e10f5e999ce8b55b00b3adff6075489a5fa2e1` | Matches Run 01 |
| Workload source SHA-256 | `c773850351f0cc5d337ba96a5fef5774a6871abf99aa1054a722ae528164397f` | Matches Run 01 |
| Dataset logical SHA-256 | `ce932b243cbfb16c34935ece3deb9f9e6479da34ab6828d93b2903f9538839b4` | Matches Run 01 |

The run manifest and bundle manifest agree on the application SHA and JAR SHA. Bundle manifest lists 21 files. The Java, MySQL, k6 and libaio tool versions and executable/package hashes match Run 01; the MySQL version output's run-specific path prefix is normalized by the current comparator, while version text and executable hash remain locked.

## 3. Workload results and application findings

| Workload | Measured result | Validation / interpretation |
|---|---|---|
| W1 | 180,020 ms; 3,601 requests; 3,601 checks passed; 0 failed; HTTP/application error rate 0; P95 29.49 ms, P99 34.05 ms; 20.003 req/s | `COMPLETED_WITHOUT_OBSERVED_ERRORS`; harness valid |
| W2 | 180,049 ms; 82,915 requests; 82,900 checks passed, 15 failed; HTTP/application error rate 0.0001809 (0.0181%); 15 business rejections; 0 server errors; P95 32.18 ms, P99 45.53 ms; 460.513 req/s | `HTTP_OR_PERFORMANCE_FAILURE`; harness valid. Business rejections are application findings, not harness failure. |
| W3 | 15 rounds each for `same_food_checkout`, `same_cart_checkout`, and `admin_stock_vs_checkout`; invariant violations in `admin_stock_vs_checkout` rounds 2, 5–9, 11–12, and 14 (9/15); no server-error rounds | `harness_valid=true`; W3 result records before state, responses, after state, and violations. Invariant violations are baseline application defects, not harness failure. |

The W2 rejection count and W3 violation rounds differ from Run 01, as expected for measured application outcomes. Neither difference is an acceptance or comparability failure.

## 4. Dataset, telemetry, cleanup, and secret scan

- Initial dataset, resets after W1 and W2, and final reset all report `all_invariants_pass=true` and logical SHA-256 `ce932b243cbfb16c34935ece3deb9f9e6479da34ab6828d93b2903f9538839b4`. `reset_matches_initial=true`; protocol consistency outcomes are `CONSISTENT` after W1, W2, and W3.
- Initial profile cardinalities: 26 users, 10 categories, 5,021 foods, 500 orders, 1,000 order items, and empty carts/cart items. Standard profile parameters match the lock.
- CPU/RSS telemetry is complete: 549 samples each for W1 and W2 (183 per backend/MySQL/driver label), 18 for W3 (6 per label), and 189 for warmup (63 per label). MySQL process I/O is unavailable on the platform and is explicitly recorded in unavailable sidecars (183 rows per W1/W2, 6 W3); it is not represented as zero.
- JVM evidence includes `logs/gc.log` (169,675 bytes) and `logs/backend.log`; MySQL evidence includes `logs/mysql-server/mysql.log` and before/after database telemetry snapshots for W1, W2, and W3.
- Cleanup reports `success=true`, backend and MySQL stopped, runtime secret removed, and no cleanup errors. `secret_scan_violations=[]`.
- `environment/backend-lifecycle.json` is a sample during official cooldown and records the backend alive at that point. The subsequent final-reset phase completed and final cleanup reports the backend stopped; this cooldown sample is not a cleanup failure.

## 5. Hardware comparability with Run 01

Run 03 preflight and manifest match Run 01 on the comparison fingerprint:

| Field | Run 01 | Run 03 | Result |
|---|---|---|---|
| CPU model | AMD EPYC 7B12 | AMD EPYC 7B12 | Match |
| Logical cores | 4 | 4 | Match |
| CPU quota / period | `400000 100000` (4.0 cores) | `400000 100000` (4.0 cores) | Match |
| Effective cpuset | `0-3` (4 CPUs) | `0-3` (4 CPUs) | Match |
| `memory_total_bytes` | 33,658,159,104 | 33,658,159,104 | Match (0-byte delta; within 1 MiB policy) |
| Cgroup memory limit / resolved limit | 32,212,254,720 bytes | 32,212,254,720 bytes | Exact match |
| OS / kernel | Ubuntu 24.04 / `6.18.55+` | Ubuntu 24.04 / `6.18.55+` | Match |
| Runtime image identity | `73b7688c6b0298bb811a52b1b22d66eac3bb3fdc7f0da53b3ac4b46db031c2ec` | Same | Match |
| Java / MySQL / k6 | 21.0.13 / 8.4.13 / 0.55.2 | Same | Match |
| Configuration / workload / dataset locks | Same values listed above | Same | Match |

The updated `compare_manifests.py` was applied directly to the archived Run 01 and Run 03 manifests. Result: `comparable=true`, `mismatches=[]`. Application SHA and JAR SHA also match because both are BEFORE baseline runs.

## 6. Verdict and run-group count

**Run 03: `ACCEPTED`. Run 03 vs Run 01: `COMPARABLE`.** Evidence integrity, official status, protocol, harness validation, dataset resets, telemetry, cleanup, and secret scan pass. Recorded W2/W3 application defects do not invalidate the run.

The AMD comparison group now contains **2 valid comparable runs out of the minimum 3**: Run 01 and Run 03. Run 02 remains `INCOMPARABLE` (Intel Xeon CPU) and is excluded. One more valid official BEFORE run matching the AMD EPYC 7B12 comparison fingerprint is required before reaching the minimum of three. Therefore, the next official run may proceed, subject to the same hardware preflight and post-run acceptance.

---

Independent acceptance based on archived Run 03 evidence and direct comparison to accepted Run 01. Evidence ZIP was read-only; no benchmark was rerun.
