# ByteMe G2.4-K — Thích ứng cho Kaggle CPU

Adapter này giữ nguyên semantics của workload và dataset G2.4, đồng thời thay cách thực thi phụ thuộc Docker bằng các user-space process chạy trên loopback. Adapter không thay đổi application source, schema, seed hoặc notebook upstream lịch sử.

## Trạng thái

Notebook và các script đã được static validation trên Local. Môi trường chuẩn bị không có Kaggle credentials/runtime, vì vậy **Kaggle runtime validation vẫn PENDING**. Không được báo cáo smoke PASS cho đến khi `smoke-result.json` từ một Kaggle session thực tế ghi nhận `PASS`.

## Input

1. Sau official regression gate, build và package trực tiếp từ executable tree đã được xác minh:

   ```powershell
   ./benchmarks/phase2/kaggle/prepare_bundle.ps1 -ExpectedApplicationSha 510f6415b6af535ceec77213f0b0c7d5082123f7
   ```

   Builder từ chối executable drift ở staged, unstaged hoặc untracked, chạy Maven Wrapper `clean package`, đồng thời ghi lại source/tree identity, Java/Maven output, build command/exit và JAR SHA-256. Đối với treatment Pha 2 trong tương lai, hãy truyền application SHA đã được review; benchmark workload vẫn được hash độc lập.

2. Thêm các archive portable Linux x86_64 chính xác cho Java 21.0.13, MySQL 8.4.13 và k6 0.55.2 vào một private Kaggle Dataset. Adapter chỉ chấp nhận system binary khi phiên bản được báo cáo chứa đúng locked value. Adapter không bao giờ âm thầm thay thế bằng phiên bản khác.
3. Upload `kaggle/script/byteme_phase2_g24k.ipynb`; chọn Accelerator `None`; attach bundle/toolchain datasets. Có thể tắt Internet khi mọi archive đã được attach.

MySQL chạy từ generic binary distribution trong `/kaggle/working`, bind vào `127.0.0.1:13309`; không yêu cầu Docker hoặc quyền root/apt. Nếu portable binary thiếu shared library, run sẽ fail closed và ghi lại blocker.

## Các giai đoạn của notebook

Notebook thu thập CPU model, core count, RAM quota chính xác, OS/kernel và capabilities; xác minh mọi bundle file; resolve phiên bản tool chính xác; khởi tạo MySQL cô lập; khởi động baseline JAR với configuration lock; chuẩn bị smoke fixtures; thực thi W1/W2/W3; thu k6 raw data, process/system resources, JVM/GC, DB status/query digests và final invariants; reset về initial logical checksum; xóa runtime secrets; tạo `SHA256SUMS.txt` và evidence ZIP.

Initial fixture validation yêu cầu exact initial order/item counts và cart rỗng. Post-workload validation cho phép các canceled order và empty cart row hợp lệ, nhưng vẫn yêu cầu read fixtures bất biến, chính xác user/category/food cardinality, khôi phục shared-stock, quantity dương/stock không âm và không có orphan order/cart items. Sau đó, reset phải vượt qua initial rules và tái tạo đúng original logical checksum.

Exit code k6 bằng 0 là chưa đủ: runner parse W1/W2 summaries và assert chính xác smoke check/request counts, không có HTTP/workload/unexpected/server errors, raw output không rỗng và có resource samples cho backend, MySQL cùng driver. Các W3 baseline violation và HTTP 500 đã ghi nhận vẫn là defect evidence; thiếu rounds/responses/final state là harness failure.

Profile `standard` vẫn gồm 5.000 read foods, 500 orders, 20 write actors và bốn contention actors. G2.4-K chỉ chạy `smoke`; thực thi standard thuộc G2.5.

## Nhóm so sánh before/after

Chạy `compare_manifests.py` trên các file `manifest/run-manifest.json` thu được. Tool từ chối cgroup CPU quota, effective cpuset, memory limit, resolved limits, kernel/runtime-image identity, CPU model, visible cores/RAM, OS image, phiên bản Java/MySQL/k6 hoặc binary hashes, configuration/workload hashes hay dataset checksum bị thiếu hoặc khác nhau. Application SHA được báo cáo như treatment pair và được kỳ vọng khác nhau giữa before/after. Tuyệt đối không gộp các session chỉ vì cả hai đều mang nhãn “Kaggle CPU”.

Các parameter đo chính thức vẫn là warm-up 60 giây, W1/W2 180 giây, cooldown 30 giây, W1 arrival rates 10/5/5 RPS, W2 10 VUs, W3 15 rounds, tối thiểu ba và mục tiêu năm independent run. Notebook smoke chỉ sử dụng smoke profile và hai W3 rounds.

## Các giới hạn đã biết

- Live Hikari gauges vẫn chưa khả dụng; Hikari configuration và MySQL connection behavior được thu thập.
- CPU quota/model có thể thay đổi giữa các Kaggle session; manifest phải khớp trước khi tổng hợp.
- Kaggle session lifetime và attached-dataset storage là các ràng buộc bên ngoài. Hãy tải evidence ZIP trước khi session kết thúc.
- Adapter không sử dụng moving apt packages, workload 50→200→500 VU hoặc unverified thresholds của notebook lịch sử.
- Cleanup, secret scan, manifest/checksum và evidence packaging là một phần của smoke success. Cleanup failure buộc trạng thái `FAIL`; runner vẫn tạo failure evidence ZIP bất cứ khi nào filesystem access cho phép.
