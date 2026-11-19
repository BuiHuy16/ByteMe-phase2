## 5. API Assessment

Phạm vi mục này là phân tích tĩnh controller, DTO, service behavior liên quan đến HTTP contract, error handler, security matcher, OpenAPI viết tay và API test source. Không chạy build/test hoặc ứng dụng. Implementation là nguồn xác nhận chính; test source chỉ chứng minh intent/coverage hiện có, không chứng minh test đang pass.

### 5.1. API Overview & Inventory

#### Thống kê

| Nhóm | GET | POST | PUT | DELETE | Tổng |
|---|---:|---:|---:|---:|---:|
| Auth | 0 | 2 | 0 | 0 | 2 |
| Food | 3 | 1 | 1 | 1 | 6 |
| Cart | 1 | 1 | 1 | 1 | 4 |
| Order | 2 | 2 | 1 | 1 | 6 |
| **Tổng** | **6** | **6** | **3** | **3** | **18** |

Không có PATCH. **CONFIRMED** — Pha 1 yêu cầu REST/JSON, tối thiểu POST/GET/DELETE, có OpenAPI và ít nhất một GET cùng một POST cần xác thực (`docs/2026.md:8-11,19-20`). Implementation có đủ cả ba method; GET Cart/Order và nhiều POST được bảo vệ.

#### Endpoint thực tế

| # | Method và URL | Controller.handler | Request → response thành công | Quyền theo source |
|---:|---|---|---|---|
| 1 | `POST /api/auth/register` | `AuthController.register` (`AuthController.java:21-24`) | `RegisterRequest` → `201 AccountRecord` | Public |
| 2 | `POST /api/auth/token` | `AuthController.login` (`AuthController.java:27-34`) | `LoginRequest` → `200 TokenResponse` | Public |
| 3 | `GET /api/foods` | `FoodController.getFoods` (`FoodController.java:21-23`) | query `categoryId?` → `200 FoodDto[]` | Public |
| 4 | `GET /api/foods/search` | `FoodController.searchFoods` (`FoodController.java:31-35`) | query `q`, `categoryId?` → `200 FoodDto[]` | Public |
| 5 | `GET /api/foods/{id}` | `FoodController.getFoodById` (`FoodController.java:26-28`) | path `id` → `200 FoodDto` | Public |
| 6 | `POST /api/foods` | `FoodController.createFood` (`FoodController.java:38-40`) | `FoodRequest` → `201 FoodDto` | ADMIN |
| 7 | `PUT /api/foods/{id}` | `FoodController.updateFood` (`FoodController.java:43-45`) | `FoodRequest` → `200 FoodDto` | ADMIN |
| 8 | `DELETE /api/foods/{id}` | `FoodController.deleteFood` (`FoodController.java:48-51`) | Không body → `204` không body | ADMIN |
| 9 | `GET /api/cart` | `CartController.getCart` (`CartController.java:22-25`) | Không body → `200 CartDto` | CUSTOMER |
| 10 | `POST /api/cart/items` | `CartController.addToCart` (`CartController.java:28-33`) | `AddToCartRequest` → `200 CartDto` | CUSTOMER |
| 11 | `PUT /api/cart/items/{cartItemId}` | `CartController.updateCartItem` (`CartController.java:36-42`) | `UpdateCartItemRequest` → `200 CartDto` | CUSTOMER |
| 12 | `DELETE /api/cart/items/{cartItemId}` | `CartController.removeCartItem` (`CartController.java:45-50`) | Không body → `200 CartDto` | CUSTOMER |
| 13 | `POST /api/orders` | `OrderController.create` (`OrderController.java:29-36`) | `CreateOrderRequest` → `201 OrderDto`, `Location` | CUSTOMER |
| 14 | `GET /api/orders` | `OrderController.list` (`OrderController.java:39-44`) | filters/page → `200 OrderPage` | CUSTOMER, EMPLOYEE |
| 15 | `GET /api/orders/{orderId}` | `OrderController.get` (`OrderController.java:47-49`) | path `orderId` → `200 OrderDto` | CUSTOMER, EMPLOYEE |
| 16 | `DELETE /api/orders/{orderId}` | `OrderController.cancel` (`OrderController.java:52-54`) | Không body → `200 OrderDto` | CUSTOMER |
| 17 | `POST /api/orders/{orderId}/confirm` | `OrderController.confirm` (`OrderController.java:57-59`) | Không body → `200 OrderDto` | EMPLOYEE |
| 18 | `PUT /api/orders/{orderId}/status` | `OrderController.updateStatus` (`OrderController.java:62-65`) | `StatusRequest` → `200 OrderDto` | EMPLOYEE |

### 5.2. REST Design Assessment

- **CONFIRMED** — resource naming nhìn chung nhất quán: danh từ số nhiều `/foods`, `/orders`; `/cart` là current-user singleton; nested `/cart/items/{id}` thể hiện ownership. Client không truyền user ID; controller lấy từ JWT (`CartController.java:22-50`; `OrderController.java:29-65`).
- **CONFIRMED** — `GET` chỉ đọc; Food list/search không phân trang, Order list có `page/size`, lọc `status/orderType`, sort cố định mới nhất trước (`FoodController.java:21-35`; `OrderController.java:39-44`; `OrderService.java:71-86`). Không có client-controlled sort.
- **CONFIRMED** — `POST /foods` và `/orders` trả 201; order tạo thêm `Location`. Cart add trả 200 vì có thể tạo mới hoặc cộng vào dòng hiện hữu (`FoodController.java:38-40`; `OrderController.java:29-36`; `CartService.java:35-62`).
- **CONFIRMED** — Food DELETE là soft delete và state-idempotent: gọi lại món INACTIVE vẫn 204 (`FoodService.java:95-98`). Cart-item DELETE và order cancel không trả success idempotently khi gọi lại, nhưng lần gọi sau không tạo thêm state change trong luồng tuần tự (`CartService.java:79-89`; `OrderService.java:96-102`).
- **CONFIRMED design issue, không phải functional defect** — `PUT /api/orders/{id}/status` biểu diễn transition, không phải replacement idempotent: gửi lại cùng status sau lần thành công trả 409 vì transition từ state mới không hợp lệ (`OrderService.java:110-129`; `openapi.yaml:602-645`). Điều này làm retry semantics khác kỳ vọng thông thường của PUT.
- **CONFIRMED** — action route `/confirm` mang phong cách RPC và trùng một phần với generic status transition; đây là yêu cầu UC16/UC17, không phải endpoint thừa (`docs/Project KTPM.md:331-350`).
- **POTENTIAL ISSUE** — create order không có idempotency key; retry tuần tự sau thành công thường gặp `EMPTY_CART`, còn retry đồng thời liên hệ trực tiếp DB-05 (duplicate checkout risk), không tính thành một defect độc lập (`openapi.yaml:410-422`; Mục 4.8).
- **POTENTIAL ISSUE** — Food list/search không phân trang. Với menu Phase 1 nhỏ có thể phù hợp; impact ở tải lớn cùng nguyên nhân query/cardinality DB-06, cần benchmark trước khi kết luận (`FoodRepository.java:10-22`).

### 5.3. Request & Response Contracts

#### Request DTO và validation

| Contract | Required/optional và validation thực tế | Đối chiếu OpenAPI |
|---|---|---|
| `RegisterRequest` | 5 trường bắt buộc theo custom service validation; trim name/email/phone, normalize email; password 8–72 code point và ≤72 UTF-8 byte; strict unknown/trailing/type coercion (`RegisterRequest.java:3-4`; `AuthValidation.java:9-31`; `AuthJsonAdvice.java:17-46`). | Required/additionalProperties false và mô tả byte/code point khớp (`openapi.yaml:857-896`). |
| `LoginRequest` | email/password bắt buộc; password tối thiểu 1, tối đa 72 code point/byte; strict JSON như register (`AuthController.java:27-34`; `LoginService.java:24-39`). | Khớp `openapi.yaml:897-914`. |
| `FoodRequest` | Required `categoryId`, `name`, `price`; optional nullable description/image/stock/status; constraints Positive/Digits/Size/Pattern (`FoodRequest.java:13-37`). Create dùng default stock 0/status ACTIVE; update giữ stock/status khi null nhưng xóa description/image khi null (`FoodService.java:54-92`). | Khớp semantics mô tả ở `openapi.yaml:957-1001`. |
| Cart requests | Add required positive `foodId`, quantity ≥1; update required quantity ≥1 (`AddToCartRequest.java:7-14`; `UpdateCartItemRequest.java:6-9`). | Khớp `openapi.yaml:1029-1050`. |
| `CreateOrderRequest` | Required `orderType`, `paymentMethod`; Size cho các chuỗi; service áp điều kiện DINE_IN/DELIVERY, trim required/note (`CreateOrderRequest.java:9-29`; `OrderService.java:151-177`). | `oneOf` và conditional fields khớp `openapi.yaml:1081-1170`. |
| `StatusRequest` | Required enum `status`; PENDING parse được nhưng service từ chối 400 (`StatusRequest.java:6-8`; `OrderService.java:110-115`). | Khớp `openapi.yaml:1171-1180`. |

Jackson toàn cục từ chối numeric enum và số thực cho integer (`application.yml:12-17`). Auth từ chối unknown fields/trailing token; DTO Food/Cart/Order dùng behavior mặc định và bỏ qua unknown field, đúng mô tả đầu OpenAPI (`openapi.yaml:16-21`; `AuthJsonAdvice.java:17-46`).

#### Response JSON và headers

- Response DTO là Java records nên field names khớp schema: `FoodDto`, `CartDto/CartItemDto`, `OrderDto/OrderItemDto/OrderPage`, `AccountRecord`, `TokenResponse` (`FoodDto.java:7-12`; `CartDto.java:5`; `OrderDto.java:12-26`; `AccountRecord.java:7-15`; `TokenResponse.java:3-4`).
- Order snapshot và total được server tính; client không gửi items/price/userId (`OrderDto.java:18-26`; `OrderItemDto.java:7-11`).
- Auth success và mọi Order success đặt `Cache-Control: no-store`; create order đặt thêm `Location` (`AuthController.java:21-34`; `OrderController.java:29-69`). Food/Cart success không đặt cache header tường minh.
- Mọi error qua Auth/Global/security handlers trả JSON `ApiError(status,code,message,path,fieldErrors)` và đặt `no-store`; 401 security đặt `WWW-Authenticate: Bearer`; 429 đặt `Retry-After` (`ApiError.java:5-10`; `AuthErrors.java:17-36`; `GlobalErrors.java:24-85`; `SecurityConfiguration.java:43-48`; `LoginIpFilter.java:14-18`).
- **CONFIRMED contract gap** — `q` thực tế sau trim phải dài 1–100 (`FoodService.java:43-51`), OpenAPI description nói 1–100 nhưng machine schema chỉ có `minLength: 1`, thiếu `maxLength: 100` (`openapi.yaml:186-193`).

### 5.4. Authentication & Authorization Matrix

| API surface | Anonymous | CUSTOMER | EMPLOYEE | ADMIN | Source of truth |
|---|---:|---:|---:|---:|---|
| `POST /api/auth/register`, `/token` | Allow | Allow | Allow | Allow | Public filter chain, bearer header không được xác thực (`SecurityConfiguration.java:19-23`). |
| `GET /api/foods`, `/search`, `/{id}` | Allow | Allow | Allow | Allow | GET `/api/foods/**` permitAll (`SecurityConfiguration.java:27-28`). |
| `POST /api/foods`, `PUT/DELETE /api/foods/{id}` | 401 | 403 | 403 | Allow | `SecurityConfiguration.java:29-31`. |
| Toàn bộ `/api/cart/**` | 401 | Allow | 403 | 403 | `SecurityConfiguration.java:32`. |
| `POST /api/orders`, `DELETE /api/orders/{id}` | 401 | Allow | 403 | 403 | `SecurityConfiguration.java:33-34`. |
| `GET /api/orders`, `GET /api/orders/{id}` | 401 | Allow, owner-scoped | Allow, mọi đơn | 403 | Matcher ở `SecurityConfiguration.java:37`; ownership ở `OrderService.java:81-93`. |
| `POST /api/orders/{id}/confirm`, `PUT /api/orders/{id}/status` | 401 | 403 | Allow | 403 | `SecurityConfiguration.java:35-36`. |

- **CONFIRMED** — thiếu/hỏng/hết hạn token ở protected API trả 401 `UNAUTHENTICATED`; token hợp lệ nhưng sai role trả 403 `FORBIDDEN` (`SecurityConfiguration.java:39-48`). JWT subject không parse thành ID dương trả 403 trước khi gọi service (`CurrentUser.java:8-13`).
- **CONFIRMED** — GET và POST được xác thực theo yêu cầu đề bài: `GET /api/cart|orders` và `POST /api/cart/items|orders|foods` có matcher role (`docs/2026.md:19-20`; `SecurityConfiguration.java:29-37`).
- **CONFIRMED nuance** — Food GET là public nhưng Bearer token hỏng vẫn bị resource-server filter trả 401; Auth routes nằm ở filter chain riêng nên Bearer hỏng bị bỏ qua. OpenAPI mô tả đúng nuance này và Food GET liệt kê 401 (`openapi.yaml:9-14,120-142,173-224`).
- OpenAPI `bearerAuth` mô tả authentication nhưng HTTP bearer scheme không mã hóa machine-readable role scope; role chỉ nằm trong summary/description. Đây là giới hạn contract/usability, không phải authorization defect.

### 5.5. Error Handling Assessment

| HTTP | Nguồn/ý nghĩa thực tế | Payload/header |
|---:|---|---|
| 400 | Binding/type/JSON sai, Bean Validation, business INVALID; gồm `VALIDATION_ERROR`, `PASSWORD_MISMATCH`, `EMPTY_CART` (`GlobalErrors.java:24-46`; `AuthErrors.java:17-25`). | `ApiError`; validation có `fieldErrors`, business error thường mảng rỗng; `no-store`. |
| 401 | Thiếu/sai JWT hoặc `INVALID_CREDENTIALS` (`SecurityConfiguration.java:43-45`; `AuthErrors.java:19-24`). | `UNAUTHENTICATED` hoặc `INVALID_CREDENTIALS`; bearer challenge chỉ từ security entry point. |
| 403 | Sai role/owner/JWT subject hoặc account không ACTIVE khi login (`SecurityConfiguration.java:46-48`; `CurrentUser.java:8-13`; `AuthErrors.java:19-24`). | `FORBIDDEN` hoặc `ACCOUNT_NOT_ACTIVE`. |
| 404 | Resource/business lookup không thấy; route không tồn tại sau khi qua security (`GlobalErrors.java:24-32,49-52`). | `FOOD_NOT_FOUND`, `CATEGORY_NOT_FOUND`, `CART_ITEM_NOT_FOUND`, `ORDER_NOT_FOUND` hoặc `NOT_FOUND`. |
| 409 | Business conflict, integrity violation, lock/deadlock translation (`GlobalErrors.java:24-32,59-69`; `AuthErrors.java:28-30`). | Mã cụ thể như `ACCOUNT_CONFLICT`, `FOOD_NAME_CONFLICT`, `INSUFFICIENT_STOCK`, `INVALID_ORDER_TRANSITION`, hoặc generic `CONFLICT`/`CONCURRENT_UPDATE`. |
| 429 | Login quota theo IP/email (`AuthErrors.java:33-36`; `LoginIpFilter.java:14-18`). | `LOGIN_RATE_LIMITED`, `Retry-After`, `no-store`. |
| 415 | Body không dùng media type được hỗ trợ (`GlobalErrors.java:72-75`). | `UNSUPPORTED_MEDIA_TYPE`. |
| 500 | Exception không có mapping cụ thể (`GlobalErrors.java:77-85`). | Generic `INTERNAL_ERROR`; không trả message nội bộ. |

Auth dùng advice riêng cho auth-specific code nhưng vẫn cùng `ApiError`; Food/Cart/Order dùng `BusinessException` + `GlobalErrors`. Security filter tự serialize cùng schema trước MVC (`AuthErrors.java:15-36`; `GlobalErrors.java:20-85`; `SecurityConfiguration.java:43-48`). Đây là **CONFIRMED contract thống nhất về shape**, dù mapping code nằm ở ba lifecycle khác nhau.

#### Xác minh bất đồng ID path không dương

- **CONFIRMED implementation/OpenAPI:** path không parse được sang integer/long → 400 qua `MethodArgumentTypeMismatchException`; số đã parse nhưng `≤ 0` không có `@Positive`, đi vào lookup và thường → 404 business not-found (`FoodController.java:26-28,43-50`; `CartController.java:36-50`; `OrderController.java:47-65`; `GlobalErrors.java:43-46`). OpenAPI không đặt `minimum: 1` và mô tả `≤ 0` là 404 (`openapi.yaml:671-694`).
- **CONFIRMED documentation inconsistency:** quy tắc chung của `Project KTPM.md:24-26` đã chọn 404, nhưng các bảng UC11/12/14–16 vẫn gọi path ID “không hợp lệ” là 400 (`Project KTPM.md:221,236,303,318,333`). Đây là cùng nguyên nhân đã ghi ở Mục 1, không phải nhiều defect API độc lập.
- **PENDING runtime test:** web tests có case path chữ `abc` → 400 nhưng không có case `0`/`-1` để khóa contract 404 (`OrderWebTest.java:186-200`; không tìm thấy case non-positive path trong test source).

**CONFIRMED OpenAPI documentation gap** — implementation đặt `Cache-Control: no-store` cho mọi handled error, và prose OpenAPI cũng nói vậy (`GlobalErrors.java:24-85`; `AuthErrors.java:17-36`; `openapi.yaml:23-24`). Tuy nhiên reusable error responses `BadRequest` đến `InternalServerError` không khai báo header này, dù component `NoStore` tồn tại (`openapi.yaml:781-855`).

### 5.6. OpenAPI vs Implementation Comparison

OpenAPI là file static được Swagger UI đọc trực tiếp (`application.yml:34-38`), không sinh từ annotation/controller.

| Operation thực tế | OpenAPI | Path/method | Security/status/body | Kết quả |
|---|---:|---|---|---|
| `POST /api/auth/register` | `46-79` | Khớp | Public, 201, `RegisterRequest → Account` khớp | **MATCH** |
| `POST /api/auth/token` | `80-119` | Khớp | Public, 200/401/403/429, `LoginRequest → TokenResponse` khớp | **MATCH** |
| `GET /api/foods` | `120-142` | Khớp | Public, category filter/list khớp | **MATCH** |
| `POST /api/foods` | `143-172` | Khớp | bearer/ADMIN trong mô tả, 201, `FoodRequest → Food` khớp | **MATCH** |
| `GET /api/foods/search` | `173-204` | Khớp | Public và response khớp; machine constraint `q` thiếu maxLength | **MATCH WITH DETAIL GAP** |
| `GET /api/foods/{id}` | `205-224` | Khớp | Public, 200/400/401/404 khớp | **MATCH** |
| `PUT /api/foods/{id}` | `225-255` | Khớp | bearer/ADMIN trong mô tả, request/status khớp | **MATCH** |
| `DELETE /api/foods/{id}` | `256-281` | Khớp | bearer/ADMIN, soft-delete 204 khớp | **MATCH** |
| `GET /api/cart` | `282-302` | Khớp | bearer/CUSTOMER trong mô tả, nullable cart ID khớp | **MATCH** |
| `POST /api/cart/items` | `303-340` | Khớp | bearer/CUSTOMER, request/200 Cart khớp | **MATCH** |
| `PUT /api/cart/items/{cartItemId}` | `341-379` | Khớp | bearer/CUSTOMER, replace quantity/200 khớp | **MATCH** |
| `DELETE /api/cart/items/{cartItemId}` | `380-404` | Khớp | bearer/CUSTOMER, 200 Cart khớp | **MATCH** |
| `POST /api/orders` | `405-461` | Khớp | bearer/CUSTOMER, 201 + Location/Order khớp | **MATCH** |
| `GET /api/orders` | `462-516` | Khớp | bearer, role behavior/filter/page khớp | **MATCH** |
| `GET /api/orders/{orderId}` | `517-544` | Khớp | bearer, CUSTOMER/EMPLOYEE behavior khớp | **MATCH** |
| `DELETE /api/orders/{orderId}` | `545-572` | Khớp | bearer/CUSTOMER, cancel/200 Order khớp | **MATCH** |
| `POST /api/orders/{orderId}/confirm` | `573-601` | Khớp | bearer/EMPLOYEE, 200 Order khớp | **MATCH** |
| `PUT /api/orders/{orderId}/status` | `602-649` | Khớp | bearer/EMPLOYEE, `StatusRequest`/200 Order khớp | **MATCH** |

Kết quả identity: **18/18 operation khớp path và method; 0 endpoint thiếu trong OpenAPI; 0 endpoint thừa trong OpenAPI**. Security requirement, success status và top-level request/response schema khớp cho cả 18. Có hai gap chi tiết đã xác nhận: machine schema `q` thiếu `maxLength: 100`, và error response components thiếu header `no-store`; bất đồng path ID nằm giữa tài liệu UC với source/OpenAPI, không phải OpenAPI-vs-source mismatch.

Test source có web/contract examples cho Auth, Food/Cart security và Order status/serialization/errors (`AuthIntegrationTest.java:48-65,82-93`; `FoodCartSecurityTest.java:51-162`; `OrderWebTest.java:57-217`). **CONFIRMED** — không tìm thấy test nào đọc/parse `openapi.yaml`, enumerate controller mappings hoặc fail khi spec drift; trạng thái PENDING ở Mục 2 nay được xác định thành maintainability risk. Test hiện hữu không được chạy trong khảo sát này.

### 5.7. API Quality Assessment

| Thuộc tính | Đánh giá tĩnh |
|---|---|
| Consistency | **Khá tốt:** naming/status/JSON/error shape nhất quán; khác biệt Auth advice/MVC advice/security filter không làm đổi payload. Action `/confirm`, transition bằng PUT và mixed null semantics của Food update là các convention cần client hiểu rõ. |
| Usability | **Tốt ở mức tài liệu:** OpenAPI mô tả nhiều edge case, default, role, enum và lỗi. Hai detail gap (`q.maxLength`, error header) cùng mâu thuẫn ID trong UC làm giảm khả năng dùng schema làm nguồn duy nhất. |
| Maintainability | **POTENTIAL ISSUE:** OpenAPI 1.327 dòng viết tay, không có sync test; controller/DTO/security thay đổi có thể drift (`application.yml:34-38`). |
| Testability | **Có nền tảng:** MockMvc tests kiểm tra role, status, validation, payload, headers và service delegation; integration Auth kiểm tra JSON/DB. **PENDING** vì không chạy và chưa có spec-driven test. |
| Security contract | **CONFIRMED rõ ở bề mặt:** 401/403 và role matrix được mô tả, user ID lấy từ principal. Role không machine-readable trong bearer security scheme và invalid bearer trên public Food GET là nuance cần giữ trong tài liệu. Không đánh giá JWT/filter internals ở mục này. |
| Backward compatibility | API khai báo `info.version: 1.0.0` nhưng URI không versioned, không thấy deprecation/compatibility policy (`openapi.yaml:1-5`). **POTENTIAL ISSUE** chỉ khi Phase 2 tạo breaking contract; chưa có yêu cầu phải version URI. |
| Performance-related design | Order list có page size tối đa 100; Food list/search không phân trang; response Order chứa toàn bộ items. Đây là input cho benchmark/query-count, không phải bằng chứng hiệu năng (`OrderService.java:71-86`; Mục 4.5–4.6). |

### 5.8. API Findings

Mức ảnh hưởng là sơ bộ đối với client correctness, usability và maintainability; không phải production incident severity.

| ID | Trạng thái | Ảnh hưởng | Phát hiện | Bằng chứng | Xác minh/quan hệ |
|---|---|---|---|---|---|
| API-01 | **CONFIRMED** | Positive / Informational | Có 18 endpoint; đủ GET/POST/DELETE và protected GET/POST; OpenAPI có đúng 18 operation, không thiếu/thừa path-method. | Controllers ở Mục 5.1; `openapi.yaml:45-649`; `docs/2026.md:8-11,19-20`. | Không cần runtime để đếm mapping tĩnh; test pass vẫn PENDING. |
| API-02 | **CONFIRMED design issue** | Medium | PUT status là non-idempotent transition; retry cùng payload sau success trả 409. | `OrderController.java:62-65`; `OrderService.java:110-129`; `openapi.yaml:602-645`. | Cần nhóm xác nhận retry semantics mong muốn; không phải functional defect hiện tại. |
| API-03 | **CONFIRMED OpenAPI detail mismatch** | Low–Medium | Search `q` tối đa 100 trong service/description nhưng schema thiếu `maxLength: 100`. | `FoodService.java:43-51`; `openapi.yaml:186-193`. | Contract validator/client generator sẽ không thấy upper bound. |
| API-04 | **CONFIRMED documentation inconsistency** | Medium | Source/OpenAPI chọn 404 cho numeric path ID `≤0`, trong khi một số bảng UC còn ghi 400. | `Project KTPM.md:24-26,221,236,303,318,333`; `openapi.yaml:671-694`; controllers/services nêu ở Mục 5.5. | Cùng finding Mục 1, không đếm lỗi mới; cần test `0/-1` và chốt tài liệu chuẩn. |
| API-05 | **CONFIRMED OpenAPI documentation gap** | Low | Error implementation luôn `no-store`, nhưng reusable error responses không khai báo header dù component đã tồn tại. | `GlobalErrors.java:24-85`; `AuthErrors.java:17-36`; `openapi.yaml:781-855`. | Kiểm tra runtime representative errors; gap machine contract đã xác nhận tĩnh. |
| API-06 | **CONFIRMED maintainability risk** | Medium | Static OpenAPI không có contract-sync test với controller/DTO/security. | `application.yml:34-38`; không có test reference `openapi.yaml` trong `src/test/java`. | Liên hệ Architecture finding PENDING ở Mục 2; cần quyết định source-of-truth/gate. |
| API-07 | **POTENTIAL ISSUE** | Medium khi dữ liệu lớn | Food list/search không pagination; response có thể tăng không giới hạn theo menu. | `FoodController.java:21-35`; `FoodRepository.java:10-22`. | Cùng root cause/cardinality với DB-06; cần dataset và benchmark, không tính thành performance defect mới. |
| API-08 | **POTENTIAL ISSUE** | Low–Medium | Không thấy URI versioning, deprecation hoặc backward-compatibility policy cho thay đổi Phase 2. | `openapi.yaml:1-5,33-45`; toàn bộ route dùng `/api/...`. | Nhóm cần xác nhận có dự kiến breaking API hay không. |
| API-09 | **POTENTIAL ISSUE** usability | Low | Machine-readable bearer security không biểu diễn role; role matrix chỉ ở prose/source. | `openapi.yaml:9-14,651-661`; `SecurityConfiguration.java:27-38`. | Không phải authorization defect; ảnh hưởng tooling/client understanding. |
| API-10 | **PENDING** | Unknown | Chưa xác minh runtime content negotiation, exact serialization/header cho mọi operation, test pass hoặc generated-client compatibility. | Giới hạn khảo sát; web tests chỉ là source evidence. | Chạy contract/API tests ở Hạng mục Testing phù hợp. |

Không phát hiện endpoint implementation thiếu hoặc thừa so với OpenAPI. API-03 và API-05 là mismatch/gap machine contract; API-04 là lệch giữa tài liệu UC với source/OpenAPI; API-02 là REST semantics trade-off, không phải lỗi nghiệp vụ.

### 5.9. Conclusions & Pending Questions

#### Kết luận

- **CONFIRMED** — 18 endpoint thực tế: 6 GET, 6 POST, 3 PUT, 3 DELETE; đủ yêu cầu method và protected GET/POST của Pha 1.
- **CONFIRMED** — URI, success status, request/response DTO và role matrix phần lớn nhất quán; `ApiError` dùng chung cho Auth, business và security boundary.
- **CONFIRMED** — OpenAPI bao phủ 18/18 operation, không có path-method thiếu/thừa; hai detail gap machine-readable đã được định vị.
- **CONFIRMED** — source/OpenAPI thống nhất 404 cho path ID số `≤0`; mâu thuẫn còn nằm trong các bảng UC cũ. Chưa có web test khóa case này.
- **POTENTIAL ISSUE** — retry semantics của status PUT, static-spec drift, unpaginated Food và compatibility policy cần quyết định/đo, chưa phải defect đã chứng minh.
- **PENDING** — test pass, runtime headers/serialization/content negotiation và client/spec validation.

#### Câu hỏi/điểm cần nhóm xác nhận

1. Quy tắc chính thức cho numeric path ID `≤0` có chốt là 404 theo source/OpenAPI/quy tắc chung không, để sửa các bảng UC và thêm contract test sau này?
2. `PUT /orders/{id}/status` có chủ đích là transition không idempotent và client không tự retry, hay nhóm yêu cầu một retry contract khác?
3. File OpenAPI hay controller/DTO là source of truth; nhóm có yêu cầu automated contract-sync gate không?
4. `Cache-Control: no-store` trên mọi error có phải phần bắt buộc của public contract để khai báo trong từng response không?
5. Food list/search cần giữ unpaginated vì quy mô một nhà hàng, hay benchmark Phase 2 phải đánh giá payload/cardinality lớn?
6. Phase 2 có dự kiến breaking request/response change để cần compatibility/versioning policy không?
7. Unknown-field policy có chủ đích khác nhau giữa Auth (reject) và Food/Cart/Order (ignore) không?

**Readiness:** đủ thông tin để chuyển sang **Hạng mục 6 – Security Assessment**. Bề mặt public/protected, role matrix, authentication/error contract và các boundary cần khảo sát sâu đã được định vị. Chưa đánh giá JWT cryptography, filter internals, key management hoặc lỗ hổng security trong mục này; runtime contract/test vẫn giữ **PENDING**.

