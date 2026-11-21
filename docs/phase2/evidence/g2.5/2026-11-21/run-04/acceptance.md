# G2.5 Official BEFORE Run 04 — Independent Acceptance

**Verdict: `INCOMPARABLE`**  
**Comparison with Run 01: `INCOMPARABLE`**  
**Comparison with Run 03: `INCOMPARABLE`**

Run 04 is internally valid official benchmark evidence, but its CPU model is Intel Xeon rather than the AMD EPYC 7B12 used by Runs 01 and 03. The current comparator reports this as the only mismatch against either reference. Keep the run as valid evidence, but exclude it from the AMD comparison group and aggregation.

## 1. Evidence identity and integrity

| Property | Run 04 | Run 01 | Run 03 |
|---|---|---|---|
| Evidence ZIP | `g25-before-20261121T145826Z-evidence.zip` | `g25-before-20261121T081712Z-evidence.zip` | `g25-before-20261121T144102Z-evidence.zip` |
| Run ID | `g25-before-20261121T145826Z` | `g25-before-20261121T081712Z` | `g25-before-20261121T144102Z` |
| ZIP size | 8,336,089 bytes | 9,334,843 bytes | 10,411,901 bytes |
| ZIP SHA-256 | `9379e5661e7fd292230f4abec109b8f29b5034fbb0c1e092b8f7e9d0b0a7a51f` | `f38404aa04d631a8312a0570cb1a9584288ecbf1f6a0e0c26130125c444ad38d` | `ed49c58fe9585661d1187385550db18292d5f1e69363194dec9b043f177fad77` |
| Run interval (UTC) | 2026-11-21 14:58:26–15:08:49 | 2026-11-21 08:17:12–08:26:51 | 2026-11-21 14:41:02–14:50:41 |

Run 04 archive path: `docs/phase2/evidence/g2.5/2026-11-21/g25-before-20261121T145826Z-evidence.zip`.

- ZIP has 63 entries; CRC validation passed (`testzip()` returned no bad entry).
- `SHA256SUMS.txt` contains 62 payload digests. All 62 were recomputed and matched. No payload file is missing, mismatched, or unlisted; the checksum file does not checksum itself.

## 2. Official status, protocol, and provenance

`official-result.json` reports `status=PASS`, `official_benchmark=true`, `requested_official_benchmark=true`, `profile=standard`, `classification=VALID_BASELINE_MEASUREMENT`, and `error=null`. The protocol validator reports `harness_valid=true`.

There are 24 phase events, in the complete locked order: `prepare_standard → warmup → w1 → post_w1 → reset_after_w1 → w2 → post_w2 → reset_after_w2 → w3 → post_w3 → cooldown → final_reset`. Warmup is excluded from official metrics. W1/W2 durations are approximately 180 seconds, W3 has 15 rounds per scenario, and cooldown is 30 seconds.

| Provenance or lock | Run 04 value | Comparison with Runs 01/03 |
|---|---|---|
| Application / protocol baseline SHA | `510f6415b6af535ceec77213f0b0c7d5082123f7` | Match |
| Repository SHA | `4418a8dd76192f6da3437968d9d8a31a4566e72b` | Match |
| Application JAR SHA-256 | `f802904a9a47cc14e8745dd7c39a1fb24b6219ef8be60be3805be4cf9af8cd98` | Match; run and bundle manifests agree |
| Configuration lock SHA-256 | `e257ab3d71b73377d40cc85612e10f5e999ce8b55b00b3adff6075489a5fa2e1` | Match |
| Workload source SHA-256 | `c773850351f0cc5d337ba96a5fef5774a6871abf99aa1054a722ae528164397f` | Match |
| Dataset logical SHA-256 | `ce932b243cbfb16c34935ece3deb9f9e6479da34ab6828d93b2903f9538839b4` | Match |

Java 21.0.13, MySQL 8.4.13, k6 0.55.2, and libaio versions and executable/package hashes match. The current comparator removes only the run-specific executable path prefix from MySQL's version output; version text and `mysqld` binary hash remain comparison requirements.

## 3. Workload results and application findings

| Workload | Measured result | Validation / interpretation |
|---|---|---|
| W1 | 180,045 ms; 3,603 requests; 3,603 checks passed; 0 failed; HTTP/application error rate 0; P95 50.00 ms, P99 56.56 ms; 20.012 req/s | `COMPLETED_WITHOUT_OBSERVED_ERRORS`; harness valid |
| W2 | 180,098 ms; 62,443 requests; 62,428 checks passed, 15 failed; HTTP/application error rate 0.0002402 (0.0240%); 15 business rejections; 0 server errors; P95 46.45 ms, P99 64.87 ms; 346.717 req/s | `HTTP_OR_PERFORMANCE_FAILURE`; harness valid. The rejections are application outcomes, not harness failure. |
| W3 | 15 rounds each for `same_food_checkout`, `same_cart_checkout`, and `admin_stock_vs_checkout`; `NON_SERIALIZABLE_FINAL_STOCK` in `admin_stock_vs_checkout` rounds 3–14 (12/15); no server-error rounds | `harness_valid=true`; round evidence is recorded. Invariant violations are baseline application findings, not harness failure. |

W1/W2 latency and throughput, W2 rejection count, and W3 concurrency findings vary from other runs. Those metric/application outcome differences are not grounds for rejection or hardware classification.

## 4. Dataset, telemetry, cleanup, and secrets

- Initial dataset, reset after W1, reset after W2, and final reset all report `all_invariants_pass=true` and logical SHA-256 `ce932b243cbfb16c34935ece3deb9f9e6479da34ab6828d93b2903f9538839b4`. `reset_matches_initial=true`; consistency outcomes after W1/W2/W3 are all `CONSISTENT`.
- Initial cardinalities are 26 users, 10 categories, 5,021 foods, 500 orders, 1,000 order items, and empty carts/cart items; standard profile parameters match the locks.
- CPU/RSS telemetry is complete: W1 and W2 each have 549 samples (183 each for backend/MySQL/driver); W3 has 21 samples (7 each); warmup has 189 samples (63 each). I/O unavailability is recorded in sidecars (183 rows each for W1/W2 and 7 for W3), not as zero.
- JVM evidence includes `logs/gc.log` (147,653 bytes) and `logs/backend.log`; MySQL evidence includes `logs/mysql-server/mysql.log` and before/after database telemetry snapshots for W1, W2, and W3.
- Cleanup reports success; backend and MySQL stopped; runtime secret removed; no cleanup errors. `secret_scan_violations=[]`.
- Backend lifecycle is sampled during cooldown while the backend is alive; the later final-reset phase completed and final cleanup reports it stopped. This is not a cleanup failure.

## 5. Hardware comparability

Run 04 matches Runs 01 and 03 on all comparator fields except `hardware.cpu_model`:

| Field | Runs 01/03 | Run 04 | Result |
|---|---|---|---|
| CPU model | AMD EPYC 7B12 | Intel(R) Xeon(R) CPU @ 2.20GHz | **Mismatch** |
| Logical cores | 4 | 4 | Match |
| CPU quota / period | `400000 100000` (4.0 cores) | `400000 100000` (4.0 cores) | Match |
| Effective cpuset | `0-3` (4 CPUs) | `0-3` (4 CPUs) | Match |
| `memory_total_bytes` | 33,658,159,104 | 33,658,159,104 | Match; 0-byte delta, within 1 MiB tolerance |
| Cgroup memory limit / resolved limit | 32,212,254,720 bytes | 32,212,254,720 bytes | Exact match |
| OS / kernel | Ubuntu 24.04 / `6.18.55+` | Ubuntu 24.04 / `6.18.55+` | Match |
| Runtime image identity | `73b7688c6b0298bb811a52b1b22d66eac3bb3fdc7f0da53b3ac4b46db031c2ec` | Same | Match |
| Toolchain and benchmark locks | Same | Same | Match |

The updated `compare_manifests.py` was applied to Run 04 against Run 01 and Run 03 separately. Both results are `comparable=false`; the sole mismatch in each is the CPU model. The 1 MiB `MemTotal` tolerance is satisfied and does not override the CPU model gate.

## 6. Verdict and aggregation status

**Run 04 verdict: `INCOMPARABLE`.** The archive, official-run gates, protocol, workload structure, reset, telemetry, cleanup, and secret scan are valid. The hardware differs from the AMD comparison group, so Run 04 cannot be `ACCEPTED` into that group. This is not a harness rejection.

The AMD group remains at **2 accepted comparable runs out of the minimum 3**: Run 01 and Run 03. Run 02 and Run 04 are both excluded due to Intel Xeon hardware. **Do not proceed to G2.5 Multi-run Aggregation yet.** The minimum three-run AMD comparison group has not been reached.

---

Independent review of archived Run 04 evidence against Runs 01 and 03. Evidence ZIPs were read-only; no benchmark was rerun.
