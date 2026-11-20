# Bộ công cụ benchmark có thể tái lập cho ByteMe Phase 2

Thư mục này chuẩn bị protocol before/after dùng chung. Thư mục **không** chứa kết quả chính thức. G2.5 phải chạy cùng workload đã commit và configuration đã khóa cho từng treatment SHA.

## Nền tảng

Nền tảng chính cho benchmark before/after chính thức theo yêu cầu của giảng viên là Kaggle CPU thông qua adapter user-space G2.4-K. Local Windows + Docker Desktop vẫn là nền tảng xác minh development/integration và giữ nguyên evidence chuẩn bị G2.4 đã PASS. Tuyệt đối không so sánh trực tiếp kết quả Local với Kaggle.

Các Kaggle session chỉ có thể so sánh khi CPU model, core/RAM quota, OS image, portable toolchain binaries chính xác, configuration, workload và dataset locks đã thu thập đều khớp nhau. Kaggle runtime validation vẫn PENDING cho đến khi một session thực tế tạo được evidence bundle PASS.

## Các file

- `compose.benchmark.yaml`: khóa runtime/resource chỉ dành cho benchmark, được xếp lớp trên baseline Compose file.
- `profiles.json`: cardinality xác định trước cho dataset smoke và standard.
- `prepare_dataset.py`: reset cô lập có kiểm tra an toàn, sinh fixture, logical checksums và file actor-token tạm thời.
- `workloads/w1_read.js`: đọc food list, food search và order list có xác thực với operation tags.
- `workloads/w2_write.js`: cart add/update, checkout và cancellation cô lập theo từng actor.
- `workloads/w3_contention.py`: các vòng correctness dựa trên barrier cho same-food checkout, same-cart checkout và admin-stock-vs-checkout.
- `tools/collect_environment.ps1`: manifest của source/toolchain/image/runtime configuration.
- `tools/collect_resources.ps1`: các sample Docker CPU/RAM có timestamp.
- `tools/collect_db_telemetry.ps1`: snapshot chỉ đọc của MySQL status và Performance Schema digest để tính delta before/after.
- `tools/new_manifest.ps1`: artifact manifest SHA-256.
- `tools/aggregate_runs.py`: tổng hợp median/min/max/CV cho các k6 summary có thể so sánh; từ chối run sai định dạng.
- `tools/run_smoke.ps1`: chỉ là smoke test chuẩn bị quy mô nhỏ.
- `kaggle/`: rootless Kaggle runtime adapter, configuration lock, bundle builder và manifest comparator.

## Các dataset profile

`smoke` chỉ dùng để xác minh bộ công cụ. `standard` là profile khởi đầu được đề xuất cho G2.5 và phải được đóng băng trước official run đầu tiên.

| Phân vùng | Smoke | Standard |
|---|---:|---:|
| Food cho search/menu | 60 | 5,000 |
| Order của read actor | 20 | 500 |
| Item trên mỗi read order | 2 | 2 |
| Write actor/food chuyên dụng | 2 | 20 |
| Contention actor | 4 | 4 |
| Số lượng shared-stock ban đầu | 10 | 10 |

Users, categories, foods, orders và order items được sinh lại từ profile. Logical checksums chủ động loại trừ password hashes, JWTs và generated timestamps. Actor tokens tạm thời nằm trong `.local/phase2-benchmark/` và tuyệt đối không được lưu vào archive.

## Protocol G2.5 dùng chung (không chạy trong G2.4/G2.4-K)

1. Tạo run ID mới, duy nhất và một runtime cô lập: user-space MySQL datadir trên Kaggle hoặc Compose project/volume chuyên dụng cho xác minh Local.
2. Build source SHA đã chọn và ghi lại JAR hash; khi dùng Local Docker, ghi thêm image/base-image IDs.
3. Chuẩn bị `standard`; lưu cardinality và logical checksums.
4. Kiểm tra readiness, sau đó warm-up 60 giây với rate thấp. Loại bỏ các metric warm-up.
5. Chạy W1 trong 180 giây bằng constant arrival rates: food list 10 RPS, search 5 RPS, order list 5 RPS. Khóa page size (đề xuất 20; thêm một diagnostic run riêng cho 50).
6. Reset và xác minh dataset.
7. Chạy W2 trong 180 giây với 10 constant VUs, không vượt quá 20 actor chuyên dụng.
8. Reset và xác minh dataset.
9. Chạy W3 riêng trong 15 correctness rounds/scenario; tuyệt đối không trộn kết quả vào throughput percentiles.
10. Cooldown 30 giây, thu logs/metrics, reset và xác minh lại, sau đó chỉ xóa processes/data/resources của run đó.
11. Lặp lại independent measurement run ít nhất 3 lần (mục tiêu 5), luân phiên thứ tự before/after khi khả thi. Run lỗi phải được giữ lại và phân loại, tuyệt đối không âm thầm rerun.

Với mỗi metric, báo cáo p50/p95/p99/RPS/error rate theo từng run, sau đó báo cáo median của các valid run cùng min/max và coefficient of variation. Không xem các threshold p95/p99 lịch sử là SLO đã được chấp nhận. Business 409, HTTP 500 và transport errors là các counter riêng.

Thu DB telemetry snapshot ngay trước và sau mỗi measured workload rồi so sánh `COUNT_STAR` theo digest; tuyệt đối không bật MySQL general logging trong lúc đo throughput. Hikari configuration được khóa, còn runtime pool gauges không khả dụng qua actuator exposure hiện tại và phải được báo cáo như một limitation thay vì suy diễn.

Aggregator yêu cầu các giá trị SHA-256 của frozen configuration và dataset trong mọi lần gọi. Xem xét manifest của từng candidate run trước khi truyền summary của run đó; tool chủ động không suy luận comparability từ tên file.

## Configuration lock

Xác minh Local sử dụng benchmark Compose override để khóa G1 heap, Hikari 10/10, Tomcat 200/10, MySQL isolation/max connections/buffer pool, CPU/memory limits, GC logging và image digests. Kaggle sử dụng `kaggle/configuration-lock.json`, phiên bản portable tool chính xác/binary hashes và hardware fingerprint. Mọi thay đổi configuration sau đó hoặc bị cấm, hoặc phải được khai báo là một treatment riêng.

## Smoke test

Từ PowerShell tại repository root:

```powershell
$env:BENCH_ACTOR_PASSWORD = '<ephemeral strong value>'
./benchmarks/phase2/tools/run_smoke.ps1 -EvidenceDir 'docs/phase2/evidence/g2.4/YYYY-MM-DD/smoke'
```

Script sử dụng project `byteme-g24-smoke`, các port 13308/18082, chỉ chạy một vài iteration/round, reset về initial checksum, ghi evidence rồi xóa project volume/containers/network/image cùng temporary secrets. Đây không phải official baseline benchmark.

## Bố cục artifact cho mỗi official run

```text
<run-id>/
  manifest/environment.json
  manifest/configuration-lock.md
  dataset/initial.json
  dataset/post-run.json
  workload/source-checksums.txt
  k6/raw.json
  k6/summary.json
  resources/docker-stats.tsv
  logs/backend.log
  logs/mysql.log
  database/status-before.txt
  database/status-after.txt
  consistency/result.json
  exit-codes/
  SHA256SUMS.txt
```

Tuyệt đối không lưu runtime env files, passwords, private keys, JWTs hoặc Authorization headers vào archive.
