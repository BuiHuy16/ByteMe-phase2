# G2.5 Official Run 01 — Báo cáo Nghiệm thu

**Kết luận: ACCEPTED**

Nghiệm thu thực hiện ngày 2026-11-21 (15:58–16:03 ICT). Người thực hiện: Antigravity agent.  
Tình trạng trước: Codex đang tái tạo thuật toán hash, chưa kết luận ACCEPT.

---

## 1. Evidence Identity

| Thuộc tính | Giá trị |
|---|---|
| Evidence ZIP | `docs/phase2/evidence/g2.5/2026-11-21/g25-before-20261121T081712Z-evidence.zip` |
| ZIP size | 9 334 843 bytes |
| ZIP SHA-256 | `f38404aa04d631a8312a0570cb1a9584288ecbf1f6a0e0c26130125c444ad38d` |
| Run ID | `g25-before-20261121T081712Z` |
| Thời gian chạy | 2026-11-21T08:17:12Z → 08:26:51Z (UTC) |
| Total ZIP entries | 63 |

---

## 2. ZIP Integrity và SHA256SUMS

**PASS — 62/62 checksums xác minh OK, 0 lỗi.**

Tất cả 62 file trong `SHA256SUMS.txt` được tái tính SHA-256 từ dữ liệu thực tế trong ZIP và khớp hoàn toàn. Không có file bị thiếu, không có checksum không khớp.

> [!NOTE] SHA256SUMS.txt không tự liệt kê chính nó — đây là hành vi bình thường, 62/63 entries là đúng.

---

## 3. Source Baseline Verification

| Trường | Giá trị | Đúng? |
|---|---|---|
| `protocol_baseline_sha` (run-manifest) | `510f6415b6af535ceec77213f0b0c7d5082123f7` | ✅ |
| `application_sha` (run-manifest) | `510f6415b6af535ceec77213f0b0c7d5082123f7` | ✅ |
| `application_sha` (bundle-manifest) | `510f6415b6af535ceec77213f0b0c7d5082123f7` | ✅ |
| `repository_sha` (Phase 2 HEAD khi chạy) | `4418a8dd76192f6da3437968d9d8a31a4566e72b` | ✅ tồn tại trong git |
| Baseline SHA `510f641...` tồn tại trong git | True | ✅ |
| `application_sha` ≠ `repository_sha` | True (đúng: app = Pha 1, repo = Pha 2) | ✅ |

**PASS.** `application_sha = 510f6415b6af535ceec77213f0b0c7d5082123f7` khớp đúng với Baseline Pha 1 được khóa trong protocol.

---

## 4. JAR Provenance và Hash Discrepancy — Giải quyết

### 4a. Tình huống

- Evidence JAR SHA-256: `f802904a9a47cc14e8745dd7c39a1fb24b6219ef8be60be3805be4cf9af8cd98`
- G2.5.2-LOCAL doc JAR SHA-256: `8856c06b07b8f7b1dc2043db8039ea4759207ea92eb2c0f59fa32e603a9789a4`
- **Hai giá trị khác nhau.**

### 4b. Giải thích (xác nhận)

Hai SHA-256 này đến từ **hai Maven build riêng biệt của cùng commit `510f641...`**:
- Build trong G2.5.2-LOCAL session → JAR `8856c06b...`
- Build trong G2.5-official bundle (commit `4418a8d`) → JAR `f802904a...`

Maven JAR không byte-deterministic: timestamps metadata trong các entry ZIP của JAR thay đổi theo thời điểm build. G2.5.2-LOCAL doc đã xác nhận (đoạn cuối): "So sánh 278 ZIP entries cho thấy **0 content difference** và 87 timestamp metadata differences."

### 4c. Nhất quán nội bộ của evidence

| Kiểm tra | Kết quả |
|---|---|
| `run-manifest.application_jar_sha256` == `bundle-manifest.application_jar_sha256` | ✅ `f802904a...` cả hai |
| `bundle-manifest.json` SHA-256 trong ZIP == SHA256SUMS entry | ✅ `3f88938b...` khớp |
| `build/build-provenance.json` được liệt kê trong bundle files | ✅ |
| `application_sha` nhất quán qua tất cả fields | ✅ `510f641...` |

**PASS.** JAR hash nhất quán nội bộ trong evidence run này. Khác biệt với G2.5.2-LOCAL là do Maven build non-determinism (archive metadata), không phải source drift. Mỗi run tham chiếu đúng JAR của bundle của nó.

---

## 5. Toolchain Verification

| Thành phần | Phiên bản | SHA-256 executable |
|---|---|---|
| Java | OpenJDK 21.0.13 (Temurin-21.0.13+9) | `7afc2880...` |
| MySQL | 8.4.13 (Linux x86_64, GPL) | `e48e2b50...` (mysqld) |
| k6 | v0.55.2 (go1.23.4, linux/amd64) | `df3ede49...` |
| libaio | 0.3.113-6build1.1 (amd64) | `9dbba744...` (ELF) |
| libaio package SHA-256 | `433212b3...` | ✅ khớp lock |

Tất cả phiên bản khớp `configuration-lock.json` (sha256 `e257ab3d...` khớp cả local và evidence).

---

## 6. Configuration Lock Verification

| Trường | Giá trị |
|---|---|
| `configuration_sha256` (run-manifest) | `e257ab3d71b73377d40cc85612e10f5e999ce8b55b00b3adff6075489a5fa2e1` |
| SHA-256 của local `configuration-lock.json` | `e257ab3d71b73377d40cc85612e10f5e999ce8b55b00b3adff6075489a5fa2e1` |
| `workload_source_sha256` | `c773850351f0cc5d337ba96a5fef5774a6871abf99aa1054a722ae528164397f` |

**PASS.** Configuration lock khớp local.

---

## 7. Protocol Validation

| Tiêu chí | Giá trị |
|---|---|
| `requested_official_benchmark` | `true` |
| `official_benchmark` | `true` |
| `profile` | `standard` |
| `classification` | `VALID_BASELINE_MEASUREMENT` |
| `harness_valid` | `true` |
| `status` | `PASS` |

**Phase order** (đúng theo protocol):
```
prepare_standard → warmup → w1 → post_w1 → reset_after_w1 →
w2 → post_w2 → reset_after_w2 → w3 → post_w3 → cooldown (30s) → final_reset
```

24 phase events được ghi, timestamps liên tục từ 08:18:34Z đến 08:26:50Z.

**Warmup:** 242 requests, 0 checks failed, bị loại khỏi official metrics (`warmup_excluded_from_official_metrics = true`).

---

## 8. W1 — Read Workload

**Outcome: `COMPLETED_WITHOUT_OBSERVED_ERRORS`**

| Metric | Giá trị |
|---|---|
| Duration | 180 027 ms (đúng 180s) |
| Load | 10/5/5 RPS (food list/search/order list), page size 20 |
| Total requests | 3 602 |
| Checks passed | 3 602 / 3 602 (100%) |
| Checks failed | 0 |
| HTTP failure rate | 0 |
| Application error rate | 0 |
| Unexpected responses | 0 |
| **P50 latency** | **19.69 ms** |
| **P95 latency** | **29.73 ms** |
| **P99 latency** | **33.65 ms** |
| Max latency | 49.40 ms |
| Data received | 1 611 MB |
| Resource telemetry | 549 rows, 183 rows/label (backend/mysql/driver) |

**PASS.** W1 không có lỗi nào.

---

## 9. W2 — Write Workload

**Outcome: `HTTP_OR_PERFORMANCE_FAILURE` (baseline defect, không phải harness failure)**

| Metric | Giá trị |
|---|---|
| Duration | 180 075 ms (đúng 180s) |
| Load | 10 VUs |
| Total requests | 73 496 |
| Checks passed | 73 480 / 73 496 (99.978%) |
| Checks failed | 16 |
| HTTP failure rate | 0.000218 (0.022%) |
| Unexpected responses | 16 |
| Business rejections | 16 |
| Server errors | 0 |
| **P50 latency** | **23.05 ms** |
| **P95 latency** | **35.68 ms** |
| **P99 latency** | **48.29 ms** |
| Max latency | 418.01 ms |
| Resource telemetry | 549 rows, 183 rows/label (backend/mysql/driver) |

> [!NOTE] 16 request thất bại (0.022%) được phân loại là `business_rejections` — application defect được đo làm baseline evidence. `harness_valid = true`. Điều này không phải harness failure và không ảnh hưởng đến kết luận ACCEPT.

---

## 10. W3 — Contention Workload

**Outcome: `harness_valid = true` (violations là baseline defects)**

| Scenario | Violation rounds | Server error rounds |
|---|---|---|
| `same_food_checkout` | [9] | [] |
| `same_cart_checkout` | [] | [15] |
| `admin_stock_vs_checkout` | [4, 6, 7, 9, 11, 13, 14, 15] | [] |

Tổng: 15 rounds/scenario, 45 rounds tổng cộng. Harness ghi đầy đủ `before`, `responses`, `after`, `violations` cho mỗi round.

**Violation type:** `NON_SERIALIZABLE_FINAL_STOCK` trong `admin_stock_vs_checkout` — stock sau concurrent checkout không khớp bất kỳ serial order nào. Đây là baseline defect của ứng dụng Pha 1.

**same_cart_checkout round 15:** server error (HTTP 5xx), được ghi đúng và không làm harness fail.

**Resource telemetry:** 18 rows, 6 rows/label — đủ minimum.

**PASS harness.** Violations là baseline evidence theo đúng protocol.

---

## 11. Dataset Resets và Final Reset

| Checkpoint | SHA-256 | Phase | all_invariants_pass |
|---|---|---|---|
| Initial | `ce932b24...` | `initial` | `true` |
| After reset W1 | `ce932b24...` | `initial` | `true` |
| After reset W2 | `ce932b24...` | `initial` | `true` |
| After final reset | `ce932b24...` | `initial` | `true` |

**4/4 resets có cùng SHA-256 `ce932b243cbfb16c34935ece3deb9f9e6479da34ab6828d93b2903f9538839b4`.**

`reset_matches_initial = true`. `locks.dataset_sha256 = ce932b24...` khớp.

**PASS.**

---

## 12. Cleanup và Secret Scan

| Tiêu chí | Kết quả |
|---|---|
| `cleanup.success` | `true` |
| backend stopped | `true` |
| mysql stopped | `true` |
| runtime_secret_removed | `true` |
| cleanup errors | `[]` |
| `secret_scan_violations` | `[]` |

**PASS.** Không có secret leak.

---

## 13. Hardware và Runtime

| Thuộc tính | Giá trị |
|---|---|
| CPU | AMD EPYC 7B12 |
| Logical cores | 4 (cgroup quota 4.0 cores, cpuset 0-3) |
| RAM | 32 212 254 720 bytes (~30 GB, limit 32212254720) |
| OS | Ubuntu 24.04 |
| Kernel | 6.18.55+ |
| Python | 3.13.18 |
| `is_kaggle` | `true` |
| `quota_evidence_complete` | `true` |
| Chạy dưới root (uid=0) | `true` |

---

## 14. Findings và Limitations

### Findings (không ảnh hưởng ACCEPT)

1. **W2 HTTP failures (16 requests, 0.022%):** Application defect được đo làm baseline. Protocol phân loại đúng là `HTTP_OR_PERFORMANCE_FAILURE`, không phải harness failure.

2. **W3 `admin_stock_vs_checkout` 8/15 violation rounds:** `NON_SERIALIZABLE_FINAL_STOCK` liên tục. Đây là race condition trong checkout logic Pha 1 — baseline defect được ghi nhận.

3. **W3 `same_cart_checkout` server error round 15:** HTTP 5xx được ghi nhận và không làm harness fail.

4. **JAR SHA mismatch với G2.5.2-LOCAL doc:** Giải thích hoàn toàn bởi Maven build non-determinism (timestamp metadata). Không phải source drift. Evidence run nhất quán nội bộ.

5. **`phase-events.json` có `outcome: null`:** Các events được ghi là pair start/end theo timestamp; `outcome` null trong event entries là bình thường (outcome được aggregate trong `protocol-validation.json`).

### Limitations

- **Không thể chạy lại Kaggle runtime** để xác minh độc lập.
- **I/O telemetry không khả dụng** (`io_unavailable_rows` = 183 cho W1/W2, 6 cho W3): `/proc/<pid>/io` trên Kaggle bị giới hạn. CPU và RSS telemetry đầy đủ.
- **Chỉ 1 official run** — multi-run comparability (G2.5.4) chưa thực hiện.
- **`outcome` field trong phase events là `null`:** Đây là behavior của implementation hiện tại, không ảnh hưởng đến protocol validation.

---

## 15. Kết luận

**RUN 01: ACCEPTED**

Tất cả acceptance gates đã được xác minh:

| Gate | Kết quả |
|---|---|
| ZIP integrity | ✅ PASS |
| SHA256SUMS (62/62) | ✅ PASS |
| Source baseline SHA `510f641...` | ✅ PASS |
| JAR provenance nhất quán nội bộ | ✅ PASS (mismatch với G2.5.2-LOCAL giải thích được) |
| Configuration lock SHA | ✅ PASS |
| Toolchain versions locked | ✅ PASS |
| `requested_official_benchmark = true` | ✅ PASS |
| `official_benchmark = true` | ✅ PASS |
| `harness_valid = true` | ✅ PASS |
| Phase order đúng | ✅ PASS |
| W1 COMPLETED_WITHOUT_ERRORS | ✅ PASS |
| W2 HTTP failures là baseline (not harness) | ✅ PASS |
| W3 violations là baseline (not harness) | ✅ PASS |
| Dataset: 4/4 resets SHA-256 khớp initial | ✅ PASS |
| Cleanup success | ✅ PASS |
| Secret scan 0 violations | ✅ PASS |
| `classification = VALID_BASELINE_MEASUREMENT` | ✅ PASS |

Evidence này là **Valid Baseline Measurement** của ứng dụng ByteMe Pha 1 trên Kaggle CPU (AMD EPYC 7B12, 4 cores, ~30 GB RAM, Ubuntu 24.04).

---

*Báo cáo tạo bởi: Antigravity (Claude Sonnet 4.6 Thinking), 2026-11-21T16:03 ICT*  
*Evidence ZIP không bị thay đổi. Báo cáo này không tạo ra kết quả mới hay thay đổi evidence.*
