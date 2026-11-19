# ByteMe Phase 2 — System Assessment

Ngày hoàn tất khảo sát: 2026-11-17. Đây là entry point của Giai đoạn 1 và Final System Assessment Review. Phân tích chi tiết được bảo toàn trong tám tài liệu chuyên đề; file này chỉ tổng hợp kết quả kiểm toán, findings, nguyên nhân gốc và các exit gate.

## 1. Project & Assessment Overview

ByteMe là backend đặt món cho một nhà hàng, triển khai dưới dạng một Spring Boot layered monolith kết nối MySQL. Phạm vi hiện hành có ba role `CUSTOMER`, `EMPLOYEE`, `ADMIN`, 18 use case/18 endpoint, hỗ trợ menu, cart, checkout và vòng đời order. Stack tĩnh đã xác minh gồm Java 21, Spring Boot 3.5.16, Maven Wrapper 3.9.11, Spring Web/Data JPA/Security, JWT RS256, MySQL 8.4 và Docker Compose.

Giai đoạn 1 đã khảo sát đủ tám hạng mục: nghiệp vụ, kiến trúc, source, database, API, security, Docker/configuration và testing. Mục tiêu là tạo baseline hiểu biết có bằng chứng trước khi lựa chọn thuộc tính chất lượng hoặc giải pháp cải tiến Pha 2; assessment không tự chọn microservices, Kubernetes, Redis hay một kiến trúc đích.

Nguồn yêu cầu và baseline ban đầu: [00_REQUIREMENTS_AND_BASELINE.md](00_REQUIREMENTS_AND_BASELINE.md).

## 2. Scope & Assessment Methodology

- Đối chiếu tài liệu với repository thực tế; source/config/test là bằng chứng ưu tiên khi tài liệu cũ khác implementation.
- Truy vết nghiệp vụ theo Controller → Service → Repository → Entity; phân tích dependency/import, transaction, schema, API/security policy và deployment configuration.
- Thống kê source/test theo phương pháp được ghi ngay trong chuyên đề; không suy đoán line/branch coverage.
- Chỉ thực hiện static assessment. Không build JAR/image, không chạy test/container/database/benchmark/scanner và không triển khai hệ thống.
- Nhận định runtime, capacity, concurrency, vulnerability và pass/fail chỉ được xác nhận khi có execution artifact phù hợp.
- Finding được deduplicate ở Final Review theo nguyên nhân gốc; finding chuyên đề vẫn giữ nguyên ID, trạng thái và bằng chứng.

Quy ước:

- **CONFIRMED**: có bằng chứng trực tiếp trong repository ở đúng mức được nêu; có thể là đặc tính tích cực, gap hoặc design issue, không mặc định là defect.
- **PENDING**: thiếu execution evidence, provenance hoặc quyết định cần thiết để kết luận.
- **POTENTIAL ISSUE**: có cơ sở tĩnh cho rủi ro nhưng chưa tái hiện/định lượng impact runtime.

## 3. Assessment Documents & Completion Status

| # | Chuyên đề | Trạng thái | Kết quả chính |
|---:|---|---|---|
| 1 | [Business & Functional Assessment](<System Assessment/01_BUSINESS_ASSESSMENT.md>) | **COMPLETE** | 18/18 UC có implementation path; business rules và mismatch tài liệu đã được truy vết. |
| 2 | [Architecture Assessment](<System Assessment/02_ARCHITECTURE_ASSESSMENT.md>) | **COMPLETE** | Layered monolith/package-by-layer; một cycle `service ↔ repository`; transaction/component diagrams As-Is. |
| 3 | [Source Code Assessment](<System Assessment/03_SOURCE_CODE_ASSESSMENT.md>) | **COMPLETE** | 69 files, 1.667 source LOC; hotspot/coupling/duplication/error/testability đã được định vị. |
| 4 | [Database Assessment](<System Assessment/04_DATABASE_ASSESSMENT.md>) | **COMPLETE** | 7 bảng; mapping/constraints/transactions/lifecycle/query và năm concurrency scenario đã được đánh giá tĩnh. |
| 5 | [API Assessment](<System Assessment/05_API_ASSESSMENT.md>) | **COMPLETE** | 18 endpoints và 18 OpenAPI operations khớp path-method; contract gaps và retry semantics được ghi nhận. |
| 6 | [Security Assessment](<System Assessment/06_SECURITY_ASSESSMENT.md>) | **COMPLETE** | JWT/RBAC/ownership/input controls có nền tảng; lifecycle, deployment trust và runtime assurance còn mở. |
| 7 | [Docker & Configuration Assessment](<System Assessment/07_DOCKER_CONFIGURATION_ASSESSMENT.md>) | **COMPLETE** | Multi-stage/non-root deployment; config drift, operations và Kaggle reproducibility gaps đã rõ. |
| 8 | [Testing Assessment](<System Assessment/08_TESTING_ASSESSMENT.md>) | **COMPLETE** | 14 test files, 12 classes, 90 JUnit methods; traceability 18/18 endpoint và test gaps đã được lập. |

**Giai đoạn 1: 8/8 assessment complete.** “Complete” ở đây là hoàn tất khảo sát tĩnh, không đồng nghĩa Phase 1 đã được runtime-verified.

## 4. Final System Assessment Review

### 4.1. Overall assessment

Kiến trúc As-Is là một layered monolith phù hợp với phạm vi một nhà hàng, nhóm hai người và thời gian 3–4 tuần: một deployable, luồng đồng bộ ngắn, responsibility theo tầng tương đối rõ, transaction tập trung ở service và MySQL giữ FK/unique chính. Không có bằng chứng cho thấy cần phân rã thành microservices ở thời điểm review.

Nền tảng chức năng tương đối hoàn chỉnh ở mức tĩnh: 18/18 UC và endpoint tồn tại; checkout dùng server-side cart/price snapshot; order state machine, cancellation stock restore, RBAC và ownership đều có source/test evidence. OpenAPI bao phủ 18/18 operation. Docker runtime chạy non-root và test source có 32 methods dùng MySQL thật.

Các giới hạn quyết định chất lượng chưa nằm ở số lượng chức năng mà ở khả năng kiểm chứng và tính nhất quán khi thay đổi/tải cạnh tranh:

1. Concurrency correctness chưa có lock/version hoặc năm integration scenario cần thiết; chưa được gọi là defect cho tới khi tái hiện.
2. Baseline Kaggle thiếu provenance có thể resolve, raw outputs, exact versions, reset/warm-up/repetition và resource telemetry.
3. Artifact build/benchmark chưa gắn với một test/CI gate; 90 test methods chưa có current report.
4. Schema/seed/volume không có versioned migration/reset lifecycle; clean deployment và repeated run chưa được bảo đảm.
5. Package cycle, DTO/entity coupling, OrderService hotspot và static contract governance làm tăng change surface, nhưng impact thực tế cần gắn với quality attribute được chọn.
6. JWT/key lifecycle, TLS/proxy, secret/sample-data policy và security observability phụ thuộc target deployment chưa được chốt.

### 4.2. Decision posture

- Có đủ bằng chứng để bắt đầu chọn quality attribute và thiết kế thí nghiệm Pha 2.
- Chưa đủ bằng chứng để tuyên bố Phase 1 verified, benchmark hiện tại reproducible hoặc một performance/reliability/security target đã đạt.
- Không nên chọn giải pháp kiến trúc trước khi khóa baseline, acceptance criteria và workload đại diện.
- Reliability/consistency và reproducibility/measurement readiness là các gate cấp cao; performance bottleneck cụ thể vẫn **PENDING** profiling/benchmark đúng provenance.

## 5. Consolidated Findings Register

Sáu chuyên đề có numbered findings, tổng cộng **70 finding IDs**: **36 CONFIRMED**, **26 POTENTIAL ISSUE**, **8 PENDING/mixed**. Business và Architecture giữ findings dạng bảng không đánh số; các issue lặp đã được chuyển tiếp sang SC/DB/API/SEC2/TEST thay vì tạo ID mới.

| Register | IDs | Tổng | Confirmed | Potential | Pending/mixed | Chi tiết |
|---|---|---:|---:|---:|---:|---|
| Source code | `SC-01`–`SC-10` | 10 | 5 | 4 | 1 | [Source Code Findings](<System Assessment/03_SOURCE_CODE_ASSESSMENT.md>) |
| Database | `DB-01`–`DB-12` | 12 | 5 | 5 | 2 | [Database Findings](<System Assessment/04_DATABASE_ASSESSMENT.md>) |
| API | `API-01`–`API-10` | 10 | 6 | 3 | 1 | [API Findings](<System Assessment/05_API_ASSESSMENT.md>) |
| Security | `SEC2-01`–`SEC2-11` | 11 | 2 | 8 | 1 | [Security Findings](<System Assessment/06_SECURITY_ASSESSMENT.md>) |
| Docker/configuration | `DEP-01`–`DEP-14` | 14 | 9 | 4 | 1 | [Docker & Configuration Findings](<System Assessment/07_DOCKER_CONFIGURATION_ASSESSMENT.md>) |
| Testing | `TEST-01`–`TEST-13` | 13 | 9 | 2 | 2 | [Testing Findings](<System Assessment/08_TESTING_ASSESSMENT.md>) |
| **Total** | **70 unique IDs** | **70** | **36** | **26** | **8** | Không mất/trùng ID sau khi tách. |

Các finding informational/positive như API-01, DB-01/03, TEST-13 vẫn nằm trong register để bảo toàn traceability; tổng số finding không phải tổng số defect.

## 6. Root-Cause Analysis

Final review quy 70 findings và các issue không đánh số về **11 root-cause clusters độc lập**. Mapping dưới đây dùng “primary cause”; một finding có thể ảnh hưởng nhiều quality attributes nhưng chỉ được đặt ở cụm nguyên nhân chính để tránh double counting.

| Root cause | Mô tả | Findings đại diện | Hệ quả chính |
|---|---|---|---|
| RC-01 — Layer boundary erosion | Auth adapter phụ thuộc service exception; service dùng transport DTO/JPA-backed model; error/common conventions pha trộn. | SC-01/02/05/06/07, TEST-04 | Maintainability, modifiability, architecture enforcement. |
| RC-02 — Orchestration/complexity concentration | Order/Food/Cart và security/config logic tập trung, code nén và test feedback không đồng đều. | SC-03/04/08, TEST-11 | Change surface, readability, testability. |
| RC-03 — Concurrency policy/protection chưa xác định | Không lock/version; loser/idempotency semantics chưa chốt cho checkout/cancel/cart/admin stock. | DB-05/12, API-02, TEST-05 | Reliability, integrity, retry behavior. |
| RC-04 — Query/data-growth uncertainty | Search/filter/sort/count và lazy order items chưa có index/query-count/cardinality evidence. | SC-09, DB-06/07, API-07 | Performance, scalability. |
| RC-05 — Schema/seed lifecycle thủ công | SQL-first không migration history; seed non-idempotent; volume/notebook không reset/upgrade có version. | DB-01/02/08/09/10, DEP-05/12 | Deployability, consistency, reproducibility. |
| RC-06 — Contract governance thiếu automated gate | Static OpenAPI/tài liệu/controller có detail drift; compatibility, role metadata và retry contract chưa được quản trị tự động. | API-03/04/05/06/08/09/10, TEST-02/03 | API correctness, maintainability, compatibility. |
| RC-07 — Token/security policy lifecycle chưa hoàn chỉnh | Stale token, rotation/revocation, deny-by-default, registration abuse, password/audit/advisory policy chưa chốt/test đủ. | SEC2-01/02/03/05/09/10/11, TEST-06 | Security, authorization, incident response. |
| RC-08 — Deployment trust boundary chưa được đặc tả | Per-node limiter/client IP, TLS/proxy, secrets/sample accounts và key-file ACL phụ thuộc môi trường. | SEC2-04/06/07, DEP-06/07/08 | Confidentiality, abuse resistance, deployability. |
| RC-09 — Artifact/toolchain provenance và CI gate thiếu | Mutable tags/packages, manual artifact upload, test-skipping packaging, không CI/SBOM/manifest đầy đủ. | SEC2-08, DEP-01/02/09/10/11/13, TEST-10/12 | Reproducibility, supply-chain assurance, release confidence. |
| RC-10 — Runtime operations/config drift | Compose/Kaggle lệch JVM/pool/thread; thiếu backend health/restart/resource/log policy và resolved runtime evidence. | DEP-03/04/14 | Reliability, performance comparability, operability. |
| RC-11 — Verification/observability evidence thiếu | Test source chưa có official report/coverage/repetition; benchmark thiếu representative writes, raw/resource metrics và statistical protocol. | SC-10, DB-11, TEST-01/07/08/09/13 | Assurance, benchmark validity, defect detection. |

## 7. Quality Attribute Mapping

| Quality attribute | Evidence tích cực | Rủi ro/gap chính | Trạng thái Final Review |
|---|---|---|---|
| Functional suitability | 18/18 UC/endpoint có implementation; business rules/state machine rõ. | 7 UC còn partial JUnit happy-path HTTP assertion; một số tài liệu cũ lệch chi tiết. | **CONFIRMED static / PENDING runtime**. |
| Maintainability | Package/tên/trách nhiệm rõ; DI, centralized errors/security, ArchUnit source. | RC-01/02, package cycle, hotspot, contract drift; ArchUnit không bắt cycle. | **Medium risk**, có bằng chứng tĩnh. |
| Modifiability | Monolith nhỏ, một deployable; Auth có một số ports. | Feature trải qua package-by-layer; DTO/entity coupling và không có compatibility policy. | **POTENTIAL ISSUE**, cần change-impact theo mục tiêu Pha 2. |
| Testability | 90 JUnit methods; mocks, fixed clocks, MockMvc, MySQL Testcontainers. | Không current report/coverage; five races, JWT matrix, contract sync và query count thiếu; shared-state risk. | **Source ready / execution PENDING**. |
| Reliability & consistency | Transaction boundary, FK/unique, rollback test source. | RC-03/05; startup/recovery/parallel behavior chưa test. | **High-priority verification gap**. |
| Performance | Workload k6 và một baseline report tồn tại; request path đồng bộ đơn giản. | RC-04/10/11; baseline provenance/config/resource evidence thiếu. | **PENDING**, chưa xác định bottleneck tin cậy. |
| Security | RS256, BCrypt, exact claim validation, RBAC/ownership, bounded inputs, non-root container. | RC-07/08; deployment/rotation/revocation/audit/advisory verification chưa đủ. | **Strong static foundation / deployment-dependent risk**. |
| Scalability | Stateless bearer auth ở application path. | Một backend/MySQL, per-JVM limiter, unpaginated menu/search, unknown query behavior. | **PENDING**; không có nhu cầu scale-out đã xác nhận. |
| Deployability & operability | Multi-stage JRE image, non-root, MySQL health gate, loopback local ports. | RC-05/08/09/10; backend health/restart/log/resource/migration policy thiếu. | **Local-ready by design / production readiness PENDING**. |
| Reproducibility | Source/config/notebook/test instructions có trong repo. | Provenance, versions/digests/checksums, DB reset, warm-up, repetitions và output retention chưa khóa. | **Blocking before/after conclusions**. |

## 8. Verification Backlog

### P0 — bắt buộc trước khi dùng baseline hoặc chốt cải tiến Pha 2

1. **Baseline provenance:** quyết định khôi phục run `ed8be73` hay rerun; chọn full source SHA, clean state và mốc bất biến; tạo manifest/checksum cho JAR/schema/seed/notebook/workload.
2. **Official test gate:** chạy đúng SHA với expected 90 JUnit tests, phân loại fail/error/skip, lưu Surefire reports; chạy black-box API và xác minh cleanup. Không dùng “rerun until green”.
3. **Benchmark protocol:** khóa Kaggle CPU/environment, Java/MySQL/k6 versions, JVM/Hikari/Tomcat settings, dataset/cardinality, DB reset, readiness/warm-up, stages/think time, repetitions và statistical reporting.
4. **Artifact retention:** giữ raw k6 CSV/summary, notebook output, server/DB/resource logs, test reports, tool versions và manifest với checksum.
5. **Concurrency semantics:** chốt expected behavior cho năm race; chạy integration tests MySQL thật với barrier và final DB-state assertions trước khi tuyên bố consistency improvement.

### P1 — bắt buộc nếu quality attribute tương ứng được chọn

6. Query count/`EXPLAIN ANALYZE` cho order list và food search trên dataset đại diện; xác minh N+1/index/cardinality trước khi tối ưu.
7. Contract-sync/role-matrix gate nếu Phase 2 thay API/DTO/security; chốt 404 path-ID, status retry/idempotency và compatibility policy.
8. Deployment security contract nếu expose ngoài local: TLS termination, trusted proxy/client IP, secrets/sample-data removal, key ACL/rotation/revocation và audit events.
9. Failure/recovery tests nếu reliability/operability là mục tiêu: DB unavailable, restart, OOM/disk/log retention, graceful shutdown và backend readiness.

### P2 — debt có thể lên kế hoạch sau khi có mục tiêu đo

10. Đánh giá refactor package cycle, error conventions, DTO/entity boundary và hotspot bằng change/test evidence; không refactor chỉ dựa vào kích thước.
11. Chốt coverage tool/threshold, test parallel policy và flaky-test protocol nếu dùng làm quality gate.

## 9. Readiness & Exit Criteria

### Giai đoạn 1 exit criteria

- [x] Hoàn thành 8/8 specialist assessments với source evidence, findings, conclusions và pending questions.
- [x] Tách tám chuyên đề không mất nội dung; giữ entry point cũ hoạt động.
- [x] Kiểm toán đủ 70 finding IDs và gom thành 11 root-cause clusters.
- [x] Hoàn thành Final System Assessment Review và quality-attribute mapping.
- [x] Lập verification backlog và gate trước benchmark/cải tiến.
- [ ] **PENDING** — official build/test/black-box results trên source SHA được chọn.
- [ ] **PENDING** — verified immutable Phase 1 baseline và đầy đủ benchmark provenance/artifacts.
- [ ] **DECISION** — quality attribute ưu tiên, acceptance criteria, concurrency/security semantics và benchmark protocol.

**Kết luận readiness:** Giai đoạn 1 **hoàn thành về khảo sát và tài liệu**. Dự án sẵn sàng bước vào hoạt động ra quyết định đầu Giai đoạn 2, nhưng chưa sẵn sàng triển khai hoặc tuyên bố hiệu quả cải tiến cho tới khi các mục P0 được đóng. Final review không chọn kiến trúc cải tiến.

## 10. Documentation Integrity Audit

File gốc trước khi tái cấu trúc có 233.241 byte, SHA-256 `64FF240B45132B2ABD167B869B8AF43D4BE1EA9B3686395AE799DCB11D15C6FE`. Phần từ `## 1` đến EOF có 232.011 byte, SHA-256 `C4E6485170E4E5B27DEA6AC96D82D377B0058A7DCEB2862B358EA12A55EDFFEF`. Ngay sau khi tách, phép ghép tám file theo thứ tự 01→08 cho đúng 232.011 byte và cùng SHA-256, chứng minh không mất nội dung.

Sau kiểm tra Markdown, một chỉnh sửa trình bày tối thiểu được áp dụng: escape hai ký tự pipe trong inline code `\|\| true` tại bảng Kaggle để không bị parser hiểu là cột mới. Thay đổi thêm đúng hai backslash, không đổi ý nghĩa. Bộ tám file sau chỉnh sửa có 232.013 byte, SHA-256 `154EE93869FC0636FD3711C01DDD9480E46B90E4DB57C5FEC4B97143F2AEB42E`.

| File | Bytes | SHA-256 |
|---|---:|---|
| `01_BUSINESS_ASSESSMENT.md` | 19.535 | `DEA8E314AABAC28FCC615D1CBF1B05EF21AE64242595670EB62BCBEA2777334F` |
| `02_ARCHITECTURE_ASSESSMENT.md` | 28.708 | `E129E3CE410826C157DCB910AE758BDC25AC134FDDC647EF146D6297F685A4C6` |
| `03_SOURCE_CODE_ASSESSMENT.md` | 23.306 | `CCC7F881C42DFAD00AF1A49A209C7E54BD5B628682D10DFE9885D38AD81F3360` |
| `04_DATABASE_ASSESSMENT.md` | 28.097 | `37E6A257C30324E9FF3CBE27C4AD349809798BC4372CA7AD07815AE414530DAE` |
| `05_API_ASSESSMENT.md` | 26.707 | `A8DD4B77211647558CEF43551C16057337DEE430D95540E69F3CAAA4FFBC9C25` |
| `06_SECURITY_ASSESSMENT.md` | 36.763 | `8C569DD923EE8036CAF8F2ACD06ABAFC0FD7D75A8DF8AEEBB1747164AC594B18` |
| `07_DOCKER_CONFIGURATION_ASSESSMENT.md` | 29.301 | `42B35AC6703B94F0E5A9702279AA718D13E7B6BDAC37BC86CD56AE7EECE86DCB` |
| `08_TESTING_ASSESSMENT.md` | 39.596 | `B9CD82B2A1025286182D68CE3ACC3765737F7C7D8BE9F0F00FC681E113E64F40` |

Ngoài escape Markdown nêu trên, không chỉnh nội dung chuyên đề, finding ID, source citation, bảng hay Mermaid diagram trong quá trình tách. Không có Markdown link cũ bên trong file nguồn cần rewrite; các link mới dùng destination bọc `<...>` để xử lý thư mục có khoảng trắng.
