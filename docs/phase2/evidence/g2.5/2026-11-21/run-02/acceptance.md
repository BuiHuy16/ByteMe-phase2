# G2.5 Official BEFORE Run 02 — Independent Acceptance

**Verdict: `INCOMPARABLE`**

Run 02 is internally valid official evidence, but it does not belong to Run 01's comparison group. The Kaggle CPU model differs, and exact total memory differs by 4,096 bytes. Both are locked comparison fields. Run 02 must be excluded from aggregation with Run 01.

## 1. Scope and evidence identity

This review inspected the Run 02 archive named in the task and compared it directly with the separately identified, previously accepted Run 01 archive. The local report for Run 01 identifies its ZIP and run ID; the two IDs are not interchangeable.

| Item | Run 02 | Run 01 reference |
|---|---|---|
| Evidence ZIP | `g25-before-20261121T103301Z-evidence.zip` | `g25-before-20261121T081712Z-evidence.zip` |
| Run ID | `g25-before-20261121T103301Z` | `g25-before-20261121T081712Z` |
| ZIP size | 10,764,705 bytes | 9,334,843 bytes |
| ZIP SHA-256 | `7a2eec7738c972f4fba2706be5daa4c49781a59d04e6670362d2558e455f6a17` | `f38404aa04d631a8312a0570cb1a9584288ecbf1f6a0e0c26130125c444ad38d` |
| Run interval (UTC) | 2026-11-21 10:33:01–10:43:04 | 2026-11-21 08:17:12–08:26:51 |

Run 02 archive path: `docs/phase2/evidence/g2.5/2026-11-21/g25-before-20261121T103301Z-evidence.zip`.

The requested `BYTEME_PHASE2_FULL_ROADMAP_HANDOFF_2026-11-21.md` was not present in the workspace file inventory. The available G2.5 references inspected were `run-01/acceptance.md`, `G2.5.2-LOCAL-ACCEPTANCE.md`, `FINAL-RESET-RATE-LIMIT-REMEDIATION.md`, `VMRSS-REMEDIATION.md`, and the G2.5 sections in `docs/phase2/02_BASELINE_BENCHMARK.md`. The missing handoff was not inferred or reconstructed.

## 2. ZIP integrity, manifest, and provenance

- ZIP opens successfully; 63 entries; `ZipFile.testzip()` reports no CRC failure.
- `SHA256SUMS.txt` contains 62 file digests. All 62 were recomputed from archive bytes and match; there are no missing, mismatched, or unlisted payload entries (the checksum file does not checksum itself).
- `official-result.json`: `status=PASS`, `official_benchmark=true`, `requested_official_benchmark=true`, `profile=standard`, `classification=VALID_BASELINE_MEASUREMENT`, `error=null`.
- `official/protocol-validation.json`: `harness_valid=true`; official phase sequence is complete and in the locked order.
- Application/protocol baseline SHA: `510f6415b6af535ceec77213f0b0c7d5082123f7`.
- Repository SHA: `4418a8dd76192f6da3437968d9d8a31a4566e72b`.
- Application JAR SHA-256: `f802904a9a47cc14e8745dd7c39a1fb24b6219ef8be60be3805be4cf9af8cd98`. Run manifest, bundle manifest, and the bundle's application.jar entry agree. Run 01 carries the same application SHA, repository SHA, and JAR SHA.
- Configuration lock SHA-256: `e257ab3d71b73377d40cc85612e10f5e999ce8b55b00b3adff6075489a5fa2e1`.
- Workload source SHA-256: `c773850351f0cc5d337ba96a5fef5774a6871abf99aa1054a722ae528164397f`.
- Dataset logical SHA-256: `ce932b243cbfb16c34935ece3deb9f9e6479da34ab6828d93b2903f9538839b4`.
- The three lock hashes and all source/JAR provenance above match Run 01.

## 3. Protocol and workload evidence

There are 24 phase events (start and completion for each phase), with this complete order: `prepare_standard → warmup → w1 → post_w1 → reset_after_w1 → w2 → post_w2 → reset_after_w2 → w3 → post_w3 → cooldown → final_reset`. Warmup is marked excluded from official metrics. Durations and load match the standard lock: warmup 60 seconds; W1 and W2 180 seconds; W3 15 rounds per scenario; cooldown 30 seconds.

| Workload | Duration / volume | Errors and findings | Harness |
|---|---|---|---|
| W1 | 180,032 ms; 3,602 requests; 10/5/5 RPS | 0 failed checks; 0 HTTP/application errors; P95 42.63 ms, P99 49.28 ms; throughput 20.008 req/s | Valid |
| W2 | 180,066 ms; 82,726 requests; 10 VUs | 10 failed checks/business rejections (0.0121%); 0 server errors; P95 37.05 ms, P99 53.96 ms; throughput 459.422 req/s | Valid |
| W3 | 15 rounds in each of 3 scenarios | `admin_stock_vs_checkout`: non-serializable violations in rounds 4–15 (12/15); `same_cart_checkout`: server-error round 14; no violations in the other scenarios | Valid |

W2 rejections and W3 consistency/server-error findings are application outcomes. They are recorded by a valid harness and are not protocol or harness failures. Their counts need not match Run 01: Run 01 recorded 16 W2 business rejections and different W3 violation/error rounds. Those variations do not determine comparability or invalidate this run.

## 4. Dataset, telemetry, cleanup, and secrets

- Initial preparation, post-W1 reset, post-W2 reset, and final reset each report all invariants passing and the same logical SHA-256 `ce932b243cbfb16c34935ece3deb9f9e6479da34ab6828d93b2903f9538839b4`. `reset_matches_initial=true`; post-W1/W2/W3 consistency outcomes are all `CONSISTENT`.
- W1 and W2 each include 549 process-resource samples (183 each for backend, MySQL, and driver); W3 includes 18 (6 each). CPU/RSS completeness is true for all workloads. Process I/O is unavailable for 183 rows per W1/W2 and 6 W3 rows, recorded in the `resources.unavailable.jsonl` sidecars rather than represented as zero.
- JVM evidence includes `logs/gc.log` (171,091 bytes) and `logs/backend.log`. MySQL evidence includes its server log and before/after database telemetry snapshots for W1, W2, and W3, including connection, query, InnoDB, and Performance Schema data.
- Cleanup reports success; backend and MySQL stopped; runtime secret removed; no cleanup errors. The recorded secret scan has zero violations.
- `environment/backend-lifecycle.json` records the backend alive during the official cooldown sample. That sample is explicitly during cooldown; the later completed final-reset phase and successful final cleanup evidence show the expected shutdown. This is not a cleanup failure.

## 5. Run 01 comparison and verdict basis

The official comparator locks the following fields among others: CPU model, logical core count, exact total memory, OS/version/kernel/runtime image, cgroup limits, tool versions and executable hashes, configuration/workload/dataset locks. Run 02 matches Run 01 on all comparison and provenance fields except these hardware fields:

| Locked field | Run 01 | Run 02 | Result |
|---|---|---|---|
| `hardware.cpu_model` | AMD EPYC 7B12 | Intel(R) Xeon(R) CPU @ 2.20GHz | Mismatch |
| `hardware.memory_total_bytes` | 33,658,159,104 | 33,658,155,008 | Mismatch (4,096 bytes) |

Both runs report 4 logical cores, the same 4-core cgroup quota/cpuset, 32,212,254,720-byte memory limit, Ubuntu 24.04, kernel `6.18.55+`, runtime image identity `73b7688c…`, Java 21.0.13, MySQL 8.4.13, k6 0.55.2, and matching executable hashes and lock hashes. Those matches do not override the two exact hardware-field mismatches. P95, throughput, W2 error counts, and W3 findings vary as expected measurements and are not reasons for this verdict.

**Verdict: `INCOMPARABLE`.** The archive and protocol are valid, so this is not `REJECTED`. It cannot be accepted into Run 01's comparison group because the locked CPU model and exact memory differ. Exclude Run 02 from BEFORE baseline aggregation with Run 01.

## 6. Run 03 guidance

Run 03 execution may proceed. To enter Run 01's comparison group, its manifest must match Run 01's locked comparison fields, particularly CPU model `AMD EPYC 7B12` and exact `memory_total_bytes=33658159104`, along with the existing toolchain/configuration/workload/dataset locks. A valid Run 03 on another fingerprint would likewise be `INCOMPARABLE`. Do not include Run 02 in aggregation. This review does not run or authorize a benchmark rerun.

---

Independent review performed against the archived Run 02 and Run 01 evidence on 2026-11-21. Evidence ZIPs were read-only; no benchmark was rerun.

## Comparability policy recheck

The host-visible `hardware.memory_total_bytes` comparison now allows an absolute difference of at most 1 MiB. This accommodates small Linux `MemTotal` page/accounting variation while keeping the effective cgroup memory cap exact. Under this policy, the 4,096-byte Run 01/Run 02 difference is within tolerance. The CPU model mismatch (AMD EPYC 7B12 versus Intel Xeon) remains a hard comparison failure, so Run 02 remains **`INCOMPARABLE`** and excluded from Run 01 aggregation. The archived evidence and original run result were not changed.
