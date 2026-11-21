# Sanitized Deployment Manifest

```text
project: byteme-g22
source_sha: 510f6415b6af535ceec77213f0b0c7d5082123f7
services:
  mysql:
    image: mysql:8.4
    image_id: sha256:a81d043930e51745522bd5c430961cf8286f0a23f0a9a2a6e0108f7ea71b0902
    host_binding: 127.0.0.1:13306 -> 3306/tcp
    volume: byteme-g22_mysql_data -> /var/lib/mysql
    schema_mount: src/main/resources/db/schema.sql (read-only)
    seed_mount: src/main/resources/db/seed.sql (read-only; manually loaded once)
  backend:
    image: byteme-g22-backend:latest
    image_id: sha256:374e18d9da9322de83cfae202353ef6e9f268db6cd6289a295cf5af581da7022
    host_binding: 127.0.0.1:18080 -> 8080/tcp
    key_mount: .local/g22/keys -> /run/auth (read-only; removed after cleanup)
network: byteme-g22_default
```

Environment keys used: `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`, `DB_ROOT_PASSWORD`, `DB_PORT`, `SERVER_PORT`, `DB_URL`, `AUTH_JWT_PRIVATE_KEY_FILE`, `AUTH_JWT_PUBLIC_KEY_FILE`. Secret values are intentionally omitted.

