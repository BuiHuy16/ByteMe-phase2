# Static validation

## Provenance

- Protocol/application baseline: `510f6415b6af535ceec77213f0b0c7d5082123f7`.
- Repository/tooling HEAD observed during adaptation: `24b3ace314365bc2b727928fae2243c605b4c87c`.
- Baseline is an ancestor of tooling HEAD.
- Diff from baseline to tooling HEAD and worktree over application source, POM, Compose, Dockerfile and runtime script paths: exit `0`.
- Bundle manifests keep `repository_sha` and `application_sha` separate.

## Parser and packaging checks

| Check | Result |
|---|---|
| Shared `prepare_dataset.py` AST | PASS |
| Shared W3 AST | PASS |
| Kaggle runtime/comparator/generator AST | PASS |
| Bundle-builder PowerShell parser | PASS |
| Configuration lock JSON | PASS |
| Notebook JSON | PASS |
| Every notebook code cell AST | PASS |
| Bundle-builder dry-run | PASS — 14 files, 0 missing/hash errors |
| Runtime local fail-closed test | PASS — status FAIL, explicit non-Kaggle reason, runtime secret removed |
| Manifest comparator treatment-pair test | PASS — different application SHA allowed |
| Manifest comparator hardware test | PASS — different CPU model rejected |

The bundle dry-run used a dummy file in place of the JAR and only proves manifest/copy logic. Java, MySQL, k6, backend API calls, standard dataset generation and reset have not run on Kaggle.

## Compatibility design

The shared generator and W3 default to the original `compose` mode. Kaggle passes `--db-mode direct` plus loopback connection settings and an environment-variable name for the password. W1/W2 are unchanged. The new notebook refuses non-Kaggle runtime, ambiguous inputs, baseline/provenance mismatch, bundle checksum mismatch, non-exact tool versions or failed reset.
