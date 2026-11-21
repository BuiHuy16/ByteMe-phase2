# G2.1 Evidence — 2026-11-19

Evidence cho `HEAD 510f6415b6af535ceec77213f0b0c7d5082123f7`, thu thập tại UTC+07:00.

| Path | Nội dung |
|---|---|
| `git-baseline.txt` | Git repository, refs, remotes, ancestry và diff classification |
| `environment-manifest.txt` | OS/CPU/RAM/Java/Maven/Docker manifest không chứa secret |
| `non-docker/` | Official 58-test command, exit code, summary, Maven output và frozen Surefire reports |
| `integration-database/BLOCKED.md` | Docker blocker cho 32 Testcontainers methods |
| `full-suite/BLOCKED.md` | Docker blocker cho full 90-test suite |
| `SHA256SUMS.txt` | SHA-256 của evidence files, không gồm chính file checksum |

Không có application source/test/configuration nào được sửa để tạo evidence này.

