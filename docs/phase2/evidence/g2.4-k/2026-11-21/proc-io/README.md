# G2.4-K proc I/O verification — 2026-11-21

Root cause: Kaggle từ chối đọc `/proc/<pid>/io` của MySQL chạy UID/GID 65534.
Sampler trước đây làm lỗi này lan ra bước khởi chạy workload. Bản sửa chỉ bắt
PermissionError của I/O; giữ việc đọc CPU/RSS và báo thiếu metrics bắt buộc.
TSV giữ các cột cũ, dùng `NA` cho I/O không đọc được; sidecar
`resources.unavailable.jsonl` ghi label/PID/lý do. Không thay quyền MySQL.

- Windows regression: 75 tests, 72 PASS, 3 SKIP, 0 FAIL/ERROR. Ba skip gồm
  hai Linux integration tests và một archive hardlink test phụ thuộc quyền Windows.
- WSL Ubuntu 22.04/Python 3.10.12: 6 PASS, gồm 2 integration tests procfs thật
  (cùng UID đọc I/O; nobody đọc procfs của process root và nhận PermissionError,
  CPU/RSS còn được ghi và sampler tiếp tục). Bốn tests còn lại dùng mocks.
- WSL có cảnh báo systemd user session root; process kiểm thử vẫn exit 0.
- LOCAL LINUX SMOKE: BLOCKED, chưa chạy startup/W1/W2/W3/reset/cleanup end-to-end.
- KAGGLE SMOKE: PENDING.

Môi trường quan sát: WSL2 Ubuntu-22.04 có sẵn; Docker client 29.9.1,
context desktop-linux, daemon không kết nối được. WSL thiếu Java/k6, mysqld
8.0.46-0ubuntu0.22.04.5. Windows Java 21.0.12 và MySQL 8.0 trên PATH,
không có k6. Thư mục D:\byteme-g24k-toolchain chỉ thấy gói libaio đã khóa.
Chưa đủ Java 21.0.13/MySQL 8.4.13/k6 0.55.2 để chạy smoke đúng lock.
Không cài toolchain, bật Docker hoặc sửa hệ thống để né điều kiện thiếu.

Specification hiện yêu cầu CPU/RAM samples cho backend/MySQL/driver;
read/write bytes được liệt kê trong telemetry dự kiến nhưng không có gate
bắt buộc khả dụng trong configuration lock. Bản sửa không đổi lock và không
coi I/O thiếu là đầy đủ. Không dùng NA như 0 hoặc so sánh I/O nếu thiếu evidence.

Pha 1 executable tree so với baseline 510f6415b6af535ceec77213f0b0c7d5082123f7
không đổi; git diff --check PASS. Xem logs kiểm thử và artifact-verification.json.
