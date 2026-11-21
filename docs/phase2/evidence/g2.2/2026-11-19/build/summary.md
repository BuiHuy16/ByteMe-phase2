# Image Build Summary

- Command: `docker compose -p byteme-g22 --env-file <ignored> -f compose.yaml -f <ignored-override> build --progress plain`
- Started: `2026-11-19T11:15:52.7424173+07:00`
- Finished: `2026-11-19T11:27:17.2148247+07:00`
- Exit code: `0`
- Maven package: `BUILD SUCCESS`; tests intentionally skipped by the baseline Dockerfile (`-Dmaven.test.skip=true`), with G2.1 regression evidence retained separately.
- Image: `byteme-g22-backend:latest`.
- Image ID/digest: `sha256:374e18d9da9322de83cfae202353ef6e9f268db6cd6289a295cf5af581da7022`.
- Size: 583,684,096 bytes.
- Base image digests are preserved in raw build output.

Result: **PASS**. Initial duration is dominated by first-time Temurin/Maven dependency downloads.

