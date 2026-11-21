# Platform decision

| Factor | Local Windows + Docker Desktop | Kaggle CPU |
|---|---|---|
| CPU/RAM control | Docker reports 12 CPUs and 8,171,761,664 bytes; benchmark limits backend and MySQL explicitly | Historical note says 4 vCPU/30 GB, but CPU model/image/noisy-neighbor state was not captured |
| Toolchain | MySQL digest, k6 tag/digest, Java runtime and Compose controls are captured | Notebook installs generic JDK/MySQL/k6 from moving apt repositories |
| Reset/isolation | Unique Compose project, dedicated volume, safety-checked destructive reset, logical checksum | Existing notebook has no deterministic reset/checksum protocol |
| Telemetry | Raw k6 JSON, Docker CPU/RAM, GC logs, DB status/query digests, application/MySQL logs | Historical artifacts omitted raw CSV/server log and resource/DB/pool telemetry |
| Noise | Load generator shares the Docker VM; collect and report it as a confounder | Session/noisy-neighbor variance is outside repository control |
| Repetition/artifacts | Unique run directories, hashes and min 3/target 5 repetitions | Notebook output/version retention was not demonstrated |

Decision: use local Docker as the only primary comparison platform for G2.5. Use Kaggle only as a fallback with a newly frozen Kaggle-specific protocol, and compare only Kaggle-before with Kaggle-after. Historical Kaggle numbers are context, not a compatible baseline.
