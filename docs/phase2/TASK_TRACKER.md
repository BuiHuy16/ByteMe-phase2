# ByteMe Phase 2 — Task Tracker

- **Tracking window:** 22/11/2026–09/12/2026
- **Last planning update:** 22/11/2026
- **Status vocabulary:** `TODO`, `IN_PROGRESS`, `IN_REVIEW`, `BLOCKED`, `DONE`
- **Roadmap:** [ROADMAP.md](ROADMAP.md)

G0–G2 đã hoàn thành và không được tạo lại thành task. G3 documentation đã có nhưng approval/publish tasks dưới đây chưa thực hiện nên vẫn `TODO`. Status chỉ được cập nhật từ evidence thực tế.

## 1. G3 — Approval and planning closeout

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G3-01 | G3 | Review ADR-001/002 | Review lựa chọn pessimistic locking/two-step fetch, trade-offs và acceptance | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-23 | 2026-11-23 | P0 | — | Review notes cho 2 ADR | Hai người thống nhất hoặc ghi blocker cụ thể; không auto-approve | TODO |
| G3-02 | G3 | Review implementation plans | Review scope, file/method, timeout/isolation, test và gates của hai plan | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-23 | 2026-11-24 | P0 | — | Approved change requests/checklist | Không còn chi tiết implementation mơ hồ ảnh hưởng G4 | TODO |
| G3-03 | G3 | Approve coordination contract | Chốt owners, method ownership, parallel coding, A-first merge và Git workflow | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-24 | 2026-11-24 | P0 | G3-01, G3-02 | Signed coordination decision | ADR/plans có reviewer/date; owners và merge order được xác nhận | TODO |
| G3-04 | G3 | Publish approved G3 docs | Cập nhật status `ACCEPTED` sau xác nhận thực tế, commit/push tài liệu approved | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-24 | 2026-11-24 | P0 | G3-03 | Published G3 documentation commit | Chỉ approved status được đổi; links/files đúng; commit SHA được ghi | TODO |

## 2. G4-A — Pessimistic locking

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G4-A-01 | G4-A | Targeted concurrency test skeleton | Tạo C1/C2/C4, rollback và lock-contention tests trước implementation | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-25 | 2026-11-25 | P0 | G3-04 | Failing targeted test suite | Tests tái hiện/bao phủ invariant, dùng barrier/latch và final DB assertions | TODO |
| G4-A-02 | G4-A | Repository locking methods | Thêm Cart/Food/Order pessimistic locking queries theo lock order | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-25 | 2026-11-25 | P0 | G4-A-01 | Repository lock implementation | `PESSIMISTIC_WRITE`, Food IDs ascending, no unrelated repository change | TODO |
| G4-A-03 | G4-A | Verify NO_WAIT on MySQL | Chứng minh `lock.timeout=0` fail-fast và maps typed exception | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-26 | 2026-11-26 | P0 | G4-A-02 | Runtime test evidence | Contender không chờ DB default; conflict không thành 500; nếu fail thì ADR review | TODO |
| G4-A-04 | G4-A | Locked cart snapshot | Khóa Cart trước đọc items và giữ lock tới checkout commit/rollback | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-26 | 2026-11-26 | P0 | G4-A-02, G4-A-03 | Cart checkout lock path | Same-cart overlap có tối đa một commit; empty-cart semantics giữ nguyên | TODO |
| G4-A-05 | G4-A | Batch stock reserve/release | Lock distinct Food IDs ASC, validate-all-before-mutate, batch reserve/release | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-27 | 2026-11-27 | P0 | G4-A-02, G4-A-03 | Food mutation implementation | Không partial mutation; missing/inactive/insufficient codes giữ nguyên | TODO |
| G4-A-06 | G4-A | Integrate mutation transactions | Cập nhật checkout, admin update/delete và Order transitions/cancel | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-27 | 2026-11-27 | P0 | G4-A-04, G4-A-05 | End-to-end service implementation | Lock graph đúng; sequential behavior/snapshot/rollback không đổi | TODO |
| G4-A-07 | G4-A | Conflict handling and API docs | Chuẩn hóa 409 `CONCURRENT_UPDATE`, no-store/no retry; cập nhật spec nếu thiếu | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-28 | 2026-11-28 | P1 | G4-A-06 | Error mapping + contract diff | Expected contention không 5xx; success schema không đổi; không lộ DB message | TODO |
| G4-A-08 | G4-A | Targeted and regression gate | Chạy targeted unit/web/MySQL suites và regression liên quan | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-28 | 2026-11-28 | P0 | G4-A-03, G4-A-06, G4-A-07 | Test reports + reviewed result | C1/C2/C4/rollback pass; NO_WAIT proof pass; không unresolved P0 | TODO |
| G4-A-09 | G4-A | PR review and merge | Mở PR, xử lý review, merge A trước B | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-29 | 2026-11-29 | P0 | G4-A-08, G4-B-07 | Merged G4-A PR | Reviewer approves; CI/local required gates pass; merge SHA recorded | TODO |

## 3. G4-B — Two-step fetching

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G4-B-01 | G4-B | Query-count and pagination test skeleton | Tạo baseline N+1/query count và page/contract fixtures | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-25 | 2026-11-27 | P0 | G3-04 | Failing query-count test suite | Page 1/5/20/50 có items; N+1 được phát hiện; fixtures cover scope/order | TODO |
| G4-B-02 | G4-B | Page-ID query | Implement scoped/filter/sorted Order ID page query | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-26 | 2026-11-28 | P0 | G4-B-01 | Repository page-ID method | Chỉ ID query paginate; sort `createdAt DESC,id DESC`; count không ẩn | TODO |
| G4-B-03 | G4-B | Bulk fetch Orders and items | Implement non-paginated left fetch cho IDs, root de-duplication | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-27 | 2026-11-29 | P0 | G4-B-02 | Fetch-with-items method | Zero-item Order còn tồn tại; không lazy item query/order | TODO |
| G4-B-04 | G4-B | Deterministic assembly | Implement validate/reorder, DTO mapping và count trong one read-only transaction | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-28 | 2026-11-30 | P0 | G4-B-02, G4-B-03 | Updated `OrderService.list` | Output order/page/count/DTO unchanged; missing/duplicate IDs fail clearly | TODO |
| G4-B-05 | G4-B | Pagination and contract tests | Cover empty, zero/multi-item, ties, page boundary, filter, ownership, API compatibility | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-29 | 2026-11-30 | P0 | G4-B-04 | Unit/MySQL contract tests | Không duplicate/missing; item/root order, total, fields và scopes đúng | TODO |
| G4-B-06 | G4-B | Query-count acceptance | Prove non-empty page 3 app SELECT/captured total ≤4 và no N+1 | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-30 | 2026-12-01 | P0 | G4-B-04, G4-B-05 | Query-count report | Count hằng ở size 1/5/20/50; SQL không lặp `order_id=?` theo N | TODO |
| G4-B-07 | G4-B | Cross-review G4-A | Review lock graph, conflict semantics và shared-file ownership trước A merge | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-11-28 | 2026-11-29 | P0 | G4-A-08 | G4-A PR review | Blocking findings resolved; approval recorded without editing A-owned methods | TODO |
| G4-B-08 | G4-B | Rebase and integration tests | Rebase B sau A merge, resolve shared imports/methods và rerun targeted A+B | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-01 | 2026-12-01 | P0 | G4-B-06, G4-A-09 | Rebasing/integration evidence | A locks preserved; A+B targeted/impacted regression pass; no scope drift | TODO |
| G4-B-09 | G4-B | PR review and merge | Mở/finalize PR B, xử lý review và merge | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-01 | 2026-12-01 | P0 | G4-B-08 | Merged G4-B PR | Reviewer approves; query/pagination/API gates pass; merge SHA recorded | TODO |

## 4. G5 — Verification and hardening

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G5-01 | G5 | Combined full regression | Run full suite trên integrated A+B SHA; archive reports | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-02 | 2026-12-02 | P0 | G4-A-09, G4-B-09 | Full regression evidence | Expected tests pass; failures classified; no rerun-until-green | TODO |
| G5-02 | G5 | Black-box API verification | Verify current endpoints, auth/roles, success/error contracts | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-02 | 2026-12-02 | P0 | G4-A-09, G4-B-09 | Black-box result + cleanup | API behavior unchanged ngoài approved conflicts; cleanup pass | TODO |
| G5-03 | G5 | Concurrency invariant verification | Run integrated C1/C2/C4/order transition/data integrity checks; C1 tối thiểu 45 overlapping rounds theo G3.2 | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-02 | 2026-12-02 | P0 | G4-A-09, G4-B-09 | Concurrency report + raw C1 round evidence | C1 đủ ≥45 overlapping rounds và 0 oversell/lost update; 0 targeted 5xx; rollback/final DB states đúng; evidence được lưu | TODO |
| G5-04 | G5 | Query/pagination verification | Re-run query count, pagination, filtering, ordering và ownership | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-02 | 2026-12-02 | P0 | G4-A-09, G4-B-09 | Data-access verification report | Captured SELECT ≤4; contract/page assertions pass | TODO |
| G5-05 | G5 | Docker and contract verification | Build/start Docker, readiness, API smoke, OpenAPI conflict check và cleanup | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-02 | 2026-12-02 | P0 | G5-01, G5-02 | Docker/contract evidence | Deploy/smoke/cleanup pass; no config/secret drift | TODO |
| G5-06 | G5 | Fix and focused retest | Bắt đầu sửa verified G5 blocker ngay khi bất kỳ verification task nào phát hiện; rerun affected gate và full gate cần thiết | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-02 | 2026-12-02 | P0 | G4-A-09, G4-B-09 | Rolling fix/retest log hoặc no-fix-needed record | Không chờ toàn bộ G5 mới sửa; mỗi fix có reproducer/retest; không unresolved P0 trước freeze | TODO |
| G5-07 | G5 | Acceptance review and Code Freeze | Review evidence, lock application SHA/JAR for AFTER | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-02 | 2026-12-02 | P0 | G5-01, G5-02, G5-03, G5-04, G5-05, G5-06 | Code Freeze manifest/SHA | All G5 gates pass; full SHA/JAR checksum recorded; M4 approved | TODO |

## 5. G6 — AFTER benchmark and evaluation

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G6-01 | G6 | Build AFTER bundle | Build benchmark bundle từ frozen SHA bằng existing G2 harness | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-03 | 2026-12-03 | P0 | G5-07 | AFTER bundle + provenance | Source/JAR/schema/workload/dataset checksums complete; no unreviewed drift | TODO |
| G6-02 | G6 | Verify locks and comparability | Check application SHA, config/toolchain/dataset/workload and Intel manifest comparator | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-03 | 2026-12-03 | P0 | G6-01 | Compatibility report | All allowed fields match BEFORE group; only approved application treatment differs | TODO |
| G6-03 | G6 | AFTER smoke test | Run smoke/reset/telemetry/cleanup/integrity validation | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-03 | 2026-12-03 | P0 | G6-02 | Smoke evidence | W1/W2/W3 harness, resets, telemetry, cleanup and secret scan pass | TODO |
| G6-04 | G6 | Official AFTER run attempt 1 | Execute first fresh Intel-compatible official session; archive evidence and classify attempt `VALID`, `INVALID` or `INCOMPATIBLE` | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-04 | 2026-12-04 | P0 | G6-03 | Run-1 evidence ZIP and classification | Task may be DONE once attempt was performed, evidence saved and classification recorded, even if no valid run was obtained; only G6-09 decides minimum-run gate | TODO |
| G6-05 | G6 | Official AFTER run attempt 2 | Execute second fresh Intel-compatible official session; archive evidence and classify attempt `VALID`, `INVALID` or `INCOMPATIBLE` | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-05 | 2026-12-05 | P0 | G6-03 | Run-2 evidence ZIP and classification | Task may be DONE once attempt was performed, evidence saved and classification recorded, even if no valid run was obtained; only G6-09 decides minimum-run gate | TODO |
| G6-06 | G6 | Official AFTER run attempt 3 | Execute third fresh Intel-compatible official session; archive evidence and classify attempt `VALID`, `INVALID` or `INCOMPATIBLE` | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-06 | 2026-12-06 | P0 | G6-03 | Run-3 evidence ZIP and classification | Task may be DONE once attempt was performed, evidence saved and classification recorded, even if no valid run was obtained; only G6-09 decides minimum-run gate | TODO |
| G6-07 | G6 | Pre-buffer run validation | Validate/archive run attempts, hashes, comparator and outcomes; xác định còn thiếu bao nhiêu Intel run | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-06 | 2026-12-06 | P0 | G6-04, G6-05, G6-06 | Pre-buffer validity/gap report | Mọi run được classified; `<3` valid được phép và phải tạo explicit rerun requirement cho 07/12 | TODO |
| G6-08 | G6 | Benchmark incident support | Diagnose application/harness failures without changing locks silently | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-04 | 2026-12-07 | P1 | G6-03 | Incident log/resolution patches if approved | Root cause/effect documented; code change triggers re-freeze/rerun rule | TODO |
| G6-09 | G6 | Buffer reruns and final minimum decision | Chạy bù invalid/CPU-mismatch runs còn thiếu; nếu đã đủ thì mới attempt run 4–5; cuối ngày chốt minimum outcome | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-07 | 2026-12-07 | P0 | G6-07 | Additional evidence + final minimum-group decision | `PASS` iff ≥3 valid Intel runs same SHA; nếu thiếu ghi `NOT_MET`; no AMD/SHA mixing; failures retained | TODO |
| G6-10 | G6 | Aggregate or document evidence shortfall | Aggregate valid Intel group khi gate PASS; nếu NOT_MET, tạo per-run/shortfall summary không giả lập official aggregate | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-07 | 2026-12-07 | P0 | G6-09 | AFTER aggregate MD/JSON hoặc limited-evidence summary | Samples không pooled; provenance/missing telemetry đúng; artifact nêu rõ `PASS` hay `NOT_MET` | TODO |
| G6-11 | G6 | Quantitative BEFORE/AFTER evaluation | Compare metrics khi minimum gate PASS; nếu NOT_MET, chỉ báo cáo observations/limitations không claim acceptance | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-07 | 2026-12-07 | P0 | G6-10 | Evaluation tables/charts hoặc limited evaluation | Same locks/group; criteria chính xác; minimum status và mức độ kết luận được phân biệt rõ | TODO |
| G6-12 | G6 | Correctness and ADR evaluation | Evaluate C1/C2/C4, query count, pagination and ADR acceptance | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-07 | 2026-12-07 | P0 | G6-10 | ADR acceptance assessment | Each criterion pass/fail/inconclusive with evidence; no threshold rewrite | TODO |
| G6-13 | G6 | Publish evaluation evidence | Consolidate aggregate/limited analysis, minimum status, limitations and evidence references | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-07 | 2026-12-07 | P0 | G6-11, G6-12 | G6 evaluation report/evidence index | Report hoàn thành đúng hạn trong cả hai trường hợp; không biến `NOT_MET` thành minimum-gate PASS | TODO |

## 6. G7 — Final acceptance and delivery

| Task ID | Phase | Task name | Description | Primary owner | Reviewer | Start | Due | Priority | Dependencies | Deliverable | Acceptance criteria | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G7-01 | G7 | Pre-draft architecture improvement report | Draft G4-A/G4-B rationale, implementation and correctness before/during G6; finalize only after G6 evidence | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-30 | 2026-12-08 | P1 | G4-A-09, G4-B-09 | Architecture report draft and final evidence-backed report | Draft may precede Code Freeze/G6 results with placeholders; final report matches merged code/ADRs and incorporates complete G6 evidence/limitations before acceptance | TODO |
| G7-02 | G7 | Prepare ADR/diagram/evidence traceability | Update draft diagrams and map decisions→tests→evidence | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-03 | 2026-12-06 | P1 | G5-07 | Traceability draft | No fabricated result; all links target known/future evidence slots | TODO |
| G7-03 | G7 | Finalize architecture report | Incorporate G6 correctness/acceptance results and limitations | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-08 | 2026-12-08 | P0 | G7-01, G7-02, G6-12 | Final architecture/correctness report | ADR outcomes and trade-offs match G6 evidence | TODO |
| G7-04 | G7 | Finalize experiment report and charts | Turn G6 evaluation into final BEFORE/AFTER narrative, tables and visuals | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G6-13 | Final experimental report/charts | Metrics reproducible, labels/units/group/variance correct; no cherry-pick | TODO |
| G7-05 | G7 | Quality attribute conclusions | Conclude consistency/performance goals, trade-offs and limits | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-08 | 2026-12-08 | P0 | G7-03, G7-04 | Quality attribute assessment | Pass/fail/inconclusive traceable to acceptance/evidence | TODO |
| G7-06 | G7 | Finalize README and architecture docs | Update navigation, status, To-Be/ADRs and evidence references | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G7-05 | Final README/docs | No stale status/broken links; approved architecture represented accurately | TODO |
| G7-07 | G7 | Reproduction and deployment guide | Document build/deploy/test/benchmark reproduction using frozen artifacts | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G6-13 | Reproduction/deployment guide | Another reviewer can follow inputs/locks/steps; secrets excluded | TODO |
| G7-08 | G7 | Prepare demo and Q&A | Prepare scenarios, fallback evidence, likely defense questions and ownership before/during G6; finalize claims after evidence | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-11-30 | 2026-12-08 | P0 | G4-A-09, G4-B-09 | Draft and final demo/Q&A runbook | Draft may precede Code Freeze/G6 results; final runbook covers verified concurrency/query results, limitations and fallback with evidence-backed claims before acceptance | TODO |
| G7-09 | G7 | Final acceptance and requirements audit | Check assignment, DoD, milestones, docs/evidence and unresolved risks | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-08 | 2026-12-08 | P0 | G7-06, G7-07, G7-08 | Signed final acceptance checklist | All required items pass or limitation explicitly accepted; no secret/untracked deliverable | TODO |
| G7-10 | G7 | Demo/Q&A rehearsal and corrections | Rehearse end-to-end demo, vấn đáp và fix document/demo defects | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G7-09 | Rehearsal record + corrected artifacts | Demo succeeds or fallback works; answers trace evidence; links/numbers rechecked | TODO |
| G7-11 | G7 | Build final release/submission package | Package repository/release, reports, evidence index and instructions | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-08 | 2026-12-08 | P0 | G7-09, G7-10 | Final submission package/checksums | Package complete, opens cleanly, SHA/checksums recorded, secret scan pass | TODO |
| G7-12 | G7 | Official submission | Submit approved package and record receipt/link before deadline | Bùi Công Huy | Nguyễn Văn Huy Hoàng | 2026-12-09 | 2026-12-09 | P0 | G7-11 | Submission receipt/link | Correct package submitted on time; receipt verified by both | TODO |
| G7-13 | G7 | Emergency submission support | Handle upload/access issue without changing accepted content | Nguyễn Văn Huy Hoàng | Bùi Công Huy | 2026-12-09 | 2026-12-09 | P1 | G7-11 | Emergency log or no-incident closure | Submission continuity protected; any action documented and reviewed | TODO |

## 7. Ownership summary

| Primary owner | Task count | Task IDs |
|---|---:|---|
| **Bùi Công Huy** | **32** | G3-01, G3-03; G4-B-01…09; G5-02,04,05,07; G6-01…07,09,10,11,13; G7-04,06,07,10,11,12 |
| **Nguyễn Văn Huy Hoàng** | **23** | G3-02, G3-04; G4-A-01…09; G5-01,03,06; G6-08,12; G7-01,02,03,05,08,09,13 |
| **Total** | **55** | G3–G7 |

Huy có nhiều task hơn do sở hữu integration và toàn bộ Kaggle/aggregation. Huy giữ workload G4-B linh hoạt/nhẹ trong 25–30/11 vì bài tập lớn môn khác; Hoàng triển khai G4-A độc lập và pre-draft báo cáo/demo/Q&A từ 30/11, đồng thời hỗ trợ incident trong benchmark window.

## 8. Milestones

| ID | Milestone | Deadline | Required task evidence | Status |
|---|---:|---:|---|---|
| M1 | G3 approved | 2026-11-24 | G3-01…04 | TODO |
| M2 | G4-A completed and merged | 2026-11-29 | G4-A-01…09 | TODO |
| M3 | G4-B completed and merged | 2026-12-01 | G4-B-01…09 | TODO |
| M4 | G5 passed — Code Freeze | 2026-12-02 | G5-01…07 | TODO |
| M5 | G6 AFTER evaluation package completed | 2026-12-07 | G6-01…13; final minimum decision G6-09 | TODO |
| M6 | G7 final delivery ready | 2026-12-08 | G7-01…11 | TODO |
| M7 | Official submission | 2026-12-09 | G7-12; G7-13 conditional support | TODO |

M5 có hai outcome tách biệt: minimum-run gate `PASS` khi G6-09 xác nhận ≥3 valid comparable Intel runs; hoặc `NOT_MET` khi vẫn thiếu evidence sau buffer. Cả hai outcome đều bắt buộc hoàn thành G6-10…13 và tiếp tục G7/submission đúng deadline; `NOT_MET` không được trình bày như acceptance pass.

## 9. Critical path tasks

Nominal critical path:

- `G3-01 → G3-03 → G3-04`
- `G3-02 → G3-03`
- `G4-A-01…09` and parallel `G4-B-01…07`; B final path is `G4-A-09 + G4-B-06 → G4-B-08 → G4-B-09`
- `G5-01…07`
- `G6-01…07 → G6-09 → G6-10 → G6-11/G6-12 → G6-13`
- G7 pre-drafts `G7-01/G7-02/G7-08` can start after G4 merges and run during G6; finalization still depends on G6 evidence: `G6-12/G6-13 → G7-03/G7-04 → G7-05 → G7-06/G7-07 → G7-09 → G7-10/G7-11 → G7-12`

`G6-08` và `G7-13` là conditional critical tasks khi có incident. Hoàng pre-draft G7-01/02/08 trước và trong G6; Huy dùng các ngày benchmark/evaluation để chuẩn bị trước G7-04/07 và bảng kết quả sau khi có dữ liệu. Chỉ bản cuối đã đối chiếu đầy đủ evidence mới được nghiệm thu.

## 10. Daily schedule

| Date | Bùi Công Huy | Nguyễn Văn Huy Hoàng | Daily exit condition |
|---|---|---|---|
| 23/11 | G3-01 | G3-01, G3-02 | ADR review underway; no G4 implementation before approval window closes |
| 24/11 | G3-03, G3-04 | G3-02, G3-03 | M1 approval/publish; G4 ready to start 25/11 |
| 25/11 | G4-B-01 (flexible/light workload) | G4-A-01,02 | G4 starts; concurrency skeleton and foundations |
| 26/11 | G4-B-01/02 (flexible) | G4-A-03,04 | NO_WAIT proof; A checkout lock path |
| 27/11 | G4-B-02/03 (flexible) | G4-A-05 | A stock reserve/release; B page/fetch foundation |
| 28/11 | G4-B-03 (flexible) | G4-A-06,07,08 | A implementation and targeted gate complete |
| 29/11 | G4-B-04/05 (flexible) | G4-A-09; G4-B-07 | A reviewed/merged (M2); B cross-review |
| 30/11 | G4-B-04/05 (flexible; reduced availability) | G7-01, G7-08 prep | Huy workload remains light; Hoàng prepares report/demo/Q&A skeleton |
| 01/12 | G4-B-06,08,09 (focused integration/rebase/merge) | G4-B review; G7-01/02 | B rebased, verified and merged (M3) |
| 02/12 | G5-02,04,05,07 | G5-01,03,06 | G5 gates complete; M4 Code Freeze SHA/JAR locked |
| 03/12 | G6-01,02,03; draft G7-04/07 | G6-08; G7-01/02/08 | AFTER bundle, compatibility and smoke pass; G7 drafts continue |
| 04/12 | G6-04; draft result-table template G7-04 | G6-08; G7-02/08 | Official run attempt; evidence classified; docs/demo prep continues |
| 05/12 | G6-05; prepare G7-04 structure | G6-08; G7-01/02/08 | Official run attempt; report/demo pre-drafts continue |
| 06/12 | G6-06,07; stage G7-04 inputs | G6-08; G7-02/08 | Third attempt and pre-buffer gap classification; reproduction guide drafted |
| 07/12 | G6-09,10,11,13; populate G7-04 | G6-08,12; G7-01/02/08 | Buffer, final minimum decision, aggregation/evaluation; evidence-backed draft tables ready |
| 08/12 | Finalize G7-04,06,07,10,11 | Finalize G7-01/02/03/05/08/09 | M6 final acceptance and package ready; review final evidence links |
| 09/12 | G7-12 | G7-13 | M7 submission receipt verified |

## 11. Progress tracking

### By phase

| Phase | Total | TODO | IN_PROGRESS | IN_REVIEW | BLOCKED | DONE | Completion |
|---|---:|---:|---:|---:|---:|---:|---:|
| G3 | 4 | 4 | 0 | 0 | 0 | 0 | 0% |
| G4-A | 9 | 9 | 0 | 0 | 0 | 0 | 0% |
| G4-B | 9 | 9 | 0 | 0 | 0 | 0 | 0% |
| G5 | 7 | 7 | 0 | 0 | 0 | 0 | 0% |
| G6 | 13 | 13 | 0 | 0 | 0 | 0 | 0% |
| G7 | 13 | 13 | 0 | 0 | 0 | 0 | 0% |
| **Total** | **55** | **55** | **0** | **0** | **0** | **0** | **0%** |

### By member

| Member | Total | TODO | IN_PROGRESS | IN_REVIEW | BLOCKED | DONE | Completion |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bùi Công Huy | 32 | 32 | 0 | 0 | 0 | 0 | 0% |
| Nguyễn Văn Huy Hoàng | 23 | 23 | 0 | 0 | 0 | 0 | 0% |

### Update rules

- Chuyển `TODO → IN_PROGRESS` khi owner thực sự bắt đầu và ghi link branch/work artifact.
- Chuyển `IN_REVIEW` khi deliverable/evidence sẵn sàng cho reviewer.
- Chỉ `DONE` khi acceptance của task đạt và evidence link/reviewer được ghi; deadline đến không tự đổi status.
- `BLOCKED` phải ghi blocker, ảnh hưởng milestone, owner xử lý và next review time.
- Khi status đổi, cập nhật summary counts và milestone/critical-path impact trong cùng change.
