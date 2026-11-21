# Docker Environment Preflight

## Git and toolchain

- HEAD `510f6415b6af535ceec77213f0b0c7d5082123f7`, branch `main`; baseline content diff exit `0`.
- Docker client/server `29.9.1`, API `1.56`, context `desktop-linux`, Linux/amd64.
- Docker Compose `v5.6.0`.
- Docker VM: 12 CPUs, 8,171,769,856 bytes memory, overlayfs at `/var/lib/docker`.
- Host physical memory: 16,473,776 KiB total; 2,720,852 KiB free at preflight.
- Drive `D:` free: 34,908,233,728 bytes (~32.51 GiB).

## Isolation and ownership precheck

- Ports `13306` and `18080` had no listening process.
- No container, network or volume carried `com.docker.compose.project=byteme-g22` before deployment.
- Existing shared resources were inventoried and left untouched.
- Resolved bindings: MySQL `127.0.0.1:13306→3306`, backend `127.0.0.1:18080→8080`.
- Unique named volume: `byteme-g22_mysql_data`.
- Unique default network: `byteme-g22_default`.

## Environment and key requirements

- Required DB variables were supplied through a generated ignored runtime env file; values were never added to evidence.
- A dedicated 3072-bit RSA pair was generated under ignored `.local/g22/keys`; private/public numbers matched.
- Compose override replaced only backend `/run/auth` with the dedicated read-only bind.
- Container UID/GID `10001` successfully read both key files without exposing contents.

## Black-box script safety review

- HTTP target is configurable through `BYTEME_BASE_URL`; set to `http://127.0.0.1:18080`.
- SQL selects `docker compose exec mysql`; `COMPOSE_PROJECT_NAME=byteme-g22` binds it to the isolated MySQL service.
- Fixtures use a random `api_test_<hex>` prefix.
- Cleanup discovers only user/category IDs for that prefix, deletes dependent rows in a transaction and compares row counts plus total stock to its baseline.
- Output is `.local/endpoint-test-results.json`; it did not exist before the run, was copied into evidence and then removed with other temporary secrets.

