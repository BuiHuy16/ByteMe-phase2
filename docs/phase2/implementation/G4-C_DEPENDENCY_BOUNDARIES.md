# G4-C Implementation Plan — Dependency Boundaries

- **Status:** `PENDING_TEAM_APPROVAL`
- **ADR:** ADR-003 trong [`03_ARCHITECTURE_DECISIONS.md`](../03_ARCHITECTURE_DECISIONS.md)
- **Owner:** Bùi Công Huy (workstream C)
- **Reviewer:** Nguyễn Văn Huy Hoàng (workstream D)
- **Branch:** `feature/g4-c-dependency-boundaries`
- **Application changes authorized:** Chưa; chỉ bắt đầu sau khi ADR-003 chuyển `ACCEPTED`

## 1. Mục tiêu và phạm vi

Mục tiêu là loại dependency ngược từ Auth persistence adapter sang service exceptions, đóng package cycle `service ↔ repository` và đặt automated architecture gates để ngăn tái diễn mà không đổi API/error behavior.

Trong phạm vi:

- Thêm repository exceptions nội bộ cho lỗi persistence chung và duplicate account.
- `MySqlAccountRepository` chỉ ném repository exceptions; không import package `service`.
- `RegisterService`/`LoginService` map repository exceptions sang service exceptions hiện hữu.
- Thêm ArchUnit rules cấm `repository → service` và kiểm tra cycle giữa top-level packages.
- Chạy Auth unit/web/integration regression để giữ duplicate-account và persistence-error semantics.

Ngoài phạm vi:

- Refactor `OrderService`, `OrderRepository`, Cart/Food paths hoặc bất kỳ method ownership nào của G4-A/G4-B/G4-D.
- Tách DTO/entity, đổi `AccountRepository` port sang package mới, modularize build hoặc chuyển toàn bộ code sang ports/adapters.
- Sửa `GlobalErrors`, `AuthErrors`, endpoint, payload, HTTP status/code, schema, OpenAPI hoặc benchmark protocol.
- Chuẩn hóa transaction convention của Auth; thay đổi vendor-specific duplicate detection ngoài phần bọc exception tối thiểu.

**BEFORE reference bất biến:** một top-level package cycle `service ↔ repository` đã được G1 xác nhận; `MySqlAccountRepository` có hai import ngược tới `AccountPersistenceException` và `DuplicateAccountException`; `ArchitectureTest` chưa có rule cấm hướng này hoặc package-cycle rule.

## 2. Các chi tiết đã chốt cho implementation

### 2.1. Exception boundary

| Layer | Exception contract | Trách nhiệm |
|---|---|---|
| Repository | `AccountRepositoryException`, `DuplicateAccountRecordException` (tên cuối do team duyệt) | Bao lỗi data access/vendor detection; không phụ thuộc service/controller |
| Service | Existing `AccountPersistenceException`, `DuplicateAccountException` | Giữ use-case/error semantics mà controller và test hiện hữu quan sát |
| Controller | Existing `AuthErrors` mapping | Giữ `409 ACCOUNT_CONFLICT`, `no-store` và generic 500 path hiện hữu |

Repository exceptions là unchecked và không xuất hiện trong controller contract. `RegisterService` map duplicate repository exception sang `DuplicateAccountException`; cả `RegisterService` và `LoginService` map lỗi repository chung sang `AccountPersistenceException`. Existing pre-check duplicate và post-create invariant giữ nguyên.

### 2.2. Dependency direction

Sau thay đổi, hướng dependency được phép trong lát Auth là:

`controller → service → repository interface/exception → repository adapter/entity`

Không class trong `org.example.repository..` được phụ thuộc `org.example.service..`. G4-C không đổi lựa chọn package-by-layer hiện tại và không đưa ra tuyên bố rằng toàn bộ application đã thành clean/hexagonal architecture.

### 2.3. Architecture-test policy

`ArchitectureTest` bổ sung hai gate:

1. `repository` không phụ thuộc class trong `service`.
2. Các top-level slices dưới `org.example.(*)..` không có cycle.

Test đầu tiên cho failure message trực tiếp theo boundary; test thứ hai bảo vệ graph tổng quát. Không thêm allow-list để che cycle hiện tại. Nếu cycle khác xuất hiện sau khi import full production classes, dừng và review evidence thay vì exclude package âm thầm.

### 2.4. Behavior preservation

- Duplicate từ pre-check hoặc unique constraint race vẫn thành service `DuplicateAccountException` và HTTP `409 ACCOUNT_CONFLICT`.
- Lỗi persistence khác vẫn thành service `AccountPersistenceException`, đi qua generic server-error policy hiện hữu và không lộ DB message.
- Login invalid credentials/account inactive, registration validation, hashing/token behavior và transaction annotations giữ nguyên.

## 3. File và method cần sửa

| File | Method/khối | Thay đổi dự kiến | Owner |
|---|---|---|---|
| new `src/main/java/org/example/repository/AccountRepositoryException.java` | toàn file | Repository-local wrapper cho persistence failure | C — Bùi Công Huy |
| new `src/main/java/org/example/repository/DuplicateAccountRecordException.java` | toàn file | Repository-local duplicate signal, không chứa HTTP concern | C — Bùi Công Huy |
| `src/main/java/org/example/repository/MySqlAccountRepository.java` | `existsByEmailOrPhone`, `createCustomer`, `findCredentialByEmail` | Thay service exceptions bằng repository exceptions; giữ vendor detection/mapping hiện hữu | C — Bùi Công Huy |
| `src/main/java/org/example/service/RegisterService.java` | `register` | Map repository duplicate/general failure sang service exceptions hiện hữu | C — Bùi Công Huy |
| `src/main/java/org/example/service/LoginService.java` | `login` repository call | Map repository failure sang `AccountPersistenceException` | C — Bùi Công Huy |
| `src/test/java/org/example/ArchitectureTest.java` | new dependency/cycle rules | Cấm `repository → service`; enforce cycle-free top-level slices | C — Bùi Công Huy |
| `src/test/java/org/example/AuthWebAndServiceTest.java` | duplicate/persistence cases | Giữ service exception và API/error behavior | C — Bùi Công Huy |
| `src/test/java/org/example/AuthIntegrationTest.java` | concurrent duplicate/persistence coverage | Xác minh unique-race mapping trên MySQL nếu fixture hiện hữu hỗ trợ | C — Bùi Công Huy |

Không sửa `OrderService.java`, `OrderRepository.java`, `OrderServiceTest.java`, `CartService.java`, `FoodService.java`, DTO/entity, `AuthErrors.java`, `GlobalErrors.java`, schema/config, OpenAPI, benchmark profiles hoặc BEFORE evidence.

## 4. Thiết kế method-level

### 4.1. Repository adapter

`MySqlAccountRepository` giữ nguyên `SQLException` code/constraint inspection. Nhánh duplicate ném repository duplicate exception; các nhánh `RuntimeException` khác ném repository persistence exception với cause. Adapter không import service exception và không tự quyết HTTP/error code.

### 4.2. Service mapping

`RegisterService.register` map repository duplicate exception sang existing `DuplicateAccountException`; repository failure khác sang `AccountPersistenceException`. Mapping chỉ bao quanh repository calls, không catch service validation/hash failure và không nuốt cause.

`LoginService.login` map repository failure tại credential lookup sang `AccountPersistenceException`; invalid credentials và account-state behavior sau lookup giữ nguyên.

### 4.3. Architecture rules

Rule direction dùng package predicate rõ ràng để failure nêu class dependency vi phạm. Cycle rule dùng production classes, top-level package slices và không include tests. Cả hai rule chạy trong existing `ArchitectureTest` để thuộc default Maven test gate.

## 5. Thứ tự task

1. **C0 — Approval gate:** team duyệt ADR-003, exception names/mapping, owner/reviewer và out-of-scope list.
2. **C1 — Tests-first baseline:** thêm hai ArchUnit rules, lưu failure chứng minh một cycle và hai reverse imports trên baseline.
3. **C2 — Repository exception contract:** thêm hai exception nội bộ, không phụ thuộc service/controller.
4. **C3 — Adapter cleanup:** chuyển `MySqlAccountRepository` sang repository exceptions; giữ duplicate detection và cause.
5. **C4 — Service mapping:** map tại `RegisterService`/`LoginService`, giữ outward service exceptions.
6. **C5 — Auth regression:** chạy/cập nhật Auth unit, web và MySQL integration tests cho duplicate/general persistence behavior.
7. **C6 — Architecture/combined gate:** ArchUnit đạt 0 reverse dependency/0 cycle; targeted Auth và impacted G4-A/G4-B tests pass sau rebase.
8. **C7 — Handoff:** review/merge C sau A và B trong ngày 02/12; D rebase trên integrated A+B+C trước khi G5 chạy trên A+B+C+D SHA.

## 6. Test cần viết/cập nhật

### Architecture tests

- BEFORE failure chỉ ra `MySqlAccountRepository` phụ thuộc hai service exception và cycle `service ↔ repository`.
- AFTER `repositoryDoesNotDependOnServices` pass với 0 violation.
- AFTER top-level slices cycle rule pass với 0 cycle.
- Rules import toàn bộ production package `org.example`, không exclude Auth adapter hoặc exception classes.

### Unit/web

- `RegisterService` map duplicate repository signal sang `DuplicateAccountException`.
- General repository failure từ exists/create/login lookup thành `AccountPersistenceException` với cause được giữ.
- Validation, invalid credential và account inactive vẫn dùng error/service path hiện hữu.
- Registration duplicate vẫn trả `409 ACCOUNT_CONFLICT`, payload/message policy và `Cache-Control: no-store` không đổi.

### MySQL integration

- Concurrent unique race tiếp tục cho tối đa một create success; loser nhận duplicate service behavior, không generic 500.
- Repository mapping/transaction behavior hiện hữu giữ nguyên; không đổi schema hoặc constraint.

## 7. Acceptance criteria

- AFTER có **0** top-level package cycle và **0** dependency `repository → service`, được chứng minh bằng hai ArchUnit rules trong default test suite.
- `MySqlAccountRepository` có **0** import từ `org.example.service`; repository exceptions không import controller/service.
- `RegisterService`/`LoginService` là nơi duy nhất trong scope map repository failure sang service exceptions hiện hữu.
- Auth unit/web/integration regression pass; duplicate account vẫn là `409 ACCOUNT_CONFLICT`; lỗi persistence khác không lộ DB/vendor message.
- Không sửa endpoint/payload/schema/transaction semantics và không đổi file/method ownership G4-A/G4-B/G4-D.
- Review diff xác nhận không có refactor `OrderService`, DTO/entity, common error policy hoặc package/module redesign.

## 8. Ownership và merge contract

- Bùi Công Huy sở hữu toàn bộ G4-C; Nguyễn Văn Huy Hoàng review từng task/PR slice.
- G4-C phát triển từ 25/11 đến 02/12 trên branch riêng; không chạm shared files/methods của A/B và không sửa authorization fallback thuộc D.
- Thứ tự merge bắt buộc giữ A trước B. Sau B merge, C rebase lên integrated A+B, chạy Architecture/Auth regression cùng impacted targeted gates rồi merge trước D trong ngày 02/12.
- `ArchitectureTest.java` thuộc C trong workstream này. Nếu A/B cần sửa file này, thay đổi phải được review chéo và không được làm yếu dependency/cycle rules.
- Trong `AuthIntegrationTest`, C sở hữu duplicate/persistence/concurrent-insert methods và repository fixture; D chỉ sở hữu `OtherModuleController`, method `/scope-check/**` và test-only security setup liên quan sau C-05. C không sửa D-owned blocks.
- Conflict resolution không được format/rewrite file ngoài scope hoặc đổi A/B/D semantics. G5 chỉ bắt đầu khi A, B, C và D đều merge; C architecture/Auth gates phải pass lại sau D rebase.

## 9. Approval checklist

- [ ] ADR-003 chuyển `ACCEPTED` sau review thực tế.
- [ ] Bùi Công Huy nhận owner responsibility; Nguyễn Văn Huy Hoàng nhận review responsibility.
- [ ] Team duyệt repository exception names, service mapping và behavior-preservation contract.
- [ ] Team duyệt hai ArchUnit rules, BEFORE/AFTER measures và out-of-scope list.
- [ ] Team xác nhận merge order A → B → C → D và G5 dependency trên integrated A+B+C+D SHA.
- [ ] Chỉ sau năm điều kiện trên mới bắt đầu application change.
