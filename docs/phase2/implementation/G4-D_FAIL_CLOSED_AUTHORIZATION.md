# G4-D Implementation Plan — Fail-Closed Authorization Boundary

- **Status:** `APPROVED`
- **ADR:** ADR-004 trong [`03_ARCHITECTURE_DECISIONS.md`](../03_ARCHITECTURE_DECISIONS.md)
- **Owner:** Nguyễn Văn Huy Hoàng (workstream D)
- **Reviewer:** Bùi Công Huy (workstream C)
- **Branch:** `feature/g4-d-fail-closed-authorization`
- **Approval basis:** Quyết định dự án ngày 28/11/2026 chấp thuận plan và ADR-004 như đã viết; không yêu cầu approval riêng của từng thành viên.
- **Application changes authorized:** Sau khi bản approved được merge/publish và G3-04/M1 chuyển `DONE`.

## 1. Mục tiêu và phạm vi

Mục tiêu là áp dụng security tactic **fail-safe defaults** cho HTTP authorization: mọi route không được khai báo rõ trong hai `SecurityFilterChain` phải bị từ chối, trong khi 18 endpoint hiện hữu giữ nguyên public access, role permissions, status/error contract và nghiệp vụ.

Trong phạm vi:

- Đổi terminal fallback của protected chain từ `authenticated()` sang `denyAll()`.
- Giữ nguyên public Auth routes, public Food GET, Swagger/OpenAPI/health routes và role matchers hiện hữu.
- Thêm role-matrix regression cho đủ 18 endpoint hiện tại.
- Thêm synthetic test-only controller/route không có matcher để chứng minh valid CUSTOMER/EMPLOYEE/ADMIN đều bị từ chối trước controller.
- Giữ hành vi 401/403, `WWW-Authenticate`, `Cache-Control: no-store` và `ApiError` hiện hữu.
- Tách method ownership trong Auth tests với G4-C và chỉ tích hợp phần shared test sau khi C merge.

Ngoài phạm vi:

- Thêm, xóa hoặc đổi endpoint production; đổi nghiệp vụ, ownership/BOLA, service/repository/database hoặc response payload.
- JWT key rotation/revocation, claim redesign, login rate limiting, TLS/proxy hoặc audit logging.
- Refactor toàn bộ `SecurityConfiguration`, thay framework security hoặc sinh role policy từ OpenAPI.
- Sửa Auth persistence exception paths, `MySqlAccountRepository`, `RegisterService`, `LoginService` hoặc ArchUnit rules của G4-C.

**BEFORE reference bất biến:** G1 `SEC2-03` xác nhận protected chain kết thúc bằng `.anyRequest().authenticated()` và `TEST-06` xác nhận chưa có fail-closed route-registration test. Cả 18 endpoint production hiện tại đã có matcher cụ thể. `AuthIntegrationTest.OtherModuleController` khai báo `/scope-check/echo` ngoài matcher production, và test source hiện mong valid token nhận 200; đây là source-level proof cho fallback behavior, không được ghi thành runtime pass nếu chưa chạy test.

## 2. Các chi tiết đã chốt cho implementation

### 2.1. Authorization policy

Hai filter chain tiếp tục giữ trách nhiệm hiện tại:

1. Auth chain chỉ match `POST /api/auth/register` và `POST /api/auth/token`, `permitAll` như hiện tại.
2. Protected chain giữ explicit permit/role matchers cho documentation/health, Food, Cart và Order.
3. Terminal rule của protected chain đổi thành `.anyRequest().denyAll()`.

Không thêm wildcard rộng để làm synthetic test xanh. Route production mới trong tương lai phải có explicit policy và role-matrix evidence trước khi merge.

### 2.2. Current-route behavior preservation

| API group | Policy phải giữ |
|---|---|
| Auth register/token | Public qua chain riêng; malformed/invalid bearer nuance hiện hữu không đổi |
| Food GET list/search/detail | Public; invalid bearer behavior hiện hữu không đổi |
| Food POST/PUT/DELETE | Chỉ ADMIN |
| Cart GET/POST/PUT/DELETE | Chỉ CUSTOMER |
| Order POST/DELETE | Chỉ CUSTOMER |
| Order GET list/detail | CUSTOMER hoặc EMPLOYEE; ownership/service checks không đổi |
| Order confirm/status | Chỉ EMPLOYEE |

Role-matrix gate phải bao phủ toàn bộ **18/18** endpoint patterns và bốn caller classes: anonymous, CUSTOMER, EMPLOYEE, ADMIN. Test chỉ phân biệt security allow/deny; business response phía sau matcher có thể dùng mock để không biến D thành business integration scope.

### 2.3. Synthetic unlisted-route proof

Test định nghĩa controller chỉ tồn tại trong test source với path không xuất hiện trong production matchers. Với valid token của CUSTOMER, EMPLOYEE và ADMIN:

- response là `403 FORBIDDEN` theo error contract hiện hữu;
- controller invocation count bằng **0**;
- không role nào đi qua fallback nhờ chỉ cần authenticated.

Anonymous request tới route này tiếp tục nhận `401 UNAUTHENTICATED`. Test không thêm endpoint production và không đưa synthetic path vào production allow-list.

### 2.4. Auth-test integration với G4-C

G4-C sở hữu duplicate/persistence cases trong `AuthWebAndServiceTest` và `AuthIntegrationTest`. G4-D sở hữu duy nhất `OtherModuleController`, method kiểm tra `/scope-check/**` và test-only security setup cần thiết để giữ mục đích kiểm tra JSON/global error ngoài Auth.

D phát triển test matrix/synthetic proof trong file mới khi C đang làm việc. Phần shared `AuthIntegrationTest` chỉ được cập nhật sau khi C hoàn tất G4-C-05; D rebase sau C merge trước final gate. Không rewrite fixture/import hoặc persistence assertions thuộc C.

## 3. File và method cần sửa

| File | Method/khối | Thay đổi dự kiến | Owner |
|---|---|---|---|
| `src/main/java/org/example/config/SecurityConfiguration.java` | `protectedApi` terminal authorization rule | Đổi `.anyRequest().authenticated()` thành `.anyRequest().denyAll()`; không đổi matcher hiện hữu | D — Nguyễn Văn Huy Hoàng |
| new `src/test/java/org/example/FailClosedAuthorizationTest.java` | toàn file | 18-endpoint role matrix, synthetic-unlisted-route, 401/403/no-store regression | D — Nguyễn Văn Huy Hoàng |
| `src/test/java/org/example/AuthIntegrationTest.java` | `OtherModuleController`, `sharedJsonRulesAndGlobalErrorsApplyOutsideAuth` và test-only security setup liên quan | Bảo toàn mục đích JSON/global-error test sau fail-closed; không cho synthetic production-unlisted route dựa vào fallback | D sau C merge |
| `src/test/java/org/example/AuthIntegrationTest.java` | duplicate/persistence/concurrent insert methods và shared repository fixture | Không sửa trong D | C — Bùi Công Huy |
| `src/test/java/org/example/AuthWebAndServiceTest.java` | duplicate/persistence cases | Không sửa trong D | C — Bùi Công Huy |
| `src/test/java/org/example/ArchitectureTest.java` | dependency/cycle rules | Không sửa hoặc làm yếu | C — Bùi Công Huy |

Không sửa controllers, services, repositories, DTO/entity, `ApiError`, `AuthErrors`, `GlobalErrors`, OpenAPI, schema/config benchmark hoặc BEFORE evidence.

## 4. Thiết kế method-level

### 4.1. Production fallback

Thay đổi production duy nhất là terminal authorization decision trong `protectedApi`. Matcher có thứ tự cụ thể giữ nguyên; `denyAll` chỉ áp dụng sau khi request không match bất kỳ policy hiện hữu nào.

### 4.2. Role-matrix test

Test dùng cases dữ liệu hóa cho method/path/role/expected security outcome. Mỗi endpoint hiện hữu phải xuất hiện đúng một policy row; test kiểm tra anonymous và các role không được phép bị chặn trước service, còn role/public caller hợp lệ đi qua security layer. Business success chi tiết vẫn thuộc existing web/integration tests.

### 4.3. Error and filter-chain regression

Representative cases giữ:

- anonymous protected request → 401, `WWW-Authenticate: Bearer`, no-store;
- authenticated wrong role hoặc unlisted route → 403, no-store;
- public Auth/Food/documentation/health routes không bị fallback chặn;
- invalid bearer nuance của public Food GET và Auth chain không thay đổi;
- response body vẫn là `ApiError`, không thêm field hoặc status mới.

## 5. Thứ tự task

1. **D0 — Approval gate:** hoàn tất theo quyết định dự án ngày 28/11/2026 cho ADR-004, current-route matrix, synthetic test design, Auth-test method ownership và merge A → B → C → D; execution chờ G3-04/M1 `DONE`.
2. **D1 — BEFORE/test skeleton:** lưu source-level BEFORE, tạo role-matrix và synthetic route cases để chứng minh authenticated fallback hiện tại không fail-closed.
3. **D2 — Production fallback:** đổi terminal matcher sang `denyAll`, không chạm explicit matchers.
4. **D3 — Current-route matrix:** hoàn thiện 18/18 public/role regression và security error headers/body.
5. **D4 — Synthetic boundary:** chứng minh all authenticated roles bị 403 và controller không được gọi; anonymous nhận 401.
6. **D5 — Auth-test integration:** sau C-05, cập nhật đúng D-owned blocks trong `AuthIntegrationTest`, giữ global-error coverage và C-owned assertions.
7. **D6 — Targeted/combined gate:** chạy D tests, existing security/web/Auth regression và impacted C architecture/Auth gates trên branch đã cập nhật.
8. **D7 — Rebase/review/merge:** sau C merge, rebase D trên integrated A+B+C, rerun gates, review và merge ngày 02/12.

## 6. Test cần viết/cập nhật

### Authorization matrix

- Đủ 18 endpoint patterns; không thiếu/thừa so với controller inventory đã khóa trong G1.
- Auth public, Food public GET, protected Food writes, Cart, Order customer/employee actions giữ permission hiện hữu.
- Anonymous, CUSTOMER, EMPLOYEE và ADMIN đều có representative allow/deny assertions; allowed requests phải đi qua security tới mocked boundary.

### Fail-closed boundary

- Test-only unlisted route: valid CUSTOMER/EMPLOYEE/ADMIN đều 403, invocation count 0.
- Anonymous unlisted route: 401.
- Không thêm matcher production hoặc endpoint production chỉ để phục vụ test.

### Regression

- Existing Food/Cart/Order/Auth security tests pass.
- G4-C Auth duplicate/persistence behavior và ArchUnit gates vẫn pass sau rebase.
- 401/403 JSON, `WWW-Authenticate` và no-store giữ nguyên.
- Full regression thực hiện ở G5; D targeted gate không thay thế G5.

## 7. Acceptance criteria

- Protected chain có terminal `.anyRequest().denyAll()` và không còn authenticated fallback cho route chưa khai báo.
- **18/18** endpoint production giữ nguyên public/role permissions và không đổi nghiệp vụ, payload hoặc success/error contract.
- Synthetic unlisted route trả 403 cho valid CUSTOMER/EMPLOYEE/ADMIN, 401 cho anonymous, và controller invocation bằng 0.
- Không có endpoint/matcher production mới, không mở scope sang key rotation, audit logging hoặc Auth persistence.
- G4-C architecture/Auth gates và existing security/web regression pass sau integration.
- Review diff xác nhận D chỉ sửa production fallback, D-owned test file/blocks và không làm yếu matcher hoặc boundary rule khác.

## 8. Ownership và merge contract

- Nguyễn Văn Huy Hoàng sở hữu toàn bộ G4-D; Bùi Công Huy review từng task/PR slice.
- D phát triển song song từ 25/11 đến 02/12 trên branch riêng. Production file của D không overlap A/B/C.
- Bùi Công Huy sở hữu G4-C và persistence-related Auth test methods. Nguyễn Văn Huy Hoàng không sửa các method đó; shared Auth test change chỉ thực hiện sau C-05 và được Huy review.
- **Merge order:** A merge trước B; C rebase/merge sau B; D rebase trên integrated A+B+C và merge cuối. D phụ thuộc C chỉ ở shared Auth-test integration, C không phụ thuộc D, nên không có vòng dependency.
- G5 chỉ bắt đầu khi A/B/C/D đều merge và D role-matrix/fail-closed gates cùng C architecture/Auth gates pass.

## 9. Approval checklist

- [x] ADR-004 chuyển `ACCEPTED` theo quyết định dự án.
- [x] 18-endpoint policy matrix và public-route nuances phải giữ nguyên.
- [x] Synthetic-unlisted-route design, 401/403 contract và controller-not-invoked assertion được chốt.
- [x] Method ownership C/D trong `AuthIntegrationTest` và file test mới của D được chốt.
- [x] Merge order A → B → C → D và G5 dependency trên integrated SHA được giữ nguyên.
- [ ] Bản approved được merge/publish; G3-04/M1 `DONE` trước khi bắt đầu application change.
