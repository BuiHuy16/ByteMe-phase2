# ByteMe G2.4-K — Kaggle CPU adaptation

This adapter keeps the G2.4 workload and dataset semantics while replacing Docker-specific execution with loopback, user-space processes. It does not change application source, schema, seed or the historical upstream notebook.

## Status

The notebook and scripts have been statically validated locally. No Kaggle credentials/runtime are available in the preparation environment, so **Kaggle runtime validation is PENDING**. Do not report a smoke PASS until `smoke-result.json` from a real Kaggle session says `PASS`.

## Inputs

1. After the official regression gate, build and package directly from the verified executable tree:

   ```powershell
   ./benchmarks/phase2/kaggle/prepare_bundle.ps1 -ExpectedApplicationSha 510f6415b6af535ceec77213f0b0c7d5082123f7
   ```

   The builder rejects staged, unstaged or untracked executable drift, runs Maven Wrapper `clean package`, and records source/tree identity, Java/Maven output, build command/exit and JAR SHA-256. For a future Phase 2 treatment, pass that reviewed application SHA; the benchmark workload remains independently hashed.

2. Add exact portable Linux x86_64 archives for Java 21.0.13, MySQL 8.4.13 and k6 0.55.2 to a private Kaggle Dataset. The adapter accepts a system binary only when its reported version contains the exact locked value. It never silently substitutes a different version.
3. Upload `kaggle/script/byteme_phase2_g24k.ipynb`; select Accelerator `None`; attach the bundle/toolchain datasets. Internet may remain off when all archives are attached.

MySQL runs from its generic binary distribution under `/kaggle/working`, bound to `127.0.0.1:13309`; Docker and root/apt are not required. If a portable binary has missing shared libraries, the run fails closed and records the blocker.

## Notebook phases

The notebook captures CPU model, core count, exact RAM quota, OS/kernel and capabilities; verifies every bundle file; resolves exact tool versions; initializes isolated MySQL; starts the baseline JAR with the configuration lock; prepares smoke fixtures; executes W1/W2/W3; captures raw k6, process/system resources, JVM/GC, DB status/query digests and final invariants; resets to the initial logical checksum; removes runtime secrets; creates `SHA256SUMS.txt` and an evidence ZIP.

Initial fixture validation requires exact initial order/item counts and empty carts. Post-workload validation permits legitimate canceled orders and empty cart rows while still requiring immutable read fixtures, exact user/category/food cardinality, shared-stock restoration, positive quantities/non-negative stock and no orphan order/cart items. Reset then has to pass the initial rules and reproduce the original logical checksum.

A zero k6 exit code is insufficient: the runner parses W1/W2 summaries and asserts exact smoke check/request counts, zero HTTP/workload/unexpected/server errors, non-empty raw output and resource samples for backend, MySQL and driver. W3 baseline violations and recorded HTTP 500s remain defect evidence; missing rounds/responses/final state are harness failures.

The `standard` profile remains 5,000 read foods, 500 orders, 20 write actors and four contention actors. G2.4-K runs only `smoke`; standard execution belongs to G2.5.

## Before/after grouping

Run `compare_manifests.py` on the resulting `manifest/run-manifest.json` files. It rejects missing or different cgroup CPU quota, effective cpuset, memory limit, resolved limits, kernel/runtime-image identity, CPU model, visible cores/RAM, OS image, Java/MySQL/k6 versions or binary hashes, configuration/workload hashes or dataset checksum. Application SHA is reported as the treatment pair and is expected to differ for before/after. Never merge sessions merely because both are labelled “Kaggle CPU”.

Official measurement parameters remain warm-up 60 s, W1/W2 180 s, cooldown 30 s, W1 arrival rates 10/5/5 RPS, W2 10 VUs, W3 15 rounds, minimum three and target five independent runs. The notebook smoke uses the smoke profile and two W3 rounds only.

## Known limitations

- Live Hikari gauges remain unavailable; Hikari configuration and MySQL connection behavior are captured.
- CPU quota/model can vary between Kaggle sessions; manifests must match before aggregation.
- Kaggle session lifetime and attached-dataset storage are external constraints. Download the evidence ZIP before the session ends.
- The adapter does not use the historical notebook's moving apt packages, 50→200→500 VU workload or unverified thresholds.
- Cleanup, secret scan, manifest/checksum and evidence packaging are part of smoke success. Cleanup failure forces `FAIL`; the runner still creates a failure evidence ZIP whenever filesystem access permits.
