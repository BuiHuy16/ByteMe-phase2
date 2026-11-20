#!/usr/bin/env python3
"""Generate the checked-in Kaggle notebook from small auditable cells."""

from __future__ import annotations

import json
import pathlib
import textwrap


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": textwrap.dedent(source).strip().splitlines(True)}


def code(source: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
            "source": textwrap.dedent(source).strip().splitlines(True)}


notebook = {
    "cells": [
        markdown("""
        # ByteMe Phase 2 — G2.4-K Kaggle CPU smoke

        This notebook adapts the versioned G2.4 kit without changing its business workload. It is a **smoke test only**, never an official G2.5 baseline.

        Before Run All:

        1. Select **Accelerator: None**.
        2. Attach the private G2.4-K bundle dataset produced by `prepare_bundle.ps1`.
        3. Attach exactly one portable Linux x86_64 archive for Java 21.0.13, MySQL 8.4.13 and k6 0.55.2, unless the Kaggle image already reports that exact version.
        4. Do not attach credentials or shared databases. Download the evidence ZIP before the session expires.

        The runner probes root/apt/Docker only as capabilities; it does not assume or require them.
        """),
        code("""
        import datetime as dt
        import json
        import pathlib
        import sys

        runtime_files = list(pathlib.Path('/kaggle/input').rglob('benchmarks/phase2/kaggle/kaggle_runtime.py'))
        if len(runtime_files) != 1:
            raise RuntimeError(f'Expected one bundled kaggle_runtime.py, found {len(runtime_files)}: {runtime_files}')
        sys.path.insert(0, str(runtime_files[0].parent))
        from kaggle_runtime import KaggleSession

        RUN_ID = 'g24k-smoke-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        session = KaggleSession(run_id=RUN_ID)
        print({'run_id': RUN_ID, 'runtime_module': str(runtime_files[0])})
        """),
        code("""
        # Hardware/runtime fingerprint is written before any toolchain setup.
        probe = session.probe()
        print(json.dumps(probe, indent=2, ensure_ascii=False))
        """),
        code("""
        # This method fails closed, always attempts cleanup, writes checksums, and packages evidence.
        result = session.run_smoke()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if result['status'] != 'PASS':
            raise RuntimeError('Kaggle smoke did not pass; inspect the evidence ZIP and do not report PASS')
        """),
        markdown("""
        ## Result interpretation

        A green notebook is not enough by itself. Retain `smoke-result.json`, `manifest/run-manifest.json`, raw W1/W2 JSON, W3 result, resource/DB/JVM logs and `SHA256SUMS.txt` from the ZIP. A smoke PASS validates orchestration only; it is not an official Phase 1 performance result.

        Before G2.5, compare session manifests and reject different CPU model, core quota, RAM quota, OS image or toolchain/configuration/workload hashes. Run the standard profile only under the separately approved official protocol.
        """),
    ],
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
        "kaggle": {"accelerator": "none", "internet": False, "isGpuEnabled": False, "isInternetEnabled": False},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

output = pathlib.Path(__file__).resolve().parents[3] / "kaggle/script/byteme_phase2_g24k.ipynb"
output.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(output)
