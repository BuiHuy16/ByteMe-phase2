## 1. Business & Functional Assessment

### 1.1. Tổng quan nghiệp vụ

ByteMe là backend đặt món cho **một nhà hàng duy nhất**. Khách hàng dùng một tài khoản và một giỏ để tạo đơn ăn tại chỗ (`DINE_IN`) hoặc giao hàng (`DELIVERY`); hệ thống không có chọn nhà hàng, đặt bàn, khách vãng lai hay tích hợp cổng thanh toán. Phạm vi này được đặc tả tại `docs/Project KTPM.md:3-18` và được phản ánh bởi các entity `User`, `Food`, `Cart`, `Order` trong `src/main/java/org/example/entity/`.

#### Vai trò và quyền thực tế

| Vai trò | Quyền nghiệp vụ đã xác minh | Bằng chứng source |
|---|---|---|
| Anonymous | Đăng ký, đăng nhập; xem/tìm món đang `ACTIVE`. | `SecurityConfiguration.java:19-28`; `AuthController.java:21-34`; `FoodController.java:21-35`. |
| `CUSTOMER` | Xem/tìm món; quản lý giỏ của mình; tạo, xem và hủy đơn của mình khi còn `PENDING`. | `SecurityConfiguration.java:28,32-34,37`; `CartController.java:22-50`; `OrderController.java:29-54`; `OrderService.java:81-102`. |
| `EMPLOYEE` | Xem danh sách/chi tiết mọi đơn; xác nhận và chuyển trạng thái/hủy theo vòng đời cho phép. | `SecurityConfiguration.java:35-37`; `OrderController.java:39-65`; `OrderService.java:77-86,90-93,105-148`. |
| `ADMIN` | Tạo, cập nhật và ngừng bán món; không kế thừa quyền Cart/Order. | `SecurityConfiguration.java:29-37`; `FoodController.java:38-51`. |

**CONFIRMED** — danh tính tác nhân cho các thao tác bảo vệ lấy từ JWT, không lấy `customerId`/`employeeId` do client gửi. Controller truyền `CurrentUser.id(user)` xuống service (`CartController.java:22-50`; `OrderController.java:29-65`; `CurrentUser.java:8-13`).

### 1.2. Đối chiếu UC01–UC18 với implementation

Trạng thái dưới đây xác nhận sự tồn tại và logic tĩnh của đường thực thi, chưa khẳng định test/runtime đang pass.

| UC | Nghiệp vụ / actor | Truy vết implementation | Trạng thái và nhận xét |
|---|---|---|---|
| UC01 | Đăng ký / Anonymous | `AuthController.java:21-24` → `RegisterService.java:22-34` → `AccountRepository.java:8-11`, `MySqlAccountRepository.java:33-50` → `User.java:7-32`. | **CONFIRMED** — chuẩn hóa/validate dữ liệu, kiểm tra trùng email/phone, BCrypt, tạo `CUSTOMER/ACTIVE`, trả 201. |
| UC02 | Đăng nhập / mọi vai trò | `AuthController.java:27-34` → `LoginService.java:24-39` → `MySqlAccountRepository.java:55-66` → `User`; token tại `LocalRsaTokenIssuer.java:29-37`. | **CONFIRMED** — giới hạn theo email/IP, kiểm tra mật khẩu và `ACTIVE`, cấp JWT RS256 chứa subject/role. |
| UC03 | Xem danh sách món / Public | `FoodController.java:21-23` → `FoodService.java:28-31` → `FoodRepository.java:10-14` → `Food.java:8-39`. | **CONFIRMED** — chỉ `ACTIVE`, lọc category tùy chọn, kiểm tra category tồn tại, sắp xếp id. |
| UC04 | Xem chi tiết món / Public | `FoodController.java:26-28` → `FoodService.java:34-40` → `FoodRepository.findById` → `Food`. | **CONFIRMED** — món không tồn tại hoặc `INACTIVE` cùng trả `FOOD_NOT_FOUND`. |
| UC05 | Tìm món / Public | `FoodController.java:31-35` → `FoodService.java:43-51,157-158` → `FoodRepository.java:16-22`. | **CONFIRMED** — q sau trim dài 1–100, escape `%/_/!`, tìm name/description không phân biệt hoa thường, chỉ `ACTIVE`. |
| UC06 | Thêm món / Admin | `FoodController.java:38-40` → `FoodService.java:54-72` → `CategoryRepository`, `FoodRepository` → `Food`. | **CONFIRMED** — validate DTO, category tồn tại, tên không trùng, mặc định stock 0/status `ACTIVE`, trả 201. |
| UC07 | Cập nhật món / Admin | `FoodController.java:43-45` → `FoodService.java:75-92` → `FoodRepository`, `CategoryRepository` → `Food`. | **CONFIRMED** — cập nhật cả món `INACTIVE`; description/image thay thế, stock/status null thì giữ nguyên. |
| UC08 | Ngừng bán món / Admin | `FoodController.java:48-51` → `FoodService.java:95-97` → `FoodRepository.findById` → `Food.status`. | **CONFIRMED** — xóa mềm bằng `INACTIVE`, idempotent với món đã inactive, trả 204. |
| UC09 | Xem giỏ / Customer | `CartController.java:22-25` → `CartService.java:28-32,109-115` → `CartRepository.java:7-12` → `Cart.java`, `CartItem.java`. | **CONFIRMED** — giỏ theo user từ JWT; chưa có giỏ trả `id=null/items=[]`; vẫn trả thông tin món `INACTIVE`. |
| UC10 | Thêm món vào giỏ / Customer | `CartController.java:28-33` → `CartService.java:35-62` → `CartRepository`; kiểm tra món qua `FoodService.java:101-105`. | **CONFIRMED** — tạo giỏ khi cần, chỉ nhận món `ACTIVE`, cộng quantity nếu đã có, bắt integer overflow; chủ ý chưa kiểm tra tồn kho. |
| UC11 | Cập nhật quantity / Customer | `CartController.java:36-42` → `CartService.java:65-76` → `CartRepository` → `CartItem`. | **CONFIRMED** — quantity ≥ 1; chỉ tìm item trong giỏ của user; không kiểm tra lại trạng thái món/tồn kho theo đặc tả. |
| UC12 | Xóa item / Customer | `CartController.java:45-50` → `CartService.java:79-89` → `CartRepository` → orphan removal của `Cart.java:23-26`. | **CONFIRMED** — chỉ xóa item thuộc giỏ hiện tại; item khác chủ được xử lý như không tồn tại. |
| UC13 | Checkout / Customer | `OrderController.java:29-36` → `OrderService.java:34-68` → `CartService.java:93-106`, `FoodService.java:116-130`, `OrderRepository` → `Order`, `OrderItem`. | **CONFIRMED** — kiểm tra loại đơn/giỏ/món/tồn kho, trừ kho, snapshot tên/giá, tạo `PENDING`, dọn giỏ trong transaction, trả 201 + Location. Bảo đảm đồng thời vẫn là **POTENTIAL ISSUE**. |
| UC14 | Xem đơn của mình / Customer | `OrderController.java:39-49` → `OrderService.java:71-93` → `OrderRepository.java:14-30` → `Order`; DTO tại `OrderDto.java:18-26`. | **CONFIRMED** — list theo owner, filter/trang/sort; detail kiểm tra ownership; total tính từ snapshot item. |
| UC15 | Hủy đơn / Customer | `OrderController.java:52-54` → `OrderService.java:96-102,132-148` → `OrderRepository`, `FoodService.releaseStock`. | **CONFIRMED** — chỉ chủ đơn và chỉ `PENDING`; chuyển `CANCELLED`, đặt `cancelledAt`, hoàn kho trong transaction. Hủy đồng thời là **POTENTIAL ISSUE**. |
| UC16 | Xác nhận đơn / Employee | `OrderController.java:57-59` → `OrderService.java:105-116,120-148` → `OrderRepository` → `Order`. | **CONFIRMED** — chỉ `PENDING → CONFIRMED`; ghi `confirmedBy/confirmedAt`. |
| UC17 | Cập nhật trạng thái / Employee | `OrderController.java:62-65` → `OrderService.java:110-148` → `OrderRepository`, `FoodService.releaseStock` → `Order`. | **CONFIRMED** — ép state machine theo order type; nhân viên hủy từ PENDING/CONFIRMED/PROCESSING và hoàn kho. |
| UC18 | Danh sách đơn xử lý / Employee | `OrderController.java:39-44` → `OrderService.java:24-26,71-86` → `OrderRepository.java:14-30`. | **CONFIRMED** — mặc định PENDING/CONFIRMED/PROCESSING/SHIPPING; filter cụ thể có thể xem cả COMPLETED/CANCELLED; nhân viên xem detail mọi đơn. |

**Kết luận đối chiếu:** **CONFIRMED** 18/18 UC có đường thực thi trong source. Không phát hiện UC hoàn toàn chưa triển khai ở mức khảo sát tĩnh.

### 1.3. Các luồng nghiệp vụ chính

#### A. Đăng ký và đăng nhập

1. Auth payload được đọc nghiêm ngặt, từ chối field lạ/trailing token/coercion kiểu (`AuthJsonAdvice.java:17-46`).
2. Đăng ký trim tên, lowercase email, validate phone/password, so confirm password và kiểm tra trùng (`AuthValidation.java:9-31`; `RegisterService.java:22-33`).
3. Repository tạo user với role `CUSTOMER`, status `ACTIVE`; unique conflict được đổi thành `ACCOUNT_CONFLICT` (`MySqlAccountRepository.java:33-50`; `AuthErrors.java:28-30`).
4. Đăng nhập giới hạn theo IP tại filter và theo email tại controller (`LoginIpFilter.java:11-20`; `AuthController.java:29-32`), sau đó kiểm tra credential/status và cấp JWT (`LoginService.java:24-39`).

#### B. Thực đơn và giỏ hàng

1. Public chỉ nhìn thấy món `ACTIVE`; Admin có thể tạo/sửa/ngừng bán (`FoodRepository.java:10-22`; `SecurityConfiguration.java:28-31`).
2. Thêm giỏ xác minh món còn bán nhưng không giữ chỗ và không kiểm tra stock; cùng food thì cộng quantity (`CartService.java:35-61`).
3. Update/remove luôn định vị Cart Item bên trong giỏ lấy theo user từ JWT, không tra item toàn cục (`CartService.java:65-89`).
4. Món chuyển `INACTIVE` vẫn xuất hiện trong giỏ để người dùng nhận biết; checkout sau đó từ chối món này (`CartService.java:109-115`; `FoodService.java:117-124,143-145`).

#### C. Checkout

1. Validate cặp `orderType`/field/payment: `DINE_IN` yêu cầu bàn, cấm thông tin giao hàng/COD; `DELIVERY` yêu cầu người nhận/phone/address, cấm bàn/CASH; `BANK_TRANSFER` dùng cho cả hai (`OrderService.java:151-177`; enum tại `OrderType.java:3`, `PaymentMethod.java:3`).
2. Lấy giỏ của customer từ server; giỏ thiếu/rỗng trả `EMPTY_CART` (`OrderService.java:35-38`; `CartService.java:93-98`).
3. Với từng món: tìm entity, yêu cầu `ACTIVE`, kiểm tra đủ stock, trừ stock và lưu snapshot `foodName/unitPrice/quantity` (`OrderService.java:54-64`; `FoodService.java:116-124`; `OrderItem.java:24-35`).
4. Lưu order `PENDING`, cascade order items rồi dọn giỏ; toàn bộ nằm dưới transaction của `OrderService.create` (`OrderService.java:33-68`; `Order.java:70-74`).
5. `totalAmount` không nhận từ client và không lưu riêng; response tính `unitPrice × quantity` từ snapshot (`OrderItemDto.java:7-11`; `OrderDto.java:18-26`).

#### D. Hủy và xử lý đơn

- Customer: chỉ hủy đơn của mình khi `PENDING` (`OrderService.java:96-102,180-182`).
- Employee: xác nhận PENDING; chuyển theo state machine; có thể hủy PENDING/CONFIRMED/PROCESSING (`OrderService.java:105-148`).
- Khi hủy, mọi item được hoàn kho kể cả món đã ngừng bán vì `releaseStock` không yêu cầu `ACTIVE` (`OrderService.java:134-137`; `FoodService.java:127-130`).
- Hủy/xác nhận/hoàn thành ghi timestamp UTC từ `Clock`, cắt tới microsecond (`OrderService.java:132-147,185-186`).

### 1.4. Business rules và bất biến

| Nhóm | Rule/bất biến thực tế | Trạng thái và bằng chứng |
|---|---|---|
| Account identity | Email được trim/lowercase; phone là `0` + 9 số hoặc E.164 đơn giản; password đăng ký 8–72 code point và tối đa 72 byte UTF-8, không trim. | **CONFIRMED** — `AuthValidation.java:9-28`; `RegisterService.java:22-29`. |
| Account creation | Public chỉ tạo `CUSTOMER/ACTIVE`; password lưu dạng BCrypt; email/phone unique. | **CONFIRMED** — `RegisterService.java:30-33`; `MySqlAccountRepository.java:33-48`; `BCryptPasswordHasher.java:7-19`. |
| Login | Sai email và sai password cùng `INVALID_CREDENTIALS`; tài khoản khác `ACTIVE` bị từ chối; JWT chứa user id và role. | **CONFIRMED** — `LoginService.java:24-39`; `LocalRsaTokenIssuer.java:29-37`. |
| Role separation | Role không kế thừa: Admin không thao tác cart/order; Employee không quản trị món; Customer không xử lý đơn. | **CONFIRMED** — `Role.java:3`; `SecurityConfiguration.java:28-38`. |
| Menu visibility | Public chỉ xem/tìm món `ACTIVE`; detail của món `INACTIVE` được che như không tồn tại. | **CONFIRMED** — `FoodService.java:28-51`; `FoodRepository.java:10-22`. |
| Food identity | Category phải tồn tại; name trim và unique trong thực đơn; create mặc định stock 0/status ACTIVE; delete là soft delete. | **CONFIRMED** — `FoodService.java:54-97,137-154`; unique DB tại `schema.sql:56`. |
| Cart ownership | Mỗi user có tối đa một cart; mọi thao tác lấy cart bằng user id từ JWT và tìm item trong cart đó. | **CONFIRMED** — `Cart.java:20-26`; `CartRepository.java:7-12`; `CartService.java:28-89`. |
| Cart quantity | Add/update yêu cầu quantity ≥ 1; add cùng món cộng số lượng và bắt overflow; không giữ stock ở cart. | **CONFIRMED** — `AddToCartRequest.java:7-14`; `UpdateCartItemRequest.java:6-9`; `CartService.java:41-59`. |
| Order input | Order type/payment/field phải đúng cặp; field bắt buộc được trim và không rỗng; giới hạn độ dài được validate trước trim. | **CONFIRMED** — `CreateOrderRequest.java:9-29`; `OrderService.java:151-177`. |
| Server authority | Customer id từ JWT; item/quantity từ cart; tên/giá/total từ server, không tin giá hoặc total phía client. | **CONFIRMED** — `OrderController.java:29-36`; `OrderService.java:35-68`; `OrderDto.java:18-26`. |
| Checkout tuần tự | Giỏ phải không rỗng; tất cả món phải tồn tại, ACTIVE, đủ stock; tạo order/item, trừ stock và clear cart cùng transaction. | **CONFIRMED** cho thực thi tuần tự — `OrderService.java:33-68`; `FoodService.java:116-124`. |
| Ownership đọc/hủy | Customer list chỉ đơn của mình; đọc/hủy detail khác chủ trả `FORBIDDEN`; Employee đọc được mọi đơn. | **CONFIRMED** — `OrderService.java:71-102,180-182`. |
| Cancellation | Hủy là terminal; customer chỉ từ PENDING, employee từ PENDING/CONFIRMED/PROCESSING; hoàn stock và ghi `cancelledAt`. | **CONFIRMED** cho thực thi tuần tự — `OrderService.java:120-148`. |
| Error contract | Business invalid/forbidden/not-found/conflict ánh xạ lần lượt 400/403/404/409; validation/type mismatch 400; data conflict 409. | **CONFIRMED** — `BusinessException.java:3-33`; `GlobalErrors.java:24-69`; Auth dùng `AuthErrors.java:17-36`. |

### 1.5. Vòng đời đơn hàng thực tế

```text
PENDING ──► CONFIRMED ──► PROCESSING ──► COMPLETED            (DINE_IN)
   │              │             │
   │              │             └────► SHIPPING ──► COMPLETED (DELIVERY)
   │              │
   └──────────────┴────────────► CANCELLED
```

- `PENDING → CANCELLED`: Customer hoặc Employee.
- `CONFIRMED/PROCESSING → CANCELLED`: chỉ Employee.
- `SHIPPING`, `COMPLETED`, `CANCELLED` không thể hủy; `COMPLETED` và `CANCELLED` là terminal.
- `DINE_IN` không thể `SHIPPING`; `DELIVERY` không thể đi thẳng `PROCESSING → COMPLETED`.
- `PENDING` không thể là trạng thái đích qua API update; yêu cầu đó trả `VALIDATION_ERROR` 400 (`OrderService.java:110-128`).

### 1.6. Điểm không khớp, chưa rõ và rủi ro cần xác minh

| Trạng thái | Phát hiện | Bằng chứng và tác động cần xác minh |
|---|---|---|
| **POTENTIAL ISSUE** | Đặc tả tự mâu thuẫn về ID path không dương. | Quy tắc chung nói ID path parse được nhưng không tồn tại, kể cả `≤ 0`, trả 404 (`docs/Project KTPM.md:25-26`); các bảng UC07/08/11/12/14–17 lại ghi “ID không hợp lệ” trả 400. Source không có `@Positive` cho path ID: chuỗi không parse được → 400 qua `GlobalErrors.java:43-46`, còn số `≤ 0` thường đi tới repository/item lookup → 404 (`FoodService.java:133-150`; `CartService.java:66-72,118-119`; `OrderService.java:90-114,189-190`). Cần chọn một contract và đồng bộ đặc tả/OpenAPI/test. |
| **POTENTIAL ISSUE** | Precondition UC01 “khách chưa đăng nhập” không được enforce. | Auth filter chain `permitAll` cho `/api/auth/register` (`SecurityConfiguration.java:19-23`); controller không kiểm tra principal (`AuthController.java:21-24`). Cần xác nhận đây chỉ là mô tả actor hay một business rule bắt buộc. |
| **POTENTIAL ISSUE** | Checkout đồng thời chưa bảo vệ bất biến không bán vượt kho/một giỏ chỉ tạo một đơn. | `FoodRepository`/`CartRepository` dùng read thông thường, entity không có version; `OrderService.java:35-68` và `FoodService.java:116-124` không khóa. Tài liệu cũng thừa nhận giới hạn này (`docs/architecture-single-restaurant.md:145-149`). Chưa tái hiện bằng test trong khảo sát này. |
| **POTENTIAL ISSUE** | Hai yêu cầu hủy đồng thời có thể cùng hoàn kho. | `OrderService.java:97-102,111-148` đọc status rồi release stock mà không khóa/version; rủi ro được ghi tại `docs/architecture-single-restaurant.md:146,176`. Chưa tái hiện runtime. |
| **POTENTIAL ISSUE** | Admin cập nhật stock đồng thời với checkout có thể ghi đè nhau. | Cả `FoodService.updateFood` và `reserveStock` sửa cùng entity bằng read-modify-write, không lock/version (`FoodService.java:75-92,116-124`); tài liệu ghi lost update tại `docs/architecture-single-restaurant.md:147`. |
| **POTENTIAL ISSUE** | Hai request đầu tiên thêm giỏ đồng thời có thể trả 409 thay vì hợp nhất. | Cả hai có thể không thấy cart rồi cùng tạo tại `CartService.java:35-38`; unique `user_id` nằm ở `Cart.java:20`/`schema.sql:66`. Tài liệu dự đoán một request nhận `CONFLICT` (`docs/architecture-single-restaurant.md:151`). |
| **PENDING** | Chính sách role không kế thừa cần Product Owner xác nhận. | Source và tài liệu cùng quy định Admin không xử lý đơn/cart, Employee không quản trị món (`SecurityConfiguration.java:28-38`; `docs/Project KTPM.md:22-23`), nhưng chưa có xác nhận nghiệp vụ độc lập ngoài repository. |
| **PENDING** | Tính nguyên tử rollback và toàn bộ error contract chưa được kiểm chứng runtime ở lần khảo sát này. | Annotation transaction và handler tồn tại, nhưng theo giới hạn nhiệm vụ không chạy test/DB (`OrderService.java:33-68,96-116`; `GlobalErrors.java:24-80`). |

Không coi các hành vi sau là mismatch vì đặc tả và source thống nhất: cart không kiểm tra tồn kho; update quantity không kiểm tra lại món; món inactive vẫn hiện trong cart; tổng tiền chỉ được tính khi đọc đơn; Employee có thể dùng cả endpoint confirm và endpoint status để chuyển `PENDING → CONFIRMED`.

### 1.7. Kết luận hạng mục nghiệp vụ

- **CONFIRMED** — đã lập bản đồ đầy đủ phạm vi, actor, 18 UC, các luồng Auth/Menu/Cart/Order, state machine, ownership, validation và error mapping.
- **CONFIRMED** — không thấy UC nào thiếu hoàn toàn ở mức source tĩnh; các khác biệt chính đã được cô lập ở Mục 1.6.
- **PENDING** — chưa có bằng chứng thực thi trong lượt khảo sát này; các bất biến đồng thời và chính sách role cần được xác minh ở hạng mục phù hợp sau.
- Đủ thông tin để chuyển sang **khảo sát kiến trúc**, vì ranh giới nghiệp vụ, luồng phụ thuộc và các điểm nóng đã rõ. Chưa đủ căn cứ để chọn giải pháp kiến trúc hoặc tuyên bố các `POTENTIAL ISSUE` là defect.

