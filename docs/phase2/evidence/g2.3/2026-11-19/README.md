# ByteMe G2.3 evidence

Run window: 2026-11-19 UTC / 2026-11-20 Asia/Saigon. Baseline: `510f6415b6af535ceec77213f0b0c7d5082123f7`.

## Artifact map

- `environment/`: redacted resolved Compose, runtime/image/JVM/MySQL metadata, baseline/environment narrative and resource snapshots.
- `build/`: raw Compose build output, timestamps, exit code and backend image identity.
- `startup/`: raw Compose startup, health, timestamps and container state.
- `concurrency/`: raw JSON for all 75 rounds, aggregate output, backend log and reviewed classification.
- `query/`: raw general-log SQL counts, normalized SQL, EXPLAIN/EXPLAIN ANALYZE plans, scale measurements and reviewed summary.
- `harness/`: reproducibility copies of the executed Python harnesses and the non-secret Compose override. The only redaction change is that the ephemeral actor password is supplied through `G23_ACTOR_PASSWORD` instead of being embedded.
- `cleanup/`: pre-cleanup ownership inventory, Compose down output and post-cleanup verification.
- `SHA256SUMS.txt`: SHA-256 manifest for all evidence artifacts except the manifest itself.

## Safety and reproducibility

No password, access token, Authorization header, private/public key content, or runtime env file is archived. Raw HTTP results retain only response status and compact non-secret response fields. The original application source, tests, schema, seed, Maven/Docker/Compose configuration and scripts were not modified. No G2.4/G2.5 workload was run.
