# Official Run A — Non-Docker Tests

Command:

```powershell
.\mvnw.cmd test "-Dtest=!*IntegrationTest,!DatabaseDesignTests"
```

- Exit code: `0`
- Maven/Surefire: Maven `3.9.11`; Surefire `3.5.6`; JUnit Platform provider auto-detected
- Executed: 58
- Passed: 58
- Failures: 0
- Errors: 0
- Skipped: 0
- Maven total duration: 14.020 seconds
- Aggregate Surefire suite duration: 7.339 seconds

| Suite | Tests | Failures | Errors | Skipped | Seconds |
|---|---:|---:|---:|---:|---:|
| `AdaptersTest` | 2 | 0 | 0 | 0 | 0.615 |
| `ArchitectureTest` | 5 | 0 | 0 | 0 | 1.458 |
| `AuthWebAndServiceTest` | 8 | 0 | 0 | 0 | 3.426 |
| `FoodCartSecurityTest` | 9 | 0 | 0 | 0 | 0.949 |
| `FoodServiceTest` | 11 | 0 | 0 | 0 | 0.149 |
| `LoginIpFilterTest` | 1 | 0 | 0 | 0 | 0.006 |
| `OrderServiceTest` | 10 | 0 | 0 | 0 | 0.106 |
| `OrderWebTest` | 10 | 0 | 0 | 0 | 0.619 |
| `RateLimiterTest` | 2 | 0 | 0 | 0 | 0.011 |

Warnings observed but non-failing:

- Mockito/Byte Buddy dynamic agent warning on Java 21.
- Surefire dumpstream absolute-classpath/different-root warning.

No test failure or error required root-cause classification.

