# G2.4-K Kaggle Runtime Acceptance — 21/11/2026

## Quyết định

**G2.4-K ACCEPTED.** Kaggle CPU smoke thực tế hoàn tất với `status = PASS`.
Evidence có integrity đầy đủ, các kết quả workload và database nhất quán với
PASS, cleanup hoàn tất và không phát hiện secret. Đây là nghiệm thu smoke của
adapter G2.4-K; không phải kết quả benchmark chính thức G2.5.

G2.5 **đủ điều kiện bắt đầu**. G2.5 phải tạo các run `standard` mới theo protocol
official và chỉ so sánh các run có hardware/configuration/toolchain/workload/
dataset locks tương thích. Không dùng số liệu smoke này làm baseline hiệu năng.

## Evidence được nghiệm thu

- File lưu cục bộ: `g24k-smoke-PASS-evidence.zip`.
- SHA-256 ZIP: `8e836ee04d0cd36cdab1b984c38bed369c584086d8f55eb84eda4178af65cdd6`.
- ZIP integrity: PASS; 42 entries, không có entry hỏng.
- `SHA256SUMS.txt`: PASS; 41/41 file evidence được liệt kê và khớp hash,
  không có file thiếu hoặc file evidence ngoài danh sách.
- File đã được đổi tên sau khi tải xuống. `smoke-result.json` ghi đường dẫn gốc
  `/kaggle/working/byteme-g24k/g24k-smoke-20261121T052932Z-evidence.zip` và
  `manifest/run-manifest.json` ghi `run_id = g24k-smoke-20261121T052932Z`;
  vì vậy nội dung xác nhận đúng ZIP được yêu cầu.
- Thời gian: 05:29:32–05:31:46 UTC ngày 21/11/2026
  (12:29:32–12:31:46 Asia/Saigon).

## Source, artifact và configuration lock

- Protocol/application baseline SHA:
  `510f6415b6af535ceec77213f0b0c7d5082123f7`.
- Repository SHA chứa adapter/evidence logic:
  `72dd551970df4c04c77aeeabd8a046844ae74f19`.
- Application JAR SHA-256:
  `eed3d70045a6884f36f1fc398ccc1de6f6fc8c661f170df08905c0bf76195311`.
- Configuration SHA-256:
  `fef0fcf03b4dadd66a7b1f8619da9263e1500bf8b903f760aad3abd541b89620`;
  khớp `benchmarks/phase2/kaggle/configuration-lock.json` tại thời điểm nghiệm thu.
- Workload source SHA-256:
  `5ee9cee0808de431928dc10011f0042611e1358504dd994af9535ab99cfc7f3e`.
- JVM: `-Xms512m -Xmx768m -XX:+UseG1GC`; Hikari min/max `10/10`;
  Tomcat min/max `10/200`.
- MySQL: `REPEATABLE-READ`, max connections `100`, InnoDB buffer pool
  `536870912` bytes. Smoke lock yêu cầu W1 6 checks/6 requests, W2 8/8 và
  W3 2 vòng mỗi scenario.

## Kaggle runtime và toolchain

- Kaggle runtime: Ubuntu 24.04, kernel `6.18.55+`, Python 3.13.18,
  image identity SHA-256
  `73b7688c6b0298bb811a52b1b22d66eac3bb3fdc7f0da53b3ac4b46db031c2ec`.
- CPU: Intel Xeon 2.20 GHz; 4 logical cores; cgroup v2 quota 4.0 cores;
  effective cpuset `0-3`; quota evidence complete.
- RAM quan sát: `33658159104` bytes; cgroup limit `32212254720` bytes
  (30 GiB); resolved limit `32212254720` bytes.
- Java: Temurin OpenJDK 21.0.13+9; executable SHA-256
  `7afc28801f744050aeba646b20e7314265279f76f9d0273b21a2b66411e1bf6d`.
- MySQL Community Server 8.4.13; `mysqld` SHA-256
  `e48e2b508487a2e8db31d345385ab7c4d358c4b191fc456086e558a909813f31`.
- k6 0.55.2; executable SHA-256
  `df3ede493661504b11f5ae34fdb38f8517e511c35587d36e55ba7d45ce4dc2a1`.
- libaio package `0.3.113-6build1.1`, package/library hashes và SONAME khớp
  configuration lock. MySQL chạy bằng UID/GID 65534 (`nobody`) và báo ready
  trên port 13309; shutdown hoàn tất.

## Kết quả smoke

### W1 read

- 6/6 checks PASS, 6 HTTP requests, failure rate 0,
  application error rate 0, unexpected responses 0.
- 3 scenarios hoàn tất 6 iterations, không có iteration bị ngắt.
- k6 raw JSON, summary, console, validation và telemetry đều có mặt.

### W2 write

- 8/8 checks PASS, 8 HTTP requests, failure rate 0,
  write error rate 0, unexpected responses 0.
- 2 write-flow iterations hoàn tất, không có iteration bị ngắt.
- k6 raw JSON, summary, console, validation và telemetry đều có mặt.

### W3 concurrency

- Harness valid; đủ 3 scenarios × 2 vòng; response và final-state evidence đầy đủ;
  không có HTTP 5xx/server-error round.
- `same_food_checkout` và `same_cart_checkout`: không có consistency violation.
- `admin_stock_vs_checkout` vòng 2 ghi nhận
  `NON_SERIALIZABLE_FINAL_STOCK`: stock cuối 7, ngoài hai kết quả tuần tự hợp lệ
  17/20. Đây là **defect baseline được harness phát hiện**, không phải lỗi harness
  và không mâu thuẫn với smoke PASS.
- Method limit đã khai báo: client barrier không chứng minh database
  in-transaction barrier.

## Dataset, database và reset

- Initial fixture (`validation_phase = initial`) PASS mọi invariant:
  8 users, 3 categories, 63 foods, 0 carts/items, 20 orders, 40 order items.
- Post-workload (`validation_phase = post_workload`) PASS mọi consistency
  invariant: 2 carts, 22 orders, 42 order items; mutation phù hợp workload.
- Reset trở lại đúng initial counts và logical checksum:
  `1563f0bc27189c805d600347a497830593289542cfc3543d3b73d29117961e50`.
- `reset_matches_initial = true`.
- DB telemetry có đủ before-W1, after-W1, after-W2 và after-W3; mỗi file có
  capture timestamp, MySQL version/database, global status và Performance Schema
  query digest rows. GC log có 220 dòng cùng pause/heap evidence.

## Resource telemetry, lifecycle và cleanup

- W1/W2/W3 lần lượt có 12/12/6 sample rows, đủ labels
  `backend`, `mysql`, `driver`; CPU và RSS không thiếu.
- Linux từ chối đọc `/proc/240/io` của MySQL chạy khác UID. I/O được ghi `NA`
  cùng sidecar evidence 4/4/2 dòng cho W1/W2/W3; không ghi số 0 giả. Đây là
  hạn chế I/O telemetry đã khai báo, không làm mất CPU/RSS bắt buộc.
- Backend còn alive sau W3 (`PID 287`, exit code null), rồi graceful shutdown
  trong cleanup. MySQL shutdown hoàn tất. Các deadlock SQL trong W3 được chuyển
  thành HTTP 409 `CONCURRENT_UPDATE`, không thành server error.
- Cleanup PASS: backend stopped, MySQL stopped, runtime-secret directory removed,
  không có cleanup error.
- Secret scan của runner: 0 violations. Kiểm tra độc lập 42 text evidence files:
  0 JWT, 0 private-key block và 0 password assignment match.

## Hạn chế còn lại và gate G2.5

- `official_benchmark = false`, profile là `smoke`; dataset standard 5.000 foods,
  500 orders, 20 write actors và duration chính thức chưa được chạy.
- Chỉ có một Kaggle session. Hardware equivalence giữa các session before/after
  chỉ được quyết định sau khi so sánh run manifests; không gộp session khác CPU,
  quota, image identity hoặc lock.
- MySQL per-process read/write bytes unavailable do procfs permissions; CPU/RSS,
  JVM/GC và DB telemetry vẫn đầy đủ. Không dùng I/O `NA` như 0 khi phân tích.
- W3 đã ghi nhận defect baseline và method limit nêu trên; G2.5 phải giữ nguyên
  workload/harness để so sánh treatment.
- Một số message tiếng Việt trong raw W3 evidence hiển thị mojibake; HTTP status,
  machine-readable code, state và invariants vẫn đọc và kiểm tra được.

G2.5 có thể bắt đầu từ official baseline runs với minimum 3, target 5 run theo
configuration lock. Mỗi run phải giữ raw evidence, reset checksum và chỉ được
đưa vào comparison group sau khi `compare_manifests.py` xác nhận tương thích.
