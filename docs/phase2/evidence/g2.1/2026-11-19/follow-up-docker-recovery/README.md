# G2.1 Follow-up Evidence — Docker Recovery

Follow-up trên `HEAD 510f6415b6af535ceec77213f0b0c7d5082123f7`, ngày 2026-11-19, UTC+07:00. Evidence ban đầu 58/58 PASS ở thư mục cha được giữ nguyên; follow-up này không thay thế hoặc ghi đè lượt chạy đó.

| Path | Nội dung |
|---|---|
| `docker-environment.md` | Docker client/server/context, host/Docker resources, image MySQL và cleanup check |
| `git-provenance.md` | Commit graph, remote/ref/reflog, diff classification và hai baseline candidate |
| `integration-database/` | Command, timestamps, exit code, raw Maven output, summary và frozen Surefire reports cho 32 methods |
| `full-suite/` | Command, timestamps, exit code, raw Maven output, summary và frozen Surefire reports cho 90 methods |
| `SHA256SUMS.txt` | SHA-256 cho toàn bộ file follow-up, không gồm chính manifest checksum |

Không sửa application source, test, configuration, schema/seed hoặc Git refs. Không dùng database/volume của Compose stack; mỗi integration class tạo MySQL 8.4 riêng qua Testcontainers và Ryuk đã dọn container tạm sau mỗi JVM.

