# ByteMe Phase 2 — Baseline & Benchmark

## G2.1 — Phase 1 Verification

Ngày xác minh: **2026-11-19** (`Asia/Saigon`, UTC+07:00).

### 1. Objective & Scope

G2.1 xác minh provenance của source ứng viên Phase 1, khả năng sử dụng toolchain Java/Maven/Docker và kết quả regression chính thức trước khi đo benchmark hoặc triển khai cải tiến kiến trúc Phase 2.

Phạm vi phiên này chỉ gồm Git read-only, kiểm tra môi trường, chạy JUnit được môi trường cho phép và lưu evidence dạng text/XML. Không checkout/reset/commit/tag, không sửa application source/test/schema/configuration, không dùng database shared, không chạy benchmark, black-box stack hay G2.2.

### 2. Git Fork/Upstream Provenance

| Hạng mục | Kết quả | Trạng thái |
|---|---|---|
| Repository | `D:/projects/main projects/ByteMe-phase2` | **PASS** |
| Branch hiện tại | `main` | **PASS** |
| Full HEAD | `510f6415b6af535ceec77213f0b0c7d5082123f7` | **PASS** |
| Commit HEAD | `docs: viết lại README súc tích, loại bỏ văn phong AI slop`; parent `5a7bf4004abad672b92b7be1e3d83e8d19e81470` | **PASS** |
| Remote đã cấu hình | Chỉ có `origin = https://github.com/BuiHuy16/ByteMe-phase2.git` cho fetch/push | **PASS** cho inventory |
| Original upstream remote/source | Không có remote/ref riêng để xác định repository nguồn ban đầu của fork | **BLOCKED/PENDING** |
| Repository depth | Không phải shallow clone | **PASS** |
| Tags | Không có tag | **PASS** cho inventory |

Không suy đoán original upstream từ tên `origin`: URL đã được kiểm tra nhưng repository không cấu hình `upstream`, nên upstream URL/SHA gốc chưa thể chứng minh bằng Git metadata hiện có.

Trước khi G2.1 tạo evidence, working tree không có tracked modification hoặc staged change; toàn bộ thay đổi là thư mục `docs/phase2/` untracked đã tồn tại từ Giai đoạn 0–1. Trong phiên này chỉ bổ sung file báo cáo/evidence dưới chính thư mục đó. Không có application source, test, schema, POM hay runtime configuration nào bị sửa.

### 3. Baseline Candidate

`phase1-baseline`, `main`, `master` và `origin/master` cùng trỏ tới:

`510f6415b6af535ceec77213f0b0c7d5082123f7`

Commit yêu cầu kiểm tra `510f6415b6af535ceec77213f0b0c7d5082123f7` tồn tại, là `HEAD`, và vì hai SHA bằng nhau nên quan hệ ancestry đúng theo cả hai chiều. Không có commit hoặc committed-path drift giữa current HEAD và branch `phase1-baseline`; do đó **không có source/config drift giữa hai mốc này**.

Phân loại lịch sử gần candidate:

- `510f641…`: chỉ thay `README.md`.
- `5a7bf40…`: chỉ thay `docs/architecture-single-restaurant.md`.
- `1ee1cbf…`: thay đổi kiến trúc source/test đáng kể, di chuyển 67 file từ package-by-feature sang package-by-layer và sửa import/rule test; commit message là `refactor(arch): tái cấu trúc mã nguồn sang package-by-layer theo tầng nhiệm vụ`.

Vì vậy candidate hiện tại **có chứa một architectural refactor** so với parent `cfe2222…`. Tài liệu Giai đoạn 0–1 đang coi tree này là Phase 1 As-Is, nhưng Git không có immutable marker trước Phase 2 và không có upstream ref để chứng minh `1ee1cbf…` thuộc Phase 1 hay là cải tiến Phase 2. Phân loại “candidate chưa chứa cải tiến kiến trúc Phase 2” vì thế là **PENDING**, không được khẳng định chỉ từ tên branch.

Đề xuất freeze, chưa thực hiện:

1. Nhóm xác nhận bằng provenance ngoài Git hiện có rằng `1ee1cbf…` thuộc phạm vi Phase 1.
2. Sau khi 32 Testcontainers methods và full 90-test suite có kết quả chính thức đạt policy, tạo annotated tag `phase1-baseline-verified` tại full SHA `510f6415b6af535ceec77213f0b0c7d5082123f7`.
3. Nếu `1ee1cbf…` thực chất là treatment Phase 2, không tag `510f641…` làm Phase 1 baseline; cần xác định commit pre-treatment đúng và chạy lại toàn bộ G2.1 trên SHA đó.

### 4. Environment Manifest

| Thành phần | Kết quả quan sát | Trạng thái |
|---|---|---|
| Thời gian | `2026-11-19T10:40:09+07:00`; Windows timezone `SE Asia Standard Time` | **PASS** |
| OS | Microsoft Windows 11 Home Single Language `10.0.26200`, build `26200`, x64 | **PASS** |
| Host | Micro-Star International `Thin 15 B12UCX` | **PASS** |
| CPU | 12th Gen Intel Core i5-12450H; 8 cores / 12 logical processors | **PASS** |
| RAM lúc capture | 16,869,146,624 bytes total (~15.71 GiB); 3,529,170,944 bytes free (~3.29 GiB) | **PASS** |
| Java | Oracle Java `21.0.12` LTS, HotSpot 64-bit, `amd64` | **PASS** |
| Maven Wrapper | Wrapper `3.3.4`; Apache Maven `3.9.11`; UTF-8; chạy bằng Java `21.0.12` | **PASS** |
| Docker CLI | `29.9.1`, API `1.56` | **PASS** cho client |
| Docker Compose | `v5.6.0` | **PASS** cho client |
| Docker context | `desktop-linux` | **PASS** cho inventory |
| Docker daemon/Desktop | Không có pipe `//./pipe/dockerDesktopLinuxEngine`; không có Docker Desktop/backend/dockerd process hoặc service được phát hiện | **BLOCKED** |
| MySQL Testcontainers image | Không thể inspect/pull/resolve `mysql:8.4` qua daemon | **BLOCKED** |
| Testcontainers prerequisites | Java/Maven usable; Docker daemon không usable, nên ba test class MySQL không thể chạy | **BLOCKED** |

Maven Wrapper ban đầu không thể tải distribution trong sandbox. Lần chạy chính thức dùng cache tạm writable và quyền network được phê duyệt; không thay `.mvn/wrapper/maven-wrapper.properties`, `pom.xml` hoặc source. Không thu thập hay ghi password, token, private key hoặc secret environment values.

### 5. Test Execution Matrix

| Run | Command | Expected | Exit | Executed | Passed | Failed | Errors | Skipped | Duration | Trạng thái |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A — Non-Docker | `.\mvnw.cmd test "-Dtest=!*IntegrationTest,!DatabaseDesignTests"` | 58 | `0` | 58 | 58 | 0 | 0 | 0 | Maven 14.020 s; XML suite sum 7.339 s | **PASS** |
| B — Integration/DB | `.\mvnw.cmd test "-Dtest=AuthIntegrationTest,OrderIntegrationTest,DatabaseDesignTests"` | 32 | N/A | 0 | N/A | N/A | N/A | N/A | N/A | **BLOCKED — Docker daemon unavailable; command not run** |
| C — Full suite | `.\mvnw.cmd test` | 90 | N/A | 0 | N/A | N/A | N/A | N/A | N/A | **BLOCKED — cannot execute complete suite without Docker; command not run** |

Test discovery/configuration evidence:

- POM không cấu hình Surefire riêng; Spring Boot parent resolve `maven-surefire-plugin 3.5.6`.
- Official run auto-detect `org.apache.maven.surefire.junitplatform.JUnitPlatformProvider`.
- Run A discover đúng 9 test classes và 58 methods dự kiến, bao gồm đủ 5 `ArchitectureTest` methods.
- Assessment source inventory vẫn là 90 methods tổng: 58 non-Docker + 32 Testcontainers/MySQL trong `AuthIntegrationTest`, `OrderIntegrationTest`, `DatabaseDesignTests`.

### 6. Detailed Test Results

#### Run A — Non-Docker

| Suite | Tests | Passed | Failed | Errors | Skipped | Seconds |
|---|---:|---:|---:|---:|---:|---:|
| `AdaptersTest` | 2 | 2 | 0 | 0 | 0 | 0.615 |
| `ArchitectureTest` | 5 | 5 | 0 | 0 | 0 | 1.458 |
| `AuthWebAndServiceTest` | 8 | 8 | 0 | 0 | 0 | 3.426 |
| `FoodCartSecurityTest` | 9 | 9 | 0 | 0 | 0 | 0.949 |
| `FoodServiceTest` | 11 | 11 | 0 | 0 | 0 | 0.149 |
| `LoginIpFilterTest` | 1 | 1 | 0 | 0 | 0 | 0.006 |
| `OrderServiceTest` | 10 | 10 | 0 | 0 | 0 | 0.106 |
| `OrderWebTest` | 10 | 10 | 0 | 0 | 0 | 0.619 |
| `RateLimiterTest` | 2 | 2 | 0 | 0 | 0 | 0.011 |
| **Tổng** | **58** | **58** | **0** | **0** | **0** | **7.339** |

Không có test thất bại nên không có application/test defect cần phân loại từ Run A. Log có hai warning không làm fail run: Mockito/Byte Buddy dynamic-agent warning trên Java 21 và Surefire dumpstream báo absolute classpath ở khác drive root. Đây là **toolchain/test-runner warning**, chưa phải application defect hay flakiness evidence.

#### Run B — Integration & Database

Không chạy. Docker client trả exit `1` vì engine pipe của context `desktop-linux` không tồn tại. Đây là **environment/configuration blocker**; không có cơ sở báo 32 methods pass/fail hoặc suy luận root cause trong application.

#### Run C — Full Regression

Không chạy. Full suite chứa ba Testcontainers class nên không thể tạo official 90-test report khi Docker daemon unavailable. Kết quả 58-test Run A không được dùng thay thế cho full suite.

### 7. Failure/Blocker Analysis

| Vấn đề | Phân loại | Ảnh hưởng | Kết luận |
|---|---|---|---|
| Docker Desktop/Engine daemon unavailable | Environment/configuration failure | Chặn 32 MySQL methods và full 90-test suite | **BLOCKED**, không phải test/application failure |
| Original upstream remote/ref không có | Chưa đủ bằng chứng/provenance | Không chứng minh được source gốc của fork | **PENDING** |
| Candidate chứa `1ee1cbf…` architectural refactor nhưng không có pre-Phase-2 marker | Chưa đủ bằng chứng/provenance | Không xác nhận chắc candidate là pre-improvement Phase 1 | **PENDING** |
| Mockito dynamic-agent/Surefire classpath warnings | Toolchain warning | Không ảnh hưởng exit/count/assertions trong Run A | **NON-BLOCKING** |

Không có failure chưa phân loại trong phần đã thực thi. Không rerun để che failure và không sửa test/source/config.

### 8. Evidence Artifact References

Root evidence: `docs/phase2/evidence/g2.1/2026-11-19/`.

- `git-baseline.txt`: repository/branch/SHA/remotes/refs/ancestry/diff classification.
- `environment-manifest.txt`: OS/CPU/RAM/Java/Maven/Docker/Testcontainers manifest đã loại secret.
- `non-docker/maven-output.txt`: raw Maven output của official Run A.
- `non-docker/exit-code.txt`: exit code `0`.
- `non-docker/summary.md`: aggregate và per-suite result.
- `non-docker/surefire-reports/`: Surefire XML/text đã copy ngay sau Run A để không bị ghi đè.
- `integration-database/BLOCKED.md`: evidence và lý do Run B không chạy.
- `full-suite/BLOCKED.md`: evidence và lý do Run C không chạy.
- `SHA256SUMS.txt`: checksum của evidence files để phát hiện thay đổi.

Không lưu generated binary, Maven cache, Docker data, credential hoặc key trong evidence tree.

### 9. Phase 1 Verification Readiness

| Exit criterion | Trạng thái | Cơ sở |
|---|---|---|
| Baseline source SHA xác định được | **PASS cho candidate** | Branch/ref cùng trỏ `510f641…` |
| Working tree/diff được phân loại | **PASS** | Chỉ docs untracked; không source/test/config working drift |
| Java/Maven usable | **PASS** | Wrapper 3.9.11 và Run A exit 0 |
| Docker/Testcontainers usable hoặc blocker rõ | **BLOCKED nhưng đã phân loại** | Daemon pipe không tồn tại |
| 58 non-Docker tests có kết quả chính thức | **PASS** | 58/58 pass, 0 skip |
| 32 integration/database tests có kết quả hoặc blocker | **BLOCKED** | Environment blocker, không có test result |
| Full 90-test suite có report hoặc blocker | **BLOCKED** | Environment blocker, không có full report |
| Không còn failure chưa phân loại | **PASS cho phạm vi đã chạy** | Không có failure; blocker đã phân loại |
| Test artifacts/environment metadata được lưu | **PASS** | Evidence tree + checksums |
| Original upstream và pre-improvement provenance đủ chắc | **PENDING** | Không có upstream ref; `1ee1cbf…` cần xác nhận |

**Overall G2.1: BLOCKED/PENDING. Phase 1 chưa được đánh dấu VERIFIED.** Hai gate runtime quan trọng (32 Testcontainers và full 90) chưa thực thi, đồng thời provenance pre-improvement của candidate chưa đủ chắc.

### 10. Conclusions & Next Steps

1. Current fork HEAD và Phase 1 baseline candidate đều là `510f6415b6af535ceec77213f0b0c7d5082123f7`.
2. Không có source/config drift giữa HEAD và branch candidate vì cùng SHA; working tree chỉ có tài liệu Phase 2. Candidate vẫn chứa architectural refactor `1ee1cbf…` trong lịch sử, nên cần xác nhận đó là Phase 1 chứ không phải treatment Phase 2.
3. Java/Maven sẵn sàng; Docker CLI/Compose có nhưng daemon/Testcontainers không sẵn sàng.
4. Official non-Docker result: **58/58 passed**, exit `0`, 0 failure/error/skip.
5. Official 32-Testcontainers result: **BLOCKED**, không chạy.
6. Official full-90 result: **BLOCKED**, không chạy.
7. Không có test fail trong phần đã chạy; blocker là Docker environment, không phải application defect.
8. Evidence đã lưu tại `docs/phase2/evidence/g2.1/2026-11-19/`.
9. Phase 1 **chưa VERIFIED**.
10. **Chưa đủ điều kiện chuyển sang G2.2 — Docker & Black-box Verification.** Cần khởi động/khôi phục Docker daemon, chạy và archive Run B/C trên cùng SHA; đồng thời xác nhận upstream/pre-improvement provenance trước khi tạo tag bất biến.

## G2.1 Follow-up Verification

Follow-up ngày 2026-11-19 được thực hiện trên cùng `HEAD 510f6415b6af535ceec77213f0b0c7d5082123f7`. Phần này bổ sung kết quả sau khi Docker recovery; dữ liệu G2.1 ban đầu, gồm official 58/58 PASS và các blocker tại thời điểm đó, được giữ nguyên phía trên.

### 1. Docker environment recovery

Docker daemon đã hoạt động và trả exit `0` cho `docker version`, `docker info`, `docker ps`; context giữ nguyên `desktop-linux`. Client/server đều là Docker `29.9.1`, server API `1.56`, Linux/amd64, 12 CPUs và Docker memory ~7.61 GiB. Trước run, ổ `D:` còn ~32.51 GiB; host free RAM chỉ ~0.47 GiB nhưng các container đang chạy dùng khoảng 0.57 GiB và hai lượt Testcontainers sau đó hoàn tất không OOM/disk error.

Không cài lại Docker, đổi context, reset WSL hoặc xóa/stop/restart shared container/image/volume. MySQL test được tạo riêng bằng Testcontainers `1.21.4`, image `mysql:8.4` digest `sha256:a81d043930e51745522bd5c430961cf8286f0a23f0a9a2a6e0108f7ea71b0902`; runtime database version là 8.4.13. Ryuk `0.12.0` đã cleanup: sau mỗi run không còn container có label Testcontainers.

### 2. Integration/database test results

Command chính xác:

```powershell
.\mvnw.cmd test "-Dtest=AuthIntegrationTest,OrderIntegrationTest,DatabaseDesignTests"
```

| Tests | Passed | Failures | Errors | Skipped | Maven total | Exit |
|---:|---:|---:|---:|---:|---:|---:|
| 32 | 32 | 0 | 0 | 0 | 03:36 min | 0 |

Ba suite lần lượt đạt `8 + 14 + 10 = 32` methods. Mỗi class dùng MySQL 8.4 container riêng; không dùng database hoặc volume của Compose stack. First-run duration bao gồm pull Ryuk/MySQL image. Raw Maven output, timestamps, exit code và ba XML/text Surefire reports được freeze riêng ngay sau run.

### 3. Full suite results

Command chính xác:

```powershell
.\mvnw.cmd test
```

| Tests | Passed | Failures | Errors | Skipped | Maven total | Exit |
|---:|---:|---:|---:|---:|---:|---:|
| 90 | 90 | 0 | 0 | 0 | 01:57 min | 0 |

Full suite có 12 suites và đúng 90 methods. Không có failed test details vì không có failure/error. Expected exception/validation log từ negative-path tests và warning Mockito/Byte Buddy/Surefire là non-blocking toolchain/test-path output, không làm thay đổi Maven/Surefire result. Không có rerun để che failure. Ba Testcontainers classes pass trong cả lượt 32 riêng và full suite ngay sau đó; không quan sát flakiness qua hai lần chạy liên tiếp, nhưng không suy rộng thành bằng chứng stress dài hạn.

### 4. Git provenance findings

- `1ee1cbf7b8d6d37f71c8a30ef57e0d68a3497763` là commit thực hiện thay đổi package-by-feature → package-by-layer: 67 source/test files, chủ yếu rename và package/import/test-rule update; không đổi Maven/resources/Docker/schema/config.
- Chain xác minh là `cfe2222… → 1ee1cbf… → 5a7bf40… → 510f641…`; hai commit sau refactor chỉ đổi tài liệu, nên executable tree tại HEAD mang refactor của `1ee1cbf…`.
- Live remote `origin/master`, remote HEAD, local `main`, `master` và `phase1-baseline` đều trỏ `510f641…`. Reflog ghi local `main`/`phase1-baseline` được tạo từ `origin/master` ngày 2026-11-17.
- Chỉ có origin fork URL; không có upstream remote/ref, immutable pre-Phase-2 tag, PR/issue marker hoặc independent decision record. Commit message/author/timestamp không được dùng để suy diễn ownership hay intent.
- `1ee1cbf…` tồn tại trước các tài liệu assessment và local baseline branch ngày 2026-11-17. Tuy nhiên `docs/phase2/` đang untracked và không chứng minh độc lập thời điểm thực tế nhóm bắt đầu Phase 2.
- Không có bằng chứng độc lập xác định `1ee1cbf…` là treatment Phase 2; cũng chưa có bằng chứng độc lập đủ mạnh xác định nó thuộc Phase 1. Classification giữ **PENDING**.

Hai baseline candidate:

| Candidate | Evidence hiện có | Hệ quả before/after |
|---|---|---|
| `510f641…` (runtime tree tương đương `1ee1cbf…`) | Provenance tương đối tốt nhất: HEAD/live remote/local baseline refs/Phase 0–1 docs và runtime 90/90 đều hội tụ | Nếu `1ee1cbf…` là Phase 2 treatment, before đã chứa treatment và comparison bị contaminated. |
| `cfe2222…` | Parent ngay trước architectural refactor | Pre-refactor theo chain, nhưng chưa được official runtime verification ở G2.1 này và chưa được chứng minh là official Phase 1 endpoint. |

Không đổi baseline SHA. HEAD hiện tại dùng được làm **current executable candidate**, nhưng chưa được tuyên bố chắc chắn là **pre-improvement baseline**.

### 5. Artifact manifest and checksums

Follow-up evidence nằm trong `docs/phase2/evidence/g2.1/2026-11-19/follow-up-docker-recovery/`, tách biệt hoàn toàn với evidence 58/58 ban đầu:

- `README.md`: phạm vi và manifest.
- `docker-environment.md`: Docker/context/resources/image/isolation/cleanup.
- `git-provenance.md`: commit/ref/remote/reflog và candidate analysis.
- `integration-database/maven-output.txt`, `exit-code.txt`, timestamps, `summary.md`, `surefire-reports/`.
- `full-suite/maven-output.txt`, `exit-code.txt`, timestamps, `summary.md`, `surefire-reports/`.
- `SHA256SUMS.txt`: SHA-256 của toàn bộ follow-up artifact, trừ chính file checksum.

### 6. Updated G2.1 exit-criteria matrix

| Exit criterion | Follow-up status | Cơ sở |
|---|---|---|
| Candidate SHA/refs xác định | **PASS** | HEAD/local refs/live remote master cùng `510f641…` |
| Java/Maven usable | **PASS** | Hai wrapper runs exit 0 |
| Docker daemon/Testcontainers usable | **PASS** | Docker checks exit 0; MySQL containers start/cleanup thành công |
| Original non-Docker run | **PASS** | Giữ nguyên evidence 58/58 ban đầu |
| 32 integration/database methods | **PASS** | 32/32, 0 failure/error/skip, exit 0 |
| Full official regression | **PASS** | 90/90, 0 failure/error/skip, exit 0 |
| Failure classification | **PASS** | Không có test failure; warning/log noise đã phân loại non-blocking |
| Raw outputs/reports/checksums | **PASS** | Follow-up evidence tách riêng và checksum manifest |
| Independent pre-improvement provenance | **PENDING** | Không upstream/immutable marker/independent phase decision cho `1ee1cbf…` |

**Runtime verification component: VERIFIED/PASS. Overall G2.1 baseline freeze: PENDING chỉ vì provenance pre-improvement chưa đóng.**

### 7. Remaining blockers

Docker và regression không còn blocker. Blocker duy nhất là provenance: chưa thể phân loại độc lập `1ee1cbf…` thuộc Phase 1 hay Phase 2, nên chưa thể đóng băng `510f641…` như pre-improvement baseline mà không có nguy cơ treatment contamination. Cần upstream history/ref, PR/issue record, signed team decision/minutes hoặc Phase 1 artifact gắn immutable SHA.

### 8. G2.2 readiness decision

Phase 1 **runtime verification đã đạt**: original non-Docker 58/58, focused Testcontainers 32/32 và full suite 90/90 đều có evidence; Docker environment hiện usable. Tuy nhiên **chưa đủ điều kiện chuyển sang G2.2** vì baseline provenance gate vẫn PENDING. Không bắt đầu G2.2, không tạo tag/commit và không đổi baseline SHA trong follow-up này.

### 9. G2.1 provenance resolution — independent upstream evidence

Phần PENDING phía trên được giữ nguyên như lịch sử quyết định tại thời điểm chưa có upstream evidence. Sau đó, verification độc lập xác nhận:

1. GitHub hiển thị `BuiHuy16/ByteMe-phase2` là fork từ [`maaL6/ByteMe`](https://github.com/maaL6/ByteMe).
2. [`1ee1cbf7b8d6d37f71c8a30ef57e0d68a3497763`](https://github.com/maaL6/ByteMe/commit/1ee1cbf7b8d6d37f71c8a30ef57e0d68a3497763) tồn tại trên upstream và là historical 67-file package-by-layer refactor.
3. [`510f6415b6af535ceec77213f0b0c7d5082123f7`](https://github.com/maaL6/ByteMe/commit/510f6415b6af535ceec77213f0b0c7d5082123f7) tồn tại trên upstream; live upstream HEAD/master cũng trả đúng full SHA này.
4. Local HEAD đúng `510f641…`, tree `9b8972489beffd34ac9873f1ff7f88c1c9f6b21a`; diff của `src`, tests/resources, Maven, Docker/Compose và scripts so với commit bằng 0.

Phân loại cập nhật: `1ee1cbf…` là **upstream historical refactor inherited by the fork**. Nó không được ghi nhận là thành quả Phase 2 tương lai của nhóm và không suy diễn ownership từ commit message. Với operational scope “improvement của nhóm là treatment mới sau baseline”, `510f641…` được công nhận là **pre-improvement source của nhóm**. Future Phase 2 changes phải được tách rõ khỏi SHA này.

**G2.1 provenance: RESOLVED/PASS. G2.1 overall: VERIFIED/PASS.** Không tạo tag/branch/commit/push; baseline SHA không đổi.

## G2.2 — Docker & Black-box Verification

### 1. Preflight and isolation

- Docker client/server `29.9.1`, API `1.56`, Compose `v5.6.0`, context `desktop-linux`.
- Docker VM: 12 CPUs, ~7.61 GiB RAM; host còn ~2.59 GiB physical RAM và ổ `D:` còn ~32.51 GiB.
- Ports 13306/18080 rảnh; project `byteme-g22` chưa có container/network/volume trước deployment.
- Resolved ports chỉ bind loopback: MySQL `127.0.0.1:13306`, backend `127.0.0.1:18080`.
- Named volume/network riêng: `byteme-g22_mysql_data`, `byteme-g22_default`.
- DB secrets và RSA 3072-bit pair được tạo trong `.local/g22/` ignored; override chỉ đổi read-only `/run/auth` bind. Không lưu secret/key content trong evidence.
- Script review xác nhận `BYTEME_BASE_URL` định tuyến HTTP; `COMPOSE_PROJECT_NAME=byteme-g22` định tuyến `docker compose exec mysql`; fixture/cleanup chỉ dùng prefix ngẫu nhiên của run.

### 2. Image build

| Item | Result |
|---|---|
| Compose build | **PASS**, exit 0 |
| Maven package in Dockerfile | `BUILD SUCCESS` |
| Image | `byteme-g22-backend:latest` |
| Image ID/digest | `sha256:374e18d9da9322de83cfae202353ef6e9f268db6cd6289a295cf5af581da7022` |
| Size | 583,684,096 bytes |

Build dùng source tree đã đối chiếu với `510f641…`. Dockerfile baseline skip tests khi package; regression 90/90 của G2.1 là gate test độc lập, không bị thay thế bởi build này.

### 3. Startup and readiness

| Layer | Status | Evidence |
|---|---|---|
| Image built | **PASS** | Build exit 0 + resolved image ID |
| Containers started | **PASS** | MySQL/backend running |
| MySQL healthy | **PASS** | Compose health `healthy`, MySQL 8.4.13 |
| Database connected | **PASS** | Hikari start completed; schema queries và API succeed |
| RSA readable | **PASS** | UID/GID 10001 đọc private/public key, check exit 0 |
| Application ready | **PASS** | `/actuator/health` HTTP 200, `{"status":"UP"}` |
| Public food API | **PASS** | `/api/foods` HTTP 200, 17 ACTIVE foods sau seed |
| Serious startup errors | **PASS** | 0 ERROR/FATAL/exception/access-denied/OOM trong captured logs |

### 4. Database initialization

Fresh volume có đúng bảy bảng và các primary/unique/foreign-key/user CHECK constraints. Trước seed, tất cả bảng có 0 rows và stock total 0. `seed.sql` chạy đúng một lần, exit 0:

| users | categories | foods | carts | cart_items | orders | order_items | stock_total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 6 | 18 | 5 | 6 | 8 | 16 | 846 |

### 5. Black-box API result

Exact command `python -X utf8 scripts/test-endpoints.py` được chạy nguyên bản với isolated project/env.

| Passed | Failed | Fatal | Exit | cleanupVerified |
|---:|---:|---|---:|---|
| **196** | **0** | `null` | 0 | **true** |

Coverage gồm Infrastructure 3, Auth 32, Food 45, Cart 27, Order 65, Checkout failures/rollback 12, rate-limit 11 và Cleanup 1. HTTP observations: 42×200, 15×201, 1×204, 35×400, 17×401, 16×403, 8×404, 17×409, 1×429. DB counts và `stock_total=846` sau cleanup khớp trước run.

### 6. Cleanup verification

Trước cleanup, ownership labels xác nhận đúng hai containers, một network và một volume thuộc `byteme-g22`. Sau `docker compose ... down -v --remove-orphans` exit 0:

- 0 project containers, 0 project networks, 0 project volumes.
- 0 listeners trên 13306/18080.
- Bốn shared containers ban đầu vẫn chạy; không tài nguyên project khác bị xóa.
- RSA keys, runtime secrets và result tạm `.local` đã xóa sau khi evidence được copy.
- Image `byteme-g22-backend:latest` được giữ lại có chủ đích làm build artifact; không chứa database data hay runtime secret.

Infrastructure cleanup và black-box fixture cleanup đều có `cleanupVerified=true`.

### 7. Findings and blockers

Không có application failure, black-box failure, database contamination hoặc environment blocker. MySQL log có warning chuẩn của entrypoint về bước `--initialize-insecure` nội bộ trước khi apply configured credentials; final application/non-root DB access, health, seed và tests đều thành công. Một lỗi format ở lần đầu chụp `docker image inspect` chỉ là evidence-command issue, đã chụp lại đúng và không ảnh hưởng build/deployment.

### 8. Artifacts and checksums

Evidence: `docs/phase2/evidence/g2.2/2026-11-19/`, gồm provenance/preflight/deployment manifest, raw build/startup/test/cleanup output, image/service states, schema/constraints/counts, JSON test result, HTTP summary, relevant logs và exit codes. `SHA256SUMS.txt` bảo vệ toàn bộ artifact; secret/JWT/private key/Authorization header đã được scan và không có trong evidence.

### 9. Exit criteria and next step

| Criterion | Status |
|---|---|
| Upstream/fork provenance resolved | **PASS** |
| Local baseline matches tested source/config/scripts | **PASS** |
| Isolated image build | **PASS** |
| MySQL/backend startup and readiness | **PASS** |
| Schema + one-time seed | **PASS** |
| Black-box API | **PASS — 196/196** |
| Fixture cleanup | **PASS** |
| Docker resource cleanup | **PASS** |
| Evidence/checksums/redaction | **PASS** |

**Overall G2.2: PASS.** Đủ điều kiện kỹ thuật để bắt đầu **G2.3 — Concurrency & Query Verification** trên một isolated stack mới, nhưng G2.3 chưa được thực hiện trong nhiệm vụ này.

## G2.3 — Concurrency & Query Verification

### 1. Objectives & Scope

G2.3 kiểm chứng runtime hai nhóm nghi vấn đã ghi tại DB-05/DB-06/DB-07: năm race condition nghiệp vụ và ba nhóm query plan/count, kèm synthetic dataset scaling. Đây là diagnostic verification trên baseline, không phải benchmark k6/G2.5 và không triển khai locking, versioning, index, cache hay refactor.

Phân loại dùng đúng bốn trạng thái: **CONFIRMED DEFECT**, **OBSERVED CORRECT**, **INCONCLUSIVE**, **BLOCKED**. “Không tái hiện” chỉ có nghĩa trong các lượt đã chạy, không chứng minh tuyệt đối không có race.

### 2. Baseline Source and Environment

- HEAD/branch: `510f6415b6af535ceec77213f0b0c7d5082123f7`, `main`; đây là pre-improvement baseline đã giải quyết provenance tại G2.1.
- `git diff --exit-code 510f... -- src pom.xml compose.yaml Dockerfile .dockerignore .env.example scripts` trả `0` trước và sau run. Working tree chỉ có cây tài liệu Phase 2 untracked đã biết; harness nằm dưới ignored `.local/g2.3/`.
- Project riêng `byteme-g23`, ports loopback `13307/18081`, volume/network riêng; không dùng G2.2 database/volume.
- Backend image `sha256:8bd11bf3ae9e5f7daeaf0c600c79639eae57cff13f5a719b930890fbe3b164af`; MySQL image digest `sha256:a81d043930e51745522bd5c430961cf8286f0a23f0a9a2a6e0108f7ea71b0902`.
- Docker 29.9.1/Compose 5.6.0, 12 CPUs, 7.611 GiB Docker RAM; MySQL 8.4.13; JVM Temurin 21.0.13; Hibernate 6.6.53.Final.
- MySQL `REPEATABLE-READ`, autocommit 1, lock wait 50s. Hikari dùng baseline defaults và connection init UTC.
- Schema khởi tạo với bảy bảng rỗng; không sửa/chạy lại `seed.sql`. Runtime secrets và RSA-3072 key mới chỉ tồn tại tạm trong `.local/g2.3/`.

Run diễn ra ngày 2026-11-20 theo Asia/Saigon, tương ứng 2026-11-19 UTC nên evidence giữ đúng thư mục được yêu cầu.

### 3. Experimental Methodology

Mỗi C1–C5 chạy **15 rounds**, concurrency level 2, fixture riêng và targeted cleanup trước/sau round. Harness gọi backend thật qua HTTP và query MySQL thật để chụp initial/final state. `threading.Barrier` đồng bộ lúc thả hai worker; request start/end timestamp và raw response được lưu từng round.

Client request intervals overlap 15/15 rounds cho cả năm scenario. Median start delta là 0 ms cho C1/C2/C3/C5 và 0.628 ms cho C4; max 6.870 ms. Giới hạn: barrier chứng minh near-simultaneous HTTP attempts nhưng không phải database in-transaction barrier, nên không khẳng định mọi transaction đã overlap tại cùng instruction. Không thêm synchronization hook vào application.

Query count dùng MySQL `general_log` bật chỉ trong cửa sổ một API request rồi tắt; raw statement được lưu. Query plan dùng `EXPLAIN FORMAT=JSON` và `EXPLAIN ANALYZE` trên DB riêng. Synthetic scale tối đa 5,000 foods hoặc 5,000 orders + items; `ANALYZE TABLE` chỉ refresh statistics, không tạo index. Latency là single-run diagnostic, không phải official benchmark.

### 4. Concurrency Scenarios

- **C1:** stock 10; hai customer/cart khác nhau, mỗi cart quantity 7, concurrent checkout.
- **C2:** một customer/cart quantity 2, hai concurrent checkout requests; stock 10.
- **C3:** tạo pending order quantity 2 từ stock 10, sau đó hai concurrent DELETE cùng order.
- **C4:** admin `PUT` gán stock từ 10 thành 20 đồng thời customer checkout quantity 3. Contract hiện tại là absolute assignment khi `stockQuantity` non-null.
- **C5:** customer chưa có cart gửi hai concurrent add-item quantity 1 cùng food; unique `carts.user_id` là DB guard.

Invariant chính gồm committed quantity không vượt initial stock, stock khớp order items, tối đa một consumption của cùng cart, cancel release đúng một lần, outcome C4 phải tương đương một thứ tự tuần tự hợp lệ, và một customer có đúng một first cart.

### 5. Concurrency Results Matrix

| Scenario | Rounds | Kết quả quan sát | Classification |
|---|---:|---|---|
| C1 same food | 15 | 6 rounds: HTTP 201+201, 2 orders/14 units từ stock 10, final stock 3; 9 rounds chỉ 1 order và loser cart còn nguyên | **CONFIRMED DEFECT** — overselling + lost update 6/15 |
| C2 same cart | 15 | 15/15 chỉ 1 order, qty 2, stock 8, cart empty; loser: 11×409, 2×400, 2×500 | **INCONCLUSIVE** — data đúng nhưng loser semantics có unhandled stale-row 500 |
| C3 same cancellation | 15 | 15/15 final CANCELLED và stock 10; 13×(200+200), 2×(200+409) | **OBSERVED CORRECT** cho data invariants |
| C4 stock update vs checkout | 15 | Cả hai call success; final stock 7×12, 20×2, 17×1 | **CONFIRMED DEFECT** — non-serializable/lost admin update 12/15 |
| C5 first cart | 15 | 15/15 một 200 + một 409; đúng 1 cart, 1 item quantity 1 | **OBSERVED CORRECT** trong tested conflict semantics |

C1 không có partial order; cả hai successful carts đều được clear. C2 HTTP 500 log là `ObjectOptimisticLockingFailureException`/`StaleObjectStateException` khi hai transaction xóa cùng `CartItem`; transaction rollback giữ final data đúng. C3 không double stock release. C4 final 7 không thuộc hai outcome tuần tự hợp lệ: update→checkout = 17, checkout→update = 20. C5 unique constraint rollback không làm mất committed cart/item.

### 6. Query Diagnostics

**Q1 order listing:** dataset 60 orders, một item/order. API page content 1/5/20/50 tạo lần lượt 4/8/23/53 captured SELECTs, trong đó `order_items` SELECT là đúng 1/5/20/50. N+1 đã quan sát runtime, **CONFIRMED DEFECT / DB-07 confirmed**. Detail endpoint có một order query + một item query và không có list growth.

**Q2 food search:** ở 100/1,000/5,000 rows, keyword-only và category-filtered plans đều primary-index scan toàn bộ rows rồi áp dụng `LOWER(...) LIKE '%needle%'`. Unique name index không phục vụ leading wildcard; category FK index tồn tại nhưng optimizer không chọn trong single-category distribution + `ORDER BY id`. Plan fact confirmed; end-user severity **INCONCLUSIVE / DB-06 retained**.

**Q3 order filter/pagination:** scale 100/1,000/5,000 total orders qua 21 users; measured owner có 5/48/239. Plan dùng implicit `fk_orders_user`, sau đó filter status/type và sort `created_at DESC,id DESC`; không có composite filter/sort index. Count scan cùng owner rows; offset 100 sort/limit 120 trong 239 owner rows. Performance severity **INCONCLUSIVE / DB-06 retained** vì chưa có representative workload/SLO.

**Q4 scaling:** synthetic rows chỉ tồn tại trong isolated volume và được xóa sau investigation. Không thiếu RAM/disk/OOM và không thay schema/seed/index.

### 7. SQL Plans & Query Counts

| Diagnostic | Cardinality | Plan/query-count fact | Diagnostic latency |
|---|---:|---|---:|
| Order list size 1 | 60 owner orders | 1 page + 1 item + 1 count + 1 stable version SELECT | 68.048 ms |
| Order list size 20 | 60 owner orders | 1 page + 20 item + 1 count + 1 stable version SELECT | 62.575 ms |
| Order list size 50 | 60 owner orders | 1 page + 50 item + 1 count + 1 stable version SELECT | 50.642 ms |
| Food search | 5,000 foods, 500 matches | primary-index scan 5,000; filter actual ~4.29 ms | API 53.742 ms |
| Food search + category | 5,000 foods, 500 matches | primary-index scan 5,000; filter actual ~4.32 ms | API 44.223 ms |
| Customer order list | 5,000 total / 239 owner | user-id index lookup 239 + filter/sort; plan ~0.459 ms | API 33.573 ms |
| Customer count | 5,000 total / 239 owner | user-id index lookup/filter 239; plan ~0.311 ms | n/a |

Không dùng các latency đơn lẻ này làm before/after benchmark hoặc tuyên bố bottleneck production.

### 8. Confirmed Issues vs Inconclusive Risks

| Finding | G2.3 resolution |
|---|---|
| DB-05 C1 | **CONFIRMED DEFECT:** overselling + lost stock update 6/15 |
| DB-05 C2 | **INCONCLUSIVE:** no double checkout trong 15 rounds; hai unhandled 500 cần được carry forward |
| DB-05 C3 | **OBSERVED CORRECT:** no double release trong 15 rounds; double-200 retry semantics chưa được contract hóa |
| DB-05 C4 | **CONFIRMED DEFECT:** successful absolute stock update bị lost 12/15 |
| DB-05 C5 | **OBSERVED CORRECT:** unique constraint + rollback giữ một cart/item trong 15 rounds |
| DB-07 | **CONFIRMED DEFECT:** order list N+1, query count tăng N+3 captured SELECTs |
| DB-06 food | Access scan confirmed; performance impact **INCONCLUSIVE** |
| DB-06 order | Owner index + post-filter/sort confirmed; performance impact **INCONCLUSIVE** |

Không có scenario BLOCKED. Conflict 409 hợp lệ không bị ghi thành defect. C2 500 được bảo toàn trong raw evidence và không biến thành data-corruption finding khi final invariant vẫn đúng.

### 9. Evidence & Reproducibility

Evidence nằm tại `docs/phase2/evidence/g2.3/2026-11-19/`:

- environment/build/startup metadata và raw output;
- `concurrency/c1-raw.json` … `c5-raw.json`, aggregate summary, timestamps/exit code, backend log và reviewed summary;
- `query/q1-order-listing.json`, `q2-food-search.json`, `q3-order-filter-pagination.json`, aggregate summary, timestamps/exit code;
- `harness/` chứa reproducibility copies của hai Python harness và Compose override; ephemeral actor password được externalize qua env trong copy để không lưu credential;
- `SHA256SUMS.txt` bảo vệ mọi artifact trừ chính manifest.

Evidence scan không chứa runtime DB secret, JWT value, Authorization header value hoặc RSA key content. Raw HTTP chỉ lưu status, timing và compact response fields.

### 10. Cleanup Verification

Trước Compose down, `general_log=0` và cả bảy business tables về 0 rows. `docker compose ... down -v --remove-orphans` exit 0, xóa đúng hai G2.3 containers, một network và một volume. Post-check: 0 resource mang project label, không listener 13307/18081; sáu shared containers vẫn chạy.

`.local/g2.3/` được resolve đúng dưới workspace rồi xóa, gồm runtime secrets, RSA keys và temp outputs. Sau khi đã archive ID/size và xác minh không container nào sử dụng, image `byteme-g23-backend:latest` riêng của G2.3 cũng được xóa; image G2.2 và các image/resource dùng chung không bị đụng tới.

### 11. G2.3 Exit Criteria

| Criterion | Status |
|---|---|
| Baseline SHA và executable diff locked | **PASS** |
| Isolated Docker/MySQL/backend environment | **PASS** |
| 5/5 concurrency scenarios, 10–20 rounds | **PASS — 15 rounds/scenario** |
| Raw HTTP/DB state/timestamps retained | **PASS** |
| C1–C5 classified without hiding conflicts/failures | **PASS** |
| Q1 SQL count from runtime telemetry | **PASS** |
| Q2/Q3 EXPLAIN at scaled cardinality | **PASS** |
| No source/test/schema/config/index change | **PASS** |
| Redacted harness/evidence/checksums | **PASS** |
| Dedicated resource/secret cleanup | **PASS** |

**G2.3 verification gate: PASS.** PASS means requested experiments/evidence/cleanup completed; it does not mean the application is concurrency-safe. Application findings C1, C4 and Q1 are confirmed defects, while C2 and DB-06 performance severity remain explicitly inconclusive.

### 12. Conclusions & Next Steps

G2.3 produced actionable evidence for the later Architecture Issues decision: protect checkout stock reservation, define same-cart/duplicate cancellation semantics and stale-update error mapping, resolve admin-stock vs checkout serialization, and eliminate/measure order-list N+1. G2.3 did not choose or implement any solution.

Baseline verification and diagnostics are sufficient to move to **G2.4 — Benchmark Preparation**, carrying the confirmed defects and inconclusive risks as explicit constraints. G2.4/G2.5 were not started here; official performance claims must still use a locked workload, repetitions, resource telemetry and dataset protocol rather than these single diagnostic timings.

## G2.4 — Reproducible Benchmark Preparation

### 1. Objectives & Scope

G2.4 đã chuẩn bị một benchmark kit dùng chung cho phép đo before/after ở G2.5, không chạy official benchmark và không tạo performance claim. Phạm vi chỉ gồm chọn platform, khóa cấu hình, tạo dataset/reset protocol, workload W1–W3, telemetry, artifact format và smoke validation. Application source/test/config, schema/seed và Kaggle notebook gốc không bị sửa.

Baseline application vẫn là `510f6415b6af535ceec77213f0b0c7d5082123f7`; final smoke ghi `executable_diff_exit=0`. Benchmark kit mới nằm riêng tại `benchmarks/phase2/` và được bảo vệ bằng SHA-256 thay vì Git commit/tag theo giới hạn của hạng mục.

### 2. Platform Decision

Quyết định ban đầu của G2.4 là **Local Windows + Docker Desktop Compose** vì khả năng pin image/tool version, cô lập volume/project, reset/checksum, giữ raw artifacts và thu Docker/JVM/DB telemetry. Docker runtime quan sát được 12 CPU và 8.171.761.664 byte RAM; backend/MySQL/k6 có resource limit riêng. Phần chuẩn bị và smoke Local này vẫn **PASS** và được giữ làm development/integration verification.

Theo yêu cầu giảng viên được áp dụng tại G2.4-K, **primary platform cho official G2.5 được đổi thành Kaggle CPU**; Local trở thành platform phụ cho development/integration. Kaggle historical path cài moving packages và thiếu reset/telemetry nên không được tái sử dụng trực tiếp; adapter G2.4-K dùng exact-version user-space toolchain và manifest phần cứng. Chỉ so Kaggle-before với Kaggle-after khi CPU model/core/RAM quota và lock khác khớp. **Không so chéo Local với Kaggle; không dùng historical Kaggle result làm baseline tương thích.**

### 3. Benchmark Goals

G2.5 sẽ đo p50/p95/p99, request rate, HTTP/transport/application error và business rejection theo workload/operation; đồng thời thu CPU/RAM của backend, MySQL và load generator, JVM/GC, MySQL connection/lock/buffer/query digest và kiểm tra data consistency. Mục tiêu là before/after trên cùng platform/config/dataset/workload, không biến các threshold cũ thành SLO được chấp thuận.

Hikari maximum/minimum được khóa và ghi nhận. Live Hikari gauges không được actuator hiện tại expose; pool saturation vì vậy là **UNAVAILABLE**, không được suy diễn từ DB connection count.

### 4. Workload Design

| Workload | Thiết kế đã version hóa | Tách metric/correctness |
|---|---|---|
| W1 reads | `GET /api/foods`, food search `needle`, authenticated order list page 0/size 20; token được tạo trước measurement | Ba k6 scenario có operation tag riêng; auth không nằm trong timed request |
| W2 writes | Mỗi VU có actor và food riêng; cart add 1 → update 2 → checkout → cancel để restore stock | 400/409 business rejection, 500/transport và unexpected response là counter riêng |
| W3 contention | Same-food checkout, same-cart checkout, admin absolute-stock update vs checkout, client barrier | 15 rounds/scenario ở official run; invariant/server error báo riêng, không trộn vào throughput percentile |

W1 dùng constant-arrival-rate 10/5/5 RPS trong 180 giây. W2 dùng 10 constant VUs trong 180 giây và không vượt 20 actor riêng. W3 giữ client-side barrier limitation rõ ràng: barrier không chứng minh database in-transaction barrier.

### 5. Dataset Profiles

| Partition | Smoke | Standard đề xuất cho G2.5 |
|---|---:|---:|
| Categories | 3 | 10 |
| Read/search foods | 60 | 5.000 |
| Read actor orders | 20 | 500 |
| Items/read order | 2 | 2 |
| Dedicated write actors/foods | 2 | 20 |
| Contention actors | 4 | 4 |
| Dedicated write stock | 1.000 | 1.000.000 |
| Shared contention stock | 10 | 10 |

Generator tạo fixture deterministic trong database/project cô lập. Manifest ghi cardinality, invariants và logical SHA-256 nhưng loại password hash, JWT và generated timestamp. Actor token chỉ tồn tại tạm dưới `.local/phase2-benchmark/`, không được archive.

### 6. Reset & Warm-up Protocol

Mỗi official run phải có project/volume/run ID mới, prepare dataset rồi xác minh checksum. Warm-up 60 giây ở low rate và discard toàn bộ metric warm-up. Trình tự measurement là W1 → reset/checksum → W2 → reset/checksum → W3 → reset/checksum; sau đó cool-down 30 giây, thu logs và xóa đúng resource của run.

Reset destructive chỉ chạy khi project/database namespace khớp `byteme-g24-*` hoặc `byteme-benchmark-*`. Final smoke khởi đầu và kết thúc cùng logical checksum `1563f0bc27189c805d600347a497830593289542cfc3543d3b73d29117961e50`, chứng minh reset deterministic ở profile smoke.

### 7. Measurement & Repetition Protocol

Mỗi candidate SHA cần tối thiểu 3 independent measurement runs, mục tiêu 5; nên xen kẽ thứ tự before/after khi thực tế cho phép. Mỗi run lưu raw/summary riêng. Failed run được giữ và phân loại, không rerun để che giấu. Chỉ aggregate run có cùng platform, workload source, configuration SHA và dataset checksum.

Báo cáo phải nêu per-run p50/p95/p99/RPS/error, sau đó median giữa các run hợp lệ, min/max và coefficient of variation. `aggregate_runs.py` yêu cầu caller truyền configuration/dataset SHA; malformed summary bị reject. Một-run smoke aggregate chỉ kiểm tra tool, không có statistical meaning.

### 8. Configuration Lock Matrix

| Control | Locked value |
|---|---|
| Docker | context `desktop-linux`; engine 29.9.1; Compose 5.6.0 |
| Backend | 2 CPU; 1.280 MiB; image ID/build/base resolution ghi từng run |
| Java/JVM | Temurin 21.0.13+9 LTS; G1; Xms 512 MiB; Xmx 768 MiB; GC log stdout |
| Hikari/Tomcat | pool 10/10; threads 200/10 |
| MySQL | 8.4.13; digest `sha256:a81d043…`; 2 CPU; 1.536 MiB; RR; max connections 100; buffer pool 512 MiB; Performance Schema on |
| k6 | 0.55.2; digest `sha256:3cd0ae83…`; 1 CPU/512 MiB per container |
| Benchmark Compose SHA | `d5841d80e0776b4eb6a07a26ed0095dce6940e04e2d12ebcaa52c64b43c99e60` tại final smoke |

Thay đổi bất kỳ giá trị nào là configuration/treatment mới và không được gộp vào cùng aggregate. Exact values, IDs và full hashes nằm trong `configuration-lock.md` và environment artifacts của từng run.

### 9. Metrics Collection

- k6 giữ raw JSON-lines và full summary JSON; operation/workload tags phân tách endpoint.
- `docker stats` lấy timestamped CPU/RAM/network/block/PID cho backend, MySQL và k6; final smoke cũng thu cho W3.
- Backend stdout giữ GC events và application log; environment capture xác minh Java/heap/GC/Hikari/Tomcat resolved controls.
- MySQL read-only snapshots lấy global status và tối đa 200 normalized Performance Schema digests ngay trước/sau workload; G2.5 tính delta `COUNT_STAR`/time/rows giữa hai snapshot thay vì bật general log trong throughput run.
- Dataset snapshot/invariant kiểm tra data consistency trước, sau và sau reset.

### 10. Artifact & Provenance Format

Mỗi run có `manifest/`, `dataset/`, `workload/`, `k6/`, `resources/`, `logs/`, `database/`, `consistency/`, `exit-codes/` và `SHA256SUMS.txt`. Environment manifest gồm application SHA/status, Docker/context/Compose, image IDs/digests, resolved runtime settings, dataset/workload hashes và timestamps. Raw output không ghi Authorization header/JWT/password/private key.

Evidence G2.4 nằm tại `docs/phase2/evidence/g2.4/2026-11-20/`; ngày thư mục theo Asia/Saigon, còn runtime timestamps là UTC ngày 2026-11-19. Sáu smoke attempt có thư mục/manifests độc lập, không ghi đè evidence cũ.

### 11. Implementation/Smoke Results

Benchmark kit gồm Compose override, hai dataset profile, deterministic generator/reset, W1/W2 k6, W3 Python harness, collectors environment/resource/DB, aggregator, checksum tool và smoke orchestrator. `smoke-attempt-6` là final validation, exit 0:

| Validation | Result |
|---|---|
| W1 | 6/6 checks PASS, HTTP failure rate 0 |
| W2 | 8/8 checks PASS, HTTP failure rate 0 |
| W3 harness | Hoàn tất 2 rounds/scenario; giữ nguyên known race evidence, gồm same-food violation 2/2, same-cart HTTP 500 round 2, admin-stock violation round 2 |
| DB/SQL telemetry | 4 snapshots PASS |
| Docker resource telemetry | W1/W2/W3 lần lượt có 7/9/13 dòng gồm header |
| Reset | Exact initial checksum restored |
| Cleanup | 0 project container/network/volume/listener/backend image |

Các latency/RPS smoke không được coi là baseline vì chỉ có vài request. Attempts 1–3 và 5 đều được giữ: lỗi collector stderr, hai lỗi namespace W3 và thiếu privilege Performance Schema; mỗi lần đều cleanup. Attempt 4 là end-to-end pass trước telemetry enhancement; attempt 6 là final pass.

### 12. Known Limitations

1. Load generator dùng chung Docker VM/host với SUT; cần giữ limit và báo resource/noise mỗi run.
2. Hikari live gauges không expose; chỉ có config lock, DB connections và log. Không được tuyên bố pool saturation nếu thiếu metric.
3. W3 dùng client barrier, không phải in-transaction DB barrier, và chỉ phục vụ correctness.
4. Standard profile/chính thức chưa chạy nên duration, throughput stability và disk capacity ở 5.000 foods/500 orders chưa có runtime evidence G2.5.
5. Backend image provenance metadata có thể đổi giữa build dù source không đổi; phải khóa application SHA, executable diff, base-image resolution và per-run image ID.
6. Historical Kaggle result thiếu provenance/raw telemetry tương thích và không dùng trong aggregate local.

### 13. G2.4 Exit Criteria

| Criterion | Status |
|---|---|
| Primary/fallback platform quyết định, cấm cross-platform comparison | **PASS** |
| Versioned W1/W2/W3 workload và deterministic dataset profiles | **PASS** |
| Isolated, safety-checked reset + logical checksum | **PASS** |
| Warm-up/duration/cool-down/repetition/aggregation protocol | **PASS** |
| JVM/Hikari/Tomcat/MySQL/k6/resource configuration lock | **PASS** |
| k6, CPU/RAM, GC/JVM, DB/SQL, consistency evidence path | **PASS** — Hikari live gauge limitation declared |
| Failed smoke attempts retained, final end-to-end smoke passes | **PASS** |
| Secrets excluded, dedicated resources cleaned | **PASS** |
| Application source/test/config/schema/seed unchanged | **PASS** |
| Official G2.5 benchmark absent | **PASS — đúng phạm vi** |

**G2.4 preparation gate: PASS.** PASS chỉ xác nhận protocol/tooling/smoke; chưa có official performance baseline hay before/after conclusion.

### 14. G2.5 Execution Plan

G2.5 có thể bắt đầu sau khi copy/freeze `benchmark-source-SHA256SUMS.txt` vào run manifest và giữ nguyên configuration lock. Với mỗi baseline/treatment SHA: tạo unique project/run; build/capture; prepare `standard`; warm-up; chạy W1, reset, W2, reset, W3, reset; thu telemetry/logs; cleanup; lặp tối thiểu 3, mục tiêu 5. Sau đó chỉ aggregate run có manifest khớp và công bố cả failed/rejected run.

Readiness decision tại thời điểm G2.4 Local: **READY WITH DECLARED LIMITATIONS cho development/integration**, nhưng không còn là quyết định platform chính thức. Sau yêu cầu giảng viên, official G2.5 phải chờ Kaggle adaptation được runtime-validate; xem G2.4-K bên dưới. G2.5 chưa được bắt đầu trong hạng mục này.

## G2.4-K — Kaggle CPU Benchmark Adaptation

### 1. Scope and access evidence

G2.4-K chuyển cùng benchmark semantics từ Docker sang Kaggle CPU, không thiết kế lại nghiệp vụ và không chạy official G2.5. Môi trường thực thi hiện tại không có Kaggle CLI, `KAGGLE_USERNAME`, `KAGGLE_KEY`, `KAGGLE_API_TOKEN` hoặc `~/.kaggle/kaggle.json`; vì vậy không có quyền tạo/chạy Kaggle session thật. Theo policy, **Kaggle runtime validation giữ PENDING** và không báo smoke PASS.

HEAD hiện là repository/tooling commit `24b3ace314365bc2b727928fae2243c605b4c87c`, còn executable tree không khác baseline `510f6415b6af535ceec77213f0b0c7d5082123f7` trên `src`, POM, Compose, Dockerfile và runtime scripts (`git diff --quiet` exit 0). Bundle manifest tách `repository_sha` khỏi `application_sha` để không biến commit tài liệu/tooling thành treatment ứng dụng.

### 2. Primary platform decision

**Official primary platform: Kaggle CPU. Local Docker: development/integration verification.** Local G2.4 preparation/smoke vẫn PASS nhưng kết quả Local không được gộp hoặc so trực tiếp với Kaggle. Historical upstream notebook được giữ nguyên để bảo toàn provenance; notebook mới nằm cạnh nó với tên khác.

Một nhãn “Kaggle CPU” không đủ chứng minh phần cứng cố định. Mỗi run phải ghi CPU model, logical core count, `MemTotal`, OS image/version và kernel. Comparator yêu cầu CPU model/core, cgroup CPU quota/cpuset và memory limit, OS/runtime cùng toolchain/config/workload/dataset lock khớp chính xác. `hardware.memory_total_bytes` host-visible được phép chênh tối đa 1 MiB vì Linux `MemTotal` có thể khác vài page do kernel/host memory accounting; cgroup memory limit và resolved limit vẫn là giới hạn RAM hiệu dụng và phải khớp tuyệt đối.

### 3. Rootless fixed toolchain design

Adapter không giả định Docker, root, `sudo` hoặc `apt-get`. Notebook chỉ probe các capability này. Java 21.0.13, MySQL 8.4.13 và k6 0.55.2 được resolve từ exact portable Linux x86_64 archives đã attach, hoặc từ system binary chỉ khi output version khớp lock chính xác. Binary path, full version output và executable SHA-256 được lưu.

MySQL generic distribution được extract dưới `/kaggle/working`, initialize bằng `--initialize-insecure` trong datadir riêng, chỉ bind `127.0.0.1:13309`, bật Performance Schema và giữ RR/max connections/buffer pool như G2.4. Root chỉ dùng Unix socket nội bộ cho lifecycle/telemetry; application user có password ngẫu nhiên trong process environment và không được archive. Spring Boot chạy trực tiếp từ JAR với G1, Xms 512 MiB, Xmx 768 MiB, Hikari 10/10 và Tomcat 200/10.

### 4. Workload compatibility

W1 và W2 dùng nguyên JavaScript G2.4. `prepare_dataset.py` và W3 được mở rộng bằng optional `--db-mode direct`; default vẫn là `compose`, nên Local kit không bị xóa hoặc đổi semantics. Direct mode dùng MySQL client qua loopback và password environment variable, không hardcode credential.

| Workload | Kaggle adaptation | Runtime status |
|---|---|---|
| W1 food list/search/order list | Native k6, actors/tokens tạo trước measurement, page size 20 | **STATIC PASS; KAGGLE PENDING** |
| W2 add/update/checkout/cancel | Native k6, per-actor food/cart, business/server error tách riêng | **STATIC PASS; KAGGLE PENDING** |
| W3 same-food/same-cart/admin-vs-checkout | Python barrier harness + direct MySQL final-state inspection | **STATIC PASS; KAGGLE PENDING** |

### 5. Dataset and reset

Profile `standard` không đổi: 5.000 read foods, 500 read orders, hai items/order, 20 write actors/foods, bốn contention actors, write stock 1.000.000 và shared stock 10. Kaggle smoke chỉ dùng profile `smoke` và hai W3 rounds. Generator vẫn giới hạn namespace `byteme-g24-*`/`byteme_g24_*`, ghi counts/invariants/logical checksum và reset toàn bộ benchmark DB cô lập.

Bundle builder copy đúng `schema.sql` gốc và không copy/áp dụng `seed.sql`; generator tạo toàn bộ fixture benchmark. Static bundle dry-run xác minh 14 file và 0 checksum error. Standard dataset và exact reset trên Kaggle vẫn **PENDING** vì chưa có runtime session.

### 6. Telemetry and artifacts

Notebook/runner chuẩn bị thu:

- hardware/runtime fingerprint trước setup;
- exact Java/MySQL/k6 versions và executable hashes;
- raw k6 JSON + full summary cho W1/W2;
- system CPU/RAM và per-process CPU/RSS/read/write bytes cho backend, MySQL và driver;
- backend stdout, dedicated JVM GC log;
- MySQL global connection/query/lock/buffer status và normalized Performance Schema digest trước/sau W1/W2/W3;
- W3 outcomes/final state, dataset snapshots và reset checksum;
- run manifest, `SHA256SUMS.txt`, cleanup result và evidence ZIP.

Live Hikari gauges vẫn unavailable; chỉ config lock và MySQL connection behavior được observed. Metric thiếu không được suy diễn.

### 7. Configuration and comparability lock

Kaggle configuration lock giữ cùng workload/load controls của G2.4: warm-up 60 s; W1 10/5/5 RPS và W2 10 VUs trong 180 s; W3 15 rounds; cooldown 30 s; minimum 3, target 5 runs. Kaggle smoke không chạy các duration này.

`compare_manifests.py` yêu cầu trùng CPU model, logical cores, cgroup CPU quota/cpuset, cgroup memory limit/resolved limits, OS/kernel/runtime image, exact Java/MySQL/k6 versions và binary hashes, configuration hash, workload-source hash và dataset checksum. Riêng host-visible `hardware.memory_total_bytes` có dung sai tuyệt đối tối đa 1 MiB: khác biệt vài page trong `MemTotal` là nhỏ so với bộ nhớ khả dụng thực tế, vốn được giới hạn bởi memory cgroup; dung sai này không áp dụng cho cgroup limit. Prefix đường dẫn executable theo run bị bỏ qua khi so sánh output phiên bản MySQL; nội dung version còn lại và SHA-256 của executable vẫn phải khớp. CPU model mismatch hoặc quota/resource limit mismatch vẫn làm run không cùng comparison group. Application SHA được báo thành treatment pair và được phép khác. Không normalize hoặc gộp các trường khác.

### 8. Implementation and static validation

Đã thêm:

- `kaggle/script/byteme_phase2_g24k.ipynb` — notebook mới, không ghi đè notebook lịch sử;
- `benchmarks/phase2/kaggle/kaggle_runtime.py` — rootless lifecycle/smoke/telemetry/evidence runner;
- `configuration-lock.json`, `prepare_bundle.ps1`, `compare_manifests.py`, generator và README;
- direct DB transport tùy chọn cho dataset generator và W3.

Python AST, PowerShell parser, JSON/notebook parsing và từng notebook code cell đều PASS. Bundle static dry-run PASS với baseline `application_sha 510f641…`, repository SHA `24b3ace…`, 14 files và 0 hash mismatch. Không có application/test/schema/production-config change.

### 9. G2.4-K status and blockers

| Criterion | Status |
|---|---|
| Kaggle-specific notebook and rootless adapter | **PASS — implemented/static validated** |
| W1/W2/W3 semantics retained | **PASS — static compatibility** |
| Standard profile retained | **PASS — definition** |
| Bundle provenance/checksum | **PASS — local dry-run** |
| Exact-version toolchain on real Kaggle | **PENDING** |
| MySQL/backend lifecycle on real Kaggle | **PENDING** |
| Smoke W1/W2/W3/reset/telemetry on real Kaggle | **PENDING** |
| Cross-session hardware equivalence evidence | **PENDING — requires at least two actual manifests** |

**Overall G2.4-K: PARTIAL.** Implementation is complete enough to attempt a real smoke, but runtime validation cannot pass without Kaggle access and exact portable toolchain inputs. This is an external execution blocker, not an application failure.

### 10. G2.5 readiness

Official G2.5 is **BLOCKED/PENDING on Kaggle runtime validation**. Trước G2.5 cần: upload private bundle/toolchain datasets; chạy notebook smoke thật; archive evidence ZIP; xác minh tool versions, W1/W2 checks, W3 completion, reset checksum và cleanup; sau đó chạy thêm session để kiểm tra hardware manifest comparability. Chỉ khi các bước này PASS mới freeze Kaggle comparison group và bắt đầu official Phase 1 baseline. Không có official load run nào được thực hiện trong G2.4-K.

### 11. Independent Code Review Remediation

Review độc lập được kiểm tra lại ngày 2026-11-20. Các finding sau đều tái hiện được trên code trước remediation; không có finding nào bị gắn PASS chỉ bằng suy luận.

| Finding | Recheck | Fix và trạng thái |
|---|---|---|
| P0 post-workload snapshot dùng initial invariants | **CONFIRMED** — canceled orders/empty cart rows hợp lệ làm `initial_carts_empty` và exact total items fail | **FIXED** — `initial` yêu cầu exact fixture/empty carts; `post_workload` cho phép mutation nhưng vẫn khóa read fixtures, cardinality, shared stock, positive quantity/non-negative stock và no-orphan |
| P0 k6 exit 0 có thể che failed checks | **CONFIRMED** — JS không có threshold bắt buộc nên process exit không đủ | **FIXED** — parse summary, assert exact smoke checks/requests, zero HTTP/workload/unexpected/server errors và raw output |
| Missing telemetry/cleanup vẫn có thể để status PASS | **CONFIRMED** | **FIXED** — resource file phải có sample cho backend/MySQL/driver; DB telemetry phải đủ header; reset checksum và cleanup/secret scan là PASS criteria; failure cố tạo evidence ZIP |
| W3 baseline defect vs harness failure | **CONFIRMED ambiguity** | **FIXED** — violation/HTTP 500 được giữ làm defect evidence; chỉ thiếu scenario/round/response/final-state làm harness fail |
| P1 chỉ dùng `os.cpu_count()`/`MemTotal` | **CONFIRMED** | **FIXED trong implementation** — capture cgroup v1/v2 CPU quota/period, effective cpuset, memory limit, resolved limits, kernel và runtime-image hash; comparator fail closed khi thiếu/khác. **Actual Kaggle values PENDING** |
| P1 builder nhận arbitrary JAR và bỏ sót staged/untracked drift | **CONFIRMED** | **FIXED** — builder tự chạy Maven Wrapper `clean package`, chặn staged/unstaged/untracked executable drift, lưu source/tree/build/JAR provenance và hỗ trợ reviewed future application SHA |
| Tar path check chưa xử lý link đầy đủ | **CONFIRMED** | **FIXED** — manual extraction chỉ cho regular file/directory và in-tree symlink/hardlink; reject special/path-escape entries |

Verification thực tế:

- **18/18 Python unit/adversarial tests PASS**: initial/post invariants, orphan rejection, valid/invalid k6 summaries, request-count mismatch, header-only telemetry, W3 defect semantics, cleanup/reset failure, failure ZIP, secret scan, malicious symlink/hardlink, cgroup v2 resolution và comparator missing/mismatched quota.
- PowerShell bundle parser PASS; adversarial untracked file dưới `src` bị từ chối và được xóa sau test.
- Maven Wrapper provenance build thực tế **PASS**, tests intentionally skipped cho packaging step; JAR SHA-256 và 17 bundle-file checksums khớp build/bundle manifests; runtime bundle resolution PASS.
- Application source/test/schema/seed/production configuration và baseline SHA không đổi. Không commit/tag/push và không chạy official benchmark.

Kaggle runtime validation vẫn **PENDING** vì không có Kaggle session/credential/toolchain input trong môi trường này. Overall G2.4-K vẫn **PARTIAL**; blockers còn lại là chạy notebook thật, xác minh portable toolchain/lifecycle/W1–W3/reset/telemetry và chứng minh hardware manifests tương đương giữa các session trước G2.5.

## G2.5.2 — Official Standard Benchmark Runner

G2.5.2 bổ sung execution layer riêng cho một official standard run trên Kaggle, không thay đổi
notebook hoặc hành vi smoke G2.4-K. Entrypoint `KaggleSession.run_official()` thực thi và ghi
evidence theo thứ tự: prepare standard; warm-up; W1; post snapshot/reset; W2; post
snapshot/reset; W3; post snapshot; cooldown; final reset. `official_benchmark=true` chỉ được ghi
khi protocol validation, ba reset checksum, telemetry, cleanup, secret scan, checksum manifest và
evidence packaging hoàn tất.

Warm-up được khóa read-only trong `configuration-lock.json`: 60 giây, food list 2 RPS, food
search 1 RPS và order list 1 RPS. Raw/summary/resource telemetry của warm-up nằm dưới
`warmup/` riêng và không được đưa vào metric W1/W2 chính thức. W1/W2/W3 vẫn giữ nguyên
measured semantics 180 giây 10/5/5 RPS, 180 giây 10 VUs và 15 rounds/scenario.

Official validation phân biệt harness failure với application outcome. HTTP/performance errors,
dropped iterations và W3/business consistency violations được lưu làm baseline evidence; thiếu
phase, duration/load lock, raw/summary, CPU/RSS, reset, cleanup hoặc integrity mới làm run invalid.
MySQL process I/O được phép là `NA` chỉ khi có sidecar unavailable evidence; không thay bằng 0.

Notebook riêng là `kaggle/script/byteme_phase2_g25_official.ipynb`, thực hiện đúng một run mỗi
fresh Kaggle CPU session và reuse bootstrap/toolchain G2.4-K. Comparator CLI đã sửa exit status
để dùng kết quả `comparable` thay vì biến ngoài scope. Multi-run aggregation mở rộng vẫn dành
cho G2.5.4.

Local regression/acceptance verification: **83 PASS, 0 FAIL, 3 SKIP, 0 ERROR**. Ba SKIP là hai
procfs Linux integration tests và một Windows hardlink privilege test; Kaggle official Run 01
chưa được chạy trong G2.5.2.



## G2.5.4 - Intel BEFORE Multi-run Aggregation and Baseline Lock

**Status: COMPLETE for the BEFORE aggregation gate.** The selected official comparison group is the Intel Xeon group (Runs 02, 04, 05). Each ZIP passed CRC and all 62 SHA256SUMS entries, official status/classification/harness checks, the three reset checksum checks, raw W1/W2-to-validation counter checks, W3 scenario/round coverage, CPU/RSS telemetry coverage, cleanup and secret scan. All three pairwise comparisons passed the current manifest comparator. The 4,096-byte MemTotal difference is within the documented 1 MiB allowance; CPU model, quota, cpuset, cgroup memory limit, OS/kernel/runtime image, toolchain, application/JAR SHA and configuration/workload/dataset locks match.

| Run | ZIP SHA-256 | CPU | MemTotal bytes | W1/W2 | W3 findings |
|---|---|---|---:|---|---|
| 02 | `7a2eec7738c972f4fba2706be5daa4c49781a59d04e6670362d2558e455f6a17` | Intel Xeon @ 2.20GHz | 33,658,155,008 | W1 3,602; W2 82,726 requests; 10 business rejections; 0 server errors | Admin-stock invariant violation in 12/15 rounds; same-cart server error in 1 round |
| 04 | `9379e5661e7fd292230f4abec109b8f29b5034fbb0c1e092b8f7e9d0b0a7a51f` | Intel Xeon @ 2.20GHz | 33,658,159,104 | W1 3,603; W2 62,443 requests; 15 business rejections; 0 server errors | Admin-stock invariant violation in 12/15 rounds |
| 05 | `c2925ebc19f8d23dd242cdc12d8f2922631739dacf569b23b859ae1c9c0222cf` | Intel Xeon @ 2.20GHz | 33,658,155,008 | W1 3,602; W2 68,928 requests; 4 business rejections; 0 server errors | Admin-stock invariant violation in 13/15 rounds |

Runs 01 and 03 are valid accepted AMD evidence and remain preserved, but are excluded from this Intel aggregation because the comparator reports `hardware.cpu_model` (AMD EPYC 7B12 vs Intel Xeon). Their evidence ZIP SHA-256 values are recorded in the JSON report. No AMD and Intel values are pooled. W2 business rejections and W3 invariant/server-error findings remain application outcomes and were retained as baseline results; they did not invalidate the harness or evidence.

The baseline lock has **minimum_runs=3 met (n=3)**. `target_runs=5` is not met; this is recorded as a remaining stretch target and does not block the minimum-run baseline lock. AFTER measurements must be made on a Kaggle CPU session whose manifest passes the same comparator against this locked Intel group. Do not compare or aggregate an AMD AFTER result with this baseline.

Deliverables:

- `docs/phase2/evidence/g2.5/2026-11-21/before-baseline-intel.md`
- `docs/phase2/evidence/g2.5/2026-11-21/before-baseline-intel.json`

Aggregator verification: 14 focused tests pass; module/test `py_compile` passes; official evidence was aggregated directly from the three immutable ZIPs. No benchmark was run and no source application, benchmark protocol, dataset, workload, or evidence archive was changed. G2.5 BEFORE acceptance, multi-run aggregation and baseline lock are complete; the five-run target remains unmet, and AFTER/G3 work is outside this lock.
