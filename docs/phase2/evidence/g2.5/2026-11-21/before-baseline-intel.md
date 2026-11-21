# G2.5 Official BEFORE Baseline — Intel Multi-run Aggregation

**Baseline status: `LOCKED`**

Selected group: `kaggle-intel-xeon`. Valid runs: **3**; minimum 3 met: **true**; target 5 met: **false**.

Percentiles are calculated per run and then summarized across runs. Request samples are not pooled.

## Run traceability

| Run ID | CPU | MemTotal bytes | Evidence SHA-256 | ZIP checksums |
|---|---|---:|---|---:|
| `g25-before-20261121T103301Z` | `Intel(R) Xeon(R) CPU @ 2.20GHz` | 33658155008 | `7a2eec7738c972f4fba2706be5daa4c49781a59d04e6670362d2558e455f6a17` | 62 verified |
| `g25-before-20261121T145826Z` | `Intel(R) Xeon(R) CPU @ 2.20GHz` | 33658159104 | `9379e5661e7fd292230f4abec109b8f29b5034fbb0c1e092b8f7e9d0b0a7a51f` | 62 verified |
| `g25-before-20261121T151926Z` | `Intel(R) Xeon(R) CPU @ 2.20GHz` | 33658155008 | `c2925ebc19f8d23dd242cdc12d8f2922631739dacf569b23b859ae1c9c0222cf` | 62 verified |

## Hardware, toolchain and benchmark locks

| Fingerprint | Locked value |
|---|---|
| CPU model | `Intel(R) Xeon(R) CPU @ 2.20GHz` |
| CPU quota | `400000 100000` |
| cpuset | `0-3` |
| cgroup memory limit | `32212254720` |
| MemTotal bytes (reference) | `33658155008` |
| OS / kernel | `ubuntu 24.04 / 6.18.55+` |
| runtime image identity | `73b7688c6b0298bb811a52b1b22d66eac3bb3fdc7f0da53b3ac4b46db031c2ec` |
| Java | `openjdk version "21.0.13" 2026-10-20 LTS` |
| MySQL | `8.4.13 for Linux on x86_64 (MySQL Community Server - GPL)` |
| k6 | `k6 v0.55.2 (commit/9b848870aa, go1.23.4, linux/amd64)` |
| application SHA | `510f6415b6af535ceec77213f0b0c7d5082123f7` |
| JAR SHA-256 | `f802904a9a47cc14e8745dd7c39a1fb24b6219ef8be60be3805be4cf9af8cd98` |
| configuration SHA-256 | `e257ab3d71b73377d40cc85612e10f5e999ce8b55b00b3adff6075489a5fa2e1` |
| workload SHA-256 | `c773850351f0cc5d337ba96a5fef5774a6871abf99aa1054a722ae528164397f` |
| dataset SHA-256 | `ce932b243cbfb16c34935ece3deb9f9e6479da34ab6828d93b2903f9538839b4` |

## Per-run W1/W2 metrics

| Run ID | Workload | Operation | Requests | RPS | P50 ms | P95 ms | P99 ms | Errors | Business rejections |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| `g25-before-20261121T103301Z` | W1 | `food_list` | 1801 | 10.004 | 34.146 | 45.269 | 51.439 | 0 | 0 |
| `g25-before-20261121T145826Z` | W1 | `food_list` | 1801 | 10.003 | 40.390 | 52.317 | 59.638 | 0 | 0 |
| `g25-before-20261121T151926Z` | W1 | `food_list` | 1800 | 9.999 | 38.400 | 50.726 | 57.820 | 0 | 0 |
| `g25-before-20261121T103301Z` | W1 | `food_search` | 901 | 5.005 | 23.803 | 29.631 | 33.900 | 0 | 0 |
| `g25-before-20261121T145826Z` | W1 | `food_search` | 901 | 5.004 | 26.023 | 32.098 | 40.423 | 0 | 0 |
| `g25-before-20261121T151926Z` | W1 | `food_search` | 901 | 5.005 | 25.150 | 31.121 | 38.731 | 0 | 0 |
| `g25-before-20261121T103301Z` | W1 | `order_list` | 900 | 4.999 | 16.734 | 25.028 | 35.182 | 0 | 0 |
| `g25-before-20261121T145826Z` | W1 | `order_list` | 901 | 5.004 | 19.041 | 28.398 | 33.971 | 0 | 0 |
| `g25-before-20261121T151926Z` | W1 | `order_list` | 901 | 5.005 | 17.975 | 27.032 | 32.126 | 0 | 0 |
| `g25-before-20261121T103301Z` | W2 | `cancel` | 20679 | 114.842 | 18.873 | 35.033 | 48.680 | 0 | 0 |
| `g25-before-20261121T145826Z` | W2 | `cancel` | 15607 | 86.658 | 25.568 | 43.400 | 58.234 | 0 | 0 |
| `g25-before-20261121T151926Z` | W2 | `cancel` | 17231 | 95.677 | 22.927 | 40.314 | 54.867 | 0 | 0 |
| `g25-before-20261121T103301Z` | W2 | `cart_add` | 20689 | 114.897 | 19.279 | 37.455 | 53.682 | 10 | 10 |
| `g25-before-20261121T145826Z` | W2 | `cart_add` | 15622 | 86.742 | 26.288 | 48.129 | 64.513 | 15 | 15 |
| `g25-before-20261121T151926Z` | W2 | `cart_add` | 17235 | 95.700 | 23.523 | 43.674 | 61.351 | 4 | 4 |
| `g25-before-20261121T103301Z` | W2 | `cart_update` | 20679 | 114.842 | 18.437 | 34.369 | 49.907 | 0 | 0 |
| `g25-before-20261121T145826Z` | W2 | `cart_update` | 15607 | 86.658 | 24.988 | 42.816 | 58.055 | 0 | 0 |
| `g25-before-20261121T151926Z` | W2 | `cart_update` | 17231 | 95.677 | 22.381 | 39.304 | 54.803 | 0 | 0 |
| `g25-before-20261121T103301Z` | W2 | `checkout` | 20679 | 114.842 | 21.061 | 41.996 | 60.579 | 0 | 0 |
| `g25-before-20261121T145826Z` | W2 | `checkout` | 15607 | 86.658 | 28.235 | 51.516 | 73.407 | 0 | 0 |
| `g25-before-20261121T151926Z` | W2 | `checkout` | 17231 | 95.677 | 25.485 | 47.810 | 69.858 | 0 | 0 |

## W1/W2 operation aggregates

| Workload | Operation | Metric | Median | Min | Max | CV |
|---|---|---|---:|---:|---:|---:|
| W1 | `food_list` | `requests` | 1801.000 | 1800.000 | 1801.000 | 0.0003 |
| W1 | `food_list` | `request_rate_rps` | 10.003 | 9.999 | 10.004 | 0.0002 |
| W1 | `food_list` | `latency_p50_ms` | 38.400 | 34.146 | 40.390 | 0.0692 |
| W1 | `food_list` | `latency_p95_ms` | 50.726 | 45.269 | 52.317 | 0.0611 |
| W1 | `food_list` | `latency_p99_ms` | 57.820 | 51.439 | 59.638 | 0.0624 |
| W1 | `food_list` | `errors` | 0.000 | 0.000 | 0.000 | NA |
| W1 | `food_list` | `error_rate` | 0.000 | 0.000 | 0.000 | NA |
| W1 | `food_list` | `business_rejections` | 0.000 | 0.000 | 0.000 | NA |
| W1 | `food_list` | `server_errors` | 0.000 | 0.000 | 0.000 | NA |
| W1 | `food_search` | `requests` | 901.000 | 901.000 | 901.000 | 0.0000 |
| W1 | `food_search` | `request_rate_rps` | 5.005 | 5.004 | 5.005 | 0.0001 |
| W1 | `food_search` | `latency_p50_ms` | 25.150 | 23.803 | 26.023 | 0.0365 |
| W1 | `food_search` | `latency_p95_ms` | 31.121 | 29.631 | 32.098 | 0.0328 |
| W1 | `food_search` | `latency_p99_ms` | 38.731 | 33.900 | 40.423 | 0.0733 |
| W1 | `food_search` | `errors` | 0.000 | 0.000 | 0.000 | NA |
| W1 | `food_search` | `error_rate` | 0.000 | 0.000 | 0.000 | NA |
| W1 | `food_search` | `business_rejections` | 0.000 | 0.000 | 0.000 | NA |
| W1 | `food_search` | `server_errors` | 0.000 | 0.000 | 0.000 | NA |
| W1 | `order_list` | `requests` | 901.000 | 900.000 | 901.000 | 0.0005 |
| W1 | `order_list` | `request_rate_rps` | 5.004 | 4.999 | 5.005 | 0.0005 |
| W1 | `order_list` | `latency_p50_ms` | 17.975 | 16.734 | 19.041 | 0.0526 |
| W1 | `order_list` | `latency_p95_ms` | 27.032 | 25.028 | 28.398 | 0.0516 |
| W1 | `order_list` | `latency_p99_ms` | 33.971 | 32.126 | 35.182 | 0.0372 |
| W1 | `order_list` | `errors` | 0.000 | 0.000 | 0.000 | NA |
| W1 | `order_list` | `error_rate` | 0.000 | 0.000 | 0.000 | NA |
| W1 | `order_list` | `business_rejections` | 0.000 | 0.000 | 0.000 | NA |
| W1 | `order_list` | `server_errors` | 0.000 | 0.000 | 0.000 | NA |
| W2 | `cancel` | `requests` | 17231.000 | 15607.000 | 20679.000 | 0.1185 |
| W2 | `cancel` | `request_rate_rps` | 95.677 | 86.658 | 114.842 | 0.1186 |
| W2 | `cancel` | `latency_p50_ms` | 22.927 | 18.873 | 25.568 | 0.1226 |
| W2 | `cancel` | `latency_p95_ms` | 40.314 | 35.033 | 43.400 | 0.0873 |
| W2 | `cancel` | `latency_p99_ms` | 54.867 | 48.680 | 58.234 | 0.0734 |
| W2 | `cancel` | `errors` | 0.000 | 0.000 | 0.000 | NA |
| W2 | `cancel` | `error_rate` | 0.000 | 0.000 | 0.000 | NA |
| W2 | `cancel` | `business_rejections` | 0.000 | 0.000 | 0.000 | NA |
| W2 | `cancel` | `server_errors` | 0.000 | 0.000 | 0.000 | NA |
| W2 | `cart_add` | `requests` | 17235.000 | 15622.000 | 20689.000 | 0.1184 |
| W2 | `cart_add` | `request_rate_rps` | 95.700 | 86.742 | 114.897 | 0.1185 |
| W2 | `cart_add` | `latency_p50_ms` | 23.523 | 19.279 | 26.288 | 0.1252 |
| W2 | `cart_add` | `latency_p95_ms` | 43.674 | 37.455 | 48.129 | 0.1016 |
| W2 | `cart_add` | `latency_p99_ms` | 61.351 | 53.682 | 64.513 | 0.0760 |
| W2 | `cart_add` | `errors` | 10.000 | 4.000 | 15.000 | 0.4652 |
| W2 | `cart_add` | `error_rate` | 0.000 | 0.000 | 0.001 | 0.5406 |
| W2 | `cart_add` | `business_rejections` | 10.000 | 4.000 | 15.000 | 0.4652 |
| W2 | `cart_add` | `server_errors` | 0.000 | 0.000 | 0.000 | NA |
| W2 | `cart_update` | `requests` | 17231.000 | 15607.000 | 20679.000 | 0.1185 |
| W2 | `cart_update` | `request_rate_rps` | 95.677 | 86.658 | 114.842 | 0.1186 |
| W2 | `cart_update` | `latency_p50_ms` | 22.381 | 18.437 | 24.988 | 0.1228 |
| W2 | `cart_update` | `latency_p95_ms` | 39.304 | 34.369 | 42.816 | 0.0892 |
| W2 | `cart_update` | `latency_p99_ms` | 54.803 | 49.907 | 58.055 | 0.0617 |
| W2 | `cart_update` | `errors` | 0.000 | 0.000 | 0.000 | NA |
| W2 | `cart_update` | `error_rate` | 0.000 | 0.000 | 0.000 | NA |
| W2 | `cart_update` | `business_rejections` | 0.000 | 0.000 | 0.000 | NA |
| W2 | `cart_update` | `server_errors` | 0.000 | 0.000 | 0.000 | NA |
| W2 | `checkout` | `requests` | 17231.000 | 15607.000 | 20679.000 | 0.1185 |
| W2 | `checkout` | `request_rate_rps` | 95.677 | 86.658 | 114.842 | 0.1186 |
| W2 | `checkout` | `latency_p50_ms` | 25.485 | 21.061 | 28.235 | 0.1186 |
| W2 | `checkout` | `latency_p95_ms` | 47.810 | 41.996 | 51.516 | 0.0832 |
| W2 | `checkout` | `latency_p99_ms` | 69.858 | 60.579 | 73.407 | 0.0796 |
| W2 | `checkout` | `errors` | 0.000 | 0.000 | 0.000 | NA |
| W2 | `checkout` | `error_rate` | 0.000 | 0.000 | 0.000 | NA |
| W2 | `checkout` | `business_rejections` | 0.000 | 0.000 | 0.000 | NA |
| W2 | `checkout` | `server_errors` | 0.000 | 0.000 | 0.000 | NA |

## W3 scenario aggregates

| Scenario | Rounds | Violations | Violation rate | Server-error rounds | Runs with violations | Runs with server errors |
|---|---:|---:|---:|---:|---:|---:|
| `admin_stock_vs_checkout` | 45 | 37 | 0.8222 | 0 | 3 | 0 |
| `same_cart_checkout` | 45 | 0 | 0.0000 | 1 | 0 | 1 |
| `same_food_checkout` | 45 | 0 | 0.0000 | 0 | 0 | 0 |

## W3 per-run findings

| Run ID | Scenario | Rounds | Invariant violations | Violation rate | Server-error rounds |
|---|---|---:|---:|---:|---:|
| `g25-before-20261121T103301Z` | `admin_stock_vs_checkout` | 15 | 12 | 0.8000 | 0 |
| `g25-before-20261121T145826Z` | `admin_stock_vs_checkout` | 15 | 12 | 0.8000 | 0 |
| `g25-before-20261121T151926Z` | `admin_stock_vs_checkout` | 15 | 13 | 0.8667 | 0 |
| `g25-before-20261121T103301Z` | `same_cart_checkout` | 15 | 0 | 0.0000 | 1 |
| `g25-before-20261121T145826Z` | `same_cart_checkout` | 15 | 0 | 0.0000 | 0 |
| `g25-before-20261121T151926Z` | `same_cart_checkout` | 15 | 0 | 0.0000 | 0 |
| `g25-before-20261121T103301Z` | `same_food_checkout` | 15 | 0 | 0.0000 | 0 |
| `g25-before-20261121T145826Z` | `same_food_checkout` | 15 | 0 | 0.0000 | 0 |
| `g25-before-20261121T151926Z` | `same_food_checkout` | 15 | 0 | 0.0000 | 0 |

## Telemetry coverage

CPU/RSS, JVM/GC and MySQL per-run values and across-run summaries are preserved in the JSON report. Missing telemetry remains `null` with availability counts; it is not represented as zero.

## Excluded runs

| Run ID | Evidence SHA-256 | Official evidence | Comparator mismatch |
|---|---|---|---|
| `g25-before-20261121T081712Z` | `f38404aa04d631a8312a0570cb1a9584288ecbf1f6a0e0c26130125c444ad38d` | `PASS` / `VALID_BASELINE_MEASUREMENT` | `hardware.cpu_model` |
| `g25-before-20261121T144102Z` | `ed49c58fe9585661d1187385550db18292d5f1e69363194dec9b043f177fad77` | `PASS` / `VALID_BASELINE_MEASUREMENT` | `hardware.cpu_model` |

## Baseline lock

The official BEFORE baseline is locked to Runs 02, 04 and 05 in the Intel Xeon comparison group. Runs 01 and 03 remain preserved AMD evidence and are not aggregated. AFTER must use an Intel-compatible manifest and pass the same comparator. The minimum run count is met; the five-run target is not met.
