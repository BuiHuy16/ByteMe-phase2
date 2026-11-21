# Cleanup Summary

- Ownership was verified by Compose project labels before deletion.
- Removed: containers `byteme-g22-backend-1`, `byteme-g22-mysql-1`; network `byteme-g22_default`; volume `byteme-g22_mysql_data`.
- `docker compose ... down -v --remove-orphans` exit: `0`.
- Post-check: 0 project containers, 0 project networks, 0 project volumes, 0 listeners on ports 13306/18080.
- Shared containers still running: `aws-cloud-mailpit-1`, `busbooking-backend`, `busbooking-db`, `learncloud-db`.
- Retained intentionally: immutable local image `byteme-g22-backend:latest` / `sha256:374e18…` as the G2.2 build artifact.
- Removed after evidence copy: generated RSA keys, runtime secret env, ignored Compose override/generator and `.local/endpoint-test-results.json`.

Both cleanup dimensions passed: black-box fixture cleanup and Docker project cleanup. `cleanupVerified=true`.

