# ByteMe Phase 2 — Requirements and Baseline

Ngày rà soát: 2026-11-17. Tài liệu này chỉ bao phủ Giai đoạn 0; chưa đánh giá sâu API, database, nghiệp vụ, security hay lựa chọn kiến trúc cải tiến.

Quy ước trạng thái:

- **CONFIRMED**: có bằng chứng trực tiếp trong repository ở mức đã nêu.
- **PENDING**: chưa đủ bằng chứng hoặc chưa tái chạy để xác minh.
- **DECISION**: cần hai thành viên thống nhất trước khi tiếp tục.

## 1. Project Overview

| Hạng mục | Trạng thái | Kết quả và bằng chứng |
|---|---|---|
| Sản phẩm | **CONFIRMED** | Backend REST/JSON đặt món cho **một nhà hàng**, hỗ trợ `DINE_IN` và `DELIVERY` (`README.md`, `docs/Project KTPM.md:1-5`). |
| Phạm vi nghiệp vụ | **CONFIRMED** | 18 use case UC01–UC18; vai trò `CUSTOMER`, `EMPLOYEE`, `ADMIN`; thực đơn, giỏ hàng, đặt/hủy/xử lý đơn (`docs/Project KTPM.md`). |
| Ngoài phạm vi hiện tại | **CONFIRMED** | Không chọn nhiều nhà hàng, không đặt/quản lý bàn, không khách vãng lai, chưa tích hợp cổng thanh toán (`docs/Project KTPM.md:3-5,11-13`). |
| Mục tiêu Phase 2 | **CONFIRMED** | Cải tiến thuộc tính chất lượng dựa trên Phase 1 và đánh giá trước/sau trên cùng cấu hình (`docs/2026.md:2,31-35`). |
| Nguồn lực | **CONFIRMED** | Nhóm 2 người, thời gian 3–4 tuần theo bối cảnh dự án được giao. |
| Giới hạn xác minh | **CONFIRMED** | Chỉ đọc source/config/tài liệu và Git metadata; không build, chạy test, benchmark, migration hay deploy. Các kết luận runtime vẫn là **PENDING**. |

## 2. Assignment Requirements

`docs/2026.md` là nguồn ưu tiên cao nhất. Cột trạng thái chỉ là xác minh sơ bộ, không thay cho kiểm thử Giai đoạn 1.

### Phase 1

| ID | Yêu cầu trích xuất từ `docs/2026.md` | Tiêu chí kiểm chứng | Trạng thái sơ bộ |
|---|---|---|---|
| P1-01 | Chọn một nghiệp vụ và xây dựng dịch vụ backend. | Có phạm vi nghiệp vụ, entry point và API backend. | **CONFIRMED** — `src/main/java/org/example/Application.java`, bốn controller và đặc tả UC01–UC18. |
| P1-02 | REST API giao tiếp qua JSON. | Controller HTTP và hợp đồng JSON. | **CONFIRMED** — `src/main/java/org/example/controller/`, `src/main/resources/static/openapi.yaml`. |
| P1-03 | Có tối thiểu endpoint POST, GET, DELETE. | Mỗi method xuất hiện trong API/source. | **CONFIRMED** — `AuthController`, `FoodController`, `CartController`, `OrderController` có các mapping tương ứng. |
| P1-04 | Có tài liệu OpenAPI/Swagger. | Có đặc tả và cấu hình phục vụ tài liệu. | **CONFIRMED** — `openapi.yaml`; `application.yml:34-38`; dependency springdoc trong `pom.xml`. |
| P1-05 | Phân tầng API → nghiệp vụ → dữ liệu; tầng nghiệp vụ không import web framework hay thư viện DB. | Package và dependency rule thể hiện ranh giới này. | **CONFIRMED** ở mức tĩnh — `controller/`, `service/`, `repository/`; rule ArchUnit tại `src/test/java/org/example/ArchitectureTest.java:18-23`. Chưa chạy test. |
| P1-06 | Truy cập dữ liệu qua Repository/DAL, dùng ORM hoặc data mapper. | Service đi qua repository; có ORM/data mapper. | **CONFIRMED** — các interface trong `repository/` kế thừa `JpaRepository`; Spring Data JPA trong `pom.xml`. |
| P1-07 | Hỗ trợ đăng nhập. | Có endpoint và luồng cấp thông tin xác thực. | **CONFIRMED** ở mức tĩnh — `AuthController.java:27`, `LoginService.java`, `LocalRsaTokenIssuer.java`. |
| P1-08 | Ít nhất một GET và một POST cần xác thực. | Security policy bảo vệ cả hai method. | **CONFIRMED** — `GET /api/cart` và `POST /api/orders` được giới hạn trong `SecurityConfiguration.java:32-34`. |
| P1-09 | Xác thực qua middleware/filter/interceptor, không lặp tại endpoint. | Có filter chain chung. | **CONFIRMED** — `SecurityConfiguration.java:19-43`, OAuth2 resource server và `LoginIpFilter`. |
| P1-10 | Ngôn ngữ không cố định. | Nhóm chọn và khai báo một stack hợp lệ. | **CONFIRMED** — Java 21 (`pom.xml:17`, `Dockerfile:1,9`). |
| P1-11 | Hỗ trợ đóng gói Docker. | Có recipe build/run container. | **CONFIRMED** ở mức artifact — `Dockerfile`, `compose.yaml`; chưa build/smoke-test. |
| P1-12 | GitHub công khai, commit cẩn thận; README mô tả kiến trúc và đặc tả. | Truy cập công khai được remote; lịch sử phù hợp; README đủ nội dung. | **PENDING** — có remote GitHub `origin` và `README.md`, nhưng chưa xác minh truy cập công khai hay đánh giá độc lập chất lượng lịch sử commit. |
| P1-13 | Chỉ chức năng cơ bản, không cần tối ưu. | Tài liệu nêu rõ giới hạn Phase 1. | **CONFIRMED** — `docs/database-design.md:110-117` dành index/cache/locking/version cho giai đoạn sau. |
| P1-14 | Kiểm thử tải trên Kaggle CPU. | Có run có nguồn gốc xác định, cấu hình và kết quả lưu được. | **PENDING** — có report/k6 summary/ảnh trong `kaggle/results/phase1-baseline/`, nhưng commit được báo cáo không tồn tại trong clone và thiếu artifact thô; xem Mục 4. |

### Phase 2 (`docs/2026.md` gọi là “Gợi ý Pha 2”)

| ID | Yêu cầu/gợi ý trích xuất | Tiêu chí kiểm chứng | Trạng thái sơ bộ |
|---|---|---|---|
| P2-01 | Dựa vào đánh giá hệ thống hiện có hoặc đặc tả bài toán để đề xuất kiến trúc phù hợp. | Có quality-attribute evidence, phương án và lập luận truy vết được. | **PENDING** — thuộc Giai đoạn 1 trở đi. |
| P2-02 | Đánh giá trước và sau cải tiến, chỉ rõ lý do cải tiến. | Baseline và result sau cải tiến dùng cùng protocol; liên kết thay đổi → lý do → số liệu. | **PENDING** — mới có baseline ứng viên, chưa đủ provenance và chưa có after result. |
| P2-03 | Chỉ đánh giá trên một cấu hình phần cứng; nên dùng Kaggle CPU để cố định. | Cùng loại session/hardware, tool versions, data, workload và cách đo được ghi nhận. | **DECISION** — ưu tiên Kaggle CPU đã rõ; nhóm phải khóa protocol cụ thể. |
| P2-04 | Triển khai kiến trúc phù hợp với từng bài toán. | Phương án được chọn có căn cứ và được hiện thực/kiểm chứng. | **DECISION** — chưa chọn thuộc tính chất lượng hay phương án kiến trúc trong Giai đoạn 0. |

## 3. Scope & Constraints

### Phạm vi và công nghệ hiện hữu

- **CONFIRMED** — Java 21, Spring Boot 3.5.16, Spring Web, Spring Data JPA, Spring Security, JWT RS256, MySQL 8.4, Maven Wrapper 3.9.11 (`pom.xml`, `.mvn/wrapper/maven-wrapper.properties`, `compose.yaml:3`).
- **CONFIRMED** — package-by-layer hiện hữu: `controller`, `service`, `repository`, `entity`, `dto`, `config`, `platform`, `common`, `shared` (`src/main/java/org/example/`).
- **CONFIRMED** — test source có unit/web/integration/database/architecture test, Testcontainers và ArchUnit (`src/test/`, `pom.xml`). Việc các test đang pass là **PENDING** vì Giai đoạn 0 không chạy test.
- **CONFIRMED** — schema/seed do repository quản lý tại `src/main/resources/db/`; Hibernate `ddl-auto: none`, timezone JDBC/DB là UTC (`application.yml:10-23`).
- **PENDING** — các mục SEC-01…SEC-05 trong `docs/security-report.md` vẫn chờ xác minh/xử lý; không kết luận sâu trong Giai đoạn 0.

### Ràng buộc thực hiện

- Giữ quy mô phù hợp 2 người/3–4 tuần; chưa mở rộng nghiệp vụ ngoài UC01–UC18.
- Không chọn giải pháp Phase 2 chỉ vì đã được gợi ý trong tài liệu cũ; phải xác nhận vấn đề và thuộc tính chất lượng ở Giai đoạn 1.
- Không dùng kết quả giữa hai cấu hình phần cứng, dataset, schema, workload hoặc tool version khác nhau để tuyên bố cải tiến.

### Điều kiện tái lập môi trường

| Điều kiện | Trạng thái | Bằng chứng/việc còn thiếu |
|---|---|---|
| Source bất biến | **PENDING** | Cần full commit SHA có thể resolve, tag baseline và working tree sạch. Baseline report đang trỏ tới SHA không có trong clone. |
| Build toolchain | **CONFIRMED** một phần | Java 21 và Maven 3.9.11 đã khai báo. Image `eclipse-temurin:21-jdk/jre` chưa pin digest, nên exact JDK image còn **PENDING**. |
| Database | **CONFIRMED** một phần | Compose dùng `mysql:8.4`, schema và seed có sẵn. Cần pin image digest/patch version và quy trình reset volume trước mỗi run. |
| Cấu hình ứng dụng | **CONFIRMED** | `DB_URL`, `DB_USERNAME`, `DB_PASSWORD`, port và JWT key paths nằm trong `application.yml`, `compose.yaml`, `.env.example`. |
| Khóa JWT | **CONFIRMED** ở mức quy trình | Tạo bằng Python 3 + `cryptography==50.0.2` theo `README.md`; script là `scripts/generate-keys.py` và `scripts/prepare-docker-keys.py`. Không lưu/so sánh private key giữa các run. |
| Dataset benchmark | **PENDING** | Cần JAR + `schema.sql` + `seed.sql` cùng commit và SHA-256; `kaggle/dataset/` bị gitignore theo thiết kế. |
| Kaggle runtime | **PENDING** | Notebook cài Java/MySQL/k6 từ apt mà chưa pin version; cần lưu output phiên bản, CPU/RAM/OS, notebook version và dataset version của từng run. |
| Evidence | **PENDING** | Cần giữ k6 summary/raw CSV, server/resource log, notebook output và manifest. Baseline hiện thiếu raw CSV và `server.log`. |

## 4. Phase 1 Baseline

### Git snapshot khi bắt đầu Giai đoạn 0

| Thuộc tính | Trạng thái xác minh |
|---|---|
| Current branch | **CONFIRMED** — `main`. |
| HEAD | **CONFIRMED** — `510f6415b6af535ceec77213f0b0c7d5082123f7`, commit ngày `2026-11-06T23:38:44+07:00`. |
| Working tree | **CONFIRMED** — sạch trước khi tạo tài liệu này. Sau Giai đoạn 0 chỉ file này là thay đổi được phép. |
| Branch refs | **CONFIRMED** — local `main`, `master`, `phase1-baseline` và `origin/master` cùng trỏ tới `510f641…`. |
| Tags | **CONFIRMED** — không có tag. `phase1-baseline` hiện là **branch**, không phải tag. |
| Remote | **CONFIRMED** — `origin = https://github.com/BuiHuy16/ByteMe-phase2.git`; khả năng truy cập công khai chưa được kiểm tra. |
| Repository depth | **CONFIRMED** — không phải shallow clone. |

### Baseline tải hiện có

- **CONFIRMED** — `kaggle/results/phase1-baseline/README.md` báo cáo run ngày 2026-10-26 trên Kaggle CPU, 4 vCPU/30 GB RAM, MySQL 8 cùng máy; workload tăng `50 → 200 → 500` VU và gọi 4 request mỗi vòng.
- **CONFIRMED** — artifact lưu trong Git gồm `README.md`, `k6-summary.txt`, `load_test_report.png`. Summary ghi 18.029 request, 0% lỗi, khoảng 99,48 req/s, median 1,15 s và p95 8,55 s.
- **PENDING** — report nói JAR build từ commit `ed8be73`, nhưng Git không resolve được object này trong non-shallow clone. Không thể chứng minh JAR/schema của run tương ứng source hiện tại.
- **PENDING** — report liệt kê `server.log`, nhưng file không tồn tại; `k6_results.csv` cũng không được lưu trong repository. p99 và diễn biến tài nguyên không thể tái tính độc lập từ artifact hiện có.
- **PENDING** — branch `phase1-baseline` hiện trỏ tới HEAD `510f641…`, không khớp SHA được ghi trong report.

### Đề xuất đóng băng Phase 1 (chưa thực hiện Git action)

1. **DECISION** — chọn một trong hai mốc: (a) khôi phục và xác minh đúng commit/dataset của run `ed8be73`; hoặc (b) lấy một commit hiện có, tái chạy baseline theo protocol đã khóa và coi run mới là baseline chính thức.
2. Chỉ sau khi xác minh, tạo annotated tag riêng (ví dụ `phase1-baseline-verified`) trên **full SHA**; không dùng branch cùng tên làm bằng chứng bất biến.
3. Lưu manifest gồm commit SHA, trạng thái clean, SHA-256 của JAR/schema/seed/notebook, dependency/runtime versions, Kaggle notebook/dataset version và cấu hình workload.
4. Bảo toàn đầy đủ output thô và log; mọi thay đổi Phase 2 phải bắt đầu sau mốc bất biến đó.

## 5. Evaluation Principles

1. **Cùng cấu hình:** ưu tiên Kaggle CPU, Accelerator `None`; ghi lại CPU model/count, RAM, OS và chạy before/after trên cấu hình tương đương. Không dùng mô tả “Kaggle CPU” đơn lẻ làm bằng chứng đủ.
2. **Cùng đầu vào:** cùng schema, seed, trạng thái DB ban đầu, tài khoản/token setup, workload, VU stages, thời lượng, think time và network placement. Reset DB trước mỗi run.
3. **Cùng toolchain:** pin/ghi Java, MySQL, k6, application flags (`-Xms2g -Xmx6g` nếu giữ), pool/thread settings và notebook revision.
4. **So sánh công bằng:** warm-up như nhau, chạy lặp nhiều lần, ghi thứ tự run và báo cáo median/độ biến thiên; không chọn một run thuận lợi duy nhất.
5. **Metric tối thiểu:** throughput, error/check rate, p50/p90/p95/p99/max latency và startup time; bổ sung CPU, RAM, GC, DB/pool/thread metrics để lý giải nguyên nhân thay vì chỉ quan sát từ k6.
6. **Truy vết:** mỗi cải tiến phải nối từ vấn đề/quality attribute → giả thuyết → thay đổi → metric/acceptance criterion → kết quả trước/sau. Kết quả không đạt cũng phải được giữ.
7. **Không đổi bài toán âm thầm:** nếu workload hiện tại (GET foods/search/cart và POST login) không đại diện thuộc tính chất lượng được chọn, nhóm phải quyết định và version hóa workload mới; khi đó phải đo lại cả before lẫn after bằng workload đó.

Các quyết định nhóm cần xác nhận:

- **DECISION** — baseline chính thức là run cũ sau khi khôi phục provenance hay một run tái lập từ commit hiện có.
- **DECISION** — full SHA/tag và quy tắc branch Phase 2 sau khi đóng băng.
- **DECISION** — quality attribute ưu tiên, workload đại diện và acceptance criteria; chưa quyết định giải pháp kiến trúc.
- **DECISION** — số lần lặp, warm-up, cách reset DB, metric tài nguyên và format manifest/artifact.
- **DECISION** — exact Kaggle/runtime versions và nơi lưu artifact lớn (Git, release hay Kaggle output có version).

## 6. Exit Criteria

### Checklist Giai đoạn 0

- [x] **CONFIRMED** — trích xuất đầy đủ yêu cầu/gợi ý Phase 1 và Phase 2 từ `docs/2026.md`.
- [x] **CONFIRMED** — lập bảng yêu cầu, tiêu chí kiểm chứng và trạng thái sơ bộ.
- [x] **CONFIRMED** — xác định phạm vi nghiệp vụ, công nghệ và ràng buộc.
- [x] **CONFIRMED** — ghi nhận branch, HEAD, working tree, refs, tags và remote.
- [x] **CONFIRMED** — xác định điều kiện tái lập local/Docker/Kaggle mà không chạy hệ thống.
- [x] **CONFIRMED** — thiết lập nguyên tắc benchmark trước/sau, ưu tiên Kaggle CPU.
- [x] **CONFIRMED** — ghi nhận vấn đề chưa xác minh và các quyết định cần nhóm thống nhất.
- [ ] **PENDING** — xác minh hoặc thay thế provenance của baseline `ed8be73` và bổ sung artifact thiếu.
- [ ] **DECISION** — nhóm duyệt baseline commit/tag và benchmark protocol.
- [ ] **PENDING** — tạo mốc Git bất biến; không thực hiện trong Giai đoạn 0 theo giới hạn nhiệm vụ.

**Kết luận exit gate:** hồ sơ phân tích Giai đoạn 0 đã hoàn thành, nhưng dự án **chưa sẵn sàng hoàn toàn để dùng baseline cho Giai đoạn 1/đề xuất cải tiến**. Có thể bắt đầu khảo sát sâu Giai đoạn 1, song không được đưa ra kết luận kiến trúc hoặc so sánh trước/sau cho tới khi ba mục cuối được xử lý.
