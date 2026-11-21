# G2.2 Evidence — Docker & Black-box Verification

Verification thực hiện ngày 2026-11-19 (UTC+07:00) trên baseline `510f6415b6af535ceec77213f0b0c7d5082123f7` bằng Compose project cô lập `byteme-g22`.

| Path | Nội dung |
|---|---|
| `provenance.md` | GitHub fork/upstream evidence, local SHA/tree và baseline scope decision |
| `preflight.md` | Docker/Compose, RAM/disk, ports, existing resources và script safety review |
| `deployment-manifest.md` | Sanitized Compose project/service/port/volume/key manifest |
| `build/` | Raw build output, timestamps, exit code, image identity và summary |
| `startup/` | Compose startup, service state, readiness, RSA readability và logs |
| `database/` | Schema/constraints, pre-seed counts, one-time seed và post-seed sample counts |
| `black-box/` | Raw script output, JSON results, HTTP/group summary, DB before/after và logs |
| `cleanup/` | Ownership manifest, raw `down -v`, exit code và post-cleanup verification |
| `SHA256SUMS.txt` | SHA-256 của evidence files, không gồm chính checksum manifest |

Không lưu password, JWT, Authorization header hoặc nội dung private key. Không sửa source/test/schema/production configuration và không thay Git refs.

