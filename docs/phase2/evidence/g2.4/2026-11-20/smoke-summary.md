# Final smoke summary

`smoke-attempt-6` ran from 2026-11-19 18:37:59Z to 18:39:59Z and completed with exit code 0. It validates orchestration, not performance.

| Check | Result |
|---|---|
| Dataset preparation | PASS; 8 users, 3 categories, 63 foods, 20 orders, 40 order items |
| W1 read paths | PASS; 6/6 k6 checks; HTTP failure rate 0 |
| W2 write flow | PASS; 8/8 k6 checks; HTTP failure rate 0 |
| W3 correctness harness | PASS as a harness; it preserved same-food/admin-stock violations and same-cart HTTP 500 evidence |
| CPU/RAM capture | PASS; 7 W1, 9 W2 and 13 W3 timestamped samples including header |
| DB/SQL capture | PASS; four snapshots with MySQL status and up to 200 normalized query digests |
| JVM/GC/config capture | PASS; Java/G1/heap plus Hikari/Tomcat controls captured |
| Reset | PASS; post-reset logical checksum exactly matched initial checksum |
| Cleanup | PASS; no project container/network/volume/listener/backend image remained |

The one-run aggregation files only exercise the aggregator. Their p50/p95/p99/RPS values are not a baseline, have no statistical power and must not appear in a Phase 2 performance claim.

Known limitation: current actuator exposure does not provide live Hikari gauges. The kit captures Hikari configuration, DB connections/threads/query digests, container resources and logs, but it must label pool saturation as unavailable rather than infer it. The local load generator also shares the Docker VM, so its container CPU/RAM is part of the run evidence.
