#!/usr/bin/env python3
"""User-space Kaggle CPU smoke orchestration for the Phase 2 benchmark kit.

No Docker or root access is assumed. Exact portable toolchain archives may be
attached as Kaggle inputs; an already installed binary is accepted only when
its version matches the configuration lock exactly.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import platform
try:
    import pwd
except ImportError:  # Windows unit-test host; Kaggle is Linux.
    pwd = None
import re
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import tarfile
import threading
import traceback
import time
import urllib.error
import urllib.request
import zipfile


BASELINE_SHA = "510f6415b6af535ceec77213f0b0c7d5082123f7"

TOOLCHAIN_ARCHIVE_PATTERNS = {
    "java": ("*jdk*21*.tar.gz", "*jre*21*.tar.gz"),
    "mysql": ("mysql*8.4*.tar.xz", "mysql*8.4*.tar.gz"),
    "k6": ("k6*v0.55.2*linux*amd64*.tar.gz", "k6*0.55.2*linux*amd64*.tar.gz"),
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_os_release() -> dict[str, str]:
    result = {}
    path = pathlib.Path("/etc/os-release")
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, raw = line.split("=", 1)
                result[key] = raw.strip().strip('"')
    return result


def cpu_model() -> str:
    path = pathlib.Path("/proc/cpuinfo")
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "unknown"


def memory_total() -> int:
    path = pathlib.Path("/proc/meminfo")
    if path.exists():
        match = re.search(r"^MemTotal:\s+(\d+)\s+kB", path.read_text(), re.MULTILINE)
        if match:
            return int(match.group(1)) * 1024
    return 0


def parse_cpuset(value: str) -> int:
    cpus: set[int] = set()
    for part in value.strip().split(","):
        if not part:
            continue
        if "-" in part:
            start, end = (int(item) for item in part.split("-", 1))
            if end < start:
                raise ValueError(f"invalid cpuset range: {part}")
            cpus.update(range(start, end + 1))
        else:
            cpus.add(int(part))
    return len(cpus)


def _read_optional(path: pathlib.Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def resolve_cgroup_limits(cgroup_root: pathlib.Path = pathlib.Path("/sys/fs/cgroup"),
                          proc_cgroup: pathlib.Path = pathlib.Path("/proc/self/cgroup")) -> dict:
    """Capture cgroup v1/v2 quota evidence without assuming host visibility equals quota."""
    lines = (_read_optional(proc_cgroup) or "").splitlines()
    version = "v2" if (cgroup_root / "cgroup.controllers").exists() else "v1"
    relative: dict[str, str] = {}
    for line in lines:
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        controllers, path = parts[1], parts[2].lstrip("/")
        if parts[0] == "0" and not controllers:
            relative["unified"] = path
        for controller in controllers.split(","):
            if controller:
                relative[controller] = path

    def first(paths: list[pathlib.Path]) -> str | None:
        for path in paths:
            value = _read_optional(path)
            if value is not None:
                return value
        return None

    if version == "v2":
        base = cgroup_root / relative.get("unified", "")
        cpu_raw = first([base / "cpu.max", cgroup_root / "cpu.max"])
        cpuset_raw = first([base / "cpuset.cpus.effective", base / "cpuset.cpus",
                            cgroup_root / "cpuset.cpus.effective", cgroup_root / "cpuset.cpus"])
        memory_raw = first([base / "memory.max", cgroup_root / "memory.max"])
        quota_us = None
        period_us = None
        if cpu_raw:
            parts = cpu_raw.split()
            if len(parts) == 2:
                quota_us = None if parts[0] == "max" else int(parts[0])
                period_us = int(parts[1])
    else:
        cpu_bases = [cgroup_root / "cpu", cgroup_root / "cpu,cpuacct", cgroup_root]
        cpuset_bases = [cgroup_root / "cpuset", cgroup_root]
        memory_bases = [cgroup_root / "memory", cgroup_root]
        cpu_raw = first([base / relative.get("cpu", "") / "cpu.cfs_quota_us" for base in cpu_bases])
        period_raw = first([base / relative.get("cpu", "") / "cpu.cfs_period_us" for base in cpu_bases])
        cpuset_raw = first([base / relative.get("cpuset", "") / "cpuset.cpus" for base in cpuset_bases])
        memory_raw = first([base / relative.get("memory", "") / "memory.limit_in_bytes" for base in memory_bases])
        quota_us = int(cpu_raw) if cpu_raw and int(cpu_raw) >= 0 else None
        period_us = int(period_raw) if period_raw else None
        cpu_raw = f"{cpu_raw or 'missing'} {period_raw or 'missing'}"

    cpuset_count = parse_cpuset(cpuset_raw) if cpuset_raw else None
    quota_cores = quota_us / period_us if quota_us is not None and period_us else None
    visible_cpus = os.cpu_count()
    cpu_candidates = [float(item) for item in (visible_cpus, cpuset_count, quota_cores) if item is not None]
    resolved_cpu = min(cpu_candidates) if cpu_candidates else None
    numeric_memory = None
    if memory_raw and memory_raw != "max":
        try:
            numeric_memory = int(memory_raw)
        except ValueError:
            pass
    host_memory = memory_total()
    memory_candidates = [item for item in (host_memory, numeric_memory) if item and item > 0]
    resolved_memory = min(memory_candidates) if memory_candidates else None
    complete = all((version in ("v1", "v2"), cpu_raw, period_us, cpuset_raw, memory_raw,
                    cpuset_count, resolved_cpu, resolved_memory))
    return {
        "version": version,
        "cpu_quota_raw": cpu_raw,
        "cpu_quota_us": quota_us,
        "cpu_period_us": period_us,
        "cpu_quota_cores": quota_cores,
        "cpuset_effective": cpuset_raw,
        "cpuset_cpu_count": cpuset_count,
        "memory_limit_raw": memory_raw,
        "memory_limit_bytes": numeric_memory,
        "resolved_cpu_limit": resolved_cpu,
        "resolved_memory_limit_bytes": resolved_memory,
        "quota_evidence_complete": bool(complete),
    }


def runtime_image_identity(os_release: dict[str, str]) -> dict:
    files = {}
    for candidate in (pathlib.Path("/etc/os-release"), pathlib.Path("/etc/image_version"),
                      pathlib.Path("/opt/conda/conda-meta/history")):
        if candidate.is_file():
            files[str(candidate)] = sha256(candidate)
    facts = {"os_id": os_release.get("ID"), "os_version": os_release.get("VERSION_ID"),
             "kernel": platform.release(), "platform": platform.platform(),
             "python": platform.python_version(), "file_sha256": files,
             "kaggle_kernel_run_type": os.environ.get("KAGGLE_KERNEL_RUN_TYPE")}
    facts["identity_sha256"] = hashlib.sha256(json.dumps(facts, sort_keys=True).encode()).hexdigest()
    return facts


def safe_extract(archive: pathlib.Path, destination: pathlib.Path) -> None:
    """Extract regular files/directories and only in-tree links; reject special files."""
    destination.mkdir(parents=True, exist_ok=True)
    resolved = destination.resolve()
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        members_by_path: dict[pathlib.PurePosixPath, tarfile.TarInfo] = {}
        for member in members:
            pure = pathlib.PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts:
                raise RuntimeError(f"unsafe archive member: {member.name}")
            previous = members_by_path.get(pure)
            if previous is not None and not (previous.isdir() and member.isdir()):
                raise RuntimeError(f"duplicate archive member: {member.name}")
            if previous is None:
                members_by_path[pure] = member
            if not (member.isdir() or member.isfile() or member.issym() or member.islnk()):
                raise RuntimeError(f"unsupported archive member type: {member.name}")
            target = (destination / pathlib.Path(*pure.parts)).resolve()
            if resolved not in target.parents and target != resolved:
                raise RuntimeError(f"unsafe archive member: {member.name}")
            if member.issym():
                link_target = (target.parent / member.linkname).resolve()
                if resolved not in link_target.parents and link_target != resolved:
                    raise RuntimeError(f"unsafe symlink target: {member.name} -> {member.linkname}")
            if member.islnk():
                link_target = (destination / pathlib.Path(*pathlib.PurePosixPath(member.linkname).parts)).resolve()
                if resolved not in link_target.parents and link_target != resolved:
                    raise RuntimeError(f"unsafe hardlink target: {member.name} -> {member.linkname}")
        for member in members:
            target = destination / pathlib.Path(*pathlib.PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                source = bundle.extractfile(member)
                if source is None:
                    raise RuntimeError(f"cannot read archive member: {member.name}")
                with source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod(stat.S_IMODE(member.mode))
        for member in members:
            target = destination / pathlib.Path(*pathlib.PurePosixPath(member.name).parts)
            if member.issym():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(member.linkname)
            elif member.islnk():
                link_target = destination / pathlib.Path(*pathlib.PurePosixPath(member.linkname).parts)
                if not link_target.exists():
                    raise RuntimeError(f"hardlink target missing: {member.name} -> {member.linkname}")
                os.link(link_target, target)


def _matching_files(root: pathlib.Path, patterns: tuple[str, ...]) -> list[pathlib.Path]:
    found: set[pathlib.Path] = set()
    for pattern in patterns:
        found.update(path for path in root.rglob(pattern) if path.is_file())
    return sorted(found)


def _executable_candidates(root: pathlib.Path, component: str) -> list[pathlib.Path]:
    names = {"java", "java.exe"} if component == "java" else {"k6", "k6.exe"}
    candidates = []
    for name in names:
        for path in root.rglob(name):
            if not path.is_file():
                continue
            if component == "java" and path.parent.name != "bin":
                continue
            candidates.append(path)
    return sorted(set(candidates))


def _validate_extracted_tree(root: pathlib.Path) -> None:
    resolved = root.resolve()
    for path in root.rglob("*"):
        if not path.is_symlink():
            continue
        target = path.resolve()
        if target != resolved and resolved not in target.parents:
            raise RuntimeError(f"extracted toolchain symlink escapes its root: {path} -> {target}")


def _materialize_file(source: pathlib.Path, destination: pathlib.Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.symlink_to(source.resolve())
    except OSError:
        shutil.copy2(source, destination)


def _safe_bundle_relative(raw: str) -> pathlib.PurePosixPath:
    relative = pathlib.PurePosixPath(raw)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise RuntimeError(f"unsafe bundle manifest path: {raw}")
    return relative


def _bootstrap_version(component: str, executable: pathlib.Path, version_runner=None) -> str:
    args = ["-version"] if component == "java" else ["version"]
    if version_runner is not None:
        return str(version_runner(component, executable, args))
    proc = subprocess.run([str(executable), *args], text=True, encoding="utf-8", errors="replace",
                          capture_output=True, timeout=30)
    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode:
        raise RuntimeError(f"{component} executable version probe failed: {executable}: "
                           f"exit={proc.returncode}, output={output}")
    return output


def prepare_kaggle_input(input_root: str | pathlib.Path = "/kaggle/input",
                         working_root: str | pathlib.Path = "/kaggle/working/byteme-g24k-bootstrap",
                         version_runner=None) -> pathlib.Path:
    """Normalize Kaggle inputs without requiring a manual staging cell.

    Kaggle may expose Java and k6 either as original archives or as already
    extracted, non-executable dataset files. This function validates one exact
    source for each tool, materializes Java/k6 under writable storage, preserves
    MySQL/libaio as locked inputs, and returns the only input root a session
    should use. Repeated calls with the same inputs return the same directory.
    """
    source_root = pathlib.Path(input_root).resolve()
    bootstrap_root = pathlib.Path(working_root).resolve()
    if not source_root.is_dir():
        raise RuntimeError(f"Kaggle input root does not exist: {source_root}")

    bundle_manifests = sorted(source_root.rglob("bundle-manifest.json"))
    if len(bundle_manifests) != 1:
        raise RuntimeError(f"expected exactly one bundle-manifest.json below {source_root}, "
                           f"found {len(bundle_manifests)}: {bundle_manifests}")
    bundle_manifest_path = bundle_manifests[0]
    bundle_root = bundle_manifest_path.parent
    bundle_manifest = json.loads(bundle_manifest_path.read_text(encoding="utf-8-sig"))
    if bundle_manifest.get("protocol_baseline_sha") != BASELINE_SHA:
        raise RuntimeError("bundle protocol baseline mismatch during bootstrap")
    bundle_files: list[tuple[pathlib.PurePosixPath, pathlib.Path, str]] = []
    for item in bundle_manifest.get("files", []):
        relative = _safe_bundle_relative(item["path"])
        source = bundle_root / pathlib.Path(*relative.parts)
        actual = sha256(source) if source.is_file() else None
        if actual != item.get("sha256"):
            raise RuntimeError(f"bundle checksum mismatch during bootstrap: {relative.as_posix()}")
        bundle_files.append((relative, source, actual))
    locks = list(bundle_root.rglob("configuration-lock.json"))
    if len(locks) != 1:
        raise RuntimeError(f"configuration-lock.json missing or ambiguous during bootstrap: {locks}")
    config = json.loads(locks[0].read_text(encoding="utf-8-sig"))
    if config.get("baseline_sha") != BASELINE_SHA:
        raise RuntimeError("configuration baseline mismatch during bootstrap")
    expected = config["expected_versions"]

    mysql_archives = _matching_files(source_root, TOOLCHAIN_ARCHIVE_PATTERNS["mysql"])
    if len(mysql_archives) != 1:
        raise RuntimeError(f"expected exactly one MySQL {expected['mysql_contains']} archive, "
                           f"found {len(mysql_archives)}: {mysql_archives}")
    if expected["mysql_contains"] not in mysql_archives[0].name:
        raise RuntimeError(f"MySQL archive does not identify locked version {expected['mysql_contains']}: "
                           f"{mysql_archives[0]}")
    mysql_sha = sha256(mysql_archives[0])

    libaio_lock = config["offline_dependencies"]["libaio"]
    libaio_packages = sorted(path for path in source_root.rglob(libaio_lock["filename"]) if path.is_file())
    if len(libaio_packages) != 1:
        raise RuntimeError(f"expected exactly one locked libaio package, found {len(libaio_packages)}: "
                           f"{libaio_packages}")
    libaio_sha = sha256(libaio_packages[0])
    if libaio_sha != libaio_lock["package_sha256"]:
        raise RuntimeError(f"libaio package checksum mismatch during bootstrap: {libaio_sha}")

    sources = {}
    for component in ("java", "k6"):
        archives = _matching_files(source_root, TOOLCHAIN_ARCHIVE_PATTERNS[component])
        extracted = _executable_candidates(source_root, component)
        source_count = len(archives) + len(extracted)
        if source_count != 1:
            raise RuntimeError(f"expected exactly one {component} source (archive or extracted executable), "
                               f"found archives={archives}, extracted={extracted}")
        if archives:
            sources[component] = {"kind": "archive", "path": archives[0], "sha256": sha256(archives[0])}
        else:
            executable = extracted[0]
            install_root = executable.parent.parent if component == "java" else executable.parent
            _validate_extracted_tree(install_root)
            sources[component] = {"kind": "extracted", "path": install_root,
                                  "relative_executable": executable.relative_to(install_root),
                                  "sha256": sha256(executable)}

    fingerprint_document = {
        "schema_version": 1,
        "bundle_manifest_sha256": sha256(bundle_manifest_path),
        "configuration_sha256": sha256(locks[0]),
        "mysql": {"name": mysql_archives[0].name, "sha256": mysql_sha},
        "libaio": {"name": libaio_packages[0].name, "sha256": libaio_sha},
        "java": {key: str(value) if isinstance(value, pathlib.Path) else value
                 for key, value in sources["java"].items() if key != "path"},
        "k6": {key: str(value) if isinstance(value, pathlib.Path) else value
               for key, value in sources["k6"].items() if key != "path"},
    }
    fingerprint = hashlib.sha256(json.dumps(fingerprint_document, sort_keys=True).encode()).hexdigest()
    prepared = bootstrap_root / f"g24k-input-{fingerprint[:16]}"
    bootstrap_manifest_path = prepared / "bootstrap-manifest.json"
    if prepared.exists():
        if not bootstrap_manifest_path.is_file():
            raise RuntimeError(f"prepared input exists without bootstrap manifest: {prepared}")
        previous = json.loads(bootstrap_manifest_path.read_text(encoding="utf-8"))
        if previous.get("input_fingerprint_sha256") != fingerprint:
            raise RuntimeError(f"prepared input fingerprint mismatch: {prepared}")
        for component in ("java", "k6"):
            executable = prepared / pathlib.Path(*pathlib.PurePosixPath(
                previous["components"][component]["prepared_executable"]).parts)
            if not executable.is_file() or sha256(executable) != previous["components"][component]["sha256"]:
                raise RuntimeError(f"prepared {component} executable changed: {executable}")
            output = _bootstrap_version(component, executable, version_runner)
            if expected[f"{component}_contains"] not in output:
                raise RuntimeError(f"prepared {component} version drift: expected "
                                   f"{expected[f'{component}_contains']}, actual={output}")
        return prepared.resolve()

    bootstrap_root.mkdir(parents=True, exist_ok=True)
    temporary = bootstrap_root / f".{prepared.name}.tmp-{secrets.token_hex(6)}"
    temporary.mkdir(parents=False, exist_ok=False)
    try:
        _materialize_file(bundle_manifest_path, temporary / "bundle-manifest.json")
        for relative, source, _ in bundle_files:
            _materialize_file(source, temporary / pathlib.Path(*relative.parts))
        _materialize_file(mysql_archives[0], temporary / "toolchain-source/mysql" / mysql_archives[0].name)
        _materialize_file(libaio_packages[0], temporary / "toolchain-source/libaio" / libaio_packages[0].name)

        components = {}
        for component in ("java", "k6"):
            destination = temporary / "toolchain-source" / component
            source = sources[component]
            if source["kind"] == "archive":
                safe_extract(source["path"], destination)
                candidates = _executable_candidates(destination, component)
                if len(candidates) != 1:
                    raise RuntimeError(f"{component} archive must contain exactly one executable, "
                                       f"found {candidates}")
                executable = candidates[0]
            else:
                copied_root = destination / source["path"].name
                shutil.copytree(source["path"], copied_root, symlinks=True)
                executable = copied_root / source["relative_executable"]
            _validate_extracted_tree(destination)
            executable.chmod(executable.stat().st_mode | 0o111)
            output = _bootstrap_version(component, executable, version_runner)
            expected_marker = expected[f"{component}_contains"]
            if expected_marker not in output:
                raise RuntimeError(f"{component} version mismatch: expected {expected_marker}, actual={output}")
            components[component] = {
                "source_kind": source["kind"],
                "source_sha256": source["sha256"],
                "prepared_executable": executable.relative_to(temporary).as_posix(),
                "sha256": sha256(executable),
                "version": output,
            }
        document = {
            "schema_version": 1,
            "created_at_utc": utc_now(),
            "source_input_root": str(source_root),
            "prepared_input_root": str(prepared),
            "input_fingerprint_sha256": fingerprint,
            "fingerprint": fingerprint_document,
            "components": {
                **components,
                "mysql": {"archive": f"toolchain-source/mysql/{mysql_archives[0].name}",
                            "version": expected["mysql_contains"], "sha256": mysql_sha},
                "libaio": {"package": f"toolchain-source/libaio/{libaio_packages[0].name}",
                            "version": libaio_lock["version"], "sha256": libaio_sha},
            },
        }
        (temporary / "bootstrap-manifest.json").write_text(
            json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.rename(prepared)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return prepared.resolve()


def inspect_elf_library(path: pathlib.Path, lock: dict) -> dict:
    """Validate the exact locked ELF library without relying on host binutils."""
    actual_sha = sha256(path)
    if actual_sha != lock["library_sha256"]:
        raise RuntimeError(f"offline dependency library checksum mismatch: {actual_sha}")
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"\x7fELF":
        raise RuntimeError(f"offline dependency is not ELF: {path}")
    elf = lock["elf"]
    actual = {"class": data[4], "data": data[5], "osabi": data[7],
              "machine": int.from_bytes(data[18:20], "little" if data[5] == 1 else "big")}
    expected = {key: elf[key] for key in ("class", "data", "osabi", "machine")}
    if actual != expected:
        raise RuntimeError(f"offline dependency ELF mismatch: expected={expected}, actual={actual}")
    required_markers = [elf["soname"], *elf["required_symbol_versions"]]
    missing_markers = [item for item in required_markers if item.encode() + b"\0" not in data]
    if missing_markers:
        raise RuntimeError(f"offline dependency ABI markers missing: {missing_markers}")
    return {**actual, "sha256": actual_sha, "soname": elf["soname"],
            "required_symbol_versions": elf["required_symbol_versions"]}


def parse_ldd_missing(output: str) -> list[str]:
    return sorted(set(re.findall(r"^\s*([^\s]+)\s+=>\s+not found\s*$", output, re.MULTILINE)))


def validate_resource_samples(path: pathlib.Path, required_labels: set[str]) -> dict:
    if not path.is_file():
        raise RuntimeError(f"resource telemetry missing: {path}")
    lines = [line for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(lines) < 2:
        raise RuntimeError(f"resource telemetry has no samples: {path}")
    header = lines[0].split("\t")
    try:
        label_index = header.index("label")
    except ValueError as exc:
        raise RuntimeError(f"resource telemetry lacks label column: {path}") from exc
    labels = {line.split("\t")[label_index] for line in lines[1:] if len(line.split("\t")) > label_index}
    missing = sorted(required_labels - labels)
    if missing:
        raise RuntimeError(f"resource telemetry missing process labels {missing}: {path}")
    return {"sample_rows": len(lines) - 1, "labels": sorted(labels)}


def validate_k6_smoke_summary(path: pathlib.Path, workload: str, expected_checks: int | None = None,
                              expected_requests: int | None = None) -> dict:
    if not path.is_file():
        raise RuntimeError(f"k6 summary missing: {path}")
    summary = json.loads(path.read_text(encoding="utf-8-sig"))
    metrics = summary.get("metrics", {})
    expected = {"W1": {"checks": 6, "requests": 6, "error_metric": "application_error_rate"},
                "W2": {"checks": 8, "requests": 8, "error_metric": "write_error_rate"}}[workload]
    if expected_checks is not None:
        expected["checks"] = expected_checks
    if expected_requests is not None:
        expected["requests"] = expected_requests

    def values(name: str, required: bool = True) -> dict:
        metric = metrics.get(name)
        if metric is None:
            if required:
                raise RuntimeError(f"{workload} summary missing metric: {name}")
            return {}
        result = metric.get("values")
        if not isinstance(result, dict):
            raise RuntimeError(f"{workload} metric has no values: {name}")
        return result

    checks = values("checks")
    requests = values("http_reqs")
    failures = values("http_req_failed")
    workload_errors = values(expected["error_metric"])
    if checks.get("passes") != expected["checks"] or checks.get("fails") != 0:
        raise RuntimeError(f"{workload} check mismatch: {checks}")
    if requests.get("count") != expected["requests"]:
        raise RuntimeError(f"{workload} request-count mismatch: {requests}")
    if failures.get("rate") != 0 or workload_errors.get("rate") != 0:
        raise RuntimeError(f"{workload} HTTP/workload errors: http={failures}, workload={workload_errors}")
    unexpected = values("unexpected_responses", required=False)
    if unexpected and unexpected.get("count", 0) != 0:
        raise RuntimeError(f"{workload} unexpected responses: {unexpected}")
    if workload == "W2":
        server_errors = values("server_errors", required=False)
        if server_errors and server_errors.get("count", 0) != 0:
            raise RuntimeError(f"W2 server errors: {server_errors}")
    return {"workload": workload, "checks": checks.get("passes"),
            "requests": requests.get("count"), "http_failure_rate": failures.get("rate"),
            "unexpected_responses": unexpected.get("count", 0) if unexpected else 0}


def validate_w3_smoke_result(path: pathlib.Path, expected_rounds: int) -> dict:
    if not path.is_file():
        raise RuntimeError(f"W3 result missing: {path}")
    result = json.loads(path.read_text(encoding="utf-8-sig"))
    if result.get("rounds_per_scenario") != expected_rounds:
        raise RuntimeError("W3 round count mismatch")
    expected_scenarios = {"same_food_checkout", "same_cart_checkout", "admin_stock_vs_checkout"}
    scenarios = result.get("scenarios", {})
    if set(scenarios) != expected_scenarios:
        raise RuntimeError(f"W3 scenarios mismatch: {sorted(scenarios)}")
    for name, scenario in scenarios.items():
        rounds = scenario.get("rounds", [])
        if len(rounds) != expected_rounds:
            raise RuntimeError(f"W3 {name} rounds missing")
        for round_result in rounds:
            if not isinstance(round_result.get("responses"), list) or len(round_result["responses"]) != 2:
                raise RuntimeError(f"W3 {name} response evidence missing")
            if not isinstance(round_result.get("after"), dict) or not isinstance(round_result.get("violations"), list):
                raise RuntimeError(f"W3 {name} state/invariant evidence missing")
    return {"harness_valid": True,
            "violation_rounds": {name: scenario.get("violation_rounds", []) for name, scenario in scenarios.items()},
            "server_error_rounds": {name: scenario.get("server_error_rounds", []) for name, scenario in scenarios.items()},
            "note": "Baseline defects are evidence and do not make the correctness harness fail."}


class ResourceSampler:
    def __init__(self, output: pathlib.Path, processes: dict[str, int], interval: float = 1.0):
        self.output, self.processes, self.interval = output, processes, interval
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.previous_system = None
        self.previous_process: dict[int, int] = {}
        self.failure: str | None = None

    @staticmethod
    def _system_cpu() -> tuple[int, int]:
        values = [int(item) for item in pathlib.Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
        return sum(values), values[3] + (values[4] if len(values) > 4 else 0)

    @staticmethod
    def _process(pid: int) -> tuple[int, int, int, int]:
        stat = pathlib.Path(f"/proc/{pid}/stat").read_text().split()
        ticks = int(stat[13]) + int(stat[14])
        status = pathlib.Path(f"/proc/{pid}/status").read_text()
        match = re.search(r"^VmRSS:\s+(\d+)\s+kB", status, re.MULTILINE)
        rss = int(match.group(1)) * 1024 if match else 0
        io = pathlib.Path(f"/proc/{pid}/io").read_text()
        read_b = int(re.search(r"^read_bytes:\s+(\d+)", io, re.MULTILINE).group(1))
        write_b = int(re.search(r"^write_bytes:\s+(\d+)", io, re.MULTILINE).group(1))
        return ticks, rss, read_b, write_b

    @staticmethod
    def _available_memory() -> int:
        text = pathlib.Path("/proc/meminfo").read_text()
        match = re.search(r"^MemAvailable:\s+(\d+)\s+kB", text, re.MULTILINE)
        return int(match.group(1)) * 1024 if match else 0

    def start(self) -> None:
        if self.stop_event.is_set() or self.thread.ident is not None:
            raise RuntimeError("resource sampler cannot be restarted")
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text("timestamp_utc\tsystem_cpu_percent\tmemory_total_bytes\tmemory_available_bytes\tlabel\tpid\tprocess_cpu_percent\trss_bytes\tread_bytes\twrite_bytes\n", encoding="utf-8")
        self._sample_once()
        self.thread.start()

    def _sample_once(self) -> None:
        clock_ticks = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        total, idle = self._system_cpu()
        system_percent = 0.0
        if self.previous_system:
            total_delta = total - self.previous_system[0]
            idle_delta = idle - self.previous_system[1]
            system_percent = 100.0 * (total_delta - idle_delta) / total_delta if total_delta else 0.0
        self.previous_system = (total, idle)
        rows = []
        for label, pid in list(self.processes.items()):
            try:
                ticks, rss, read_b, write_b = self._process(pid)
            except (FileNotFoundError, ProcessLookupError, AttributeError):
                continue
            previous = self.previous_process.get(pid, ticks)
            process_percent = (ticks - previous) / clock_ticks / self.interval * 100.0
            self.previous_process[pid] = ticks
            rows.append(f"{utc_now()}\t{system_percent:.3f}\t{memory_total()}\t{self._available_memory()}\t{label}\t{pid}\t{process_percent:.3f}\t{rss}\t{read_b}\t{write_b}\n")
        if rows:
            with self.output.open("a", encoding="utf-8") as stream:
                stream.writelines(rows)

    def _run(self) -> None:
        try:
            while not self.stop_event.wait(self.interval):
                self._sample_once()
        except Exception:
            self.failure = traceback.format_exc()
            self.stop_event.set()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread.ident is not None:
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                raise RuntimeError("resource sampler did not stop within 5 seconds")


class KaggleSession:
    def __init__(self, input_root: str = "/kaggle/input", working_root: str = "/kaggle/working/byteme-g24k",
                 run_id: str | None = None):
        self.input_root = pathlib.Path(input_root).resolve()
        if not self.input_root.is_dir():
            raise RuntimeError(f"session input root does not exist: {self.input_root}")
        self.working_root = pathlib.Path(working_root)
        self.run_id = run_id or dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.run_dir = self.working_root / self.run_id
        if self.run_dir.exists():
            raise RuntimeError(f"run directory already exists: {self.run_dir}")
        self.evidence = self.run_dir / "evidence"
        self.runtime = self.run_dir / "runtime-secret"
        self.toolchain_dir = self.run_dir / "toolchain"
        self.processes: dict[str, subprocess.Popen] = {}
        self.active_driver: subprocess.Popen | None = None
        self.bundle_root: pathlib.Path | None = None
        self.config_path: pathlib.Path | None = None
        self.config: dict = {}
        self.tools: dict[str, pathlib.Path] = {}
        self.tool_versions: dict[str, str] = {}
        self.mysql_env = os.environ.copy()
        self.offline_dependencies: dict[str, dict] = {}
        self.dynamic_dependency_reports: dict[str, dict] = {}
        self.application_sha: str | None = None
        self.repository_sha: str | None = None
        self.db_password = secrets.token_urlsafe(24) + "9a!"
        self.actor_password = secrets.token_urlsafe(24) + "9a!"
        self.started_at = utc_now()

    def _write_json(self, relative: str, value: dict) -> None:
        path = self.evidence / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def probe(self) -> dict:
        self.evidence.mkdir(parents=True, exist_ok=False)
        self.runtime.mkdir(parents=True, exist_ok=False)
        os_release = read_os_release()
        cgroup = resolve_cgroup_limits()
        image = runtime_image_identity(os_release)
        probe = {
            "captured_at_utc": utc_now(),
            "is_kaggle": pathlib.Path("/kaggle").exists(),
            "prepared_input_root": str(self.input_root),
            "hardware": {"cpu_model": cpu_model(), "logical_cores": os.cpu_count(),
                         "memory_total_bytes": memory_total(),
                         "cgroup": cgroup,
                         "disk_working": shutil.disk_usage(self.working_root.parent if self.working_root.parent.exists() else "/tmp")._asdict()},
            "runtime": {"platform": platform.platform(), "kernel": platform.release(),
                        "python": platform.python_version(), "uid": os.geteuid() if hasattr(os, "geteuid") else None,
                        "os_id": os_release.get("ID"), "os_version": os_release.get("VERSION_ID"),
                        "image_identity": image},
            "capabilities": {"docker": shutil.which("docker"), "apt_get": shutil.which("apt-get"),
                             "sudo": shutil.which("sudo"), "openssl": shutil.which("openssl"),
                             "dpkg_deb": shutil.which("dpkg-deb"), "ldd": shutil.which("ldd")},
        }
        self._write_json("environment/hardware-runtime.json", probe)
        return probe

    def _find_single(self, name: str) -> pathlib.Path:
        matches = list(self.input_root.rglob(name))
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one {name} below {self.input_root}, found {len(matches)}")
        return matches[0]

    def resolve_bundle(self) -> None:
        manifest_path = self._find_single("bundle-manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if manifest.get("protocol_baseline_sha") != BASELINE_SHA:
            raise RuntimeError(f"bundle protocol baseline mismatch: {manifest.get('protocol_baseline_sha')}")
        self.application_sha = manifest.get("application_sha")
        if not isinstance(self.application_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", self.application_sha):
            raise RuntimeError("bundle application_sha is absent or invalid")
        self.repository_sha = manifest.get("repository_sha")
        if not isinstance(self.repository_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", self.repository_sha):
            raise RuntimeError("bundle repository_sha is absent or invalid")
        self.bundle_root = manifest_path.parent
        for item in manifest["files"]:
            path = self.bundle_root / item["path"]
            if not path.is_file() or sha256(path) != item["sha256"]:
                raise RuntimeError(f"bundle checksum mismatch: {item['path']}")
        jar_path = self.bundle_root / "application.jar"
        jar_hash = sha256(jar_path) if jar_path.is_file() else None
        if manifest.get("schema_version") != 2 or jar_hash != manifest.get("application_jar_sha256"):
            raise RuntimeError("bundle JAR provenance/hash is absent or inconsistent")
        provenance_path = self.bundle_root / manifest.get("build_provenance_path", "")
        if not provenance_path.is_file():
            raise RuntimeError("bundle build provenance is absent")
        provenance = json.loads(provenance_path.read_text(encoding="utf-8-sig"))
        if (provenance.get("application_sha") != self.application_sha or
                provenance.get("jar_sha256") != jar_hash or provenance.get("build_exit_code") != 0):
            raise RuntimeError("bundle build provenance does not match application/JAR")
        candidates = list(self.bundle_root.rglob("configuration-lock.json"))
        if len(candidates) != 1:
            raise RuntimeError("configuration-lock.json missing or ambiguous")
        self.config_path = candidates[0]
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        if self.config.get("baseline_sha") != BASELINE_SHA:
            raise RuntimeError("configuration baseline mismatch")
        self._preflight_benchmark_files()
        shutil.copy2(manifest_path, self.evidence / "environment/bundle-manifest.json")

    def setup_offline_dependencies(self) -> None:
        lock = self.config["offline_dependencies"]["libaio"]
        matches = list(self.input_root.rglob(lock["filename"]))
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one locked libaio package below {self.input_root}, found {len(matches)}")
        package = matches[0]
        package_sha = sha256(package)
        if package_sha != lock["package_sha256"]:
            raise RuntimeError(f"libaio package checksum mismatch: {package_sha}")
        dpkg_deb = shutil.which("dpkg-deb")
        if not dpkg_deb:
            raise RuntimeError("dpkg-deb is unavailable; cannot extract locked offline dependency")
        metadata = {}
        for field, expected in (("Package", lock["package"]), ("Version", lock["version"]),
                                ("Architecture", lock["architecture"])):
            proc = subprocess.run([dpkg_deb, "--field", str(package), field], text=True,
                                  encoding="utf-8", errors="replace", capture_output=True, timeout=30)
            actual = proc.stdout.strip()
            if proc.returncode or actual != expected:
                raise RuntimeError(f"libaio package metadata mismatch for {field}: expected={expected}, actual={actual}")
            metadata[field.lower()] = actual

        package_root = self.toolchain_dir / "libaio-package"
        package_root.mkdir(parents=True, exist_ok=False)
        extract = subprocess.run([dpkg_deb, "--extract", str(package), str(package_root)], text=True,
                                 encoding="utf-8", errors="replace", capture_output=True, timeout=60)
        if extract.returncode:
            raise RuntimeError(f"libaio package extraction failed: {extract.stderr.strip()}")
        source = package_root / pathlib.PurePosixPath(lock["library_path"])
        if not source.is_file():
            raise RuntimeError(f"locked libaio library is absent after extraction: {source}")
        elf = inspect_elf_library(source, lock)

        library_dir = self.toolchain_dir / "libaio"
        library_dir.mkdir(parents=True, exist_ok=False)
        library = library_dir / source.name
        shutil.copy2(source, library)
        compatibility = library_dir / lock["compatibility_soname"]
        compatibility.symlink_to(library.name)
        if not compatibility.is_file() or sha256(compatibility) != lock["library_sha256"]:
            raise RuntimeError("libaio compatibility symlink validation failed")
        previous = self.mysql_env.get("LD_LIBRARY_PATH")
        self.mysql_env["LD_LIBRARY_PATH"] = str(library_dir) + (os.pathsep + previous if previous else "")
        evidence = {**metadata, "source_url": lock["source_url"], "filename": lock["filename"],
                    "package_sha256": package_sha, "library_path": str(library),
                    "compatibility_path": str(compatibility), "compatibility_soname": lock["compatibility_soname"],
                    "elf": elf, "ld_library_path_prefix": str(library_dir)}
        self.offline_dependencies["libaio"] = evidence
        self._write_json("environment/offline-dependencies.json", self.offline_dependencies)

    def _archives(self, component: str) -> list[pathlib.Path]:
        return _matching_files(self.input_root, TOOLCHAIN_ARCHIVE_PATTERNS[component])

    def _version(self, executable: pathlib.Path, args: list[str], env: dict | None = None) -> str:
        proc = subprocess.run([str(executable), *args], text=True, encoding="utf-8", errors="replace",
                              capture_output=True, timeout=30, env=env)
        return (proc.stdout + proc.stderr).strip()

    def _dynamic_dependencies(self, executable: pathlib.Path, env: dict) -> dict:
        ldd = shutil.which("ldd")
        if not ldd:
            raise RuntimeError("ldd is unavailable; cannot preflight MySQL shared libraries")
        proc = subprocess.run([ldd, str(executable)], text=True, encoding="utf-8", errors="replace",
                              capture_output=True, timeout=30, env=env)
        output = (proc.stdout + proc.stderr).strip()
        if proc.returncode or not output or "not a dynamic executable" in output.lower():
            raise RuntimeError(f"ldd preflight failed for {executable}: exit={proc.returncode}, output={output}")
        return {"executable": str(executable), "exit_code": proc.returncode,
                "missing": parse_ldd_missing(output), "output": output}

    def _select_tool(self, component: str, binary: str, version_args: list[str], expected: str,
                     env: dict | None = None, dynamic_preflight: bool = False) -> tuple[pathlib.Path, str]:
        candidates = []
        input_names = (binary, f"{binary}.exe") if os.name == "nt" else (binary,)
        for name in input_names:
            candidates.extend(path for path in self.input_root.rglob(name) if path.is_file())
        archives = self._archives(component)
        if len(archives) > 1:
            raise RuntimeError(f"multiple {component} archives attached; keep exactly one: {archives}")
        if archives:
            destination = self.toolchain_dir / component
            safe_extract(archives[0], destination)
            candidates.extend(destination.rglob(binary))
        system = shutil.which(binary)
        if system:
            candidates.append(pathlib.Path(system))
        checked = []
        for candidate in candidates:
            if not candidate.is_file():
                continue
            if not os.access(candidate, os.X_OK):
                candidate.chmod(candidate.stat().st_mode | 0o111)
            try:
                dependency_report = self._dynamic_dependencies(candidate, env or os.environ.copy()) if dynamic_preflight else None
                if dependency_report and dependency_report["missing"]:
                    checked.append(f"{candidate}: missing shared libraries {dependency_report['missing']}")
                    continue
                version = self._version(candidate, version_args, env)
            except Exception as exc:
                checked.append(f"{candidate}: {exc}")
                continue
            checked.append(f"{candidate}: {version.splitlines()[0] if version else 'empty'}")
            if expected in version:
                if dependency_report:
                    self.dynamic_dependency_reports[str(candidate)] = dependency_report
                return candidate.resolve(), version
        raise RuntimeError(f"no exact {component} {expected}; checked={checked}; archives={archives}")

    def setup_toolchain(self) -> None:
        expected = self.config["expected_versions"]
        self.toolchain_dir.mkdir(parents=True, exist_ok=False)
        self.setup_offline_dependencies()
        java, java_v = self._select_tool("java", "java", ["-version"], expected["java_contains"])
        mysqld, mysql_v = self._select_tool("mysql", "mysqld", ["--version"], expected["mysql_contains"],
                                            self.mysql_env, dynamic_preflight=True)
        k6, k6_v = self._select_tool("k6", "k6", ["version"], expected["k6_contains"])
        mysql_bin = mysqld.parent / "mysql"
        mysqladmin = mysqld.parent / "mysqladmin"
        if not mysql_bin.exists() and shutil.which("mysql"):
            mysql_bin = pathlib.Path(shutil.which("mysql"))
        if not mysqladmin.exists() and shutil.which("mysqladmin"):
            mysqladmin = pathlib.Path(shutil.which("mysqladmin"))
        if not mysql_bin.exists() or not mysqladmin.exists():
            raise RuntimeError("selected MySQL distribution lacks mysql/mysqladmin clients")
        for client in (mysql_bin, mysqladmin):
            dependency_report = self._dynamic_dependencies(client, self.mysql_env)
            if dependency_report["missing"]:
                raise RuntimeError(f"MySQL client shared libraries missing: {client}: {dependency_report['missing']}")
            self.dynamic_dependency_reports[str(client)] = dependency_report
            client_version = self._version(client, ["--version"], self.mysql_env)
            if expected["mysql_contains"] not in client_version:
                raise RuntimeError(f"MySQL client version mismatch: {client}: {client_version}")
        self.tools = {"java": java, "mysqld": mysqld, "mysql": mysql_bin, "mysqladmin": mysqladmin, "k6": k6}
        self.tool_versions = {"java_version": java_v, "mysql_version": mysql_v, "k6_version": k6_v}
        self._write_json("environment/mysql-dynamic-dependencies.json", {
            "ld_library_path": self.mysql_env.get("LD_LIBRARY_PATH"),
            "executables": self.dynamic_dependency_reports,
            "all_dependencies_resolved": all(not item["missing"] for item in self.dynamic_dependency_reports.values()),
        })
        self._write_json("environment/toolchain.json", {
            **self.tool_versions,
            "executables": {key: str(value) for key, value in self.tools.items()},
            "sha256": {key: sha256(value) for key, value in self.tools.items()},
            "offline_dependencies": self.offline_dependencies,
        })

    def _mysql(self, sql: str, user: str = "root", password: str = "", database: str | None = None) -> str:
        runtime = self.config["runtime"]
        command = [str(self.tools["mysql"]), "--batch", "--raw", "--user", user]
        if user == "root":
            command.extend(["--protocol=SOCKET", "--socket", str(self.run_dir / "mysql-runtime/mysql.sock")])
        else:
            command.extend(["--protocol=TCP", "--host", runtime["mysql_host"],
                            "--port", str(runtime["mysql_port"])])
        if database:
            command.append(database)
        env = self.mysql_env.copy()
        env["MYSQL_PWD"] = password
        proc = subprocess.run(command, input=sql, text=True, encoding="utf-8", capture_output=True, env=env)
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip())
        return proc.stdout

    def _mysql_identity(self) -> tuple[int, int, str]:
        """Return an unprivileged identity; Kaggle notebooks can run as UID 0."""
        current_uid = os.geteuid() if hasattr(os, "geteuid") else -1
        current_gid = os.getegid() if hasattr(os, "getegid") else -1
        if current_uid != 0:
            return current_uid, current_gid, "current-user"
        if pwd is None:
            raise RuntimeError("root privilege drop is only supported on Linux")
        try:
            account = pwd.getpwnam("mysql")
        except KeyError:
            try:
                account = pwd.getpwnam("nobody")
            except KeyError as exc:
                raise RuntimeError("running as root but no mysql/nobody account is available") from exc
        if account.pw_uid == 0 or account.pw_gid == 0:
            raise RuntimeError(f"refusing privileged MySQL identity: uid={account.pw_uid}, gid={account.pw_gid}")
        return account.pw_uid, account.pw_gid, account.pw_name

    @staticmethod
    def _drop_mysql_privileges(uid: int, gid: int):
        def demote() -> None:
            os.setgid(gid)
            os.setuid(uid)
        return demote

    def _prepare_mysql_writable_paths(self, paths: list[pathlib.Path], uid: int, gid: int) -> None:
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
            if hasattr(os, "geteuid") and os.geteuid() == 0:
                os.chown(path, uid, gid)
            try:
                mode = stat.S_IMODE(path.stat().st_mode)
                path.chmod(mode | stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                           stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP)
            except OSError as exc:
                raise RuntimeError(f"cannot prepare MySQL writable directory {path}: {exc}") from exc
            if not os.access(path, os.W_OK | os.X_OK):
                raise RuntimeError(f"MySQL identity cannot write directory: {path}")

    def start_mysql(self) -> None:
        runtime = self.config["runtime"]
        base = self.tools["mysqld"].parent.parent
        data = self.run_dir / "mysql-data"
        mysql_runtime = self.run_dir / "mysql-runtime"
        mysql_log_dir = self.evidence / "logs/mysql-server"
        mysql_uid, mysql_gid, mysql_account = self._mysql_identity()
        self._prepare_mysql_writable_paths([data, mysql_runtime, mysql_log_dir], mysql_uid, mysql_gid)
        config = self.run_dir / "mysql.cnf"
        config.write_text("\n".join([
            "[mysqld]", f"basedir={base}", f"datadir={data}", f"port={runtime['mysql_port']}",
            "bind-address=127.0.0.1", f"socket={mysql_runtime / 'mysql.sock'}", f"pid-file={mysql_runtime / 'mysql.pid'}",
            f"log-error={mysql_log_dir / 'mysql.log'}", "skip-name-resolve=ON", "mysqlx=OFF",
            f"transaction-isolation={runtime['mysql_transaction_isolation']}",
            f"max-connections={runtime['mysql_max_connections']}",
            f"innodb-buffer-pool-size={runtime['mysql_innodb_buffer_pool_size']}", "performance-schema=ON", "",
        ]), encoding="utf-8")
        self.mysql_process_identity = {"uid": mysql_uid, "gid": mysql_gid, "account": mysql_account}
        self._write_json("environment/mysql-process-identity.json", self.mysql_process_identity)
        demote = self._drop_mysql_privileges(mysql_uid, mysql_gid) if hasattr(os, "geteuid") and os.geteuid() == 0 else None
        init = subprocess.run([str(self.tools["mysqld"]), f"--defaults-file={config}", "--initialize-insecure"],
                              text=True, capture_output=True, env=self.mysql_env, preexec_fn=demote)
        if init.returncode:
            raise RuntimeError(f"mysqld initialize failed under uid={mysql_uid}, gid={mysql_gid}: {init.stderr}")
        for path in (data, mysql_runtime, mysql_log_dir):
            if hasattr(os, "geteuid") and os.geteuid() == 0:
                os.chown(path, mysql_uid, mysql_gid)
        startup_stdout = self.evidence / "logs/mysql-startup.stdout.log"
        startup_stderr = self.evidence / "logs/mysql-startup.stderr.log"
        with startup_stdout.open("wb") as stdout, startup_stderr.open("wb") as stderr:
            process = subprocess.Popen([str(self.tools["mysqld"]), f"--defaults-file={config}"],
                                       stdout=stdout, stderr=stderr, env=self.mysql_env, preexec_fn=demote)
        self.processes["mysql"] = process
        deadline = time.time() + 120
        while time.time() < deadline:
            if process.poll() is not None:
                self._mysql_startup_diagnostics(process, "early_exit", data)
                raise RuntimeError("mysqld exited during startup; see logs/mysql-startup.stderr.log, "
                                   "logs/mysql-startup.stdout.log, logs/mysql.log and "
                                   "environment/mysql-startup-failure.json in the evidence ZIP")
            ping = subprocess.run([str(self.tools["mysqladmin"]), "--protocol=SOCKET",
                                   "--socket", str(mysql_runtime / "mysql.sock"), "-uroot", "ping"],
                                  capture_output=True, env=self.mysql_env)
            if ping.returncode == 0:
                break
            time.sleep(1)
        else:
            self._mysql_startup_diagnostics(process, "readiness_timeout", data)
            raise RuntimeError("mysqld readiness timeout; see logs/mysql-startup.stderr.log, "
                               "logs/mysql.log and environment/mysql-startup-failure.json in the evidence ZIP")
        database, user = runtime["database"], runtime["database_user"]
        quoted_password = self.db_password.replace("'", "''")
        self._mysql(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;"
                    f"CREATE USER '{user}'@'127.0.0.1' IDENTIFIED BY '{quoted_password}';"
                    f"CREATE USER '{user}'@'localhost' IDENTIFIED BY '{quoted_password}';"
                    f"GRANT ALL ON `{database}`.* TO '{user}'@'127.0.0.1';"
                    f"GRANT ALL ON `{database}`.* TO '{user}'@'localhost'; FLUSH PRIVILEGES;")
        schema = self._find_single("schema.sql")
        self._mysql(schema.read_text(encoding="utf-8"), user, self.db_password, database)

    def _mysql_startup_diagnostics(self, process: subprocess.Popen, reason: str, data: pathlib.Path) -> None:
        """Capture startup facts before cleanup removes the run's datadir and socket."""
        code = process.poll()
        runtime = self.config["runtime"]
        mysql_runtime = self.run_dir / "mysql-runtime"
        paths = {"datadir": data, "socket_parent": mysql_runtime,
                 "socket": mysql_runtime / "mysql.sock", "pid_file": mysql_runtime / "mysql.pid",
                 "log_directory": self.evidence / "logs/mysql-server"}
        path_status = {}
        for name, path in paths.items():
            try:
                info = path.stat()
                path_status[name] = {"exists": True, "mode": oct(stat.S_IMODE(info.st_mode)),
                                     "readable": os.access(path, os.R_OK), "writable": os.access(path, os.W_OK),
                                     "executable": os.access(path, os.X_OK), "is_directory": path.is_dir()}
            except FileNotFoundError:
                path_status[name] = {"exists": False}
            except OSError as exc:
                path_status[name] = {"stat_error": f"{type(exc).__name__}: {exc}"}
        try:
            with socket.create_connection((runtime["mysql_host"], runtime["mysql_port"]), timeout=1):
                port_status = "accepting_connections"
        except OSError as exc:
            port_status = f"not_accepting: {type(exc).__name__}: {exc}"
        cgroup = {}
        for candidate in ("/sys/fs/cgroup/memory.events", "/sys/fs/cgroup/memory/memory.oom_control",
                          "/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory.max"):
            try:
                cgroup[candidate] = pathlib.Path(candidate).read_text(encoding="utf-8").strip()
            except OSError:
                pass
        mysql_log = self.evidence / "logs/mysql.log"
        self._write_json("environment/mysql-startup-failure.json", {
            "reason": reason, "exit_code": code, "signal": -code if code is not None and code < 0 else None,
            "logs": {"stdout": "logs/mysql-startup.stdout.log", "stderr": "logs/mysql-startup.stderr.log",
                     "mysql_error": "logs/mysql.log", "mysql_error_exists": mysql_log.is_file(),
                     "mysql_error_bytes": mysql_log.stat().st_size if mysql_log.is_file() else None},
            "port": {"host": runtime["mysql_host"], "number": runtime["mysql_port"], "status": port_status},
            "paths": path_status, "cgroup": cgroup,
        })

    def start_backend(self) -> None:
        if not shutil.which("openssl"):
            raise RuntimeError("openssl is unavailable; attach a portable binary or use a Kaggle image that provides it")
        keys = self.runtime / "keys"
        keys.mkdir(parents=True)
        subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072",
                        "-out", str(keys / "private.pem")], check=True, capture_output=True)
        subprocess.run(["openssl", "pkey", "-in", str(keys / "private.pem"), "-pubout",
                        "-out", str(keys / "public.pem")], check=True, capture_output=True)
        jar = self._find_single("application.jar")
        runtime = self.config["runtime"]
        env = os.environ.copy()
        env.update({
            "DB_URL": f"jdbc:mysql://127.0.0.1:{runtime['mysql_port']}/{runtime['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC",
            "DB_USERNAME": runtime["database_user"], "DB_PASSWORD": self.db_password,
            "SERVER_PORT": str(runtime["backend_port"]),
            "AUTH_JWT_PRIVATE_KEY_FILE": str(keys / "private.pem"), "AUTH_JWT_PUBLIC_KEY_FILE": str(keys / "public.pem"),
            "SPRING_DATASOURCE_HIKARI_MAXIMUM_POOL_SIZE": str(runtime["hikari_maximum_pool_size"]),
            "SPRING_DATASOURCE_HIKARI_MINIMUM_IDLE": str(runtime["hikari_minimum_idle"]),
            "SERVER_TOMCAT_THREADS_MAX": str(runtime["tomcat_threads_max"]),
            "SERVER_TOMCAT_THREADS_MIN_SPARE": str(runtime["tomcat_threads_min_spare"]),
        })
        log_path = self.evidence / "logs/backend.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log = log_path.open("w", encoding="utf-8")
        gc_log = self.evidence / "logs/gc.log"
        command = [str(self.tools["java"]), *runtime["java_options"],
                   f"-Xlog:gc*:file={gc_log}:time,level,tags", "-jar", str(jar)]
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
        self.processes["backend"] = process
        deadline = time.time() + 180
        url = f"http://127.0.0.1:{runtime['backend_port']}/actuator/health"
        while time.time() < deadline:
            if process.poll() is not None:
                log.close()
                raise RuntimeError("backend exited during startup")
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError):
                pass
            time.sleep(2)
        raise RuntimeError("backend readiness timeout")

    def _db_telemetry(self, relative: str) -> None:
        database = self.config["runtime"]["database"]
        sql = """
SELECT UTC_TIMESTAMP(6) captured_at_utc, VERSION() mysql_version, DATABASE() database_name;
SHOW GLOBAL STATUS WHERE Variable_name IN ('Threads_connected','Threads_running','Connections','Questions','Queries','Com_select','Com_insert','Com_update','Com_delete','Slow_queries','Created_tmp_disk_tables','Created_tmp_tables','Innodb_buffer_pool_read_requests','Innodb_buffer_pool_reads','Innodb_row_lock_current_waits','Innodb_row_lock_time','Innodb_row_lock_waits');
SELECT DIGEST, LEFT(DIGEST_TEXT,500), COUNT_STAR, ROUND(SUM_TIMER_WAIT/1000000000,3), SUM_ROWS_AFFECTED, SUM_ROWS_SENT, SUM_ROWS_EXAMINED, SUM_CREATED_TMP_DISK_TABLES, SUM_NO_INDEX_USED FROM performance_schema.events_statements_summary_by_digest WHERE SCHEMA_NAME=DATABASE() AND DIGEST IS NOT NULL ORDER BY COUNT_STAR DESC,DIGEST LIMIT 200;
"""
        path = self.evidence / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self._mysql(sql, "root", "", database)
        path.write_text(content, encoding="utf-8")
        if "captured_at_utc" not in content or "Variable_name" not in content:
            raise RuntimeError(f"DB telemetry incomplete: {relative}")

    def _benchmark_root(self) -> pathlib.Path:
        assert self.bundle_root
        matches = list(self.bundle_root.rglob("benchmarks/phase2/profiles.json"))
        if len(matches) != 1:
            raise RuntimeError(f"bundled benchmark root missing or ambiguous below {self.bundle_root}; matches={matches}")
        return matches[0].parent

    def _preflight_benchmark_files(self) -> None:
        root = self._benchmark_root()
        required = [root / "profiles.json", root / "prepare_dataset.py",
                    root / "workloads/w1_read.js", root / "workloads/w2_write.js",
                    root / "workloads/w3_contention.py", self.bundle_root / "schema.sql"]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(f"benchmark bundle preflight missing required files: {missing}")
        workloads = root / "workloads"
        if not workloads.is_dir():
            raise RuntimeError(f"benchmark bundle preflight missing workloads directory: {workloads}")

    def _dataset_command(self, mode: str, profile: str, output: pathlib.Path) -> list[str]:
        root = self._benchmark_root()
        runtime = self.config["runtime"]
        return ["python", "-X", "utf8", str(root / "prepare_dataset.py"), "--mode", mode, "--profile", profile,
                "--project", "byteme-g24-kaggle", "--db-mode", "direct", "--mysql-bin", str(self.tools["mysql"]),
                "--mysql-host", runtime["mysql_host"], "--mysql-port", str(runtime["mysql_port"]),
                "--mysql-user", runtime["database_user"], "--mysql-database", runtime["database"],
                "--mysql-password-env", "BENCH_DB_PASSWORD", "--base-url", f"http://127.0.0.1:{runtime['backend_port']}",
                "--runtime-actors", str(self.runtime / "actors.json"), "--output", str(output)]

    def _backend_alive(self, stage: str, health: bool = False) -> None:
        backend = self.processes.get("backend")
        code = backend.poll() if backend is not None else None
        self._write_json("environment/backend-lifecycle.json", {
            "stage": stage, "captured_at_utc": utc_now(),
            "pid": backend.pid if backend else None, "exit_code": code,
            "log": "logs/backend.log", "alive": backend is not None and code is None,
        })
        if backend is None or code is not None:
            raise RuntimeError(f"backend unavailable at {stage}: pid={backend.pid if backend else None}, "
                               f"exit_code={code}; see logs/backend.log and environment/backend-lifecycle.json")
        if health:
            url = f"http://127.0.0.1:{self.config['runtime']['backend_port']}/actuator/health"
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status != 200:
                    raise RuntimeError(f"backend health failed before {stage}: HTTP {response.status}")

    def _stop_driver(self) -> None:
        process = self.active_driver
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            self.active_driver = None

    def _run(self, command: list[str], relative_console: str, relative_resources: str | None = None,
             extra_env: dict[str, str] | None = None,
             required_resource_labels: set[str] | None = None) -> dict | None:
        env = os.environ.copy()
        env.update({"BENCH_DB_PASSWORD": self.db_password, "BENCH_ACTOR_PASSWORD": self.actor_password})
        if extra_env:
            env.update(extra_env)
        console = self.evidence / relative_console
        console.parent.mkdir(parents=True, exist_ok=True)
        if relative_resources:
            self._backend_alive(relative_console, health=True)
        with console.open("w", encoding="utf-8") as stream:
            process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, env=env)
            self.active_driver = process
            sampler = None
            primary = None
            try:
                if relative_resources:
                    pids = {key: value.pid for key, value in self.processes.items() if value.poll() is None}
                    pids["driver"] = process.pid
                    sampler = ResourceSampler(self.evidence / relative_resources, pids)
                    sampler.start()
                while True:
                    if relative_resources:
                        self._backend_alive(relative_console)
                    if sampler and sampler.failure:
                        raise RuntimeError(f"resource sampler failed:\n{sampler.failure}")
                    try:
                        code = process.wait(timeout=0.25)
                        break
                    except subprocess.TimeoutExpired:
                        continue
                if relative_resources:
                    self._backend_alive(relative_console + ":completed")
            except BaseException as exc:
                primary = exc
                raise
            finally:
                errors = []
                try:
                    self._stop_driver()
                except Exception as exc:
                    errors.append(f"driver stop: {exc}")
                if sampler:
                    try:
                        sampler.stop()
                        if sampler.failure:
                            errors.append(f"sampler: {sampler.failure}")
                    except Exception as exc:
                        errors.append(f"sampler stop: {exc}")
                if errors:
                    if primary is not None:
                        primary.add_note("; ".join(errors))
                    else:
                        raise RuntimeError("; ".join(errors))
        if code:
            raise RuntimeError(f"command failed ({code}): {' '.join(command[:4])}; see {relative_console}")
        if relative_resources:
            return validate_resource_samples(self.evidence / relative_resources,
                                             required_resource_labels or {"backend", "mysql", "driver"})
        return None

    def run_workloads(self) -> tuple[str, str]:
        root = self._benchmark_root()
        runtime = self.config["runtime"]
        initial = self.evidence / "dataset/initial.json"
        self._run(self._dataset_command("prepare", "smoke", initial), "dataset/prepare-console.txt")
        initial_doc = json.loads(initial.read_text(encoding="utf-8"))
        if initial_doc.get("validation_phase") != "initial" or not initial_doc.get("all_invariants_pass"):
            raise RuntimeError("initial dataset validation did not pass")
        initial_sha = initial_doc["overall_sha256"]
        actors, base = self.runtime / "actors.json", f"http://127.0.0.1:{runtime['backend_port']}"
        self._db_telemetry("database/before-w1.txt")
        w1 = self.evidence / "w1"
        w1.mkdir(parents=True)
        self._run([str(self.tools["k6"]), "run", "--no-color", "--out", f"json={w1 / 'raw.json'}",
                   str(root / "workloads/w1_read.js")], "w1/console.txt", "w1/resources.tsv",
                  {"ACTORS_FILE": str(actors), "BASE_URL": base, "BENCH_MODE": "smoke",
                   "ORDER_PAGE_SIZE": "20", "SUMMARY_PATH": str(w1 / "summary.json")})
        if not (w1 / "raw.json").is_file() or (w1 / "raw.json").stat().st_size == 0:
            raise RuntimeError("W1 raw k6 output missing or empty")
        self._write_json("w1/validation.json", validate_k6_smoke_summary(
            w1 / "summary.json", "W1", self.config["smoke"]["expected_w1_checks"],
            self.config["smoke"]["expected_w1_requests"]))
        self._db_telemetry("database/after-w1.txt")
        w2 = self.evidence / "w2"
        w2.mkdir(parents=True)
        self._run([str(self.tools["k6"]), "run", "--no-color", "--out", f"json={w2 / 'raw.json'}",
                   str(root / "workloads/w2_write.js")], "w2/console.txt", "w2/resources.tsv",
                  {"ACTORS_FILE": str(actors), "BASE_URL": base, "BENCH_MODE": "smoke", "WRITE_VUS": "2",
                   "SUMMARY_PATH": str(w2 / "summary.json")})
        if not (w2 / "raw.json").is_file() or (w2 / "raw.json").stat().st_size == 0:
            raise RuntimeError("W2 raw k6 output missing or empty")
        self._write_json("w2/validation.json", validate_k6_smoke_summary(
            w2 / "summary.json", "W2", self.config["smoke"]["expected_w2_checks"],
            self.config["smoke"]["expected_w2_requests"]))
        self._db_telemetry("database/after-w2.txt")
        w3 = self.evidence / "w3"
        w3.mkdir(parents=True)
        command = ["python", "-X", "utf8", str(root / "workloads/w3_contention.py"),
                   "--project", "byteme-g24-kaggle", "--db-mode", "direct", "--mysql-bin", str(self.tools["mysql"]),
                   "--mysql-host", runtime["mysql_host"], "--mysql-port", str(runtime["mysql_port"]),
                   "--mysql-user", runtime["database_user"], "--mysql-database", runtime["database"],
                   "--mysql-password-env", "BENCH_DB_PASSWORD", "--base-url", base, "--actors", str(actors),
                   "--rounds", str(self.config["smoke"]["w3_rounds"]), "--output", str(w3 / "result.json")]
        self._run(command, "w3/console.txt", "w3/resources.tsv")
        self._write_json("w3/validation.json", validate_w3_smoke_result(
            w3 / "result.json", self.config["smoke"]["w3_rounds"]))
        self._db_telemetry("database/after-w3.txt")
        post = self.evidence / "dataset/post-workloads.json"
        self._run(self._dataset_command("snapshot", "smoke", post), "dataset/post-workloads-console.txt")
        post_doc = json.loads(post.read_text(encoding="utf-8"))
        if post_doc.get("validation_phase") != "post_workload" or not post_doc.get("all_invariants_pass"):
            raise RuntimeError("post-workload consistency validation did not pass")
        reset = self.evidence / "dataset/after-reset.json"
        self._run(self._dataset_command("prepare", "smoke", reset), "dataset/reset-console.txt")
        reset_doc = json.loads(reset.read_text(encoding="utf-8"))
        if reset_doc.get("validation_phase") != "initial" or not reset_doc.get("all_invariants_pass"):
            raise RuntimeError("reset initial-state validation did not pass")
        reset_sha = reset_doc["overall_sha256"]
        if reset_sha != initial_sha:
            raise RuntimeError(f"reset checksum mismatch: {initial_sha} != {reset_sha}")
        return initial_sha, reset_sha

    def _source_hash(self) -> str:
        root = self._benchmark_root()
        digest = hashlib.sha256()
        for path in sorted(root.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                digest.update(path.relative_to(root).as_posix().encode())
                digest.update(bytes.fromhex(sha256(path)))
        return digest.hexdigest()

    def write_run_manifest(self, dataset_sha: str | None) -> None:
        hardware = json.loads((self.evidence / "environment/hardware-runtime.json").read_text(encoding="utf-8"))
        toolchain = json.loads((self.evidence / "environment/toolchain.json").read_text(encoding="utf-8")) if (self.evidence / "environment/toolchain.json").exists() else {}
        libaio = toolchain.get("offline_dependencies", {}).get("libaio", {})
        manifest = {
            "run_id": self.run_id, "timestamp_timezone": {"timestamps": "UTC", "project_timezone": "Asia/Saigon"},
            "source": {"protocol_baseline_sha": BASELINE_SHA, "repository_sha": self.repository_sha,
                       "application_sha": self.application_sha,
                       "application_jar_sha256": sha256(self._find_single("application.jar")) if self.bundle_root else None},
            "hardware": {"cpu_model": hardware["hardware"]["cpu_model"],
                         "logical_cores": hardware["hardware"]["logical_cores"],
                         "memory_total_bytes": hardware["hardware"]["memory_total_bytes"],
                         "cgroup": hardware["hardware"].get("cgroup"),
                         "os_id": hardware["runtime"]["os_id"], "os_version": hardware["runtime"]["os_version"],
                         "kernel": hardware["runtime"].get("kernel"),
                         "runtime_image_identity": hardware["runtime"].get("image_identity", {}).get("identity_sha256")},
            "toolchain": {"java_version": toolchain.get("java_version"), "mysql_version": toolchain.get("mysql_version"),
                          "k6_version": toolchain.get("k6_version"),
                          "java_executable_sha256": toolchain.get("sha256", {}).get("java"),
                          "mysqld_executable_sha256": toolchain.get("sha256", {}).get("mysqld"),
                          "k6_executable_sha256": toolchain.get("sha256", {}).get("k6"),
                          "libaio_package_version": libaio.get("version"),
                          "libaio_package_sha256": libaio.get("package_sha256"),
                          "libaio_library_sha256": libaio.get("elf", {}).get("sha256"),
                          "libaio_library_soname": libaio.get("elf", {}).get("soname"),
                          "libaio_compatibility_soname": libaio.get("compatibility_soname")},
            "locks": {"configuration_sha256": sha256(self.config_path) if self.config_path else None,
                      "workload_source_sha256": self._source_hash() if self.bundle_root else None,
                      "dataset_sha256": dataset_sha},
        }
        self._write_json("manifest/run-manifest.json", manifest)

    def _checksums(self) -> None:
        lines = []
        for path in sorted(self.evidence.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS.txt":
                lines.append(f"{sha256(path)}  {path.relative_to(self.evidence).as_posix()}")
        (self.evidence / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="ascii")

    def cleanup(self) -> dict:
        errors = []
        try:
            self._stop_driver()
        except Exception as exc:
            return {"success": False, "errors": [f"driver still active; services retained: {exc}"]}
        backend = self.processes.get("backend")
        if backend and backend.poll() is None:
            try:
                backend.terminate()
                try:
                    backend.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    backend.kill()
                    backend.wait(timeout=10)
            except Exception as exc:
                errors.append(f"backend cleanup: {type(exc).__name__}: {exc}")
        mysql = self.processes.get("mysql")
        if mysql and mysql.poll() is None:
            try:
                runtime = self.config["runtime"]
                shutdown = subprocess.run([str(self.tools["mysqladmin"]), "--protocol=SOCKET",
                                           "--socket", str(self.run_dir / "mysql-runtime/mysql.sock"), "-uroot", "shutdown"],
                                          timeout=20, capture_output=True, env=self.mysql_env)
                if shutdown.returncode:
                    mysql.send_signal(signal.SIGTERM)
                try:
                    mysql.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    mysql.kill()
                    mysql.wait(timeout=10)
            except Exception as exc:
                errors.append(f"mysql cleanup: {type(exc).__name__}: {exc}")
        backend_stopped = not backend or backend.poll() is not None
        mysql_stopped = not mysql or mysql.poll() is not None
        if not backend_stopped:
            errors.append("backend cleanup: process still running")
        if not mysql_stopped:
            errors.append("mysql cleanup: process still running")
        if self.runtime.exists():
            try:
                shutil.rmtree(self.runtime)
            except Exception as exc:
                errors.append(f"runtime-secret cleanup: {type(exc).__name__}: {exc}")
        runtime_removed = not self.runtime.exists()
        if not runtime_removed:
            errors.append("runtime-secret cleanup: directory still exists")
        return {"success": not errors, "backend_stopped": backend_stopped,
                "mysql_stopped": mysql_stopped, "runtime_secret_removed": runtime_removed,
                "errors": errors}

    def scan_evidence_secrets(self) -> list[str]:
        violations = []
        jwt = re.compile(rb"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
        exact = [self.db_password.encode(), self.actor_password.encode(), b"-----BEGIN PRIVATE KEY-----",
                 b"-----BEGIN RSA PRIVATE KEY-----"]
        for path in self.evidence.rglob("*"):
            if not path.is_file():
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if any(secret and secret in data for secret in exact) or jwt.search(data):
                violations.append(path.relative_to(self.evidence).as_posix())
        return violations

    def run_smoke(self) -> dict:
        if not self.evidence.exists():
            self.probe()
        status, error, initial_sha, reset_sha = "FAIL", None, None, None
        finalization_errors = []
        cleanup = {}
        try:
            probe = json.loads((self.evidence / "environment/hardware-runtime.json").read_text(encoding="utf-8"))
            if not probe.get("is_kaggle"):
                raise RuntimeError("not a Kaggle runtime; refusing to label this as Kaggle smoke")
            self.resolve_bundle()
            self.setup_toolchain()
            self.start_mysql()
            self.start_backend()
            initial_sha, reset_sha = self.run_workloads()
            status = "PASS"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            failure_trace = traceback.format_exc()
            for secret in (self.db_password, self.actor_password):
                failure_trace = failure_trace.replace(secret, "[REDACTED]")
                error = error.replace(secret, "[REDACTED]")
            failure_trace = re.sub(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
                                   "[REDACTED JWT]", failure_trace)
            trace_path = self.evidence / "logs/smoke-failure-traceback.txt"
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            trace_path.write_text(failure_trace, encoding="utf-8")
        finally:
            try:
                cleanup = self.cleanup()
            except Exception as exc:
                cleanup = {"success": False, "errors": [f"cleanup raised: {type(exc).__name__}: {exc}"]}
            if not cleanup.get("success"):
                finalization_errors.extend(cleanup.get("errors", ["cleanup failed"]))
            try:
                self.write_run_manifest(initial_sha)
            except Exception as exc:
                finalization_errors.append(f"manifest: {type(exc).__name__}: {exc}")
            secret_violations = self.scan_evidence_secrets()
            if secret_violations:
                finalization_errors.append(f"secret scan failed for {secret_violations}")
            if finalization_errors:
                status = "FAIL"
                suffix = "; ".join(finalization_errors)
                error = f"{error}; {suffix}" if error else suffix
            archive = self.working_root / f"{self.run_id}-evidence.zip"
            result = {"started_at_utc": self.started_at, "finished_at_utc": utc_now(), "official_benchmark": False,
                      "profile": "smoke", "status": status, "error": error,
                      "initial_dataset_sha256": initial_sha, "reset_dataset_sha256": reset_sha,
                      "reset_matches_initial": bool(initial_sha and initial_sha == reset_sha), "cleanup": cleanup,
                      "secret_scan_violations": secret_violations, "evidence_zip": str(archive)}
            self._write_json("smoke-result.json", result)
            try:
                self._checksums()
            except Exception as exc:
                result["status"] = "FAIL"
                result["error"] = f"{result['error']}; checksum: {type(exc).__name__}: {exc}" if result["error"] else f"checksum: {type(exc).__name__}: {exc}"
                self._write_json("smoke-result.json", result)
            try:
                with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                    for path in self.evidence.rglob("*"):
                        if path.is_file():
                            bundle.write(path, path.relative_to(self.evidence))
            except Exception as exc:
                result["status"] = "FAIL"
                result["error"] = f"{result['error']}; evidence zip: {type(exc).__name__}: {exc}" if result["error"] else f"evidence zip: {type(exc).__name__}: {exc}"
                self._write_json("smoke-result.json", result)
                try:
                    self._checksums()
                except Exception:
                    pass
        return result
