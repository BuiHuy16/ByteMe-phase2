# G4-B Implementation Plan — Two-Step Fetching

- **Status:** `APPROVED`
- **ADR:** ADR-002 trong [`03_ARCHITECTURE_DECISIONS.md`](../03_ARCHITECTURE_DECISIONS.md)
- **Owner:** Bùi Công Huy (workstream B)
- **Reviewer:** Nguyễn Văn Huy Hoàng (workstream A)
- **Approval basis:** Quyết định dự án ngày 28/11/2026 chấp thuận plan và ADR-002 như đã viết; không yêu cầu approval riêng của từng thành viên.
- **Application changes authorized:** Sau khi bản approved được merge/publish và G3-04/M1 chuyển `DONE`.

## 1. Mục tiêu và phạm vi

Mục tiêu là loại N+1 của `GET /api/orders` bằng fetch plan hai bước có query count hằng, đồng thời giữ nguyên pagination, role/owner scope, filter/sort, `OrderPage` và `OrderDto`.

Trong phạm vi:

- Query ordered page of Order IDs với filter/sort/offset/limit hiện có.
- Query Orders + items cho đúng ID page, không pagination trên collection join.
- Root de-duplication, deterministic reorder, item ordering, empty-page/count consistency.
- Unit/MySQL query-count/contract tests và W1 AFTER acceptance.

Ngoài phạm vi:

- Batch fetching, DTO projection, cache, food search/index, order filter composite index hoặc detail endpoint optimization.
- Thay `OrderDto`, `OrderPage`, endpoint, security role matrix, schema/index hoặc benchmark workload/dataset.
- G4-A locking/transaction code ngoài method ownership quy định.

**BEFORE reference bất biến:** page size 1/5/20/50 tạo `4/8/23/53` SELECT; official W1 có median 901 order-list requests và 18,020 item SELECT; p50/p95/p99 `17.975/27.032/33.971 ms`, error/business rejection/server error đều 0. Plan không rebaseline hoặc diễn giải lại các số này.

## 2. Các chi tiết đã chốt cho implementation

### 2.1. Fetch plan và pagination consistency

1. `OrderService.list` giữ validation `page/size`, role mapping, owner scoping, statuses và type như hiện tại.
2. Bước 1 query **Order IDs** bằng cùng FILTER và sort `createdAt DESC, id DESC`; chỉ query này nhận `Pageable`/offset/limit.
3. Bước 2 query `select distinct o ... left join fetch o.items where o.id in :ids`; không `Pageable`. Order không có item vẫn phải được trả.
4. Kết quả bước 2 được index theo ID, reject duplicate/missing/unexpected ID như internal invariant, rồi reorder đúng chuỗi IDs bước 1.
5. Item order giữ theo `OrderItem.id ASC`, tương đương `@OrderBy("id")`; test không được dựa vào DB incidental order.
6. Count dùng cùng owner/status/type FILTER. Empty page không chạy fetch query nhưng vẫn chạy count và trả đúng metadata.

### 2.2. Transaction isolation và snapshot

- Giữ một `@Transactional(readOnly = true, isolation = Isolation.DEFAULT)` logic boundary tại `OrderService.list`; annotation có thể giữ cú pháp hiện tại nếu DEFAULT là implicit.
- Baseline MySQL/InnoDB `REPEATABLE READ` được giữ nguyên. Page IDs, fetch graph và count chạy trên cùng persistence context/transaction snapshot.
- Không dùng `REQUIRES_NEW`, không tách count/fetch sang async transaction, không bật Open Session in View và không nâng lên `SERIALIZABLE`.
- DTO mapping hoàn tất trong transaction để không lazy-load sau service return.

### 2.3. Query budget

- Non-empty page: ba application SELECT — page IDs, Orders+items, count.
- Empty page: hai application SELECT — page IDs và count.
- Acceptance vẫn dùng captured total `≤4` để cho phép một environment/driver stable-version SELECT đã có trong BEFORE diagnostic.
- Không thêm fallback lazy collection access; query-count test phải fail nếu `OrderDto.fromEntity` kích hoạt item SELECT/order.

### 2.4. API/consistency semantics

- `OrderPage(content,page,size,totalElements)` và toàn bộ `OrderDto`/`OrderItemDto` fields giữ nguyên.
- Customer chỉ thấy own orders; employee queue/default statuses và explicit filters giữ nguyên.
- Root order luôn `createdAt DESC, id DESC`, kể cả nhiều rows có cùng timestamp.
- `totalElements` phản ánh cùng scoped filter snapshot, không phải số row sau join.
- Không duplicate/missing Order do join multiplication; zero-item Order vẫn xuất hiện với `items=[]`, `totalAmount=0.00` như mapper hiện tại.

## 3. File và method cần sửa

| File | Method/khối | Thay đổi dự kiến | Owner |
|---|---|---|---|
| `src/main/java/org/example/repository/OrderRepository.java` | replace `search`/`findPage` path | Thêm `findPageIds(...)` dùng FILTER + stable sort + `Pageable` | B |
| `src/main/java/org/example/repository/OrderRepository.java` | new `findWithItemsByIdIn(Collection<Long>)` | `select distinct` + `left join fetch o.items`; không paginate | B |
| `src/main/java/org/example/repository/OrderRepository.java` | `countMatching` | Giữ query/semantics; chỉ refactor FILTER nếu cần dùng chung, không đổi result | B |
| `src/main/java/org/example/repository/OrderRepository.java` | A-owned `findByIdForUpdate` | Không sửa; preserve sau rebase G4-A | A |
| `src/main/java/org/example/service/OrderService.java` | `list` | IDs → fetch graph → validate/reorder → DTO map → count | B, method-exclusive |
| `src/main/java/org/example/service/OrderService.java` | optional private reorder helper | Local helper chỉ phục vụ list; deterministic map/order/invariant checks | B |
| `src/test/java/org/example/OrderServiceTest.java` | `customerListIsAlwaysScopedAndEmployeeDefaultsToActiveOrders` | Mock hai-step calls; assert IDs, scope, filter, reorder/count | B, method-exclusive |
| new `src/test/java/org/example/OrderQueryCountIntegrationTest.java` | toàn file | MySQL Testcontainers + Hibernate Statistics query-count/page-contract suite | B |
| `src/test/java/org/example/OrderIntegrationTest.java` | existing list/flow assertions | Chỉ bổ sung nếu fixture reuse cần thiết; ưu tiên file mới để tránh conflict | B |

Không sửa `Order`, `OrderItem`, `OrderDto`, `OrderPage`, `schema.sql`, `application.yml`, OpenAPI success schema, benchmark profiles hoặc BEFORE evidence.

## 4. Thiết kế method-level

### 4.1. Repository

`findPageIds` trả `List<Long>` theo FILTER hiện hữu. `PageRequest.of(page,size)` chỉ áp dụng tại ID query. Method không trả Spring `Page` để tránh một count ẩn ngoài count query được kiểm soát.

`findWithItemsByIdIn`:

- nhận non-empty, distinct, bounded IDs (`size ≤100` đã được service validate);
- dùng `left join fetch` để giữ Order không có items;
- dùng `distinct` cho root de-duplication;
- không giả định DB trả đúng page order;
- không thêm filter/status/owner lần hai vì ID page đã scoped trong cùng snapshot, nhưng result set phải được đối chiếu chính xác với requested IDs.

### 4.2. Service reorder/invariant

`OrderService.list` tạo map `id → Order`. Duplicate root ID, unexpected ID hoặc thiếu ID phải ném internal invariant exception để rollback/read fail rõ ràng; không silently drop/duplicate. Content được tạo bằng `pageIds.stream().map(byId::get).map(OrderDto::fromEntity)`.

Count có thể chạy trước hoặc sau fetch, nhưng phải ở cùng transaction. Plan chọn **sau fetch** để giữ sequence trong ADR/diagram; test không phụ thuộc thứ tự count nếu query budget và snapshot semantics vẫn đúng.

### 4.3. Query counting

Test-only configuration bật Hibernate statistics cho class query-count; clear statistics ngay trước một service call và đọc `prepareStatementCount` sau call. Không bật statistics trong production. Đồng thời inspect captured SQL/digest ít nhất một test để chứng minh không còn pattern `where order_id=?` lặp theo N; statement count đơn lẻ không đủ nếu fixture không có items.

## 5. Thứ tự task

1. **B0 — Approval gate:** hoàn tất theo quyết định dự án ngày 28/11/2026 cho ADR-002, query shapes, invariant behavior và ownership; execution chờ G3-04/M1 `DONE`.
2. **B1 — Parallel branch start:** từ 25/11, phát triển trên B-owned methods song song với G4-A/G4-C/G4-D; không chạm A-owned mutation/lock methods hoặc C/D Auth/security scope.
3. **B2 — Tests-first baseline:** tạo query-count test với page sizes 1/5/20/50 và chứng minh baseline `4/8/23/53` hoặc N+3 behavior trong test harness phù hợp.
4. **B3 — Repository two-step:** thêm ID page và fetch-with-items queries; giữ count.
5. **B4 — Service assembly:** cập nhật duy nhất `OrderService.list`; implement validation/reorder/DTO mapping.
6. **B5 — Unit/contract coverage:** cập nhật list unit test; thêm empty/zero-item/multi-item/tie-order/page-boundary cases.
7. **B6 — Pre-integration targeted verification:** chạy unit + query-count integration suite trên MySQL; inspect SQL không N+1.
8. **B7 — A-first integration gate:** sau G4-A merge ngày 02/12, rebase B, preserve A-owned methods/imports/tests và rerun targeted A+B.
9. **B8 — PR/combined handoff:** review/merge B ngày 02/12 trước C/D; combined regression thuộc G5 ngày 03–04/12, official AFTER chỉ sau Code Freeze.

## 6. Test cần viết/cập nhật

### Unit/service

- Customer/employee owner/status/type mapping được truyền nguyên vẹn vào `findPageIds` và `countMatching`.
- Page IDs bị trả khác thứ tự từ fetch query vẫn được output theo `createdAt DESC,id DESC` của page IDs.
- Empty ID page không gọi fetch query, content empty nhưng total/page/size đúng.
- Duplicate/missing/unexpected fetch result fail rõ ràng, không trả partial page.
- Size/page validation và overflow behavior giữ nguyên.

### MySQL integration/query count

- Page size 1/5/20/50 trên fixture có ít nhất một item/order: captured SELECT hằng và `≤4`; không còn one-item-query-per-order.
- Order có 0, 1 và nhiều items: full DTO fields, item set/order và `totalAmount` đúng.
- Nhiều Order cùng `createdAt`: tie-break `id DESC`, không duplicate/missing giữa hai page liên tiếp.
- Customer scope, employee default queue, explicit status/type filter và count khớp content scope.
- Out-of-range/empty page: content empty, total giữ đúng và không fetch items query.
- Root row multiplication từ join không làm duplicate Order; item order `id ASC`.
- Detail endpoint query behavior/contract không đổi.

### Official AFTER

- W1 order-list request rate/error/latency/query digest được thu đúng locked protocol; không dùng targeted integration latency làm performance claim.
- DB query digest/time/rows và backend heap/RSS được giữ để phát hiện row-multiplication/resource regression.

## 7. Acceptance criteria

Giữ nguyên G3.2:

- `≤4 captured SELECT/request` ở page size 1, 5, 20, 50; query count không tăng theo N và không còn one `order_items` SELECT/order.
- Pagination, total/count, sort, filter, ownership/RBAC, DTO/item snapshot và zero-item behavior không đổi.
- Ba AFTER run hợp lệ: W1 order-list 0 error, 0 business rejection, 0 server error, arrival rate theo lock 5 RPS.
- Median p95 `≤28.384 ms`, p99 `≤35.670 ms`; chỉ claim response-time improvement nếu p95 `≤24.329 ms` hoặc p99 `≤30.574 ms`.
- AFTER report có total SELECT/request và DB digest/time/rows; latency không được dùng một mình để suy nguyên nhân.

Implementation-specific gates:

- Non-empty page đúng ba application SELECT trong Hibernate statistics; captured total không quá bốn.
- Fetch query không có `Pageable`/limit trên collection join; ID list không vượt validated page size 100.
- Không thêm batch-size/global Hibernate config, projection DTO, schema/index hoặc production statistics.
- Nếu heap/RSS/result rows hoặc latency regression không đạt, ADR-002 trở lại `PROPOSED`; không tự chuyển sang batch/projection trong cùng change set.

## 8. Ownership và merge contract

- G3 approval được chốt ngày 28/11/2026; bốn workstream code/test song song sau khi G3-04/M1 publish hoàn tất trên method ownership riêng. Bùi Công Huy sở hữu G4-B. B không chờ A merge để triển khai, nhưng B không được merge trước A.
- B sở hữu `OrderService.list` và private helper chỉ phục vụ list; A sở hữu mọi mutation method.
- B sở hữu `OrderRepository` FILTER/page-ID/fetch-items/count methods; A sở hữu lock-by-ID method. B phải preserve method/annotations của A sau rebase.
- Trong `OrderServiceTest`, B chỉ sửa list test và shared setup/import tối thiểu sau A; không rewrite checkout/status assertions.
- B sở hữu file query-count integration mới. Không sửa A-owned concurrency integration test.
- **Merge order bắt buộc:** A merge trước; B rebase, resolve shared files theo method ownership, chạy targeted B + targeted A, rồi merge.
- Sau B, C rồi D rebase/merge theo dependency thực tế. Conflict resolution không được format toàn file hoặc đổi method signature của owner kia. Mọi cross-owner change cần explicit review comment của cả hai.

## 9. Approval checklist

- [x] ADR-002 chuyển `ACCEPTED`.
- [x] Page-ID/fetch/count query shapes và invariant behavior được chốt.
- [x] Nguyễn Văn Huy Hoàng giữ review responsibility; parallel method ownership được xác nhận.
- [ ] Trước merge B: G4-A đã merge, branch B đã rebase và preserve lock methods.
- [ ] Bản approved được merge/publish; G3-04/M1 `DONE` trước khi bắt đầu application change. Merge B còn bắt buộc mục rebase phía trên.
