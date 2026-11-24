# G4-A Implementation Plan — Pessimistic Locking

- **Status:** `PENDING_TEAM_APPROVAL`
- **ADR:** ADR-001 trong [`03_ARCHITECTURE_DECISIONS.md`](../03_ARCHITECTURE_DECISIONS.md)
- **Owner:** Nguyễn Văn Huy Hoàng (workstream A)
- **Reviewer:** Bùi Công Huy (workstream B)
- **Application changes authorized:** Chưa; chỉ bắt đầu sau khi ADR-001 chuyển `ACCEPTED`

## 1. Mục tiêu và phạm vi

Mục tiêu là làm các mutation hiện hữu trên Cart/Order/Food cho kết quả tuần tự hợp lệ dưới contention, đóng AF-01/AF-02 và guard AF-04 mà không đổi topology, success payload hay nghiệp vụ.

Trong phạm vi:

- C1: hai cart checkout cùng food không oversell/lost update.
- C4: admin absolute stock update và checkout không tạo final stock ngoài outcome tuần tự.
- C2 guard: hai checkout cùng cart chỉ commit tối đa một order/stock consumption và expected contention không thành 5xx.
- Đồng bộ lock protocol cho stock writers hiện hữu: checkout reserve, cancellation release, admin update và soft delete Food.
- Đồng bộ Order state mutation để concurrent confirm/status/cancel không cùng đọc một stale Order state.
- Error mapping, targeted unit/MySQL concurrency tests và API conflict documentation nếu spec đang thiếu.

Ngoài phạm vi:

- Optimistic version column, atomic SQL stock update, distributed lock, retry queue hoặc idempotency key.
- Cart add/update/remove chạy đồng thời với checkout; first-cart race C5; distributed/multi-instance coordination.
- Thay isolation toàn database, đổi schema/index hoặc tối ưu data access của G4-B.
- Thay đổi business transition, success response hoặc BEFORE artifacts/metrics.

**BEFORE reference bất biến:** C1 G2.3 `6/15` violation, official C1 `0/45`; C4 G2.3 `12/15`, official C4 `37/45`; same-cart official `0/45` data violation và `1/45` server-error round; W2 checkout p50/p95/p99 `25.485/47.810/69.858 ms`. Plan không rebaseline hoặc diễn giải lại các số này.

## 2. Các chi tiết đã chốt cho implementation

### 2.1. Lock coverage

| Path | Row lock bắt buộc | Thứ tự |
|---|---|---|
| Checkout | Cart của customer; toàn bộ Food trong locked cart snapshot | `Cart → distinct Food.id ASC` |
| Admin `updateFood` | Food đích, kể cả request không đổi stock | `Food` |
| Admin `deleteFood` | Food đích trước khi đổi status | `Food` |
| Customer/employee cancellation | Order đích; Food của order items nếu transition sang `CANCELLED` | `Order → distinct Food.id ASC` |
| Confirm/other status transition | Order đích | `Order` |

`Cart` phải được khóa trước lần đọc items dùng cho checkout. `Food` phải được batch-load bằng locking query đã order theo primary key; không lock theo `cart_items.id`, map iteration hoặc request order. Không path nào trong scope được khóa Food rồi quay lại lấy Cart/Order.

Cart add/update/remove và first-cart creation không nhận lock coverage mới trong G4-A. Plan không được tuyên bố giải quyết các interleaving đó.

### 2.2. Transaction boundary và isolation

- Giữ `@Transactional` outer boundary tại `OrderService.create`, `cancel`, `confirm`, `updateStatus` và `FoodService.updateFood/deleteFood`.
- Helper service/repository tham gia transaction caller với propagation mặc định `REQUIRED`; không dùng `REQUIRES_NEW`, không flush/commit từng food và không catch exception để commit partial state.
- Giữ `Isolation.DEFAULT`, resolved thành MySQL/InnoDB `REPEATABLE READ` như baseline. Không nâng toàn transaction/database lên `SERIALIZABLE`.
- Pessimistic locking read là current/locking read; correctness đến từ row lock, không dựa vào snapshot read.
- Không external/network I/O trong transaction. DTO cần thiết được dựng trước khi method trả về; lock được release tại commit/rollback của service transaction.

### 2.3. Lock timeout

- Chốt semantic **fail-fast/no-wait: `jakarta.persistence.lock.timeout = 0`** trên mọi locking repository query của G4-A.
- Primary implementation dùng `@Lock(PESSIMISTIC_WRITE)` và repository-local `@QueryHint`; không đổi global `innodb_lock_wait_timeout`, Hikari hoặc benchmark configuration.
- MySQL integration test phải chứng minh một transaction giữ row lock làm contender fail nhanh và được map thành 409. Nếu Hibernate/MySQL dialect bỏ qua hint hoặc chờ theo DB default, dừng implementation để review ADR; không âm thầm chấp nhận 50 giây hoặc đổi sang native SQL.
- Mọi AFTER build dùng cùng application/JAR behavior; timeout là treatment code, không phải runtime drift.

### 2.4. Conflict semantics

| Condition | HTTP/code | Retry policy |
|---|---|---|
| Lock acquisition failure, no-wait conflict hoặc deadlock được Spring phân loại là pessimistic lock failure | `409 CONCURRENT_UPDATE` | Không server-side retry; client đọc lại state rồi gửi request mới |
| Stock không đủ sau khi đã lấy lock | `409 INSUFFICIENT_STOCK` | Business decision; không auto-retry |
| Food inactive sau khi đã lấy lock | Existing `409 FOOD_UNAVAILABLE` | Không auto-retry |
| Overlapping same-cart checkout thua tại Cart lock | `409 CONCURRENT_UPDATE` | Không auto-retry |
| Request bắt đầu sau khi checkout trước đã commit và thấy cart rỗng | Existing `400 EMPTY_CART` | Không được gắn nhãn concurrency failure |

Response giữ `Cache-Control: no-store`; không lộ DB/Hibernate message và không thêm `Retry-After` khi chưa có retry/idempotency contract. Existing `GlobalErrors.lockConflict` là contract mặc định. Chỉ mở rộng exception set nếu MySQL integration test chứng minh một lock timeout/deadlock hợp lệ đang rơi xuống 500.

## 3. File và method cần sửa

| File | Method/khối | Thay đổi dự kiến | Owner |
|---|---|---|---|
| `src/main/java/org/example/repository/CartRepository.java` | new `findByUserIdForUpdate(Long)` | Lock Cart bằng `PESSIMISTIC_WRITE`, no-wait; trả `Optional<Cart>` | A |
| `src/main/java/org/example/repository/FoodRepository.java` | new `findAllByIdForUpdate(Collection<Long>)` | Lock distinct Food rows bằng một query `ORDER BY id`, no-wait | A |
| `src/main/java/org/example/repository/FoodRepository.java` | optional `findByIdForUpdate(Long)` | Chỉ thêm nếu không reuse batch method cho single-row admin path | A |
| `src/main/java/org/example/repository/OrderRepository.java` | new `findByIdForUpdate(Long)` | Lock Order cho cancel/confirm/status, no-wait; không sửa query list của B | A |
| `src/main/java/org/example/service/CartService.java` | `getItemsForCheckout` | Dùng locked Cart lookup; đổi tên thành `getItemsForCheckoutLocked` nếu team duyệt explicit naming; copy items sau lock | A |
| `src/main/java/org/example/service/CartService.java` | `clearCart` | Giữ cùng outer transaction và locked persistence context; không mở transaction mới | A |
| `src/main/java/org/example/service/FoodService.java` | `updateFood`, `deleteFood` | Load Food qua locking repository method trước validation/mutation | A |
| `src/main/java/org/example/service/FoodService.java` | replace/extend `reserveStock` | Thêm batch reservation nhận map foodId→quantity, lock IDs ascending một lần, validate toàn bộ rồi mutate; trả snapshot keyed by ID | A |
| `src/main/java/org/example/service/FoodService.java` | replace/extend `releaseStock` | Batch release sau khi lock distinct IDs ascending; giữ behavior release inactive food | A |
| `src/main/java/org/example/service/OrderService.java` | `create` | Locked cart snapshot → batch lock/reserve foods → build items theo cart order → save → clear | A, method-exclusive |
| `src/main/java/org/example/service/OrderService.java` | `cancel`, `confirm`, `updateStatus`, `moveTo` | Load Order bằng lock; batch release khi cancel; không đổi transition matrix | A, method-exclusive |
| `src/main/java/org/example/common/GlobalErrors.java` | `lockConflict` | Giữ hiện trạng; chỉ mở rộng typed exceptions nếu integration evidence yêu cầu | A |
| `src/main/resources/static/openapi.yaml` | responses của checkout/admin mutation | Bổ sung/chuẩn hóa `409 CONCURRENT_UPDATE` nếu chưa được mô tả; không đổi success schema | A |
| `src/test/java/org/example/FoodServiceTest.java` | reserve/release/admin tests | Cập nhật mocks/signature; assert sort, all-before-mutate và unchanged business codes | A |
| `src/test/java/org/example/OrderServiceTest.java` | checkout/status/cancel methods | Cập nhật batch reservation/release và locked lookup; không sửa list-test của B | A, method-exclusive |
| new `src/test/java/org/example/OrderConcurrencyIntegrationTest.java` | toàn file | MySQL Testcontainers concurrency/lock-timeout/final-state suite | A |
| `src/test/java/org/example/OrderWebTest.java` | `lockConflictsAre409RetryableInsteadOf500` | Giữ regression; đổi tên “retryable” nếu semantics mới không hứa auto-retry | A |

Không sửa `Food`, `Cart`, `Order` để thêm `@Version`; không sửa `schema.sql`, `compose.yaml`, benchmark profiles hoặc BEFORE evidence.

## 4. Thiết kế method-level

### 4.1. Checkout

1. `OrderService.create` validate request fields không chạm DB.
2. `CartService.getItemsForCheckoutLocked(customerId)` lấy Cart row bằng no-wait lock rồi đọc items; trả `LinkedHashMap` snapshot. Cart không tồn tại/rỗng giữ behavior `EMPTY_CART`.
3. `FoodService.reserveStocks(cart)`:
   - reject quantity invalid theo contract hiện có;
   - distinct/sort IDs ascending;
   - lock toàn bộ Food bằng một repository query;
   - xác minh số row trả về đúng số ID; missing ID map `FOOD_NOT_FOUND` theo ID deterministic;
   - validate active và đủ stock cho **tất cả** row trước mutation;
   - decrement managed entities và trả immutable FoodDto map.
4. Dựng OrderItem theo thứ tự cart snapshot để không đổi response ordering; lấy name/price từ locked Food snapshot.
5. Save Order, clear Cart và map DTO. Bất kỳ exception nào rollback toàn bộ.

### 4.2. Admin update/delete

`updateFood`/`deleteFood` lock Food trước khi đọc field và mutate. Category/name existence checks không giữ lock row khác ngoài Food; unique constraint tiếp tục là final guard. Nếu update chỉ thay metadata, vẫn lock để checkout snapshot không trộn metadata/status cũ và stock mới.

### 4.3. Order transitions/cancellation

`cancel`, `confirm`, `updateStatus` dùng `findByIdForUpdate`. Ownership và transition validation chạy sau lock. Khi transition sang `CANCELLED`, group quantities theo food ID, sort/lock foods một lần rồi release. Hai item cùng food không được lock/mutate hai lần; tổng quantity phải dùng overflow-safe addition hoặc invariant-protected sum. Order status/timestamps chỉ mutate sau khi release validation hoàn tất.

## 5. Thứ tự task

1. **A0 — Approval gate:** team duyệt ADR-001, no-wait semantics, method signatures và out-of-scope list.
2. **A1 — Tests-first contract:** tạo skeleton MySQL concurrency tests cho C1/C2/C4, lock no-wait và rollback; xác nhận chúng fail đúng trên baseline.
3. **A2 — Repository locks:** thêm Cart/Food/Order locking methods và repository-level integration proof cho order/no-wait behavior.
4. **A3 — Cart serialization:** chuyển checkout snapshot sang locked Cart; giữ empty/missing semantics.
5. **A4 — Food batch mutation:** implement sorted batch lock/reserve/release; chuyển admin update/delete sang locked read.
6. **A5 — Order orchestration:** cập nhật `create` và transition/cancel path, giữ atomic boundary và response ordering.
7. **A6 — Conflict/API mapping:** xác minh typed exception → `409 CONCURRENT_UPDATE`; chỉ sửa `GlobalErrors`/OpenAPI nếu evidence yêu cầu.
8. **A7 — Targeted verification:** chạy unit, web và concurrency integration suites; phân loại deadlock/timeout/5xx, không rerun để che failure.
9. **A8 — Regression gate:** chạy full existing suite + new tests, lưu report; review diff không có schema/config/benchmark drift.
10. **A9 — Handoff:** merge A trước theo Mục 8; chưa chạy official AFTER cho tới khi G4-B đã merge và combined regression pass.

## 6. Test cần viết/cập nhật

### Unit/service

- Checkout gọi locked cart snapshot trước batch Food reservation; order save trước cart clear; failure không clear.
- Food IDs được distinct/sort ascending dù cart insertion order đảo; missing/inactive/insufficient giữ error code và không mutate row nào.
- Admin update/delete dùng locking lookup; request không có stock vẫn giữ existing stock behavior.
- Cancellation group/sort Food IDs, release đúng một lần và giữ transition/timestamp semantics.
- Existing rollback, ownership, snapshot price/name và order-type tests giữ pass.

### MySQL integration/concurrency

- **C1:** hai cart, same food, demand > stock; synchronized contenders; 0 oversell/lost update, 0 5xx, final stock/order/cart invariants đúng.
- **C2:** hai checkout same cart; tối đa một order; loser 409 nếu overlap tại Cart lock; 0 5xx và rollback không phá winner.
- **C4:** admin absolute assignment vs checkout; final stock chỉ thuộc tập outcome tuần tự hoặc một caller nhận 409; 0 invalid-success pair.
- No-wait proof: transaction T1 giữ Cart/Food/Order row; T2 fail-fast, elapsed nằm dưới test budget được team duyệt và HTTP mapping là 409.
- Reversed multi-food carts không deadlock do ascending Food lock order.
- Concurrent cancel/status trên same Order không double release/invalid transition commit.
- Existing fault injection vẫn rollback Order/items/stock/cart.

Không dùng sleep làm synchronization chính; dùng latch/barrier/future timeout và assert final DB state. Official 45-round/three-run evidence thuộc acceptance execution, không thay thế deterministic integration tests.

## 7. Acceptance criteria

Giữ nguyên G3.2:

- C4 official AFTER: **0/45** invariant violation, **0** server-error round.
- C1: **0** oversell/lost update trong ít nhất 45 overlapping rounds bằng protocol tương đương; không claim định lượng nếu BEFORE không tái hiện trên cùng protocol.
- C2: **0/45** data violation, **0/45** server-error round, tối đa một order/consumption.
- W2 checkout median p95 `≤52.591 ms`, p99 `≤76.844 ms`; server errors 0.
- Full existing regression và targeted tests mới pass; success API/ownership/RBAC/snapshot behavior không đổi.

Implementation-specific gates:

- Runtime proof xác nhận `lock.timeout=0` thực sự no-wait trên MySQL 8.4; không fallback DB default.
- Không có schema/index/version column, `SERIALIZABLE`, auto-retry hoặc benchmark lock drift.
- Mọi lock path tuân `Cart/Order → Food.id ASC`; static review và concurrency tests không phát hiện path ngược.
- Nếu latency hoặc lock-failure rate không đạt, ADR-001 trở lại `PROPOSED`; không tự chuyển sang atomic SQL trong cùng change set.

## 8. Ownership và merge contract

- G3 review/approval/publish diễn ra 23–24/11/2026; bốn workstream bắt đầu từ 25/11 sau M1. Nguyễn Văn Huy Hoàng sở hữu G4-A trong toàn cửa sổ 25/11–02/12; Bùi Công Huy review từng task và PR A.
- A sở hữu `OrderService.create/cancel/confirm/updateStatus/moveTo`; B sở hữu duy nhất `OrderService.list`.
- Trong `OrderRepository`, A chỉ thêm lock-by-ID method; B sở hữu filter/page/fetch/count methods. Không format/rename toàn file.
- Trong `OrderServiceTest`, A chỉ sửa checkout/status/cancel tests và shared setup tối thiểu. B sửa list test sau khi rebase.
- File riêng A: `CartRepository`, `FoodRepository`, `CartService`, `FoodService`, `FoodServiceTest`, `GlobalErrors`, concurrency integration test và conflict OpenAPI entries.
- **Merge order bắt buộc:** G4-A merge trước. G4-B rebase lên G4-A, resolve imports/constructor/shared tests theo method ownership, rồi merge sau review chéo.
- Sau merge A, B/C/D tiếp tục theo integration contract A → B → C → D. A không sửa list fetch plan, Auth dependency boundary hoặc authorization fallback; các workstream sau không sửa locking semantics khi resolve conflict.

## 9. Approval checklist

- [ ] ADR-001 chuyển `ACCEPTED`.
- [ ] Team duyệt no-wait `0`, 409 semantics và no-auto-retry.
- [ ] Team duyệt lock coverage/out-of-scope và method signatures.
- [ ] Bùi Công Huy nhận review responsibility và merge order.
- [ ] Chỉ sau bốn mục trên mới bắt đầu application change.
