# Official Run B — BLOCKED

Intended command:

```powershell
.\mvnw.cmd test "-Dtest=AuthIntegrationTest,OrderIntegrationTest,DatabaseDesignTests"
```

Expected: 32 methods using Testcontainers and isolated `mysql:8.4` containers.

The command was **not executed** because the Docker daemon prerequisite was unavailable. An unsandboxed read-only check returned Docker client `29.9.1`, Compose `v5.6.0`, context `desktop-linux`, then exit code `1` because `//./pipe/dockerDesktopLinuxEngine` did not exist. No Docker Desktop/backend/dockerd process or service was detected.

Classification: **Environment/configuration blocker**. No application or test pass/fail claim is made.

