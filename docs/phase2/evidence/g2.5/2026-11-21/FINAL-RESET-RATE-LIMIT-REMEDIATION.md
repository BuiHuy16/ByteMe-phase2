# G2.5 Final Reset Rate-limit Remediation

Ngày kiểm tra: 2026-11-21. Application baseline giữ nguyên `510f6415b6af535ceec77213f0b0c7d5082123f7`.

## Root cause

Standard profile có 26 actor: admin, read actor, 20 write actors và 4 contention actors. Implementation cũ gọi `/api/auth/token` cho cả 26 actor ở mỗi lần initial prepare, reset sau W1, reset sau W2 và final reset. Rate limiter Pha 1 áp dụng đồng thời bucket theo normalized email (10 request) và remote IP (100 request) trong fixed window 900 giây. Ba lần đầu dùng 78 IP requests. Ở final reset, admin/read/20 write actors đưa tổng lên 100; `c1a` là request thứ 101 nên nhận `429 LOGIN_RATE_LIMITED`. W3 không login mà dùng token trong runtime actor fixture.

## Remediation

Initial prepare vẫn đăng ký và login đúng một lần cho mỗi actor. Các reset vẫn truncate/rebuild toàn bộ fixture và đăng ký lại user, nhưng tái sử dụng token ban đầu trong cùng backend lifecycle. Harness kiểm tra label, ID và role sau khi tái tạo, rồi xác minh từng token qua endpoint được bảo vệ: customer token phải nhận HTTP 200 từ `/api/cart`, admin token phải được authenticate và nhận HTTP 403 do role tại `/api/orders`. Bất kỳ 401, status/role mismatch hoặc token thiếu đều fail-closed; không retry, sleep hay fallback sang login.

Mỗi prepare manifest ghi `preparation_authentication`. Official validator yêu cầu initial có 26 login và ba reset có 0 login, 26 reused token cùng 26 live validations. Logical checksum, dataset cardinality, workload và configuration lock không thay đổi. BEFORE và AFTER phải dùng cùng bundle/harness này.

## Verification

- Windows Python suite: 103 tests, 99 pass, 4 Linux-only skip, 0 fail/error.
- WSL Linux Python suite: 103 pass, 0 fail/error/skip.
- Pha 1 `RateLimiterTest` và `LoginIpFilterTest`: 3/3 pass trên implementation thật.
- Repeated-reset harness test: initial + reset W1 + reset W2 + final reset; tổng login giữ ở 26, 104 registrations, 78 live reused-token validations.
- 429 test: fail ngay, không retry.
- Invalid reused token: 401 làm reset fail, không login fallback.
- Official reset checksum validation: cả ba reset phải khớp initial; một checksum khác bị từ chối.
- `git diff --check`: pass. Executable application tree so với baseline: không đổi.
- Full backend/MySQL integration local chưa chạy: Docker daemon không hoạt động; MySQL WSL hiện có yêu cầu credential không được cung cấp. Không thay đổi môi trường để vượt giới hạn này.

## Artifact

- Bundle: `kaggle/dataset-g25-finalreset-20261121/`
- ZIP: `kaggle/byteme-g25-finalreset-20261121.zip`
- ZIP SHA-256: `93d5d4908d04a4082d08e6d70b6bd1fa42088c7ddd8c83ec3e52c38e42edcbd0`
- JAR SHA-256: `f802904a9a47cc14e8745dd7c39a1fb24b6219ef8be60be3805be4cf9af8cd98`
- ZIP có 22 entries, POSIX paths, không outer directory; manifest hashes và provenance đều pass.

Trạng thái: **LOCAL READY**. Kaggle official vẫn PENDING cho đến khi Run 01 được chạy lại bằng bundle mới.
