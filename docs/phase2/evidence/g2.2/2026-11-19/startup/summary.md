# Startup and Readiness Summary

| Check | Result |
|---|---|
| Compose up | Exit `0` |
| MySQL container | `running`, health `healthy`, MySQL `8.4.13` |
| Backend container | `running`, exit state `0` |
| Database connection | Hikari `Start completed`; schema queries and application APIs succeeded |
| RSA keys | UID/GID 10001 read both 3072-bit files; check exit `0` |
| `/actuator/health` | HTTP `200`, `{"status":"UP"}` |
| Public `/api/foods` after seed | HTTP `200`, 17 ACTIVE foods |
| Serious startup log errors | 0 `ERROR`, 0 `FATAL`, 0 exception/caused-by, 0 access denied, 0 OOM |

Image build, container start and application readiness are recorded as separate checks. A running container alone was not accepted as readiness evidence.

