# G2.4-K independent review remediation evidence

Date: 2026-11-20 Asia/Saigon. No Kaggle runtime or official G2.5 benchmark was executed.

## Results

- 18/18 Python unit/adversarial tests passed.
- Post-workload mutation now passes a separate consistency policy; the same state correctly fails initial-state validation, and orphan data still fails.
- k6 summaries with failed checks, wrong request count, HTTP/workload/unexpected errors are rejected even when a process could exit zero.
- Header-only resource telemetry, reset mismatch and cleanup failure force smoke `FAIL`.
- A valid W3 evidence structure passes even when it contains baseline violations/HTTP 500 findings.
- cgroup v2 quota parsing and manifest fail-closed comparison tests passed.
- Path-escaping tar symlink and hardlink tests passed (both rejected).
- Failure-path ZIP creation and secret-leak detection tests passed.
- Bundle builder rejected an adversarial untracked file under `src` before creating output.
- Actual Maven Wrapper `clean package` succeeded. The resulting JAR SHA-256 is `ff3d8e1c8cbdf93e07c38f25f4a732a7655accd5684307c556a110d267c475aa`; it matches both bundle and build-provenance manifests.
- Final bundle contained 17 listed files with zero checksum errors, and runtime bundle resolution passed.

## Files

- `unit-adversarial-tests.txt`, `test-summary.json`: raw test output and exit/count summary.
- `static-validation.txt`: AST/PowerShell/JSON/notebook/Git checks.
- `bundle-untracked-adversarial.txt`: fail-closed untracked-source check.
- `build/`: Maven log, build provenance, bundle manifest, validation and runtime resolution output.
- `remediated-source-SHA256SUMS.txt`: current adapter/workload/test source hashes.
- `SHA256SUMS.txt`: this remediation evidence manifest, excluding itself.

The pre-remediation G2.4-K evidence remains unchanged in the parent directory. Kaggle runtime validation remains PENDING.
