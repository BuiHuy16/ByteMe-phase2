# Black-box API Summary

- Command: `python -X utf8 scripts/test-endpoints.py`.
- Environment routing: `COMPOSE_PROJECT_NAME=byteme-g22`, `BYTEME_BASE_URL=http://127.0.0.1:18080`.
- Started: `2026-11-19T11:29:53.5510679+07:00`.
- Finished: `2026-11-19T11:30:06.6666148+07:00`.
- Exit code: `0`.
- Result: **196 passed, 0 failed, fatal=null, cleanupVerified=true**.

| Group | Checks | Passed | Failed |
|---|---:|---:|---:|
| Infrastructure | 3 | 3 | 0 |
| Auth | 32 | 32 | 0 |
| Food | 45 | 45 | 0 |
| Cart | 27 | 27 | 0 |
| Order | 65 | 65 | 0 |
| Checkout failures | 12 | 12 | 0 |
| Auth rate limit | 11 | 11 | 0 |
| Cleanup | 1 | 1 | 0 |
| **Total** | **196** | **196** | **0** |

HTTP checks observed: 42×200, 15×201, 1×204, 35×400, 17×401, 16×403, 8×404, 17×409 and 1×429. Remaining checks validate response state, ownership, JWT/RBAC behavior, order snapshots/transitions, stock/rollback and cleanup invariants.

Independent SQL counts and `stock_total` after cleanup equal the pre-run values exactly. No script modification or failure rerun was performed.

