## 8. Testing Assessment

Phần này chỉ đánh giá tĩnh test source và artifact hiện có. Không test/build/container/benchmark/scanner nào được chạy; do đó “có test source” không đồng nghĩa test đang pass hoặc behavior runtime đã được xác minh.

### 8.1. Test Suite Overview & Inventory

#### Số liệu chính xác

Phương pháp đếm: inventory toàn bộ `*.java` dưới `src/test/java`; test method là method có annotation JUnit 5 `@Test` trong source. Không cộng helper method, nested fixture controller, Python check hay k6 check vào số JUnit method.

| Chỉ số | Kết quả | Bằng chứng |
|---|---:|---|
| Java test-source files | **14** | `src/test/java` inventory. |
| JUnit test classes/files | **12** | 12 file có ít nhất một `@Test`. |
| JUnit test methods | **90** | Tổng annotation `@Test`; không có `@ParameterizedTest`/`@RepeatedTest`. |
| Support files không phải test class | **2** | `TestAuthKeys.java` tạo key tạm; `dev/LocalTokenCli.java` là CLI tạo token local. |
| Nested fixture class | **1**, không tính là test class | `AuthIntegrationTest.OtherModuleController` (`AuthIntegrationTest.java:123-130`). |
| Disabled/conditional tests | **0 tìm thấy** | Không có `@Disabled`, `@Enabled*`, `@Disabled*` hoặc assumption trong `src/test`. |
| Test reports/coverage artifacts | **0 tìm thấy** | `target/` tồn tại nhưng không có Surefire/Failsafe/JaCoCo/coverage report; repository cũng không có artifact tương ứng. |

| Phân loại chính, không cộng chồng | Class và số method | Tổng |
|---|---|---:|
| Unit/service/infrastructure | `OrderServiceTest` 10; `FoodServiceTest` 11; 6 service methods trong `AuthWebAndServiceTest`; `AdaptersTest` 2; `RateLimiterTest` 2; `LoginIpFilterTest` 1 | **32** |
| Web/controller slice | 2 web methods trong `AuthWebAndServiceTest`; `FoodCartSecurityTest` 9; `OrderWebTest` 10 | **21** |
| Spring Boot integration | `AuthIntegrationTest` 8; `OrderIntegrationTest` 14 | **22** |
| Database design/JDBC | `DatabaseDesignTests` 10 | **10** |
| Architecture | `ArchitectureTest` 5 | **5** |
| **Tổng** |  | **90** |

Security là concern xuyên suốt nhiều nhóm nên không được cộng thành một tổng riêng. Performance/load test không nằm trong JUnit: notebook sinh k6 script khi chạy; `scripts/test-endpoints.py` là black-box runner độc lập, không phải pytest/JUnit test.

#### Công cụ thực sự được dùng

| Công cụ | Mức sử dụng đã xác minh |
|---|---|
| JUnit Jupiter | Toàn bộ 90 test methods; do `spring-boot-starter-test` quản lý (`pom.xml:74-78`). |
| Mockito | Mock service/repository, `@MockitoBean` ở web slices và `@MockitoSpyBean` cho rollback fault injection (`OrderIntegrationTest.java:20,59,104-116`). |
| MockMvc | Ba web-slice classes và `AuthIntegrationTest`; kiểm tra status/header/JSON/error/RBAC. |
| Testcontainers | Ba class, tổng **32 methods**, dùng image `mysql:8.4`: `AuthIntegrationTest`, `OrderIntegrationTest`, `DatabaseDesignTests`. Không có H2. Exact Testcontainers library version được parent quản lý nhưng chưa resolve bằng dependency tree. |
| ArchUnit 1.4.1 | Năm rule trong `ArchitectureTest`; version explicit (`pom.xml:93-97`). |
| k6 | Workload được notebook sinh và chạy trên Kaggle; không có file k6 độc lập được commit (`kaggle/script/byteme_kaggle_benchmark.ipynb`, cell 3). |
| Python black-box runner | `scripts/test-endpoints.py` gọi toàn bộ API, dùng SQL cho fixture/verification và kiểm tra cleanup; chạy thủ công, ngoài Maven (`README.md:194-197`; script `:1-7,349-392`). |

Năm class dùng profile `test`: ba web slices và hai Spring integration classes. `application-test.yml` chỉ tắt SQL logging; DB integration được cấp URL/credential bằng `@DynamicPropertySource` (`src/main/resources/application-test.yml:1-4`; `AuthIntegrationTest.java:31-37`; `OrderIntegrationTest.java:46-54`). Không có `disabledWithoutDocker=true`; 32 Testcontainers methods cần Docker daemon và khả năng lấy image MySQL.

### 8.2. Unit Testing

#### Coverage nghiệp vụ nổi bật

- **CONFIRMED:** `OrderServiceTest` kiểm tra server-side price/snapshot, cart-clear ordering, empty/unavailable food, order-type validation, ownership, list scoping, confirmation/cancellation và toàn bộ ma trận transition theo `OrderType × current status × next status` (`OrderServiceTest.java:71-260`). Fixed `Clock` làm timestamp deterministic (`:27-40`).
- **CONFIRMED:** `FoodServiceTest` kiểm tra create/update/delete-soft, category/name conflicts, wildcard escaping, active-food condition, reserve/release stock và boundary bằng mock repository (`FoodServiceTest.java:42-148`).
- **CONFIRMED:** sáu service methods trong `AuthWebAndServiceTest` kiểm tra register/login success, password mismatch, duplicate, invalid credentials và locked account (`AuthWebAndServiceTest.java:61-123`). Tuy nhiên class-level `@WebMvcTest` vẫn khởi tạo web context cho các method logic này; chúng cô lập dependency bằng Mockito nhưng không phải plain-unit runner (`:30-58`).
- **CONFIRMED:** password hashing/JWT expiry adapter và single-node limiter/filter có unit source (`AdaptersTest.java:20-44`; `RateLimiterTest.java:13-28`; `LoginIpFilterTest.java:14-31`). Rate limiter dùng mutable clock và futures timeout thay vì sleep.

#### Gaps và giới hạn assertion

- Không có `CartServiceTest` độc lập; CartService được mock trong `OrderServiceTest` và được chạy thật chủ yếu trong `OrderIntegrationTest`. Điều này cho behavior DB tốt nhưng làm feedback logic cart phụ thuộc Docker/MySQL.
- Không tìm thấy unit negative tests cho application `AdapterConfiguration` validator về wrong issuer/audience, missing/invalid role, future `iat`, `nbf` hoặc tampered signature. `AdaptersTest` dùng decoder/timestamp validator tự dựng, không phải toàn bộ application decoder chain (`AdaptersTest.java:28-44`).
- `MySqlAccountRepository` exception translation được chạm qua integration duplicate/concurrent insert, nhưng không có test cô lập từng vendor code/constraint-message branch; impact portability vẫn thuộc SC-06.
- Manual loops bao phủ nhiều boundary/transition trong một method, nhưng một assertion fail sẽ dừng phần còn lại và report không chỉ rõ từng case như parameterized test. Đây là test diagnostics concern, không phải functional defect.

### 8.3. Web & API Testing

Ba `@WebMvcTest` classes có **21 methods** và dùng security filter chain thật với mocked `JwtDecoder`/business service (`AuthWebAndServiceTest.java:30-40`; `FoodCartSecurityTest.java:29-37`; `OrderWebTest.java:30-45`). Chúng kiểm tra:

- status, selected response JSON và headers (`Location`, `Cache-Control`);
- bean/deserialization validation, malformed body/ID/enum, numeric enum rejection và shared error body;
- anonymous/wrong-role rejection trước service;
- JWT subject làm owner thay vì spoofed header;
- mapping đúng tới create/list/get/cancel/confirm/update-status service methods;
- mapping lock exceptions thành retryable 409 response source (`OrderWebTest.java:155-165`).

**Static endpoint coverage:** cả 18 route patterns đều xuất hiện trong JUnit source ít nhất ở một request. Tuy nhiên successful HTTP response contract còn mỏng ở UC04–UC07 và UC10–UC12: JUnit chủ yếu kiểm tra negative/RBAC/validation hoặc service-level success; happy-path HTTP cho các UC này nằm trong `scripts/test-endpoints.py`, là runner thủ công ngoài Maven. Chi tiết ở Mục 8.9.

Không có automated test đọc/validate `static/openapi.yaml` hoặc diff OpenAPI với controller/DTO/security. Vì vậy **API-06** vẫn chưa được bảo vệ. Retry/idempotency semantics được chạm ở service transition (cancel lần hai bị reject; transition lặp không hợp lệ), nhưng không có một test suite HTTP replay/network-retry tổng quát; **API-02** vẫn cần quyết định contract.

### 8.4. Integration & Database Testing

| Class | Runtime thật | Setup/isolation | Nội dung chính |
|---|---|---|---|
| `AuthIntegrationTest` (8) | Full Spring Boot + MockMvc + MySQL `8.4` | Schema init container; seed chỉ một lần qua `static boolean seeded`; dữ liệu tạo trong test không cleanup. | Register/login/JWT thật, DB hash/status/role, malformed media/JSON, uniqueness, hai insert đồng thời, email quota, invalid bearer và shared error behavior (`:31-143`). |
| `OrderIntegrationTest` (14) | Full Spring Boot services/JPA + MySQL `8.4` | Trước mỗi test xóa 7 bảng theo thứ tự rồi nạp lại seed (`:46-66`). | Checkout/cancel/Cart CRUD, snapshot/UTC, paging/state flow, transaction rollback/fault injection và final DB state (`:72-279`). |
| `DatabaseDesignTests` (10) | JDBC trực tiếp + MySQL `8.4` | Schema init, seed ở `@BeforeAll`; mutation tests dùng rollback helper, schema/seed lifecycle kiểm tra riêng (`:27-48,179-227`). | Counts, bcrypt seed, unique/FK/enums, payment/order type, snapshot totals, schema rerun và non-idempotent seed. |

**CONFIRMED source evidence:** transaction rollback tuần tự có assertion trên orders/items/stock/cart; DB constraints và repository adapter chạy trên MySQL thật, không dùng in-memory substitute (`OrderIntegrationTest.java:104-129,164-178,269-278`; `DatabaseDesignTests.java:79-193`). Đây là nền tảng tốt cho DB-11, nhưng pass result vẫn **PENDING**.

**POTENTIAL ISSUE — isolation:** `AuthIntegrationTest` giữ DB và limiter/application state xuyên suốt class, seed-once bằng static flag và không cleanup rows; hiện các fixture có tên riêng nên không thấy dependency trực tiếp, nhưng retry cùng JVM, parallel method execution hoặc context lifecycle khác có thể làm kết quả phụ thuộc state (`AuthIntegrationTest.java:40-43,53-117`). `OrderIntegrationTest` reset tốt khi chạy tuần tự nhưng cũng không an toàn nếu các method dùng chung container bị bật parallel. Repository không khai báo parallel policy.

Các assertion thời gian dùng cửa sổ theo wall clock dưới 2 phút/60 giây (`OrderIntegrationTest.java:92-102,246-259`); có thể nhạy với host clock/load. Exact startup time/cost của ba container và behavior khi Docker unavailable là **PENDING** vì không chạy.

### 8.5. Architecture Testing

`ArchitectureTest` import production classes và định nghĩa năm ArchUnit rules (`ArchitectureTest.java:12-54`):

| Rule | Được bảo vệ tĩnh | Giới hạn |
|---|---|---|
| `businessLayerDoesNotUseWebFrameworkOrDatabaseLibraries` | Service không phụ thuộc Spring Web/HTTP/Data/JDBC/ORM, Servlet, JPA, Hibernate hoặc SQL. | Không cấm service phụ thuộc DTO/entity/repository abstraction. |
| `businessLayerDoesNotCallJpaSpecificRepositoryMethods` | Service không gọi method khai báo bởi `JpaRepository`. | Không kiểm tra mọi ORM concept đi qua custom repository. |
| `controllersGoThroughServices` | Controller không phụ thuộc repository. | Tên rule rộng hơn assertion: không yêu cầu mỗi controller chỉ phụ thuộc service, và không cấm dependency sang entity/platform/common. |
| `repositoriesDoNotDependOnControllers` | Repository không phụ thuộc controller. | Không cấm repository phụ thuộc service. |
| `servicesDoNotDependOnControllers` | Service không phụ thuộc controller. | Không kiểm tra package cycle tổng quát. |

**CONFIRMED gap:** không có `slices(...).should().beFreeOfCycles()` hoặc rule `repository !→ service`; vì vậy dependency cycle `service ↔ repository` tại **SC-01** không được rule hiện tại phát hiện. Cũng không có automated rules cho DTO/entity direction, package naming, `common/shared/platform` boundaries, controller/security matcher/OpenAPI consistency hoặc transaction annotation placement. Không bổ sung rule trong assessment này.

### 8.6. Security Testing

| Security area | Test source hiện có | Gaps còn lại / liên hệ finding |
|---|---|---|
| Authentication/password | BCrypt round-trip/UTF-8 limit; register/login thật; wrong password, inactive/locked/unknown account; strict Auth JSON (`AdaptersTest.java:20-26`; `AuthIntegrationTest.java:53-94,131-143`). | Không test breached-password/strength/work-factor policy; **SEC2-09** chỉ được chạm một phần. |
| JWT | Issued RS256 token có subject/role/expiry; expired token bị decoder từ chối; malformed bearer qua application trả 401 (`AdaptersTest.java:28-44`; `AuthIntegrationTest.java:118-120`). | Không tìm thấy tampered signature, wrong issuer/audience, missing/invalid role, future `iat`, `nbf`, key rotation/revocation hoặc stale token sau lock/role change. **SEC2-01/02** chưa được xác minh. |
| RBAC | Food/Cart/Order web tests kiểm tra anonymous và wrong role trên toàn bộ nhóm route; Auth public chấp nhận bearer hỏng (`FoodCartSecurityTest.java:51-96`; `OrderWebTest.java:57-70`; `AuthIntegrationTest.java:110-120`). | Không có generated 18-endpoint × role matrix hoặc guard tự phát hiện route mới; fallback **SEC2-03** vẫn là maintenance risk. |
| Ownership/BOLA | JWT owner chống header spoof; order service kiểm tra owner trước mutation; black-box script kiểm tra cross-user Cart/Order (`FoodCartSecurityTest.java:77-82`; `OrderServiceTest.java:178-195`; `scripts/test-endpoints.py:251-258,278-283`). | Runtime JUnit owner test cho Cart write đi qua service/integration, không phải HTTP success path đầy đủ cho UC10–UC12. |
| Rate limiting | Fixed window/bucket reset; concurrent requests không vượt quota; filter không trust forwarded IP; email quota integration (`RateLimiterTest.java:13-28`; `LoginIpFilterTest.java:14-31`; `AuthIntegrationTest.java:110-117`). | Không test multi-instance/reset-on-restart/trusted-proxy topology; **SEC2-04** còn mở. Register abuse/rate limit của **SEC2-05** không có. |
| Error disclosure/headers | Shared error code/path, no-store và synthetic 500 code có test source (`FoodCartSecurityTest.java:152-162`; `OrderWebTest.java:130-165`; `AuthIntegrationTest.java:131-143`). | Không có assertion toàn diện rằng stack trace/internal message/PII/token không leak; CSP/HSTS/TLS/CVE/audit log findings **SEC2-06/10/11** không được test. |
| Secret/sample environment | Test tự tạo RSA key tạm, xóa bằng shutdown hook (`TestAuthKeys.java:20-40`). | Không test deployment key ACL/mount, production seed exclusion hoặc dev-secret override; **SEC2-07/DEP-06/07/08** thuộc deployment verification. |

Kết luận tĩnh: authentication/RBAC/ownership/single-node limiter có coverage đáng kể, nhưng không có bằng chứng penetration/scanner mới và không có negative JWT claim matrix. Không suy ra security đạt chỉ từ test source.

### 8.7. Concurrency Testing

Đối chiếu đúng năm kịch bản DB-05:

| Kịch bản | Test hiện có | Transaction/final-state assertion | Kết luận tĩnh |
|---|---|---|---|
| 1. Hai checkout đồng thời cùng food | Không tìm thấy. | Không có. | **MISSING TEST** — oversell/lost update chưa được tái hiện hoặc bác bỏ. |
| 2. Hai checkout đồng thời cùng cart | Không tìm thấy. | Không có. | **MISSING TEST** — duplicate order/cart clear race chưa xác minh. |
| 3. Hai cancel đồng thời cùng order | Không tìm thấy. | Không có. | **MISSING TEST** — double stock release chưa xác minh. |
| 4. Admin update stock đồng thời checkout | Không tìm thấy. | Không có. | **MISSING TEST** — overwrite/serialization semantics chưa xác minh. |
| 5. Hai request cùng tạo cart lần đầu | Không tìm thấy. | Không có. | **MISSING TEST** — unique conflict/retry/final cart state chưa xác minh. |

`AuthIntegrationTest.databaseUniqueProtectsConcurrentInserts` dùng `CountDownLatch`, hai thread và MySQL thật, rồi assert đúng một account (`AuthIntegrationTest.java:100-108`); `RateLimiterTest` cũng có concurrent unit test (`RateLimiterTest.java:21-28`). Hai test này chứng minh team có pattern concurrency test nhưng không bao phủ năm scenario trên. Black-box script còn ghi rõ concurrency checks được chuyển sang Phase 2 (`scripts/test-endpoints.py:341-342`). Không có cơ sở kết luận DB-05 là defect runtime trước khi các test này được thực thi/thiết kế.

### 8.8. Performance & Load Testing

| Aspect | Hiện trạng đã xác minh |
|---|---|
| Workload | k6 chạy 3 phút với stages `50 → 200 → 500 → 0`, think time 0,1 giây; mỗi iteration gọi menu, food search, authenticated cart read và token generation (notebook cell 3:1-63). |
| Nghiệp vụ đại diện | Có **food search**; không có checkout, add/update cart, order list/detail, confirm/status/cancel hoặc concurrent write. Login/BCrypt ở mọi iteration có thể chi phối mix, nhưng chưa có resource profile để kết luận bottleneck. |
| Thresholds | p95 < 500 ms, p99 < 1.200 ms, HTTP failure < 1% (notebook cell 3:12-15). |
| Metrics | k6/CSV và notebook có request latency p50/p90/p95/p99/max, RPS/check/error; không thu CPU/RAM/GC, JVM threads, Hikari, MySQL/query/lock/resource metrics (notebook cells 3–5). |
| Repetition | Một staged run; không có warm-up riêng, repeated-run/statistical variance procedure hoặc clean DB reset. |
| Provenance | Baseline trỏ commit không resolve; thiếu raw CSV, `server.log`, exact tool versions/checksums; liên hệ **DEP-09/10/11/12** và Phần 0 (`kaggle/results/phase1-baseline/README.md:3-12,39-44`). |

K6 workload chỉ là performance test source, không phải bằng chứng benchmark hiện tại pass. Nó phù hợp đo read/auth saturation của dataset seed nhỏ, chưa đại diện luồng checkout/consistency hoặc employee order queue; protocol chính thức vẫn là quyết định sau assessment.

### 8.9. Coverage & Traceability Matrix

#### UC01–UC18 và 18 endpoint patterns

Quy ước: **COVERED SOURCE** = có happy path và assertion nghiệp vụ/HTTP đáng kể; **PARTIAL ASSERTION** = route có test nhưng JUnit happy-path HTTP hoặc response contract chưa đầy đủ. Runtime của tất cả dòng vẫn **PENDING** cho tới khi chạy.

| UC / endpoint | Test source chính | Static coverage |
|---|---|---|
| UC01 `POST /api/auth/register` | `AuthWebAndServiceTest.webRegisterEndpoint`; `AuthIntegrationTest.registerThenLoginAgainstRealMysql`, validation/duplicate tests | **COVERED SOURCE** — 201/body, normalization/hash/role/status, 400/409. |
| UC02 `POST /api/auth/token` | `AuthWebAndServiceTest.webLoginEndpoint`; `AuthIntegrationTest` login/status/quota/JWT methods | **COVERED SOURCE** — 200/body/JWT, 401/403/429, no-store. |
| UC03 `GET /api/foods` | `FoodCartSecurityTest.publicMenuWorksWithoutTokenButFoodWritesRequireAuthentication`; `FoodServiceTest.missingCategoryOrFoodIsNotFound` | **COVERED SOURCE** — public 200/delegation và category negative; response list detail mỏng. |
| UC04 `GET /api/foods/{id}` | `FoodCartSecurityTest.foodAndCartErrorsUseTheSharedErrorBody`; `FoodServiceTest.missingCategoryOrFoodIsNotFound`; black-box detail success | **PARTIAL ASSERTION** — JUnit chủ yếu 404/error; HTTP 200 shape chỉ ở manual black-box. |
| UC05 `GET /api/foods/search` | `FoodServiceTest.searchEscapesLikeWildcardsAndRejectsBadKeywords`; FoodCart missing-query error; black-box search success | **PARTIAL ASSERTION** — logic/boundary tốt, thiếu JUnit HTTP 200 JSON/filter contract. |
| UC06 `POST /api/foods` | `FoodServiceTest.createUsesDefaultsAndChecksNameAcrossWholeMenu`; `FoodCartSecurityTest` RBAC/validation; black-box admin success | **PARTIAL ASSERTION** — thiếu JUnit 201 response mapping. |
| UC07 `PUT /api/foods/{id}` | `FoodServiceTest.update*`; `FoodCartSecurityTest` RBAC/validation; black-box update success | **PARTIAL ASSERTION** — thiếu JUnit 200 response mapping. |
| UC08 `DELETE /api/foods/{id}` | `FoodServiceTest.deleteOnlyStopsSelling`; `FoodCartSecurityTest.onlyAdminCanWriteFoods` | **COVERED SOURCE** — soft delete, role và 204. |
| UC09 `GET /api/cart` | `FoodCartSecurityTest.cartUsesJwtOwner*`, `onlyCustomers*`; `OrderIntegrationTest.userWithoutCart*` | **COVERED SOURCE** — auth/owner/delegation và empty-cart DB behavior. |
| UC10 `POST /api/cart/items` | FoodCart role/validation/conflict tests; `OrderIntegrationTest` CartService CRUD; black-box success | **PARTIAL ASSERTION** — thiếu JUnit successful HTTP body/delegation. |
| UC11 `PUT /api/cart/items/{id}` | FoodCart wrong-role; `OrderIntegrationTest.cartCrud*`, overflow; black-box success/ownership | **PARTIAL ASSERTION** — service/DB tốt, JUnit authorized HTTP success thiếu. |
| UC12 `DELETE /api/cart/items/{id}` | FoodCart wrong-role; `OrderIntegrationTest.cartCrud*`; black-box success/not-found/ownership | **PARTIAL ASSERTION** — service/DB tốt, JUnit authorized HTTP success thiếu. |
| UC13 `POST /api/orders` | `OrderWebTest.creationReturnsLocation*`, validation/error/RBAC; Order service/integration checkout/rollback | **COVERED SOURCE** — HTTP + business + transaction paths. |
| UC14 `GET /api/orders/{id}` | `OrderWebTest.listAndDetailReturnPageAndSnapshot`, errors; `OrderServiceTest.ownershipIsChecked*` | **COVERED SOURCE** — response snapshot, owner/employee, 403/404. |
| UC15 `DELETE /api/orders/{id}` | `OrderWebTest.allThreeStatusEndpoints*`; `OrderServiceTest.customerCanOnlyCancel*`; integration cancel rollback | **COVERED SOURCE** — role/state/stock restoration/rollback. |
| UC16 `POST /api/orders/{id}/confirm` | Order web status method; `OrderServiceTest.confirmIsPending*`; integration flow | **COVERED SOURCE** — role/transition/metadata. |
| UC17 `PUT /api/orders/{id}/status` | Order web success/enum/validation; exhaustive service transition matrix; integration serving flows | **COVERED SOURCE** — broad static coverage; retry semantics decision remains. |
| UC18 `GET /api/orders` | `OrderWebTest.listAndDetail*`; `OrderServiceTest.customerList*`; `OrderIntegrationTest.customerScope*` | **COVERED SOURCE** — role/scope/filter/page/order and DB query behavior, không có query-count assertion. |

Kết quả: **18/18 endpoint patterns có test source**, trong đó **11 COVERED SOURCE** và **7 PARTIAL ASSERTION** (UC04–UC07, UC10–UC12). Con số này chỉ là traceability tĩnh, không phải line/branch coverage và không chứng minh 90 tests pass.

#### Traceability tới invariants và findings Hạng mục 1–7

| Invariant/finding | Test evidence | Trạng thái |
|---|---|---|
| Checkout snapshot, stock, clear cart, atomic rollback | Order service + integration tests (`OrderServiceTest.java:71-150`; `OrderIntegrationTest.java:72-129,269-278`) | **Có test source mạnh; runtime PENDING**. |
| Order state machine/cancel restore once | Exhaustive transition loops, cancel sequence và real-DB flows (`OrderServiceTest.java:197-260`; `OrderIntegrationTest.java:131-187`) | **Có test source mạnh; concurrency không covered**. |
| DB constraints/snapshot/seed lifecycle | `DatabaseDesignTests.java:50-193` | **Có test source; DB-02 migration upgrade vẫn missing**. |
| SC-01 package cycle | Năm ArchUnit rules không có cycle/repository→service rule | **NOT FOUND**. |
| SC-03/04 OrderService/transition complexity | 10 service tests + 14 order integration tests | **Có coverage đáng kể**. |
| DB-05 five races | Không có corresponding test | **NOT FOUND**. |
| DB-06/07 query plan/index/N+1 | Không có `EXPLAIN`, query counter hoặc SQL-count assertion | **NOT FOUND**. |
| API-02 retry/idempotency | Transition/cancel lần hai bị reject ở service | **PARTIAL** — behavior current được test, HTTP retry contract chưa chốt. |
| API-06 OpenAPI drift | Không test reference `openapi.yaml` | **NOT FOUND**. |
| SEC2-01/02 stale token/key lifecycle | Không có lock/role-change then reuse token hoặc rotation/revocation test | **NOT FOUND**. |
| SEC2-03/04 current RBAC + limiter | Current route roles và single-node limiter có tests | **PARTIAL** — route-new guard, multi-instance/proxy missing. |
| DEP-02 verification gate | README có commands; Docker/Kaggle bỏ test; không CI/report | **NOT VERIFIED**. |
| DEP-03/09–12 benchmark reproducibility | Notebook/workload source có; version/config/reset/provenance/resource artifacts thiếu | **PARTIAL / PENDING**. |

### 8.10. Test Quality & Reliability

#### Điểm tích cực đã xác minh từ source

- Không có `@Disabled`, conditional skip hoặc `Thread.sleep` trong JUnit source. Concurrent tests dùng latch/future timeout; Order service và limiter dùng controllable clock (`AuthIntegrationTest.java:100-108`; `RateLimiterTest.java:9-28`; `OrderServiceTest.java:27-40`).
- Unit/service tests inject mock/fake trực tiếp; web slices mock business services; integration tests dùng MySQL thật và assert final database state. Failure-path assertions thường kiểm tra không có downstream interaction hoặc rollback.
- `OrderIntegrationTest` reset toàn bộ domain tables và seed trước mỗi method; black-box script dùng prefix ngẫu nhiên, targeted cleanup và so sánh pre/post state (`OrderIntegrationTest.java:61-66`; `scripts/test-endpoints.py:19-22,349-392`).
- Test key là RSA pair tạm, không dùng key local/deployment và có shutdown cleanup (`TestAuthKeys.java:20-40`).

#### Reliability/maintainability concerns

- `AuthIntegrationTest` có shared seed/application/limiter state và không cleanup; không có explicit test-order/parallel-execution policy. Đây là **POTENTIAL ISSUE** về retry/parallel isolation, chưa phải flaky test đã tái hiện.
- Integration/database tests phụ thuộc nhiều seed ID/count cụ thể; thay đổi fixture hợp lệ có thể buộc sửa nhiều assertions (`DatabaseDesignTests.java:34-40,50-67`; `OrderIntegrationTest.java:72-279`). Một phần là intentional schema/seed contract, nhưng coupling làm tăng maintenance cost.
- Wall-clock tolerance dưới 60/120 giây và JWTs tạo bằng `Instant.now()` có thể nhạy với máy quá tải/clock (`OrderIntegrationTest.java:92-102,246-259`; web token helpers). Không có observed failure.
- Manual `for` loops gom nhiều case vào một test method; report granularity thấp hơn parameterized/dynamic tests. Không có randomized order/property test.
- 32 methods cần Docker và ba MySQL containers theo ba class; cost thực tế chưa đo. 58 methods còn lại chạy không cần Docker theo lệnh README (`README.md:181-192`).
- `scripts/test-endpoints.py` có isolation/cleanup tốt nhưng cần stack Compose, ghi report vào `.local` (bị ignore), dùng direct SQL cho role/fixture/verification và không được Maven/CI gọi. Một lỗi cleanup làm script fail, nhưng artifact không được archive tự động (`scripts/test-endpoints.py:1-7,30-41,368-392`).
- Không có JaCoCo hoặc công cụ branch/line coverage trong POM; không được phép suy ra phần trăm coverage từ traceability matrix. Không có current Surefire report để đánh giá duration/flakiness.

Khả năng chạy độc lập: unit/web/architecture phù hợp local Java 21; integration/database cần Docker/Testcontainers/network image pull. Black-box cần Compose stack và DB có thể thay đổi tạm thời; k6 cần Kaggle Internet/package installation. Khả năng chạy trong CI là **PENDING** vì repository không có workflow và chưa ghi nhận runner prerequisites/cache/artifact retention.

### 8.11. Verification Readiness

Checklist dưới đây là kế hoạch cho lần chạy chính thức, không được thực thi trong assessment này.

| Gate | Việc cần thực hiện/ghi nhận | Exit evidence |
|---|---|---|
| Source provenance | Ghi full commit SHA, branch/tag, `git status --short`; xác định chính xác diff được phép. | Manifest source + working tree clean/known. |
| Toolchain | Ghi OS/CPU/RAM, `java -version`, `./mvnw -version`, Docker Engine/Compose và resolved dependency versions. | Machine-readable/text environment manifest. |
| Docker/Testcontainers | Docker daemon usable; pull/resolve digest `mysql:8.4`; đủ disk/RAM; không dùng DB shared bên ngoài. | Docker diagnostics không chứa secret + image digest. |
| Non-Docker suite | Chạy lệnh tài liệu: `./mvnw test -Dtest="!*IntegrationTest,!DatabaseDesignTests"` (Windows dùng `mvnw.cmd`). | Expected **58** tests discovered; lưu exit code và Surefire XML/text. |
| MySQL suites | Chạy `./mvnw test -Dtest="AuthIntegrationTest,OrderIntegrationTest,DatabaseDesignTests"`. | Expected **32** tests discovered; container logs chỉ lưu khi cần và phải redaction. |
| Full regression | Chạy `./mvnw test` trên cùng SHA/toolchain. | Expected **90** JUnit tests; failures/errors/skips được phân loại, không chỉ dựa exit code. |
| Architecture | Xác nhận 5 ArchUnit methods được discover trong report. | 5 kết quả riêng; cycle gap vẫn được ghi, không coi pass là cycle-free. |
| Black-box API | Trên clean Compose stack, chạy `python -X utf8 scripts/test-endpoints.py`; archive `.local/endpoint-test-results.json` sau redaction. | Script exit 0, all checks pass, `cleanupVerified=true`; ghi stack/config SHA. |
| Determinism | Lặp suite đầy đủ hoặc ít nhất integration suite nhiều lần trên cùng SHA; nếu lệch, giữ cả reports, order/timing/log và isolate class trước benchmark. | Không “rerun until green”; flake được ghi thành issue với reproduction evidence. |
| Reports/coverage | Archive `target/surefire-reports`, resolved dependency list và logs cần thiết. Nếu nhóm cần line/branch coverage, phải chạy công cụ hợp lệ sau khi được cấu hình; không ước lượng. | Artifact manifest/checksums; pass/fail/skip/duration truy vết được. |
| Baseline gate | Existing suite pass theo policy nhóm; black-box pass/cleanup; five concurrency gaps và security/contract gaps được chấp nhận rõ hoặc có verification phù hợp; JAR/schema/seed/workload checksum và benchmark controls đã khóa. | Biên bản freeze/tag/manifest trước khi chạy baseline. |

Pass/fail/skip policy đề nghị để nhóm xác nhận: command exit 0 là cần nhưng chưa đủ; report phải discover đúng expected count, `failures=0`, `errors=0`, và mọi `skipped` phải có lý do được phê duyệt. Docker unavailable, image-pull failure hoặc test không discover không được ghi thành “pass”.

### 8.12. Testing Findings

| ID | Trạng thái | Impact sơ bộ | Finding / quality attribute | Bằng chứng | Điều kiện xác minh còn thiếu |
|---|---|---|---|---|---|
| TEST-01 | **PENDING** | High cho assurance | Có 90 JUnit methods nhưng không có current test report; pass/fail/skip/duration chưa xác minh. **Reliability, verification.** | `src/test` inventory; không có Surefire/Failsafe report. | Chạy official suite đúng SHA và archive report; liên hệ DEP-02. |
| TEST-02 | **CONFIRMED** coverage gap | Medium | 18/18 route có test source, nhưng UC04–UC07 và UC10–UC12 thiếu JUnit authorized happy-path HTTP contract đầy đủ; manual black-box có bù một phần. **Functional reliability, maintainability.** | Ma trận 8.9; three web test classes; `scripts/test-endpoints.py`. | Chạy black-box/current JUnit; nhóm quyết định mức endpoint contract cần tự động hóa. |
| TEST-03 | **CONFIRMED**, liên hệ API-06 | Medium | Không có automated OpenAPI/controller/DTO/security contract-sync test. **API compatibility, maintainability.** | Không có reference `openapi.yaml` trong `src/test`; static spec phục vụ trực tiếp. | Chọn source of truth/gate và kiểm chứng ở giai đoạn cải tiến; không bổ sung trong assessment. |
| TEST-04 | **CONFIRMED**, liên hệ SC-01 | Medium | ArchUnit rules không phát hiện package cycle `service ↔ repository` hoặc repository→service dependency. **Architecture maintainability.** | `ArchitectureTest.java:17-54`. | Prove rule behavior bằng architecture test thích hợp sau khi nhóm quyết định boundary. |
| TEST-05 | **CONFIRMED test gap**, liên hệ DB-05 | High | Không tìm thấy test cho cả năm race checkout/cart/cancel/admin-stock/cart-create. **Consistency, reliability.** | Concurrency inventory; `scripts/test-endpoints.py:341-342`. | Test MySQL thật với synchronization barrier và final DB-state assertions; chưa kết luận defect. |
| TEST-06 | **CONFIRMED test gap**, liên hệ SEC2-01/02/03 | Medium–High | JWT negative matrix thiếu tamper/issuer/audience/time/role cases; không test stale token, rotation/revocation hoặc fail-closed route registration. **Security, authorization.** | `AdaptersTest.java:28-44`; security table 8.6. | Chốt security policy rồi chạy decoder/filter/route-matrix tests phù hợp. |
| TEST-07 | **POTENTIAL ISSUE** | Medium | Shared static seed/state, hardcoded seed IDs và wall-clock windows có thể gây order/parallel/retry flakiness. **Test reliability.** | `AuthIntegrationTest.java:40-43`; `OrderIntegrationTest.java:61-66,92-102,246-259`; DB fixtures. | Repeated/random-order/parallel-policy run và duration evidence; không khẳng định flake hiện hữu. |
| TEST-08 | **CONFIRMED** | High cho performance conclusions | k6 workload không có checkout/order listing/write flow; thiếu resource metrics, repetitions, reset và provenance artifacts. **Performance, reproducibility.** | Notebook cells 1–5; baseline README `:3-12,39-44`; DEP-09–12. | Khóa representative workload/protocol và rerun có manifest/raw outputs; chưa chọn protocol. |
| TEST-09 | **CONFIRMED** | Medium | Không có JaCoCo/coverage configuration/artifact; traceability tĩnh không cung cấp line/branch percentage. **Test completeness visibility.** | `pom.xml:74-98,100-129`; report inventory. | Nếu coverage là criterion, cấu hình/chạy approved tool và lưu raw report. |
| TEST-10 | **CONFIRMED**, liên hệ DEP-02 | High cho release confidence | Không có CI workflow; Docker/Kaggle packaging skip tests nên verification không tự động gắn với artifact. **Deployability, reliability.** | `Dockerfile:7`; `kaggle/script/README.md:24-27`; CI inventory. | Có pipeline ngoài repo hay artifact gate nào phải được chứng minh; lưu SHA/report/checksum. |
| TEST-11 | **CONFIRMED coverage concentration** | Low–Medium | CartService không có plain unit test; Auth service unit methods nằm trong web context; application JWT validator negative branches thiếu isolation. **Feedback speed, testability.** | Class inventory; `AuthWebAndServiceTest.java:30-58`; `OrderIntegrationTest.java:198-267`. | Đo execution time/change-impact và quyết định test pyramid; không mặc định cần mock thêm. |
| TEST-12 | **POTENTIAL ISSUE** | Medium | Black-box runner ngoài Maven/CI, phụ thuộc Compose/direct SQL và report bị ignore; kết quả có thể không được lưu cùng artifact. **Reproducibility, operability.** | `scripts/test-endpoints.py:1-7,30-41,368-392`; `.gitignore:15-17`; `README.md:194-197`. | Chạy trên clean stack, archive result/checksum/config và verify cleanup; không chạy trong assessment. |
| TEST-13 | **CONFIRMED positive source / PENDING runtime** | Medium | 32 integration/database methods dùng MySQL 8.4 thật và có rollback/constraint/final-state assertions, tạo nền tảng tốt hơn mock-only tests. **Reliability, consistency.** | `AuthIntegrationTest.java:31-108`; `OrderIntegrationTest.java:46-279`; `DatabaseDesignTests.java:27-227`. | Official run, exact image digest/Testcontainers version và report; tag `8.4` chưa pin digest. |

Thiếu test không được coi là production defect. TEST-03/04/05/06/08/10/12 liên kết findings trước để mô tả verification gap, không tạo lại nguyên nhân kiến trúc/database/security/deployment.

### 8.13. Conclusions & Pending Questions

#### Kết luận

- **CONFIRMED:** suite có 14 Java source files, 12 JUnit test classes và 90 test methods; partition chính gồm 32 unit, 21 web, 22 Spring integration, 10 DB và 5 architecture methods.
- **CONFIRMED:** business rules trọng yếu — checkout snapshot/rollback, order state machine, ownership, constraints, JWT/RBAC/rate limiting — có test source đáng kể; 32 methods dùng MySQL 8.4 thật.
- **CONFIRMED:** 18/18 endpoint patterns được chạm trong automated source, nhưng 7 UC còn partial JUnit happy-path HTTP assertions; OpenAPI sync, package cycle rule, query-count/performance và năm concurrency scenario chưa có test.
- **PENDING:** không có bằng chứng suite pass, test duration, skip count, line/branch coverage, flakiness hay CI compatibility vì không chạy và không có report artifact.
- **POTENTIAL ISSUE:** shared integration state, hardcoded seed/time windows và manual black-box artifact handling có thể làm giảm isolation/reproducibility; cần repeated official runs để kết luận.
- Load test hiện chỉ đại diện read/search/cart-read/login saturation và chưa đủ provenance/resource telemetry để làm benchmark gate trước/sau.

#### Câu hỏi/điểm cần nhóm xác nhận

1. Official verification gate có yêu cầu đủ 90 JUnit tests, 0 skip và black-box cleanup pass không?
2. Năm concurrency scenario nào phải hoàn tất trước khi freeze baseline, và expected loser/idempotency semantics của từng race là gì?
3. UC04–UC07/UC10–UC12 cần JUnit MockMvc happy-path hay black-box suite được chấp nhận làm contract evidence?
4. OpenAPI hay controller là source of truth; drift check và role-matrix guard có là acceptance criterion Phase 2 không?
5. Security negative matrix cần bao phủ claim/key/token lifecycle nào theo threat model và revocation SLA?
6. Policy chạy test tuần tự/parallel, số lần repeat và cách phân loại flaky test là gì?
7. Coverage percentage có phải grading/quality gate không; nếu có, metric/tool/threshold nào được chấp nhận?
8. CI runner nào có Docker/Testcontainers; reports/logs/dependency manifest sẽ được giữ ở đâu và bao lâu?
9. Performance workload chính thức có cần checkout/order list/write/concurrency và resource telemetry hay chỉ giữ read/auth workload cũ?
10. Baseline provenance sẽ khôi phục run cũ hay tạo lại sau khi verification gate đạt?

**Readiness:** đã đủ thông tin để **kết thúc khảo sát chuyên sâu 8/8 và chuyển sang final assessment review**. Chưa đủ bằng chứng để tuyên bố Phase 1 verified hoặc dùng baseline hiện tại cho kết luận before/after: official test execution/report, năm concurrency gaps, test/benchmark provenance và các quyết định gate nêu trên vẫn **PENDING**. Không lựa chọn hay triển khai cải tiến Phase 2 trong assessment này.
