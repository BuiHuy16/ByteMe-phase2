# Integration & Database Test Summary

- Command: `.\mvnw.cmd test "-Dtest=AuthIntegrationTest,OrderIntegrationTest,DatabaseDesignTests"`
- Started: `2026-11-19T10:53:34.5804318+07:00`
- Finished: `2026-11-19T10:57:12.7646419+07:00`
- Maven total: `03:36 min` (first run included pulling Ryuk and MySQL images)
- Exit code: `0`
- Result: **32 executed, 32 passed, 0 failures, 0 errors, 0 skipped**
- Surefire XML suite-time sum: `212.588 s`

| Suite | Tests | Passed | Failures | Errors | Skipped | XML seconds |
|---|---:|---:|---:|---:|---:|---:|
| `AuthIntegrationTest` | 8 | 8 | 0 | 0 | 0 | 154.026 |
| `DatabaseDesignTests` | 10 | 10 | 0 | 0 | 0 | 23.936 |
| `OrderIntegrationTest` | 14 | 14 | 0 | 0 | 0 | 34.626 |
| **Total** | **32** | **32** | **0** | **0** | **0** | **212.588** |

Mỗi suite dùng container `mysql:8.4` riêng; runtime report là MySQL 8.4.13. Không dùng Compose database/volume. Không rerun và không sửa source/test/config.

