# ByteMe Phase 2 — Architecture Decisions

Ngày lập: 2026-11-22. Tài liệu gồm **G3.1–G3.5**: tổng hợp bằng chứng G1–G2, ưu tiên vấn đề, xác định phạm vi, so sánh giải pháp, đề xuất kiến trúc To-Be và lập implementation plan để review trước G4. Các lựa chọn kỹ thuật ở G3.3–G3.4 mang trạng thái **PROPOSED**; các plan G3.5 mang trạng thái **PENDING_TEAM_APPROVAL** và chưa cấp quyền sửa application code.

## G3.1 — Tổng hợp và ưu tiên architecture findings

### 1. Cơ sở quyết định

Nguồn chính là [System Assessment](01_SYSTEM_ASSESSMENT.md), [Baseline & Benchmark](02_BASELINE_BENCHMARK.md) và official [BEFORE Intel aggregation](evidence/g2.5/2026-11-21/before-baseline-intel.md)/[JSON](evidence/g2.5/2026-11-21/before-baseline-intel.json). Source chỉ được dùng ở G1–G2 để giải thích transaction/query path; G3 không audit lại source.

Quy ước trong G3:

- **CONFIRMED**: đã có runtime evidence tái hiện issue hoặc có static evidence trực tiếp cho đặc tính kiến trúc được nêu.
- **RISK — UNVERIFIED**: đã thấy plan/behavior hoặc design exposure, nhưng chưa có bằng chứng đủ để kết luận impact đối với quality attribute.
- **DEFERRED**: có thể là issue thật, nhưng không nằm trong hai lát cải tiến nhỏ nhất có giá trị đo được cho nhóm hai người.
- Số latency đơn lẻ của G2.3 chỉ là diagnostic; số BEFORE chính thức dùng cho so sánh hiệu năng là median của ba run Intel đã khóa ở G2.5.

Baseline chính thức đã khóa ở application SHA `510f6415b6af535ceec77213f0b0c7d5082123f7`, nhóm `kaggle-intel-xeon`, ba run hợp lệ. AFTER phải qua cùng manifest comparator; không gộp run AMD vào nhóm Intel. Mục tiêu năm run chưa đạt là stretch target, không chặn baseline tối thiểu ba run.

### 2. Findings register đã ưu tiên

| ID | Ưu tiên | Phân loại | Finding và bằng chứng | Quyết định phạm vi |
|---|---|---|---|---|
| AF-01 | **P0** | **CONFIRMED DEFECT** | Admin gán stock tuyệt đối đồng thời checkout làm mất cập nhật dù cả hai request báo thành công: G2.3 sai invariant **12/15** round; official W3 lặp lại **37/45** round trên cả 3 run Intel. | Đưa vào cải tiến G4-A; đây là bằng chứng mạnh và lặp lại nhất về consistency. |
| AF-02 | **P0** | **CONFIRMED DEFECT** | Hai cart khác nhau checkout cùng food gây oversell/lost update **6/15** round trong G2.3: 14 đơn vị được commit từ stock 10, final stock 3. Official W3 không tái hiện ở **0/45**, nên kết quả đó là regression observation chứ không phủ định defect đã tái hiện. | Đưa vào cùng G4-A vì dùng chung inventory transaction boundary; phải giữ rõ khác biệt giữa hai protocol. |
| AF-03 | **P0** | **CONFIRMED DEFECT** | Order list phát sinh N+1: page size 1/5/20/50 tạo **4/8/23/53 SELECT**, tức `N+3`. Official W1 cũng ghi median **18,020** item SELECT cho khoảng **901** order-list request, tương ứng 20 item SELECT/request. | Đưa vào cải tiến G4-B; phạm vi hẹp, đo được và tách tương đối độc lập với G4-A. |
| AF-04 | **P1 guard** | **CONFIRMED symptom / correctness INCONCLUSIVE** | Same-cart checkout giữ đúng final data trong 15/15 round G2.3 nhưng loser có **2 HTTP 500**; official W3 có **1 server-error round/45**. Chưa có double order, nhưng conflict/error semantics chưa ổn định. | Không mở thành cải tiến thứ ba; G4-A phải có regression guard “không 5xx, tối đa một consumption/order”. Exact client-conflict contract cần review trước khi code. |
| AF-05 | **P2** | **RISK — UNVERIFIED** | Food search scan 5,000 rows với `LOWER(...) LIKE '%needle%'`; official W1 cho food search p95 **31.121 ms**, p99 **38.731 ms**, 0 error ở tải khóa 5 RPS. Plan bất lợi đã xác nhận nhưng user-visible severity/SLO violation chưa có. | **DEFERRED**; không tự động thêm index/search engine/cache trong G4. Chỉ nâng scope nếu workload/cardinality đại diện chứng minh impact. |
| AF-06 | **P2** | **RISK — UNVERIFIED** | Order filter/count dùng owner index rồi filter/sort, chưa có composite filter/sort index. G2.3 plan chỉ khoảng 0.459 ms ở 239 order của owner; performance severity được kết luận inconclusive. | **DEFERRED**; không gộp với N+1 để tránh thay nhiều biến cùng lúc. |
| AF-07 | **P2** | **CONFIRMED design debt, impact chưa đo** | Package cycle `service ↔ repository`, DTO/entity coupling và `OrderService` hotspot đã được static assessment xác nhận, nhưng chưa có change-cost/defect evidence gắn với mục tiêu G4. | **DEFERRED**; không refactor package/module trong lát performance/consistency. Chỉ sửa tối thiểu nếu implementation G4 bắt buộc chạm boundary. |
| AF-08 | — | **OBSERVED CORRECT trong protocol đã chạy** | Same-order cancellation không double-release stock 15/15; first-cart race giữ đúng một cart/item 15/15. Đây không phải bằng chứng tuyệt đối về mọi interleaving. | Không coi là defect cần sửa; giữ làm regression scenarios nếu code G4 chạm logic liên quan. |
| AF-09 | — | **NO JUSTIFICATION** | Layered monolith hiện phù hợp một nhà hàng, một deployable, nhóm hai người; G1–G2 không có evidence yêu cầu scale-out hoặc microservices. | **DEFERRED/REJECTED FOR G4**: không phân rã service, không thêm broker/distributed cache. |

### 3. Kết luận G3.1

Ba finding đủ bằng chứng để hành động là AF-01, AF-02 và AF-03. AF-01/AF-02 cùng thuộc một consistency boundary nên được gom thành một cải tiến; AF-03 thành cải tiến thứ hai. AF-04 là acceptance guard. AF-05/AF-06 là rủi ro hiệu năng chưa xác minh; AF-07 là debt đã xác nhận nhưng không có bằng chứng ưu tiên hơn hai lỗi runtime; AF-08 không cần remediation; AF-09 không có căn cứ mở rộng topology.

## G3.2 — Phạm vi cải tiến và tiêu chí dự kiến cho G4

### 1. Nguyên tắc chia scope cho hai thành viên

| Workstream | Owner đề xuất | Mục tiêu | Ranh giới chính |
|---|---|---|---|
| **G4-A — Inventory transaction/concurrency consistency** | Thành viên A | Làm checkout và admin stock update cho kết quả tương đương một thứ tự tuần tự hợp lệ; không oversell/lost update; conflict không thành 5xx. | Food stock mutation, checkout/admin update transaction path, concurrency tests và W3 AFTER. Không mở rộng sang distributed transaction hay idempotency toàn API. |
| **G4-B — Order-list data access efficiency** | Thành viên B | Loại query amplification phụ thuộc page size trong order list mà không đổi API behavior. | Order-list repository/mapping path, query-count tests và W1 AFTER. Không tối ưu food search, filter index, cache hay detail endpoint nếu không cần. |
| **Shared integration** | Cả hai | Giữ contract, regression suite và BEFORE/AFTER comparability. | Review chéo vùng `Order`/`Food`, merge tuần tự, chạy full gate sau khi hai lát độc lập đạt targeted gate. |

G3.3 so sánh và đề xuất kỹ thuật theo correctness, contention/query behavior, migration risk và testability. Đề xuất chỉ chuyển từ `PROPOSED` sang `ACCEPTED` sau design review đầu G4.

### 2. G4-A — Inventory transaction/concurrency consistency

#### Quality attribute scenarios

| QAS | Source / stimulus / environment | Artifact & response mong đợi | Response measure |
|---|---|---|---|
| **QAS-A1: concurrent checkout cùng food** | Hai customer có cart độc lập cùng checkout số lượng mà tổng demand vượt stock; request overlap trong MySQL thật. | Inventory/order/cart transaction path chỉ commit các order hợp lệ; stock không âm, committed quantity không vượt stock ban đầu, loser không làm mất/clear cart sai. | **0** oversell/lost-update invariant violation; **0** HTTP 5xx; final DB state thỏa invariant ở mọi round. |
| **QAS-A2: admin stock update vs checkout** | Admin gán stock tuyệt đối đồng thời customer checkout cùng food; hai request overlap. | Kết quả tương đương một trong hai thứ tự tuần tự hợp lệ, hoặc một request nhận conflict rõ ràng; không được cả hai success nhưng final stock ngoài tập outcome hợp lệ. | **0** non-serializable invariant violation; **0** HTTP 5xx; mọi success response tương ứng committed state. |
| **QAS-A3: same-cart duplicate checkout guard** | Hai checkout đồng thời trên cùng cart. | Tối đa một order/consumption; loser nhận client-visible non-5xx outcome ổn định; rollback không phá committed order. | **1** order tối đa, stock giảm đúng một lần, cart clear đúng một lần, **0** server-error round. |
| **QAS-A4: performance under locked write workload** | W2 chạy 10 VUs/180 giây trên AFTER Intel-compatible session với dataset/config/workload đã khóa. | Correctness control không tạo latency regression vượt ngưỡng review và không sinh server error. | Median-of-runs checkout p95/p99 trong guard dưới đây; server errors **0**. |

#### BEFORE metrics

| Measure | BEFORE |
|---|---:|
| C1 same-food oversell/lost update, G2.3 targeted protocol | **6/15 round (40%)** |
| Official W3 same-food invariant violations | **0/45**; dùng làm regression observation, không thay thế evidence 6/15 |
| C4 admin-stock vs checkout, G2.3 | **12/15 round (80%)** |
| Official W3 admin-stock vs checkout | **37/45 round (82.22%)**, xảy ra ở 3/3 run |
| Same-cart data invariant violations / server-error rounds, official W3 | **0/45 / 1/45** |
| W2 checkout median request rate | **95.677 RPS** (min 86.658; max 114.842) |
| W2 checkout median p50 / p95 / p99 | **25.485 / 47.810 / 69.858 ms** |
| W2 checkout errors / business rejections / server errors | **0 / 0 / 0** |

#### Acceptance criteria dự kiến

1. Trên tối thiểu **3 AFTER run Intel-compatible × 15 round/scenario**, QAS-A2 đạt **0/45** invariant violation và **0** server-error round.
2. QAS-A1 phải đạt **0** oversell/lost update trong ít nhất **45 overlapping rounds** bằng protocol có thể chứng minh transaction overlap hoặc tái hiện được BEFORE. Nếu official client-barrier protocol tiếp tục không tái hiện baseline C1, chỉ được tuyên bố “đóng regression/invariant”, không tuyên bố định lượng mức cải thiện C1 từ 6/15 xuống 0/45 nếu protocol không tương đương.
3. QAS-A3 đạt **0/45** data violation, **0/45** server-error round và tối đa một committed order/stock consumption mỗi cart. Exact 4xx/conflict response là quyết định API cần chốt ở design review G4, nhưng 5xx không được chấp nhận cho expected contention.
4. Guard hiệu năng đề xuất để review: median-of-runs W2 checkout p95 không quá **52.591 ms** và p99 không quá **76.844 ms** (tối đa +10% so với BEFORE); server error vẫn bằng 0. Ngưỡng +10% là budget đánh đổi dự kiến cho correctness, chưa phải SLO sản phẩm.
5. Existing sequential checkout/cancel/rollback behavior, ownership/RBAC và order snapshot phải giữ nguyên; full regression hiện có cùng targeted concurrency tests mới đều pass trên MySQL thật.

### 3. G4-B — Order-list data access efficiency

#### Quality attribute scenarios

| QAS | Source / stimulus / environment | Artifact & response mong đợi | Response measure |
|---|---|---|---|
| **QAS-B1: bounded order-list query count** | Customer/employee lấy order list ở page size 1, 5, 20, 50 trên dataset có items/order, `open-in-view=false`. | Trả đúng page, order, ownership/filter và item snapshot; số SELECT không tăng tuyến tính theo số order trả về. | Tổng captured SELECT cho một request là hằng số **≤4** ở cả bốn page size; không còn một item SELECT/order. |
| **QAS-B2: locked W1 response time** | Official W1 order list chạy 5 RPS/180 giây trên AFTER Intel-compatible session. | Response contract/checks đúng, không error; giảm DB round trips mà không làm latency xấu đi. | p95/p99 và error guard bên dưới; request rate giữ theo arrival-rate lock. |
| **QAS-B3: pagination/contract correctness** | Gọi list với role, filter, sort và page boundary hiện có. | Không duplicate/missing order do cách tải items; total/count, stable ordering và DTO snapshot không đổi. | Contract/regression tests pass; response cardinality và item set khớp fixture ở mọi page. |

#### BEFORE metrics

| Measure | BEFORE |
|---|---:|
| Captured SELECT với page size 1 / 5 / 20 / 50 | **4 / 8 / 23 / 53** (`N+3`) |
| Official W1 order-list requests | Median **901** (min 900; max 901) |
| Official W1 item SELECT digest count | Median **18,020** (min 18,000; max 18,020), tức **20 item SELECT/request** |
| Item SELECT digest DB time / rows examined | Median **4,415.712 ms / 72,080 rows** trong W1 window |
| Official W1 order-list request rate | Median **5.004 RPS** |
| Official W1 order-list p50 / p95 / p99 | **17.975 / 27.032 / 33.971 ms** |
| Official W1 errors / business rejections / server errors | **0 / 0 / 0** |

#### Acceptance criteria dự kiến

1. Targeted query-count test trên MySQL thật trả **≤4 captured SELECT/request** cho page size 1, 5, 20 và 50; query count không tăng theo số order trong page và không còn pattern một `order_items` SELECT/order.
2. Pagination, total/count, sort, filter, ownership/RBAC và Order DTO/item snapshot không đổi; không duplicate/missing row; existing regression cùng query-count tests mới đều pass.
3. Trên tối thiểu ba AFTER run hợp lệ, W1 order-list giữ **0 error, 0 business rejection, 0 server error** và arrival rate tương đương lock 5 RPS.
4. Guard bắt buộc: median-of-runs p95 không quá **28.384 ms** và p99 không quá **35.670 ms** (tối đa +5% so với BEFORE). Chỉ tuyên bố **response-time improvement** nếu p95 hoặc p99 giảm ít nhất 10% (p95 ≤ **24.329 ms** hoặc p99 ≤ **30.574 ms**); nếu không đạt, chỉ tuyên bố cải thiện data-access efficiency dựa trên query count/DB telemetry.
5. AFTER report phải ghi total order-list SELECT/request và DB query digest/time/rows; không dùng riêng endpoint latency để suy ra nguyên nhân.

### 4. Gate chung cho BEFORE/AFTER và giới hạn quyết định

- Dùng cùng configuration/workload/dataset locks của official BEFORE và chỉ nhận AFTER manifest tương thích nhóm Intel. So sánh median của tối thiểu ba run, kèm min/max/CV; không pool request samples và không chọn một run thuận lợi.
- Chỉ application/JAR SHA được phép thay đổi theo implementation đã review. Mọi thay đổi protocol, dataset, page size, load hoặc telemetry phải version hóa và đo lại BEFORE tương ứng.
- Mỗi cải tiến phải có targeted correctness/query-count evidence trước official load run; official W1/W2/W3 không thay thế test invariant chi tiết.
- Không coi Hikari saturation là criterion vì baseline không expose live Hikari gauges. Missing telemetry giữ `null`, không đổi thành 0.
- G3.1–G3.2 chốt **problem scope, QAS, BEFORE và acceptance proposal**; G3.3–G3.4 đưa ra lựa chọn kỹ thuật `PROPOSED`; G3.5 cụ thể hóa plan `PENDING_TEAM_APPROVAL`. Exact contract và trade-off threshold cuối cùng cần hai thành viên duyệt ở đầu G4 trước khi sửa application code.

### 5. Review decision cần chốt trước G4

1. Phê duyệt hai workstream G4-A/G4-B và owner; không thêm AF-05/AF-06/AF-07 vào cùng iteration.
2. Chốt expected loser semantics cho same-cart/same-food contention (ít nhất: không 5xx và invariant đúng).
3. Phê duyệt performance budgets dự kiến: +10% cho checkout p95/p99 và +5% guard cho order-list; đây là trade-off threshold, không phải SLO sản phẩm.
4. Chốt protocol chứng minh overlap cho C1 để tránh tuyên bố cải thiện dựa trên official scenario vốn đã 0/45 ở BEFORE.
5. Sau design review, cập nhật trạng thái/reviewer của ADR và giữ nguyên số BEFORE đã khóa; không hồi tố evidence để khớp lựa chọn.

## G3.3 — So sánh giải pháp và lựa chọn đề xuất

**Decision status chung: `PROPOSED` — cần hai thành viên review trước G4.**

Phần này chỉ đọc các path trực tiếp liên quan: `OrderService.create/list/cancel`, `FoodService.updateFood/reserveStock/releaseStock`, `CartService.getItemsForCheckout/clearCart`, ba repository tương ứng, các entity `Food/Cart/Order`, `OrderDto` và `GlobalErrors`. Những fact chi phối lựa chọn:

- `OrderService.create` đang là outer `@Transactional`; stock reserve, order save và cart clear cùng unit of work. `FoodService.updateFood` là transaction riêng cho admin update.
- Stock hiện dùng entity read–check–modify; `Food` không có `@Version`. Checkout nhiều món duyệt theo thứ tự cart item, chưa có thứ tự lock theo food ID.
- Same-cart checkout đọc cart rồi clear ở cuối transaction nhưng không khóa cart trước khi đọc.
- `OrderService.list` phân trang root `Order`, sau đó `OrderDto.fromEntity` duyệt collection `Order.items` lazy trong read-only transaction; đây là nguồn N+1.
- `GlobalErrors` đã có response `409 CONCURRENT_UPDATE` cho `PessimisticLockingFailureException`; optimistic conflict chưa có mapping tương ứng.

### 1. G4-A — So sánh chiến lược concurrency control

| Phương án | Correctness đối với C1/C4 | Phù hợp code hiện tại | Chi phí/rủi ro | Kết luận |
|---|---|---|---|---|
| **Pessimistic row locking** | Serialize read–check–write trên từng `Food`; cùng protocol cho admin assignment tạo outcome tương đương một thứ tự tuần tự. Có thể khóa cart trước khi đọc để chặn duplicate checkout. | Cao: giữ entity/JPA mapping và outer service transaction; không cần cột/schema mới. Existing `409 CONCURRENT_UPDATE` là nền tảng conflict response. | Lock wait/deadlock/starvation; phải giữ transaction ngắn và khóa theo thứ tự xác định. Contention có thể tăng p95/p99. | **SELECTED — PROPOSED**. Phù hợp nhất với correctness-first, một MySQL, transaction ngắn và quy mô một nhà hàng. |
| **Optimistic locking (`@Version`)** | Phát hiện lost update lúc flush; rollback toàn checkout nếu một version conflict. | Trung bình: cần cột version/migration, mapping và conflict handler; để chặn same-cart cần version/lock thêm trên Cart hoặc CartItem. | Conflict phát hiện muộn sau khi đã dựng Order; cần retry hoặc trả conflict. Auto-retry POST checkout/absolute PUT phức tạp khi chưa có idempotency contract; nhiều row làm tăng xác suất rollback. | **REJECTED cho G4-A**. Hợp với low-contention/edit-style workload hơn; tăng migration và retry surface nhưng vẫn không giải quyết C2 một mình. |
| **Atomic conditional SQL update** | Checkout có thể decrement bằng điều kiện `stock >= quantity`; admin assignment/increment cũng serialize ở DB statement level. | Trung bình: cần custom modifying queries và row-count interpretation, đi lệch entity read–modify–write hiện tại. | Vẫn cần giải pháp riêng cho same-cart; snapshot name/price/status phải đọc nhất quán; persistence context có thể stale; multi-food workflow và error mapping phức tạp hơn. | **REJECTED làm primary G4-A**. Là fallback nếu lock contention không đạt budget; không chọn hybrid ngay để tránh hai consistency model trong cùng aggregate. |

#### Lựa chọn đề xuất A: pessimistic write locks với outer service transaction

Phạm vi transaction To-Be:

1. **Checkout:** `OrderService.create` tiếp tục là transaction owner duy nhất. Transaction khóa cart của customer **trước khi đọc items**, lấy snapshot cart sau lock, thu toàn bộ food ID, khóa tất cả `Food` liên quan theo ID tăng dần, rồi mới validate availability/stock, dựng và lưu Order, cuối cùng clear cart. Mọi lỗi rollback stock, order/items và cart như một unit.
2. **Admin food update:** `FoodService.updateFood` giữ transaction riêng nhưng đọc `Food` bằng pessimistic write lock trước khi validate/apply request. Khi request gán stock tuyệt đối, nó dùng đúng row lock mà checkout dùng; update metadata/status cũng được serialize với checkout snapshot.
3. **Cancellation/release:** transaction `OrderService.cancel/updateStatus` khóa Order trước khi quyết định transition; nếu release stock, thu food ID và khóa theo ID tăng dần trước khi cộng trả. Đây là áp dụng cùng protocol cho writer hiện hữu, không mở rộng use case.
4. Các helper reserve/release tham gia transaction caller (`REQUIRED` hiện tại); không mở transaction độc lập, không commit từng món và không thực hiện network/external I/O trong vùng giữ lock.

Lock ordering bắt buộc:

- **Aggregate root trước:** checkout khóa `Cart`; cancel/status khóa `Order`. Một transaction không được khóa `Food` rồi quay lại lấy `Cart`/`Order`.
- **Food sau, theo primary key tăng dần:** gom distinct food IDs, sort ascending, acquire write locks theo đúng thứ tự; không dùng thứ tự `cart_items.id` hoặc iteration order làm lock order.
- Admin update chỉ khóa một `Food`. Nếu sau này có admin bulk update, cũng phải dùng thứ tự food ID tăng dần; bulk update không thuộc G4.
- Không giữ lock qua serialization HTTP. DTO cần thiết được dựng trong transaction; commit/rollback xảy ra trước khi controller gửi response.

Conflict handling đề xuất:

- Thiếu stock/food unavailable vẫn là business `409` với code hiện có; không biến thành 500 và không retry.
- Lock timeout/deadlock/acquisition failure được normalize thành **HTTP 409, code `CONCURRENT_UPDATE`**, response `no-store`. Không trả raw DB/Hibernate message.
- Không auto-retry checkout hoặc admin absolute assignment trong G4 vì API chưa có idempotency key và retry có thể che contention/đổi ordering semantics. Client có thể retry bằng request mới sau khi đọc lại trạng thái.
- Lock wait phải có timeout hữu hạn, nhỏ hơn HTTP/request timeout. Exact milliseconds cần chốt trong G4 review và được version hóa như application behavior trong treatment/JAR; không đổi benchmark runtime/pool configuration và mọi AFTER run phải dùng cùng giá trị.
- Same-cart loser phải thành một conflict nghiệp vụ ổn định (đề xuất `409 CONCURRENT_UPDATE` hoặc một code cart-specific được review), không phải stale-row 500; final state vẫn tối đa một order và một stock consumption.

Trade-offs và mitigation:

- **Ưu:** serializable business outcome cho các row được bảo vệ; giữ model/domain mapping và rollback hiện tại; không schema migration; dễ viết integration test final-state.
- **Nhược:** block thay vì fail-fast; hot food có thể tạo queue; deadlock vẫn có thể xảy ra nếu path khác vi phạm ordering; transaction checkout dài hơn atomic statement.
- **Mitigation:** khóa đủ row một lần ở đầu mutation phase, deterministic ordering, không gọi external service, bounded timeout, log conflict theo code/path không chứa PII, và dùng latency guard G3.2 để quyết định có cần xem lại atomic SQL hay không.
- **Rủi ro còn lại:** checkout đồng thời cart add/update không nằm trong scenario G4-A; thiết kế không được tuyên bố bao phủ mọi cart race. Nếu targeted test phát hiện cross-path này do vùng code đã chạm, phải ghi finding mới thay vì mở scope âm thầm.

### 2. G4-B — So sánh chiến lược loại N+1

| Phương án | Pagination & API contract | Query-count predictability | Chi phí/rủi ro | Kết luận |
|---|---|---|---|---|
| **Batch fetching** | Root page query không đổi; DTO/entity contract giữ nguyên. | Có thể giảm collection load thành các `IN` batch, nhưng số query phụ thuộc batch size, Hibernate session và provider behavior; nếu batch nhỏ hơn page thì vẫn tăng theo `ceil(N/batch)`. | Ít code; annotation/global config có thể ảnh hưởng path khác và che N+1 thay vì làm fetch plan explicit. | **REJECTED làm primary G4-B**. Giữ làm fallback nhỏ nếu two-step phát sinh issue không dự kiến. |
| **Two-step fetching** | Bước 1 phân trang đúng trên root Order IDs; bước 2 fetch đúng set Order + items, không paginate collection join. API DTO không đổi. | Xác định: page-ID query + one fetch query + count; không phụ thuộc số order trong page. | Thêm repository method và bước reorder/de-duplicate; `IN` list tối đa 100 IDs; phải xử lý empty page. | **SELECTED — PROPOSED**. Đáp ứng trực tiếp query-count criterion và pagination safety. |
| **DTO projection** | Có thể trả đúng contract, nhưng flat order-item rows làm duplicate parent; paginate trực tiếp trên join sai parent page. Muốn đúng vẫn cần page-ID step hoặc SQL/window logic. | Có thể rất ít query và tránh persistence context. | Projection phải lặp gần toàn bộ `OrderDto`, group rows, tính total, giữ enum/time/null semantics; coupling repository → API DTO và contract drift tăng. | **REJECTED cho G4-B**. Lợi ích không đủ bù complexity ở DTO lớn; two-step vẫn cần nếu muốn pagination đúng. |

#### Lựa chọn đề xuất B: two-step page IDs rồi fetch Orders với items

Fetch plan To-Be trong một `@Transactional(readOnly = true)` tại `OrderService.list`:

1. Giữ nguyên validation, role-to-owner scoping, status/type filter và sort `createdAt DESC, id DESC`.
2. Query **page of Order IDs** với chính filter/sort/offset/limit hiện tại; đây là nơi duy nhất áp dụng pagination.
3. Nếu ID page không rỗng, chạy một query `Order + items` cho `id in (:pageIds)` không có pagination. Fetch phải bao gồm order không có item, de-duplicate root Order và giữ item order theo `OrderItem.id` như contract hiện tại.
4. Vì `IN` query không bảo đảm thứ tự root, reorder kết quả theo thứ tự ID của bước 2 trước khi map `OrderDto`. Missing/duplicate IDs là invariant failure, không được bỏ qua im lặng.
5. Chạy count query với cùng filter để tạo `totalElements`; map DTO trong transaction rồi trả `OrderPage` như hiện tại. Empty page bỏ qua fetch query nhưng vẫn trả count/page metadata đúng.

Query budget dự kiến là ba application SELECT cho non-empty page: page IDs, Orders+items và count. Một environment/driver SELECT đã thấy trong diagnostic có thể làm captured total thành bốn, nên acceptance G3.2 giữ `≤4` thay vì ép đúng ba. Detail endpoint `GET /api/orders/{id}` không đổi.

Trade-offs và mitigation:

- **Ưu:** query count hằng theo page size; pagination parent chính xác; giữ nguyên `OrderDto`, security scope và entity mapping; fetch plan explicit ở use case gây lỗi.
- **Nhược:** hai lượt đọc data page trước khi count; fetch join tạo row multiplication theo số item; cần reorder/de-duplicate trong memory.
- **Mitigation:** cùng read-only transaction/MySQL snapshot, page size đã chặn `≤100`, ID list bounded, deterministic reorder map, fixture có zero/one/many items và page-boundary tests.
- **Rủi ro còn lại:** số item/order cực lớn có thể làm result set phình dù query count thấp; G2 không có evidence để đưa projection/streaming vào scope. DB time/rows và heap/RSS AFTER phải được quan sát, không chỉ count query.

### 3. Decision summary cho review

| Workstream | Proposed choice | Why now | Reconsider trigger |
|---|---|---|---|
| G4-A | Pessimistic write lock trên Cart/Order aggregate root và Food rows, outer service transaction, deterministic lock order, 409 conflict | Correctness defect đã lặp; hợp entity read–modify–write, không migration, giải quyết C1/C4 và guard C2 trong một protocol | Không đạt latency budget; lock timeout/deadlock cao; targeted tests cho thấy lock plan không bao phủ invariant |
| G4-B | Two-step page Order IDs → fetch Orders+items → reorder, count trong cùng read-only transaction | Query count xác định, pagination safe, giữ API contract | Result-set/heap regression; query count >4; provider không de-duplicate đúng hoặc contract/page tests fail |

## G3.4 — Kiến trúc To-Be và Architecture Decision Records

**Architecture status: `PROPOSED` — chưa triển khai.** Topology vẫn là layered monolith + MySQL; không thêm service, cache, broker hay datastore. Thay đổi chỉ nằm trong transaction/fetch policy của hai use case đã chọn.

### 1. To-Be component view

```mermaid
flowchart LR
    Client --> Controller
    Controller --> OrderService
    Controller --> FoodService

    subgraph App[Spring Boot layered monolith]
        Controller[REST Controllers]
        OrderService[OrderService\ntransaction owner]
        FoodService[FoodService\nadmin transaction owner]
        LockPolicy[Repository lock methods\nCart/Order first; Food IDs ascending]
        PagePlan[Order page fetch plan\npage IDs -> Orders + items -> reorder]
        ErrorMap[GlobalErrors\ncontention -> 409]
    end

    OrderService --> LockPolicy
    FoodService --> LockPolicy
    OrderService --> PagePlan
    LockPolicy --> MySQL[(MySQL/InnoDB)]
    PagePlan --> MySQL
    OrderService -. exception .-> ErrorMap
    FoodService -. exception .-> ErrorMap
    ErrorMap --> Controller
```

### 2. To-Be checkout/admin concurrency sequence

```mermaid
sequenceDiagram
    participant C as Controller
    participant S as Service transaction
    participant R as Repositories
    participant DB as MySQL/InnoDB

    C->>S: checkout(customer, request)
    S->>R: lock Cart before reading items
    R->>DB: SELECT cart ... FOR UPDATE
    S->>R: lock distinct Food IDs ascending
    R->>DB: SELECT foods ... ORDER BY id FOR UPDATE
    S->>S: validate stock/status and build snapshots
    S->>R: save Order + items; clear Cart
    R->>DB: INSERT/DELETE/UPDATE in same transaction
    DB-->>S: commit
    S-->>C: 201 OrderDto

    Note over C,DB: Admin update uses its own short transaction and the same Food row lock.
    Note over C,DB: Timeout/deadlock rolls back and maps to 409 CONCURRENT_UPDATE; no automatic retry.
```

### 3. To-Be order-list sequence

```mermaid
sequenceDiagram
    participant C as OrderController
    participant S as OrderService read-only transaction
    participant R as OrderRepository
    participant DB as MySQL

    C->>S: list(user, role, filters, page, size)
    S->>R: findPageIds(scoped filters, sort, offset, limit)
    R->>DB: SELECT order IDs
    DB-->>S: ordered pageIds
    alt pageIds not empty
        S->>R: fetchOrdersWithItems(pageIds)
        R->>DB: SELECT Orders LEFT JOIN items
        DB-->>S: de-duplicated Orders + initialized items
        S->>S: reorder by pageIds; map OrderDto
    end
    S->>R: countMatching(scoped filters)
    R->>DB: SELECT COUNT
    S-->>C: OrderPage (unchanged contract)
```

### 4. ADR-001 — Serialize inventory mutations with pessimistic row locks

- **Status:** `PROPOSED`
- **Date:** 2026-11-22
- **Owners:** G4-A / Thành viên A, review bởi Thành viên B
- **Related evidence:** AF-01, AF-02, AF-04; QAS-A1–A4

**Context.** Checkout và admin stock update đang dùng concurrent entity read–modify–write mà không lock/version. G2.3 tái hiện oversell 6/15 và lost admin update 12/15; official W3 lặp lost admin update 37/45. Same-cart giữ data đúng nhưng có stale-row 500. Hệ thống là một Spring Boot instance + MySQL, transaction ngắn và chưa có idempotency/retry contract.

**Decision proposed.** Dùng pessimistic write row locks trong các transaction service hiện hữu. Checkout khóa Cart trước khi đọc, sau đó khóa toàn bộ Food theo ID tăng dần; admin update khóa Food trước khi sửa; cancel/status khóa Order rồi Food theo cùng thứ tự. Outer service method sở hữu atomic boundary. Expected contention không auto-retry; timeout/deadlock rollback và trả `409 CONCURRENT_UPDATE`. Không thêm `@Version`, không dùng atomic SQL làm consistency model thứ hai trong G4-A.

**Consequences.** Business outcome của các row được bảo vệ trở nên serializable và không cần schema migration; same-cart có một serialization point. Đổi lại, request có thể block, hot food có thể queue và deadlock vẫn cần handling. Lock duration/order/config trở thành phần của architecture contract và AFTER manifest.

**Alternatives rejected.** Optimistic locking đòi migration, late-conflict/retry handling và thêm guard Cart; atomic SQL hiệu quả nhưng tạo custom persistence path, snapshot/stale-context complexity và vẫn cần Cart strategy. Cả hai được giữ làm reconsideration options, không trộn vào lần triển khai đầu.

**Approval/validation gate.** ADR chỉ chuyển `ACCEPTED` khi hai thành viên duyệt lock graph, conflict code và timeout policy. Implementation chỉ đạt khi acceptance G3.2 cho C1/C4/C2, regression và checkout latency đều pass; nếu không, ADR quay lại `PROPOSED` để xem atomic SQL hoặc optimistic alternative.

### 5. ADR-002 — Use a two-step fetch plan for paginated order lists

- **Status:** `PROPOSED`
- **Date:** 2026-11-22
- **Owners:** G4-B / Thành viên B, review bởi Thành viên A
- **Related evidence:** AF-03; QAS-B1–B3

**Context.** Root Order đang được phân trang đúng nhưng DTO mapping chạm lazy `items`, tạo `N+3` SELECT: 4/8/23/53 query cho page 1/5/20/50 và 18,020 item SELECT trong median official W1 run. API phải giữ page metadata, filter/sort/ownership và full item snapshot.

**Decision proposed.** Trong cùng read-only transaction, query ordered page of Order IDs, fetch Orders cùng items bằng một non-paginated query giới hạn bởi ID page, de-duplicate/reorder theo page IDs, rồi map DTO; count giữ query riêng với cùng filter. Không đổi endpoint/response DTO và không áp dụng fetch join trực tiếp lên paginated collection query.

**Consequences.** Non-empty page có query count hằng và pagination root an toàn; API contract/entity model giữ nguyên. Đổi lại cần repository methods, deterministic reorder và handling empty/duplicate/missing IDs; result set vẫn nhân theo item count và cần resource telemetry.

**Alternatives rejected.** Batch fetching ít code nhưng query bound phụ thuộc batch/provider/session và có thể tác động path khác. DTO projection tránh entity loading nhưng flat rows làm pagination/grouping phức tạp, lặp API mapping và tăng repository-to-contract coupling; để phân trang đúng thường vẫn cần ID step.

**Approval/validation gate.** ADR chỉ chuyển `ACCEPTED` khi hai thành viên duyệt query shape, ordering và empty-page behavior. Implementation chỉ đạt khi captured SELECT `≤4` ở mọi page size, contract/page regression pass và W1 latency/resource guards G3.2 đạt; nếu không, ADR quay lại `PROPOSED` để đánh giá batch fetching hoặc projection.

### 6. Review checklist trước G4

- [ ] Hai thành viên xác nhận ADR-001 lock graph: `Cart/Order → Food IDs ascending`; không có path trong scope khóa ngược chiều.
- [ ] Chốt lock timeout và `409` error code/message; xác nhận không auto-retry khi chưa có idempotency contract.
- [ ] Xác nhận cancellation dùng cùng Food lock protocol nhưng cart add/update concurrency vẫn ngoài scope G4-A.
- [ ] Hai thành viên xác nhận ADR-002 query shape, root de-duplication, root/item ordering và empty-page/count semantics.
- [ ] Xác nhận API/OpenAPI success payload không đổi; nếu conflict response documentation thay đổi thì cập nhật contract trong G4.
- [ ] Chỉ sau review mới đổi ADR status sang `ACCEPTED` và bắt đầu sửa application code.

## G3.5 — Implementation planning và coordination gate

**Plan status: `PENDING_TEAM_APPROVAL`.** G3.5 cụ thể hóa ADR-001/ADR-002 thành kế hoạch G4 nhưng không đổi trạng thái hai ADR, không cấp quyền sửa application code và không thay số BEFORE/acceptance G3.2.

Hai plan độc lập:

- [G4-A — Pessimistic Locking](implementation/G4-A_CONCURRENCY.md)
- [G4-B — Two-Step Fetching](implementation/G4-B_DATA_ACCESS.md)

### 1. Các chi tiết implementation đã chốt để review

| Concern | G4-A / G4-B decision |
|---|---|
| Lock coverage | Checkout: `Cart → Food.id ASC`; admin update/delete: `Food`; cancel: `Order → Food.id ASC`; confirm/status: `Order`. Cart add/update/remove và first-cart race ngoài scope. |
| Isolation | Giữ `Isolation.DEFAULT` / MySQL `REPEATABLE READ`; không dùng `SERIALIZABLE`. Explicit row locks bảo vệ write paths; cùng read-only transaction snapshot bảo vệ page IDs/fetch/count. |
| Lock timeout | Pessimistic **no-wait**, `jakarta.persistence.lock.timeout=0` trên locking queries; phải có MySQL runtime test chứng minh hint có hiệu lực, không fallback 50 giây. |
| Conflict semantics | Lock conflict/deadlock → `409 CONCURRENT_UPDATE`, no-store, không auto-retry. Insufficient stock và unavailable giữ business code hiện tại. Request sau commit thấy cart rỗng vẫn là existing `EMPTY_CART`. |
| Pagination consistency | Chỉ page-ID query dùng offset/limit; fetch Orders+items không paginate, dùng left fetch/de-dup; reorder theo page IDs; count cùng scoped filter và cùng read-only transaction. |
| Query budget | Non-empty page: 3 application SELECT; captured total `≤4`. Empty page bỏ fetch query. |

Những chi tiết này là **proposed implementation contract**. Nếu team không duyệt no-wait, lock coverage hoặc two-step query shape, phải sửa ADR/plan trước khi code; không giải quyết khác biệt trong lúc merge.

### 2. Method ownership trên file dùng chung

| File | Nguyễn Văn Huy Hoàng — G4-A | Bùi Công Huy — G4-B |
|---|---|---|
| `OrderService.java` | `create`, `cancel`, `confirm`, `updateStatus`, `moveTo` và helper mutation | `list` và helper reorder chỉ phục vụ list |
| `OrderRepository.java` | locking lookup cho Order mutation | FILTER, page IDs, fetch Orders+items, count |
| `OrderServiceTest.java` | checkout/cancel/status tests | list tests; sửa sau khi rebase A |
| `OrderIntegrationTest.java` | Không mở rộng nếu dùng concurrency test file mới | Không mở rộng nếu dùng query-count test file mới |

Nguyễn Văn Huy Hoàng sở hữu riêng Cart/Food repository/service, lock error mapping và concurrency tests. Bùi Công Huy sở hữu riêng query-count integration test. Hai người không format/rename toàn bộ shared file và không sửa method của owner kia khi resolve conflict.

### 3. Merge order

1. Ngày 23–24/11: team review G3.5/hai plan và publish sau phê duyệt; ADR tương ứng phải chuyển `ACCEPTED` trước implementation.
2. Từ 25/11: hai workstream code/test **song song** trên method ownership riêng; B không chờ A để phát triển. Huy có workload G4-B linh hoạt/giảm tải đến 30/11 do bài tập lớn môn khác; Hoàng có thể triển khai G4-A độc lập.
3. Ngày 29/11: G4-A hoàn tất targeted gate, được Bùi Công Huy review khi khả dụng và **merge trước**.
4. Ngày 01/12: G4-B rebase lên A, preserve lock methods/imports/tests, rerun targeted A+B, được Nguyễn Văn Huy Hoàng review rồi merge.
5. Ngày 02/12: hai thành viên chạy G5 combined verification; Code Freeze chỉ sau khi mọi gate đạt. AFTER prep 03/12; benchmark 04–06/12; buffer/evaluation 07/12.
6. Không squash/rewrite evidence hoặc đổi BEFORE locks trong conflict resolution. Mọi protocol/config change phải quay lại architecture review.

### 4. Approval gate

- [ ] Team duyệt [`G4-A_CONCURRENCY.md`](implementation/G4-A_CONCURRENCY.md), gồm no-wait, lock graph, 409 và out-of-scope.
- [ ] Team duyệt [`G4-B_DATA_ACCESS.md`](implementation/G4-B_DATA_ACCESS.md), gồm query shapes, snapshot, reorder và query budget.
- [ ] Hai ADR chuyển từ `PROPOSED` sang `ACCEPTED` với reviewer/date được ghi nhận.
- [ ] Owner xác nhận method ownership và merge order.
- [ ] Chỉ sau bốn điều kiện trên mới bắt đầu G4; tới thời điểm lập G3.5, cả hai plan vẫn chờ phê duyệt.
