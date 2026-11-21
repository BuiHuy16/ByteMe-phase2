# G2.5 Official BEFORE Run 05 — Independent Acceptance and Group Evaluation

**Verdict: `ACCEPTED` within the Intel comparison group**  
**Comparable with Run 02: Yes**  
**Comparable with Run 04: Yes**  
**Comparable with Run 01 / Run 03 (AMD group): No**

Run 05 is valid official evidence and matches Runs 02 and 04 across the full current comparator key. The only mismatch when compared with Runs 01 and 03 is CPU model: Intel Xeon versus AMD EPYC 7B12. Keep the two hardware groups separate.

## 1. Evidence identity and integrity

| Property | Run 05 | Run 02 | Run 04 |
|---|---|---|---|
| Evidence ZIP | `g25-before-20261121T151926Z-evidence.zip` | `g25-before-20261121T103301Z-evidence.zip` | `g25-before-20261121T145826Z-evidence.zip` |
| Run ID | `g25-before-20261121T151926Z` | `g25-before-20261121T103301Z` | `g25-before-20261121T145826Z` |
| ZIP size | 9,111,998 bytes | 10,764,705 bytes | 8,336,089 bytes |
| ZIP SHA-256 | `c2925ebc19f8d23dd242cdc12d8f2922631739dacf569b23b859ae1c9c0222cf` | `7a2eec7738c972f4fba2706be5daa4c49781a59d04e6670362d2558e455f6a17` | `9379e5661e7fd292230f4abec109b8f29b5034fbb0c1e092b8f7e9d0b0a7a51f` |
| Run interval (UTC) | 2026-11-21 15:19:26–15:29:38 | 2026-11-21 10:33:01–10:43:04 | 2026-11-21 14:58:26–15:08:49 |

Run 05 archive path: `docs/phase2/evidence/g2.5/2026-11-21/g25-before-20261121T151926Z-evidence.zip`.

- ZIP has 63 entries; CRC validation passed (`testzip()` returned no bad entry).
- `SHA256SUMS.txt` lists 62 payload digests. All 62 were recomputed from the archive and matched. No payload entry is missing, mismatched, or unlisted; the checksum file does not checksum itself.

## 2. Official status, protocol, and provenance

`official-result.json` reports `status=PASS`, `official_benchmark=true`, `requested_official_benchmark=true`, `profile=standard`, `classification=VALID_BASELINE_MEASUREMENT`, and `error=null`. `official/protocol-validation.json` reports `harness_valid=true`.

The archive contains all 24 start/completion phase events in the locked sequence: `prepare_standard → warmup → w1 → post_w1 → reset_after_w1 → w2 → post_w2 → reset_after_w2 → w3 → post_w3 → cooldown → final_reset`. Warmup is excluded from official metrics; W1/W2 are approximately 180 seconds, W3 runs 15 rounds per scenario, and cooldown is 30 seconds. Post-W1, post-W2, and post-W3 consistency outcomes are all `CONSISTENT`.

| Provenance or lock | Run 05 value | Run 01–04 comparison |
|---|---|---|
| Application / protocol baseline SHA | `510f6415b6af535ceec77213f0b0c7d5082123f7` | Matches all |
| Repository SHA | `4418a8dd76192f6da3437968d9d8a31a4566e72b` | Matches all |
| Application JAR SHA-256 | `f802904a9a47cc14e8745dd7c39a1fb24b6219ef8be60be3805be4cf9af8cd98` | Matches; run and bundle manifests agree |
| Configuration lock SHA-256 | `e257ab3d71b73377d40cc85612e10f5e999ce8b55b00b3adff6075489a5fa2e1` | Matches all |
| Workload source SHA-256 | `c773850351f0cc5d337ba96a5fef5774a6871abf99aa1054a722ae528164397f` | Matches all |
| Dataset logical SHA-256 | `ce932b243cbfb16c34935ece3deb9f9e6479da34ab6828d93b2903f9538839b4` | Matches all |

Java is OpenJDK 21.0.13, MySQL 8.4.13, and k6 0.55.2. Executable/package hashes for Java, MySQL/mysqld, k6, and libaio match the other official runs. The current comparator strips only the run-specific executable path prefix from the MySQL version output; version text and executable hash stay locked.

## 3. Workload results and findings

| Workload | Measured result | Validation / interpretation |
|---|---|---|
| W1 | 180,018 ms; 3,602 requests and checks passed; 0 failed; HTTP/application error rate 0; P95 47.77 ms, P99 54.69 ms; 20.009 req/s | `COMPLETED_WITHOUT_OBSERVED_ERRORS`; harness valid |
| W2 | 180,095 ms; 68,928 requests; 68,924 checks passed, 4 failed; HTTP/application error rate 0.0000580 (0.0058%); 4 business rejections; 0 server errors; P95 42.62 ms, P99 61.04 ms; 382.732 req/s | `HTTP_OR_PERFORMANCE_FAILURE`; harness valid. Rejections are application outcomes. |
| W3 | 15 rounds per scenario; `NON_SERIALIZABLE_FINAL_STOCK` in `admin_stock_vs_checkout` rounds 3–15 (13/15); no violations in `same_food_checkout` or `same_cart_checkout`; no server-error rounds | `harness_valid=true`; recorded concurrency invariant defects are application findings, not harness failure. |

The W2 rejections and W3 findings do not invalidate Run 05. Latency, throughput, rejection count, and violation rounds may vary across runs and are not comparator fields.

## 4. Dataset, telemetry, cleanup, and secret scan

- Initial preparation, reset after W1, reset after W2, and final reset each report `all_invariants_pass=true` and logical SHA-256 `ce932b243cbfb16c34935ece3deb9f9e6479da34ab6828d93b2903f9538839b4`. `reset_matches_initial=true`; all four checkpoint hashes match.
- Initial dataset counts are 26 users, 10 categories, 5,021 foods, 500 orders, 1,000 order items, and empty carts/cart items; standard profile parameters match the lock.
- CPU/RSS telemetry is complete: warmup 189 samples (63 per backend/MySQL/driver); W1 and W2 549 each (183 per label); W3 21 (7 per label). Process I/O unavailability is recorded in sidecars (63 warmup, 183 per W1/W2, 7 W3), not as zero.
- JVM evidence includes `logs/gc.log` (154,533 bytes) and `logs/backend.log`; MySQL evidence includes `logs/mysql-server/mysql.log` and before/after database telemetry snapshots for W1, W2, and W3.
- Cleanup reports success; backend and MySQL stopped; runtime secret removed; no cleanup errors. `secret_scan_violations=[]`.
- Backend lifecycle was sampled while alive during official cooldown. The final-reset phase completed afterward and cleanup confirms the backend stopped; the cooldown sample is not a cleanup failure.

## 5. Comparator results and hardware groups

The updated `compare_manifests.py` was applied to archived manifests. Each pairwise comparison returned `comparable=true` with no mismatches within the two groups:

| Comparison | Result | Comparator mismatches |
|---|---|---|
| Run 01 ↔ Run 03 | Comparable (AMD) | None |
| Run 02 ↔ Run 04 | Comparable (Intel) | None |
| Run 02 ↔ Run 05 | Comparable (Intel) | None |
| Run 04 ↔ Run 05 | Comparable (Intel) | None |
| Run 01 ↔ Run 05 | Incomparable | `hardware.cpu_model`: AMD EPYC 7B12 vs Intel Xeon |
| Run 03 ↔ Run 05 | Incomparable | `hardware.cpu_model`: AMD EPYC 7B12 vs Intel Xeon |

Run 05's comparison fingerprint is:

| Field | Intel Runs 02/04/05 | AMD Runs 01/03 | Run 05 group result |
|---|---|---|---|
| CPU model | Intel(R) Xeon(R) CPU @ 2.20GHz | AMD EPYC 7B12 | Matches Intel; CPU model mismatch with AMD |
| Logical cores | 4 | 4 | Match |
| CPU quota / period | `400000 100000` (4.0 cores) | Same | Match |
| Effective cpuset | `0-3` (4 CPUs) | Same | Match |
| `memory_total_bytes` | Run 02/05: 33,658,155,008; Run 04: 33,658,159,104 | Runs 01/03: 33,658,159,104 | All pairwise differences are ≤4,096 bytes, within the 1 MiB tolerance |
| Cgroup memory limit / resolved limit | 32,212,254,720 bytes | Same | Exact match |
| OS / kernel / runtime image | Ubuntu 24.04 / `6.18.55+` / `73b7688c…` | Same | Match |
| Toolchain and benchmark locks | Same versions, hashes, and lock SHA values | Same | Match |

The CPU model mismatch is substantive; matching core count and quotas do not make AMD and Intel comparable. The `MemTotal` differences are within policy tolerance and do not cause a mismatch. Run 02 and Run 04 were previously classified `INCOMPARABLE` relative to the AMD group; this pairwise recheck confirms they are mutually comparable and Run 05 joins their Intel group.

## 6. Verdict and BEFORE group decision

**Run 05 is `ACCEPTED` as a valid official measurement in the Intel comparison group.** It is not comparable with the AMD group and must not be combined with Runs 01 or 03.

- AMD group: Runs 01 and 03 — **2 comparable valid runs**, below the minimum of 3.
- Intel group: Runs 02, 04, and 05 — **3 comparable valid runs**, meeting `minimum_runs=3` (the configuration target remains 5).

The Intel group can serve as the official BEFORE baseline if that hardware group is formally selected and AFTER runs use comparator-compatible Intel hardware: same CPU model, cores/quota/cpuset, cgroup memory limit, OS/kernel/runtime image, toolchain and benchmark locks. Do not mix AMD BEFORE values into an Intel aggregate or compare AFTER results from AMD. Three separate Intel official sessions in the available evidence show this group has been obtainable on Kaggle, but they do not guarantee future scheduling; run a hardware preflight before starting each AFTER benchmark. If the AFTER hardware is AMD or otherwise mismatched, that run is outside this comparison group.

The minimum three-run gate for G2.5 Multi-run Aggregation is now met **for the Intel group**. Aggregation may proceed using Runs 02/04/05 only, with `n=3` disclosed; the target of five has not been reached. No aggregator was implemented as part of this acceptance.

---

Independent acceptance based on archived Run 05 evidence and pairwise comparator checks against Runs 01–04. Evidence ZIPs were read-only; no benchmark was rerun.
