# G2.1 Provenance Resolution for G2.2

## Independent GitHub evidence

- Fork page: <https://github.com/BuiHuy16/ByteMe-phase2> — GitHub hiển thị `forked from maaL6/ByteMe`.
- Upstream: <https://github.com/maaL6/ByteMe>.
- Upstream refactor commit: <https://github.com/maaL6/ByteMe/commit/1ee1cbf7b8d6d37f71c8a30ef57e0d68a3497763> — 67 files, parent `cfe2222…`, package-by-layer refactor.
- Upstream baseline candidate: <https://github.com/maaL6/ByteMe/commit/510f6415b6af535ceec77213f0b0c7d5082123f7>.
- Live `git ls-remote --symref https://github.com/maaL6/ByteMe.git HEAD refs/heads/master` returned upstream HEAD/master at full SHA `510f6415b6af535ceec77213f0b0c7d5082123f7`.

## Local verification

- Local branch: `main`.
- Local HEAD: `510f6415b6af535ceec77213f0b0c7d5082123f7`.
- Git tree: `9b8972489beffd34ac9873f1ff7f88c1c9f6b21a`.
- Both upstream SHAs resolve locally as commit objects.
- `git diff 510f641… -- src pom.xml compose.yaml Dockerfile .dockerignore .env.example scripts` returned exit `0`: tested source, tests, application resources/configuration, build/deployment definitions and black-box script match the baseline commit.
- Working tree has no tracked drift; only `docs/phase2/` is untracked evidence/report work.

## Scope decision

`1ee1cbf…` is an **upstream historical refactor inherited by the fork**, not evidence of a future improvement authored by this group's Phase 2 work. For this verification, “pre-improvement” means the source before any new treatment introduced by the group after the baseline is frozen. Under that explicit scope, `510f641…` is accepted as the group's pre-improvement source candidate.

This conclusion does not claim ownership of `1ee1cbf…`, does not relabel it as a team Phase 1 deliverable, and does not treat its commit message as proof of intent. Future Phase 2 improvements must be distinguishable from this SHA. No tag, branch, commit or push was created.

