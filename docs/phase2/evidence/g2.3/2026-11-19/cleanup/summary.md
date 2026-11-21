# Cleanup verification

- Before Compose teardown, `general_log=0` and all seven business tables contained zero rows after targeted fixture cleanup.
- `docker compose ... down -v --remove-orphans` exited `0` and removed exactly the two `byteme-g23` containers, `byteme-g23_default` network and `byteme-g23_mysql_data` volume.
- Post-cleanup inventory found zero containers, networks or volumes with project label `byteme-g23` and no listeners on ports 13307/18081.
- The six non-G2.3 containers observed at preflight were still running afterward. No shared resource was stopped, restarted or deleted.
- The ignored directory `.local/g2.3/` was resolved and checked as `D:\projects\main projects\ByteMe-phase2\.local\g2.3` before recursive removal. Runtime DB credentials, RSA keys and temporary harness files were thereby removed; reproducibility copies were already archived without secrets.
- After its ID/size had been archived and zero dependent containers were confirmed, the G2.3-only image `byteme-g23-backend:latest` (`sha256:8bd11bf3ae9e5f7daeaf0c600c79639eae57cff13f5a719b930890fbe3b164af`) was also removed. `image-removal-output.txt` records exit 0 and the subsequent not-found verification.

Cleanup status: **PASS**.
