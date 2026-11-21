# Full Regression Suite Summary

- Command: `.\mvnw.cmd test`
- Started: `2026-11-19T10:58:00.0187633+07:00`
- Finished: `2026-11-19T10:59:59.1336708+07:00`
- Maven total: `01:57 min`
- Exit code: `0`
- Result: **90 executed, 90 passed, 0 failures, 0 errors, 0 skipped**
- Surefire XML suite-time sum: `112.878 s`

| Suite | Tests | Passed | Failures | Errors | Skipped | XML seconds |
|---|---:|---:|---:|---:|---:|---:|
| `AdaptersTest` | 2 | 2 | 0 | 0 | 0 | 0.595 |
| `ArchitectureTest` | 5 | 5 | 0 | 0 | 0 | 2.057 |
| `AuthIntegrationTest` | 8 | 8 | 0 | 0 | 0 | 49.047 |
| `AuthWebAndServiceTest` | 8 | 8 | 0 | 0 | 0 | 6.631 |
| `DatabaseDesignTests` | 10 | 10 | 0 | 0 | 0 | 21.452 |
| `FoodCartSecurityTest` | 9 | 9 | 0 | 0 | 0 | 5.007 |
| `FoodServiceTest` | 11 | 11 | 0 | 0 | 0 | 0.549 |
| `LoginIpFilterTest` | 1 | 1 | 0 | 0 | 0 | 0.025 |
| `OrderIntegrationTest` | 14 | 14 | 0 | 0 | 0 | 25.817 |
| `OrderServiceTest` | 10 | 10 | 0 | 0 | 0 | 0.272 |
| `OrderWebTest` | 10 | 10 | 0 | 0 | 0 | 1.400 |
| `RateLimiterTest` | 2 | 2 | 0 | 0 | 0 | 0.026 |
| **Total** | **90** | **90** | **0** | **0** | **0** | **112.878** |

Không có failed test details vì không có failure/error. Raw log có expected exception/validation output từ negative-path tests và warning test-toolchain, nhưng Maven/Surefire đều báo pass. Không rerun full suite để che failure. Ba Testcontainers suites cũng pass trong lượt 32 riêng ngay trước đó; không quan sát flakiness qua hai lần thực thi liên tiếp của chúng, nhưng đây không phải chiến dịch stress/flakiness dài hạn.

