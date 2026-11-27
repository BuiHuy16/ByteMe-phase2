# ByteMe Phase 2 — Task Tracker

- **Tracking window:** 22/11/2026–09/12/2026
- **Last planning update:** 23/11/2026
- **Last G3 evidence reconciliation:** 28/11/2026
- **Status vocabulary:** `TODO`, `IN_PROGRESS`, `IN_REVIEW`, `BLOCKED`, `DONE`
- **Roadmap:** [ROADMAP.md](ROADMAP.md)

G0–G2 đã hoàn thành và không được tạo lại thành task. Bốn ADR và bốn implementation plans được chấp thuận bằng quyết định dự án ngày 28/11/2026; quyết định này thay yêu cầu xác nhận riêng của từng thành viên và không được ghi thành review cá nhân. Bản approved đã được merge/publish qua PR #4; G3-04 và M1 hoàn tất, nên các dependency G4 trỏ tới G3-04 đã được mở khóa. Status chỉ được cập nhật từ evidence thực tế.

## 1. G3 — Approval and planning closeout

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3-01 | G3 | Review ADR-001/002/003/004 | Review pessimistic locking, two-step fetch, dependency boundaries, fail-closed authorization, trade-offs và acceptance | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-23 | 2026-11-23 | P0 | — | Decision record cho 4 ADR | Quyết định dự án ghi rõ bốn phương án được chấp thuận, cơ sở và ngày quyết định; không tạo review cá nhân giả | DONE |
| G3-02 | G3 | Review implementation plans | Review scope, file/method ownership, timeout/isolation, exception mapping, authorization matrix, tests và gates của bốn plan | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-23 | 2026-11-24 | P0 | — | Approved plans/checklist | Bốn plan `APPROVED`; không còn chi tiết implementation mơ hồ ảnh hưởng G4; owner/reviewer và C/D shared-test contract rõ | DONE |
| G3-03 | G3 | Approve coordination contract | Chốt owners, method ownership, parallel coding, A→B→C→D merge và Git workflow | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-24 | 2026-11-24 | P0 | G3-01, G3-02 | Recorded coordination decision | Quyết định ngày 28/11/2026 giữ nguyên owners/reviewers, method ownership, acceptance và merge order A→B→C→D | DONE |
| G3-04 | G3 | Publish approved G3 docs | Cập nhật status `ACCEPTED`/`APPROVED` theo quyết định thực tế và publish tài liệu approved | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-24 | 2026-11-24 | P0 | G3-03 | Published approved G3 documentation commit | Bản approved được merge/publish; links/files đúng; merge hoặc commit SHA mới được ghi | DONE |

### Decision và publication record G3 ngày 28/11/2026

Người có thẩm quyền quyết định dự án đã chấp thuận nguyên trạng ADR-001…004 và bốn implementation plans trong tài liệu, không yêu cầu xác nhận riêng của từng thành viên. Cơ sở này hoàn tất G3-01…03 nhưng không được mô tả thành review, approval hoặc chữ ký cá nhân của Bùi Công Huy hay Nguyễn Văn Huy Hoàng.

[PR #2 — tài liệu G3](https://github.com/BuiHuy16/ByteMe-phase2/pull/2), merge SHA `8668a29a8ccae80afc8ec288f56fa84f4425dbe6`, đã publish bản `PROPOSED`/`PENDING_TEAM_APPROVAL` trước quyết định. Bản approved sau đó được merge từ `docs/update-context` vào `main` qua [PR #4](https://github.com/BuiHuy16/ByteMe-phase2/pull/4) lúc 00:25:01 ngày 28/11/2026 (UTC+07), merge SHA `db39c50d9a8d9d53d2c41d026729e5e7905249aa`. Git xác nhận commit approval `dac1293` là ancestor của `main`; PR #4 chứa Architecture Decisions, Git Workflow, Roadmap, Task Tracker và bốn implementation plans. G3-04 và M1 `DONE`; các task G4 phụ thuộc G3-04 được phép bắt đầu theo trạng thái và ownership riêng.

## 2. G4-A — Pessimistic locking

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G4-A-01 | G4-A | Targeted concurrency test skeleton | Tạo C1/C2/C4, rollback và lock-contention tests trước implementation | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-25 | 2026-11-25 | P0 | G3-04 | Failing targeted test suite | Tests tái hiện/bao phủ invariant, dùng barrier/latch và final DB assertions | TODO |
| G4-A-02 | G4-A | Repository locking methods | Thêm Cart/Food/Order pessimistic locking queries theo lock order | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-25 | 2026-11-26 | P0 | G4-A-01 | Repository lock implementation | `PESSIMISTIC_WRITE`, Food IDs ascending, no unrelated repository change | TODO |
| G4-A-03 | G4-A | Verify NO_WAIT on MySQL | Chứng minh `lock.timeout=0` fail-fast và maps typed exception | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-27 | 2026-11-27 | P0 | G4-A-02 | Runtime test evidence | Contender không chờ DB default; conflict không thành 500; nếu fail thì ADR review | TODO |
| G4-A-04 | G4-A | Locked cart snapshot | Khóa Cart trước đọc items và giữ lock tới checkout commit/rollback | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-27 | 2026-11-28 | P0 | G4-A-02, G4-A-03 | Cart checkout lock path | Same-cart overlap có tối đa một commit; empty-cart semantics giữ nguyên | TODO |
| G4-A-05 | G4-A | Batch stock reserve/release | Lock distinct Food IDs ASC, validate-all-before-mutate, batch reserve/release | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-28 | 2026-11-29 | P0 | G4-A-02, G4-A-03 | Food mutation implementation | Không partial mutation; missing/inactive/insufficient codes giữ nguyên | TODO |
| G4-A-06 | G4-A | Integrate mutation transactions | Cập nhật checkout, admin update/delete và Order transitions/cancel | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-30 | 2026-11-30 | P0 | G4-A-04, G4-A-05 | End-to-end service implementation | Lock graph đúng; sequential behavior/snapshot/rollback không đổi | TODO |
| G4-A-07 | G4-A | Conflict handling and API docs | Chuẩn hóa 409 `CONCURRENT_UPDATE`, no-store/no retry; cập nhật spec nếu thiếu | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-01 | 2026-12-01 | P1 | G4-A-06 | Error mapping + contract diff | Expected contention không 5xx; success schema không đổi; không lộ DB message | TODO |
| G4-A-08 | G4-A | Targeted and regression gate | Chạy targeted unit/web/MySQL suites và regression liên quan | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-01 | 2026-12-01 | P0 | G4-A-03, G4-A-06, G4-A-07 | Test reports + reviewed result | C1/C2/C4/rollback pass; NO_WAIT proof pass; không unresolved P0 | TODO |
| G4-A-09 | G4-A | PR review and merge | Mở PR, xử lý review, merge A trước B | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-02 | 2026-12-02 | P0 | G4-A-08, G4-B-07 | Merged G4-A PR | Reviewer approves; CI/local required gates pass; merge SHA recorded | TODO |

## 3. G4-B — Two-step fetching

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G4-B-01 | G4-B | Query-count and pagination test skeleton | Tạo baseline N+1/query count và page/contract fixtures | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-25 | 2026-11-26 | P0 | G3-04 | Failing query-count test suite | Page 1/5/20/50 có items; N+1 được phát hiện; fixtures cover scope/order | TODO |
| G4-B-02 | G4-B | Page-ID query | Implement scoped/filter/sorted Order ID page query | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-26 | 2026-11-27 | P0 | G4-B-01 | Repository page-ID method | Chỉ ID query paginate; sort `createdAt DESC,id DESC`; count không ẩn | TODO |
| G4-B-03 | G4-B | Bulk fetch Orders and items | Implement non-paginated left fetch cho IDs, root de-duplication | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-27 | 2026-11-28 | P0 | G4-B-02 | Fetch-with-items method | Zero-item Order còn tồn tại; không lazy item query/order | TODO |
| G4-B-04 | G4-B | Deterministic assembly | Implement validate/reorder, DTO mapping và count trong one read-only transaction | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-28 | 2026-11-29 | P0 | G4-B-02, G4-B-03 | Updated `OrderService.list` | Output order/page/count/DTO unchanged; missing/duplicate IDs fail clearly | TODO |
| G4-B-05 | G4-B | Pagination and contract tests | Cover empty, zero/multi-item, ties, page boundary, filter, ownership, API compatibility | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-29 | 2026-11-30 | P0 | G4-B-04 | Unit/MySQL contract tests | Không duplicate/missing; item/root order, total, fields và scopes đúng | TODO |
| G4-B-06 | G4-B | Query-count acceptance | Prove non-empty page 3 app SELECT/captured total ≤4 và no N+1 | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-30 | 2026-12-01 | P0 | G4-B-04, G4-B-05 | Query-count report | Count hằng ở size 1/5/20/50; SQL không lặp `order_id=?` theo N | TODO |
| G4-B-07 | G4-B | Cross-review G4-A | Review lock graph, conflict semantics và shared-file ownership trước A merge | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-01 | 2026-12-02 | P0 | G4-A-08 | G4-A PR review | Blocking findings resolved; approval recorded without editing A-owned methods | TODO |
| G4-B-08 | G4-B | Rebase and integration tests | Rebase B sau A merge, resolve shared imports/methods và rerun targeted A+B | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-02 | 2026-12-02 | P0 | G4-B-06, G4-A-09 | Rebasing/integration evidence | A locks preserved; A+B targeted/impacted regression pass; no scope drift | TODO |
| G4-B-09 | G4-B | PR review and merge | Mở/finalize PR B, xử lý review và merge | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-02 | 2026-12-02 | P0 | G4-B-08 | Merged G4-B PR | Reviewer approves; query/pagination/API gates pass; merge SHA recorded | TODO |

### Local dependency evidence G4-B

Local dependency gate chỉ cho phép triển khai tuần tự các task G4-B trên cùng branch trước khi push; đây không phải status mới và không làm thay đổi progress summary. Predecessor đủ local gate khi có commit gắn Task ID và acceptance kỹ thuật đã được kiểm tra. Status chỉ chuyển theo Update rules và Git workflow hiện hành; review trước merge cùng thứ tự A → B → C → D giữ nguyên.

- G4-B-01: local commit `5323603`; query-count/pagination test skeleton đạt acceptance kỹ thuật với fixtures page size 1/5/20/50, phát hiện N+1 và bao phủ scope/order. G4-B-02 được mở local dependency gate; G4-B-01 vẫn `TODO` cho đến khi đủ điều kiện push/evidence/review của Git workflow.
- G4-B-02: local commit `d3f499d`; page-ID query đạt acceptance kỹ thuật với owner/status/type scope, stable sort `createdAt DESC, id DESC`, pagination chỉ trên ID query và không có count ẩn. G4-B-03 được mở local dependency gate; G4-B-02 vẫn `TODO` cho đến khi đủ điều kiện push/evidence/review của Git workflow.

## 4. G4-C — Dependency boundaries

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G4-C-01 | G4-C | Architecture baseline and failing rules | Thêm ArchUnit rules cho `repository → service` và top-level package cycles; lưu BEFORE failure | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-25 | 2026-11-26 | P0 | G3-04 | Failing architecture-test evidence | Baseline chứng minh đúng 1 cycle và 2 reverse imports; không exclude package để làm xanh | TODO |
| G4-C-02 | G4-C | Repository exception contract | Thêm repository-local exceptions cho persistence failure và duplicate account | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-26 | 2026-11-26 | P0 | G4-C-01 | Repository exception types | Exceptions không import service/controller, không chứa HTTP concern và giữ cause | TODO |
| G4-C-03 | G4-C | Remove adapter reverse dependency | Chuyển `MySqlAccountRepository` sang repository exceptions, giữ vendor duplicate detection | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-27 | 2026-11-27 | P0 | G4-C-02 | Clean repository adapter | `MySqlAccountRepository` có 0 service import; mapping/entity/transaction behavior không đổi | TODO |
| G4-C-04 | G4-C | Map repository failures in services | Map duplicate/general repository exceptions tại `RegisterService`/`LoginService` sang service exceptions hiện hữu | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-28 | 2026-11-28 | P0 | G4-C-03 | Service exception mapping | Duplicate/general errors giữ type/cause semantics; validation/login behavior không đổi | TODO |
| G4-C-05 | G4-C | Auth regression and API behavior | Cập nhật/chạy Auth unit, web và MySQL integration cases cho duplicate/persistence paths; chỉ sửa C-owned methods | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-29 | 2026-11-30 | P0 | G4-C-04 | Auth regression evidence | Duplicate vẫn `409 ACCOUNT_CONFLICT`; no-store/payload policy giữ nguyên; DB message không lộ; D-owned test blocks không đổi | TODO |
| G4-C-06 | G4-C | Architecture and combined gate | Chạy ArchUnit AFTER, Auth regression và impacted targeted gates trên branch đã cập nhật | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-01 | 2026-12-01 | P0 | G4-C-01, G4-C-05 | Architecture/Auth gate report | 0 `repository → service`, 0 cycle; Auth tests pass; không chạm file/method A/B/D | TODO |
| G4-C-07 | G4-C | Rebase, PR review and merge | Sau B merge, rebase C lên integrated A+B, rerun gates, review và merge trước D | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-02 | 2026-12-02 | P0 | G4-C-06, G4-B-09 | Merged G4-C PR | Reviewer approves; A/B behavior preserved; merge SHA và architecture evidence recorded để D rebase | TODO |

## 5. G4-D — Fail-closed authorization boundary

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G4-D-01 | G4-D | Authorization baseline and failing boundary tests | Lưu source-level BEFORE; tạo skeleton 18-endpoint role matrix và synthetic-unlisted-route proof trước implementation | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-25 | 2026-11-26 | P0 | G3-04 | BEFORE evidence + failing security tests | Chứng minh authenticated fallback hiện cho test-only unlisted route đi qua; không ghi runtime pass khi chưa chạy | TODO |
| G4-D-02 | G4-D | Implement default-deny fallback | Đổi terminal rule trong `SecurityConfiguration.protectedApi` từ authenticated fallback sang `denyAll` | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-27 | 2026-11-27 | P0 | G4-D-01 | Fail-closed production policy | Chỉ terminal fallback đổi; public routes và explicit role matchers không đổi; không thêm endpoint production | TODO |
| G4-D-03 | G4-D | Complete 18-endpoint role matrix | Data-driven regression cho anonymous, CUSTOMER, EMPLOYEE, ADMIN trên đủ 18 endpoint patterns | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-28 | 2026-11-29 | P0 | G4-D-01, G4-D-02 | Authorization matrix tests | 18/18 route policy rows; current public/role permissions và valid behavior được bảo toàn | TODO |
| G4-D-04 | G4-D | Synthetic unlisted-route and error contract | Xác minh unlisted test route fail closed và 401/403/no-store/WWW-Authenticate giữ nguyên | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-29 | 2026-11-30 | P0 | G4-D-02 | Boundary/error regression evidence | Valid CUSTOMER/EMPLOYEE/ADMIN đều 403, anonymous 401, controller invocation 0; không production allow-list | TODO |
| G4-D-05 | G4-D | Integrate shared Auth test ownership | Sau C-05, cập nhật đúng `OtherModuleController`/`scope-check` blocks hoặc test-only security setup; không sửa persistence cases | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-30 | 2026-12-01 | P0 | G4-D-04, G4-C-05 | Conflict-free Auth test integration | Global JSON/error coverage còn hiệu lực; C-owned duplicate/persistence assertions và fixtures không đổi | TODO |
| G4-D-06 | G4-D | Targeted and combined authorization gate | Chạy D matrix/boundary tests, existing security/web/Auth regression và impacted C gates trên branch cập nhật | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-01 | 2026-12-02 | P0 | G4-D-03, G4-D-04, G4-D-05, G4-C-06 | Authorization + impacted-gate report | 18/18 matrix, unlisted denial, C architecture/Auth và existing security regression pass; không scope drift | TODO |
| G4-D-07 | G4-D | Rebase, PR review and merge | Sau C merge, rebase D lên integrated A+B+C, rerun gates, review và merge cuối | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-02 | 2026-12-02 | P0 | G4-D-06, G4-C-07 | Merged G4-D PR | Reviewer approves; merge SHA recorded; A/B/C behavior và test ownership preserved | TODO |

## 6. G5 — Verification and hardening

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G5-01 | G5 | Combined full regression | Run full suite trên integrated A+B+C+D SHA; archive reports | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-03 | 2026-12-03 | P0 | G4-A-09, G4-B-09, G4-C-07, G4-D-07 | Full regression evidence | Expected tests, architecture gates và authorization boundary gates pass; failures classified; no rerun-until-green | TODO |
| G5-02 | G5 | Black-box API and authorization verification | Verify 18 endpoints, public routes, role permissions, success/error contracts, G4-C Auth behavior và fail-closed fallback | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-03 | 2026-12-03 | P0 | G4-A-09, G4-B-09, G4-C-07, G4-D-07 | Black-box result + role-matrix evidence + cleanup | 18/18 behavior unchanged ngoài approved conflicts; unlisted route denied; duplicate account contract giữ nguyên; cleanup pass | TODO |
| G5-03 | G5 | Concurrency invariant verification | Run integrated C1/C2/C4/order transition/data integrity checks; C1 tối thiểu 45 overlapping rounds theo G3.2 | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-03 | 2026-12-03 | P0 | G4-A-09, G4-B-09, G4-C-07, G4-D-07 | Concurrency report + raw C1 round evidence | C1 đủ ≥45 overlapping rounds và 0 oversell/lost update; 0 targeted 5xx; rollback/final DB states đúng; evidence được lưu | TODO |
| G5-04 | G5 | Query/pagination verification | Re-run query count, pagination, filtering, ordering và ownership | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-03 | 2026-12-03 | P0 | G4-A-09, G4-B-09, G4-C-07, G4-D-07 | Data-access verification report | Captured SELECT ≤4; contract/page assertions pass | TODO |
| G5-05 | G5 | Docker and contract verification | Build/start Docker, readiness, API/security smoke, OpenAPI conflict check và cleanup | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-04 | 2026-12-04 | P0 | G5-01, G5-02 | Docker/contract evidence | Deploy/smoke/cleanup pass; explicit public/protected routes hoạt động; no config/secret drift | TODO |
| G5-06 | G5 | Fix and focused retest | Bắt đầu sửa verified G5 blocker ngay khi bất kỳ verification task nào phát hiện; rerun affected gate và full gate cần thiết | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-03 | 2026-12-04 | P0 | G4-A-09, G4-B-09, G4-C-07, G4-D-07 | Rolling fix/retest log hoặc no-fix-needed record | Không chờ toàn bộ G5 mới sửa; mỗi fix có reproducer/retest; không unresolved P0 trước freeze | TODO |
| G5-07 | G5 | Acceptance review and Code Freeze | Review evidence, lock application SHA/JAR for AFTER | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-04 | 2026-12-04 | P0 | G5-01, G5-02, G5-03, G5-04, G5-05, G5-06 | Code Freeze manifest/SHA | All G5 gates including C architecture/Auth và D role-matrix/fail-closed pass; full SHA/JAR checksum recorded; M4 approved | TODO |

## 7. G6 — AFTER benchmark and evaluation

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G6-01 | G6 | Build AFTER bundle | Build benchmark bundle từ frozen SHA bằng existing G2 harness | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-04 | 2026-12-04 | P0 | G5-07 | AFTER bundle + provenance | Source/JAR/schema/workload/dataset checksums complete; no unreviewed drift | TODO |
| G6-02 | G6 | Verify locks and comparability | Check application SHA, config/toolchain/dataset/workload and Intel manifest comparator | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-04 | 2026-12-04 | P0 | G6-01 | Compatibility report | All allowed fields match BEFORE group; only approved application treatment differs | TODO |
| G6-03 | G6 | AFTER smoke test | Run smoke/reset/telemetry/cleanup/integrity validation | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-04 | 2026-12-04 | P0 | G6-02 | Smoke evidence | W1/W2/W3 harness, resets, telemetry, cleanup and secret scan pass | TODO |
| G6-04 | G6 | Official AFTER run attempt 1 | Execute first fresh Intel-compatible official session; archive evidence and classify attempt `VALID`, `INVALID` or `INCOMPATIBLE` | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-05 | 2026-12-05 | P0 | G6-03 | Run-1 evidence ZIP and classification | Task may be DONE once attempt was performed, evidence saved and classification recorded, even if no valid run was obtained; only G6-09 decides minimum-run gate | TODO |
| G6-05 | G6 | Official AFTER run attempt 2 | Execute second fresh Intel-compatible official session; archive evidence and classify attempt `VALID`, `INVALID` or `INCOMPATIBLE` | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-06 | 2026-12-06 | P0 | G6-03 | Run-2 evidence ZIP and classification | Task may be DONE once attempt was performed, evidence saved and classification recorded, even if no valid run was obtained; only G6-09 decides minimum-run gate | TODO |
| G6-06 | G6 | Official AFTER run attempt 3 | Execute third fresh Intel-compatible official session; archive evidence and classify attempt `VALID`, `INVALID` or `INCOMPATIBLE` | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-07 | 2026-12-07 | P0 | G6-03 | Run-3 evidence ZIP and classification | Task may be DONE once attempt was performed, evidence saved and classification recorded, even if no valid run was obtained; only G6-09 decides minimum-run gate | TODO |
| G6-07 | G6 | Pre-buffer run validation | Validate/archive run attempts, hashes, comparator and outcomes; xác định còn thiếu bao nhiêu Intel run | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-07 | 2026-12-07 | P0 | G6-04, G6-05, G6-06 | Pre-buffer validity/gap report | Mọi run được classified; `<3` valid được phép và phải tạo explicit rerun requirement cho 08/12/2026 | TODO |
| G6-08 | G6 | Benchmark incident support | Diagnose application/harness failures without changing locks silently | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-05 | 2026-12-08 | P1 | G6-03 | Incident log/resolution patches if approved | Root cause/effect documented; code change triggers re-freeze/rerun rule | TODO |
| G6-09 | G6 | Buffer reruns and final minimum decision | Chạy bù invalid/CPU-mismatch runs còn thiếu; nếu đã đủ thì mới attempt run 4–5; cuối ngày chốt minimum outcome | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G6-07 | Additional evidence + final minimum-group decision | `PASS` iff ≥3 valid Intel runs same SHA; nếu thiếu ghi `NOT_MET`; no AMD/SHA mixing; failures retained | TODO |
| G6-10 | G6 | Aggregate or document evidence shortfall | Aggregate valid Intel group khi gate PASS; nếu NOT_MET, tạo per-run/shortfall summary không giả lập official aggregate | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G6-09 | AFTER aggregate MD/JSON hoặc limited-evidence summary | Samples không pooled; provenance/missing telemetry đúng; artifact nêu rõ `PASS` hay `NOT_MET` | TODO |
| G6-11 | G6 | Quantitative BEFORE/AFTER evaluation | Compare metrics khi minimum gate PASS; nếu NOT_MET, chỉ báo cáo observations/limitations không claim acceptance | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G6-10 | Evaluation tables/charts hoặc limited evaluation | Same locks/group; criteria chính xác; minimum status và mức độ kết luận được phân biệt rõ | TODO |
| G6-12 | G6 | Correctness and ADR evaluation | Evaluate C1/C2/C4, query count, pagination, dependency boundaries, fail-closed authorization và ADR-001…004 outcomes | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-08 | 2026-12-08 | P0 | G6-10, G5-01, G5-02 | Four-ADR acceptance assessment | Mỗi criterion pass/fail/inconclusive có evidence; D gồm 18/18 matrix và unlisted-route denial; no threshold rewrite | TODO |
| G6-13 | G6 | Publish evaluation evidence | Consolidate aggregate/limited analysis, minimum status, limitations and evidence references | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G6-11, G6-12 | G6 evaluation report/evidence index | Report hoàn thành đúng hạn trong cả hai trường hợp; không biến `NOT_MET` thành minimum-gate PASS | TODO |

## 8. G7 — Final acceptance and delivery

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G7-01 | G7 | Pre-draft architecture improvement report | Draft G4-A/G4-B/G4-C/G4-D rationale, implementation and correctness before/during G6; finalize only after G6 evidence | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-03 | 2026-12-08 | P1 | G4-A-09, G4-B-09, G4-C-07, G4-D-07 | Architecture report draft and final evidence-backed report | Draft may precede Code Freeze/G6 results with placeholders; final report matches four merged ADRs and incorporates architecture/security gates plus complete G6 evidence/limitations | TODO |
| G7-02 | G7 | Prepare ADR/diagram/evidence traceability | Update draft diagrams and map decisions→tests→evidence | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-04 | 2026-12-07 | P1 | G5-07 | Traceability draft | No fabricated result; all links target known/future evidence slots | TODO |
| G7-03 | G7 | Finalize architecture report | Incorporate G6 correctness/four-ADR acceptance results and limitations | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-08 | 2026-12-08 | P0 | G7-01, G7-02, G6-12 | Final architecture/correctness report | ADR-001…004 outcomes and trade-offs match evidence; no unapproved acceptance claim | TODO |
| G7-04 | G7 | Finalize experiment report and charts | Turn G6 evaluation into final BEFORE/AFTER narrative, tables and visuals | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G6-13 | Final experimental report/charts | Metrics reproducible, labels/units/group/variance correct; no cherry-pick | TODO |
| G7-05 | G7 | Quality attribute conclusions | Conclude consistency, performance, maintainability và security-modifiability goals, trade-offs and limits | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-08 | 2026-12-08 | P0 | G7-03, G7-04 | Quality attribute assessment | Pass/fail/inconclusive cho cả bốn cải tiến traceable to acceptance/evidence | TODO |
| G7-06 | G7 | Finalize README and architecture docs | Update navigation, status, To-Be/ADRs and evidence references | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G7-05 | Final README/docs | No stale status/broken links; approved architecture represented accurately | TODO |
| G7-07 | G7 | Reproduction and deployment guide | Document build/deploy/test/benchmark reproduction using frozen artifacts | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G6-13 | Reproduction/deployment guide | Another reviewer can follow inputs/locks/steps; secrets excluded | TODO |
| G7-08 | G7 | Prepare demo and Q&A | Prepare scenarios, fallback evidence, likely defense questions and ownership before/during G6; finalize claims after evidence | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-03 | 2026-12-08 | P0 | G4-A-09, G4-B-09, G4-C-07, G4-D-07 | Draft and final demo/Q&A runbook | Final runbook covers concurrency, query, dependency-boundary and fail-closed evidence, trade-offs, limitations and fallback | TODO |
| G7-09 | G7 | Final acceptance and requirements audit | Check assignment, DoD, milestones, docs/evidence and unresolved risks | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-08 | 2026-12-08 | P0 | G7-06, G7-07, G7-08 | Signed final acceptance checklist | All required items pass or limitation explicitly accepted; no secret/untracked deliverable | TODO |
| G7-10 | G7 | Demo/Q&A rehearsal and corrections | Rehearse end-to-end demo, vấn đáp và fix document/demo defects | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G7-09 | Rehearsal record + corrected artifacts | Demo succeeds or fallback works; answers trace evidence; links/numbers rechecked | TODO |
| G7-11 | G7 | Build final release/submission package | Package repository/release, reports, evidence index and instructions | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G7-09, G7-10 | Final submission package/checksums | Package complete, opens cleanly, SHA/checksums recorded, secret scan pass | TODO |
| G7-12 | G7 | Official submission | Submit approved package and record receipt/link before deadline | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-09 | 2026-12-09 | P0 | G7-11 | Submission receipt/link | Correct package submitted on time; receipt verified by both | TODO |
| G7-13 | G7 | Emergency submission support | Handle upload/access issue without changing accepted content | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-09 | 2026-12-09 | P1 | G7-11 | Emergency log or no-incident closure | Submission continuity protected; any action documented and reviewed | TODO |

## 9. Ownership summary

| Primary owner | Task count | Task IDs |
|---|---:|---|
| **Bùi Công Huy** | **39** | G3-01, G3-03; G4-B-01…09; G4-C-01…07; G5-02,04,05,07; G6-01…07,09,10,11,13; G7-04,06,07,10,11,12 |
| **Nguyễn Văn Huy Hoàng** | **30** | G3-02, G3-04; G4-A-01…09; G4-D-01…07; G5-01,03,06; G6-08,12; G7-01,02,03,05,08,09,13 |
| **Total** | **69** | G3–G7 |

Huy điều phối dự án, sở hữu G4-B/G4-C, integration, toàn bộ Kaggle/AFTER benchmark, aggregation và đánh giá BEFORE/AFTER. Hoàng sở hữu G4-A/G4-D, dẫn kiểm thử tích hợp/correctness evidence và báo cáo kiến trúc để cung cấp kết quả cho Huy tổng hợp. Reviewer của mọi task là thành viên còn lại.

## 10. Milestones

| ID | Milestone | Deadline | Required task evidence | Status |
|---|---:|---:|---|---|
| M1 | G3 approved | 2026-11-24 | G3-01…04; ADR-001/002/003/004 và bốn plans được duyệt và bản approved được publish qua PR #4, merge SHA `db39c50d9a8d9d53d2c41d026729e5e7905249aa` | DONE |
| M2 | G4-A completed and merged | 2026-12-02 | G4-A-01…09 | TODO |
| M3 | G4-B completed and merged | 2026-12-02 | G4-B-01…09 | TODO |
| M3-C | G4-C completed and merged | 2026-12-02 | G4-C-01…07 | TODO |
| M3-D | G4-D completed and merged | 2026-12-02 | G4-D-01…07 | TODO |
| M4 | G5 passed — Code Freeze | 2026-12-04 | G5-01…07 | TODO |
| M5 | G6 AFTER evaluation package completed | 2026-12-08 | G6-01…13; final minimum decision G6-09 | TODO |
| M6 | G7 final delivery ready | 2026-12-08 | G7-01…11 | TODO |
| M7 | Official submission | 2026-12-09 | G7-12; G7-13 conditional support | TODO |

M5 có hai outcome tách biệt: minimum-run gate `PASS` khi G6-09 xác nhận ≥3 valid comparable Intel runs; hoặc `NOT_MET` khi vẫn thiếu evidence sau buffer. Cả hai outcome đều bắt buộc hoàn thành G6-10…13 và tiếp tục G7/submission đúng deadline; `NOT_MET` không được trình bày như acceptance pass.

## 11. Critical path tasks

Nominal critical path:

- `G3-01 → G3-03 → G3-04`
- `G3-02 → G3-03`
- `G4-A-01…08`, `G4-B-01…07`, `G4-C-01…06` và `G4-D-01…06` phát triển song song; final integration là `G4-A-09 → G4-B-08/09 → G4-C-07 → G4-D-07`
- `G5-01…07`
- `G6-01…07 → G6-09 → G6-10 → G6-11/G6-12 → G6-13`
- G7 pre-drafts `G7-01/G7-02/G7-08` can start after all G4 merges and run during G5/G6; finalization depends on C/D architecture-security evidence và G6 evidence: `G6-12/G6-13 → G7-03/G7-04 → G7-05 → G7-06/G7-07 → G7-09 → G7-10/G7-11 → G7-12`

`G6-08` và `G7-13` là conditional critical tasks khi có incident. Hoàng pre-draft G7-01/02/08 trong G5/G6; Huy dùng các ngày benchmark/evaluation để chuẩn bị trước G7-04/07 và bảng kết quả sau khi có dữ liệu. Chỉ bản cuối đã đối chiếu đầy đủ evidence mới được nghiệm thu.

## 12. Daily schedule

| Date | Bùi Công Huy | Nguyễn Văn Huy Hoàng | Daily exit condition |
|---|---|---|---|
| 23/11 | G3-01 | G3-01, G3-02 | ADR-001…004 review underway; no G4 implementation before approval closes |
| 24/11 | G3-03, G3-04 review | G3-02, G3-03, G3-04 | M1 approval/publish; four G4 workstreams ready to start 25/11 |
| 25/11 | G4-B-01; G4-C-01 | G4-A-01; G4-D-01 | Four test-first workstreams start on separate branches |
| 26/11 | G4-B-01/02; G4-C-01/02 | G4-A-02; G4-D-01 | Repository/query/architecture/security baselines ready |
| 27/11 | G4-B-02/03; G4-C-03 | G4-A-03/04; G4-D-02 | NO_WAIT, fetch, exception boundary và deny-all implementation progress |
| 28/11 | G4-B-03/04; G4-C-04 | G4-A-04/05; G4-D-03 | Locked checkout, deterministic assembly, service mapping và role matrix progress |
| 29/11 | G4-B-04/05; G4-C-05 | G4-A-05; G4-D-03/04 | Stock/pagination/Auth/fail-closed targeted coverage progress |
| 30/11 | G4-B-05/06; G4-C-05 | G4-A-06; G4-D-04/05 | C persistence tests stabilize; D begins only D-owned Auth-test integration |
| 01/12 | G4-B-06/07; G4-C-06 | G4-A-07/08; G4-D-05/06 | All targeted gates complete; cross-review and merge preparation underway |
| 02/12 | G4-B-07/08/09; G4-C-07; review A/D | G4-A-09; G4-D-06/07; review B/C | Merge A → B → C → D; M2/M3/M3-C/M3-D complete |
| 03/12 | G5-02,04; draft G7-04/07 | G5-01,03,06; G7-01/08 | Combined A+B+C+D verification starts; G7 pre-drafts begin |
| 04/12 | G5-05,07; G6-01,02,03 after freeze | G5-06; G7-02/08 | G5 gates complete, M4 frozen; AFTER bundle/comparator/smoke pass |
| 05/12 | G6-04; draft G7-04/07 | G6-08; G7-01/02/08 | First official run attempt classified; architecture evidence draft continues |
| 06/12 | G6-05; prepare G7-04 structure | G6-08; G7-01/02/08 | Second official run attempt; report/demo pre-drafts continue |
| 07/12 | G6-06,07; stage G7-04 inputs | G6-08; G7-01/02/08 | Official run 3 and pre-buffer validation; reproduction guide drafted |
| 08/12 | G6-09,10,11,13; finalize G7-04,06,07,10,11 | G6-08,12; finalize G7-01,02,03,05,08,09 | Buffer/reruns, four-ADR evaluation, M5/M6 and package complete |
| 09/12 | G7-12 | G7-13 | M7 submission receipt verified |

## 13. Progress tracking

### By phase

| Phase | Total | TODO | IN_PROGRESS | IN_REVIEW | BLOCKED | DONE | Completion |
|---|---:|---:|---:|---:|---:|---:|---:|
| G3 | 4 | 0 | 0 | 0 | 0 | 4 | 100% |
| G4-A | 9 | 9 | 0 | 0 | 0 | 0 | 0% |
| G4-B | 9 | 9 | 0 | 0 | 0 | 0 | 0% |
| G4-C | 7 | 7 | 0 | 0 | 0 | 0 | 0% |
| G4-D | 7 | 7 | 0 | 0 | 0 | 0 | 0% |
| G5 | 7 | 7 | 0 | 0 | 0 | 0 | 0% |
| G6 | 13 | 13 | 0 | 0 | 0 | 0 | 0% |
| G7 | 13 | 13 | 0 | 0 | 0 | 0 | 0% |
| **Total** | **69** | **65** | **0** | **0** | **0** | **4** | **5.8%** |

### By member

| Member | Total | TODO | IN_PROGRESS | IN_REVIEW | BLOCKED | DONE | Completion |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bùi Công Huy | 39 | 37 | 0 | 0 | 0 | 2 | 5.1% |
| Nguyễn Văn Huy Hoàng | 30 | 28 | 0 | 0 | 0 | 2 | 6.7% |

### Update rules

- Chuyển `TODO → IN_PROGRESS` khi owner thực sự bắt đầu và ghi link branch/work artifact.
- Chuyển `IN_REVIEW` khi deliverable/evidence sẵn sàng cho reviewer.
- Chỉ `DONE` khi acceptance của task đạt và evidence link cùng reviewer hoặc decision basis áp dụng được ghi; deadline đến không tự đổi status.
- Local dependency evidence của G4-B chỉ mở task kế tiếp trên cùng branch; không tự đổi status, progress count hoặc thay thế push/review.
- `BLOCKED` phải ghi blocker, ảnh hưởng milestone, owner xử lý và next review time.
- Khi status đổi, cập nhật summary counts và milestone/critical-path impact trong cùng change.
