# Docker Environment Recovery

Captured trước khi chạy test ngày 2026-11-19, UTC+07:00.

## Commands and result

| Check | Result | Exit |
|---|---|---:|
| `docker context show` | `desktop-linux` | 0 |
| `docker version` | Client/Server `29.9.1`, API `1.56`, linux/amd64 server | 0 |
| `docker info` | Server reachable; 12 CPUs; 8,171,769,856 bytes Docker memory; root `/var/lib/docker`; overlayfs | 0 |
| `docker ps` | Server reachable; existing shared containers listed below and left untouched | 0 |
| `docker system df` | Images 8.243 GB; containers 11.42 MB; volumes 2.364 GB; build cache 1.829 GB | 0 |

Daemon status: **RUNNING/USABLE**. Không đổi context, reset WSL, cài lại Docker hoặc cleanup image/container/volume.

## Capacity assessment

| Resource | Observed |
|---|---:|
| Host physical RAM | 16,869,146,624 bytes (~15.71 GiB) |
| Host free physical RAM trước run | 503,799,808 bytes (~0.47 GiB) |
| Docker VM memory limit | 8,171,769,856 bytes (~7.61 GiB) |
| Docker CPUs | 12 |
| Drive `D:` free trước run | 34,914,127,872 bytes (~32.51 GiB) |
| Existing running-container memory | ~0.57 GiB aggregate from `docker stats --no-stream` |

Host free RAM tại thời điểm capture thấp, nhưng Docker VM có 7.61 GiB và disk có 32.51 GiB trống. Điều kiện thực tế được xác nhận bằng hai lượt chạy thành công liên tiếp có MySQL Testcontainers; không xảy ra OOM hoặc disk-capacity failure.

## Existing shared containers

`docker ps` trước run có Mailpit, Busbooking backend/PostgreSQL và Learncloud PostgreSQL. Chúng không được stop/restart/remove và không được dùng làm database test.

## Testcontainers image and isolation

- Testcontainers `1.21.4`; Ryuk `0.12.0`.
- Requested image: `mysql:8.4`.
- Resolved image/repository digest: `sha256:a81d043930e51745522bd5c430961cf8286f0a23f0a9a2a6e0108f7ea71b0902`.
- Runtime database version reported by Flyway: MySQL `8.4.13`.
- Platform: `linux/amd64`; local image size 1,102,649,117 bytes.
- Sau integration run và full run, `docker ps -a --filter label=org.testcontainers=true` trả rỗng: không còn container Testcontainers tạm.

