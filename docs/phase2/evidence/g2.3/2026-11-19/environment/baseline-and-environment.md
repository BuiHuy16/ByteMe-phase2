# G2.3 baseline and environment

- Evidence directory follows the requested `2026-11-19` UTC run date; execution was 2026-11-20 in Asia/Saigon.
- Git HEAD/branch: `510f6415b6af535ceec77213f0b0c7d5082123f7`, `main`.
- Pre-run and post-run executable diff command: `git diff --exit-code 510f6415b6af535ceec77213f0b0c7d5082123f7 -- src pom.xml compose.yaml Dockerfile .dockerignore .env.example scripts`; exit `0`.
- Working tree before the run contained only the already-untracked `docs/phase2/` tree. Harness/runtime material was placed under ignored `.local/g2.3/`.
- Compose project: `byteme-g23`; loopback-only ports `127.0.0.1:13307` (MySQL) and `127.0.0.1:18081` (backend).
- Dedicated resources: `byteme-g23_mysql_data`, `byteme-g23_default`, `byteme-g23-mysql-1`, `byteme-g23-backend-1`.
- Docker Engine/client `29.9.1`, API `1.56`, Compose `v5.6.0`, context `desktop-linux`, Linux/amd64, 12 Docker CPUs, 7.611 GiB Docker RAM.
- Host preflight reported 16,473,776 KiB total RAM and 2,888,076 KiB free RAM. Docker resource use immediately before experiments was about 470.3 MiB for MySQL and 458.5 MiB for the backend. No OOM/disk error occurred.
- Backend image: `byteme-g23-backend@sha256:8bd11bf3ae9e5f7daeaf0c600c79639eae57cff13f5a719b930890fbe3b164af`, 583,684,096 bytes.
- MySQL image: `mysql@sha256:a81d043930e51745522bd5c430961cf8286f0a23f0a9a2a6e0108f7ea71b0902`; runtime MySQL `8.4.13`.
- JVM: Temurin OpenJDK `21.0.13+9-LTS`; Spring Boot `3.5.16`; Hibernate `6.6.53.Final` from startup log.
- Database: `REPEATABLE-READ`, autocommit `1`, InnoDB lock wait `50s`, max connections `151`.
- Hikari uses baseline defaults plus `SET time_zone = '+00:00'`; startup log did not expose an explicit pool size override.
- Database began with the seven schema tables and zero business rows; original `seed.sql` was not changed or loaded. Each concurrency round used targeted isolated fixtures and cleanup.
- Runtime DB passwords and a new RSA-3072 key pair existed only under ignored `.local/g2.3/`; no secret or key content is preserved here.

The resolved Compose artifact is redacted. The six non-G2.3 containers observed before the run belonged to other projects and were not stopped, restarted, or deleted.
