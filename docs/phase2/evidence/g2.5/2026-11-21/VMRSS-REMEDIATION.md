# G2.5 Run 01 — VmRSS lifecycle remediation

LOCAL READY; Kaggle rerun PENDING. No official benchmark was executed during this change.

## Evidence boundary and cause

The supplied traceback establishes missing VmRSS in ResourceSampler's background thread.
No Run 01 evidence ZIP was found in the local evidence directory. PID 415's label and phase
therefore remain UNKNOWN. A zombie/exit race is reproduced by tests, but cannot be asserted
as the actual cause of PID 415 without its original logs.

Previously the reader treated every missing VmRSS as a live-process telemetry failure;
it did not inspect process state/start-time or distinguish a terminating driver from a service.
Now it checks Linux stat state and start-time, records lifecycle sidecars, and skips only
permitted terminating processes. Active mandatory CPU/RSS unavailability remains fatal.
PID reuse is checked both across samples and between stat/status reads. Backend/MySQL
exit is fatal; driver exit is reconciled with the parent-owned process exit status.
Optional I/O stays NA with a reason. Valid rows are appended immediately so a later
process failure does not discard them. No missing RSS value is replaced by zero.

Each affected workload writes resources.lifecycle.jsonl alongside resources.tsv, with
label/PID/state/start-time/exit code/reason. Its directory identifies warmup/W1/W2/W3.
MySQL exit is also checked by the parent workload loop and recorded under
environment/mysql-workload-exit.json. Existing backend diagnostics and traceback remain.

Official k6 phases require CPU/RSS rows for backend/mysql/driver and a sample span covering
at least 95% of the configured phase duration (57 s warm-up; 171 s measured W1/W2), in
addition to existing k6 summary duration validation. Configuration lock was not changed.

## Tests actually executed

- Windows Python 3.12: 94 total, 90 PASS, 4 SKIP, 0 FAIL, 0 ERROR.
- WSL Ubuntu 22.04 Python 3.11: 94 total, 94 PASS, 0 SKIP, 0 FAIL, 0 ERROR.
- Linux integration includes a real child process transitioning to zombie then reaped,
  preservation of earlier CPU/RSS samples, and a real cross-UID proc I/O denial.
- Regression covers active missing RSS, permission denied, exit race, zombie, PID reuse
  between/across samples, normal driver exit, service exit, mandatory labels/sample count,
  insufficient telemetry duration, and preservation of valid rows before another process fails.
- git diff --check PASS. Phase 1 executable tree matches baseline.
- profiles.json, prepare_dataset.py, W1/W2/W3 and configuration-lock.json match the previous
  official bundle byte-for-byte. Notebook and generator were not changed in this remediation.

## Artifacts

- Official builder: PASS, new output kaggle/dataset-g25-vmrss-20261121/.
- Application SHA: 510f6415b6af535ceec77213f0b0c7d5082123f7.
- JAR SHA-256: 715818ac684af061fa7dfc31918e09c7c97cbf1af12124cec10dc11b11b0f256.
- Versus previous official JAR: 278 entries, zero content differences, 87 timestamp differences.
- ZIP: kaggle/byteme-g25-vmrss-20261121.zip; 60026027 bytes.
- ZIP SHA-256: 955f8df0d7ca4d2b36a6fc0e5504e0ac5fc115fd155dd1c9165e51e20a5538be.
- Test extraction: 22 POSIX entries, 21/21 manifest hashes match; no outer directory.

Keep the failed Run 01 evidence. Upload the new bundle and reuse the unchanged official
notebook/toolchain Dataset for a new run ID. Local tests do not establish Kaggle PASS.
