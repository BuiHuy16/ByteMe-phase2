# G2.4 configuration lock

## Source and platform

| Item | Locked value |
|---|---|
| Application source | `510f6415b6af535ceec77213f0b0c7d5082123f7`; executable diff exit `0` in final smoke |
| Branch at capture | `main` |
| Docker context / engine | `desktop-linux`; Docker Desktop 4.96.0, engine 29.9.1 |
| Docker VM capacity | 12 CPUs; 8,171,761,664 bytes RAM |
| Compose | 5.6.0 |

## Runtime controls

| Component | Locked value |
|---|---|
| Backend CPU/RAM | 2 CPUs; 1,342,177,280 bytes |
| Java | Temurin OpenJDK 21.0.13+9 LTS |
| JVM | G1; `-Xms512m -Xmx768m`; GC log to stdout |
| Hikari | maximum pool 10; minimum idle 10 |
| Tomcat | maximum threads 200; minimum spare 10 |
| MySQL | image `mysql@sha256:a81d043930e51745522bd5c430961cf8286f0a23f0a9a2a6e0108f7ea71b0902`; runtime 8.4.13 |
| MySQL CPU/RAM | 2 CPUs; 1,610,612,736 bytes |
| MySQL controls | REPEATABLE READ; autocommit 1; max connections 100; buffer pool 536,870,912; Performance Schema on |
| k6 | 0.55.2; image ID/digest `sha256:3cd0ae83b47a29b273193eb998740c3b0e219fc34cdf579b90a8fc1698f5c025` |
| k6 container | 1 CPU; 512 MiB per measured k6 process |

The backend image ID is captured per run because rebuilding can change OCI provenance metadata. Base-image resolution and the full build log are retained per run. Any setting change is a new configuration/treatment and cannot be merged into the same aggregate.

## Dataset/workload lock

- Standard profile: 10 categories, 5,000 read foods, 500 read orders, two items/order, 20 dedicated write actors/foods, four contention actors, write stock 1,000,000 and shared stock 10.
- Smoke profile used for validation: 3 categories, 60 read foods, 20 read orders, two items/order, two write actors and four contention actors.
- Final smoke initial/reset checksum: `1563f0bc27189c805d600347a497830593289542cfc3543d3b73d29117961e50`.
- Benchmark Compose SHA-256 at smoke validation: `d5841d80e0776b4eb6a07a26ed0095dce6940e04e2d12ebcaa52c64b43c99e60`.
- W1 standard: food list 10 RPS, food search 5 RPS, order list 5 RPS, page size 20, 180 s.
- W2 standard: 10 constant VUs, isolated actor/food pairs, 180 s.
- W3 standard: 15 barrier rounds/scenario, reported separately from latency/throughput.
- Warm-up: 60 s low rate, discarded. Cool-down: 30 s. Reset/checksum between workloads.
- Repetitions: minimum 3, target 5 independent runs; report each run and median/min/max/CV across comparable valid runs.

The definitive source hashes are in `benchmark-source-SHA256SUMS.txt`. Official G2.5 must copy those hashes into each run and refuse to aggregate mismatches.
