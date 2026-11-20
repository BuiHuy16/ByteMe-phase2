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
        # ByteMe Phase 2 — G2.4-K smoke test trên Kaggle CPU

        Notebook này điều chỉnh bộ công cụ G2.4 đã được version hóa mà không thay đổi business workload. Đây **chỉ là smoke test**, không bao giờ là official baseline G2.5.

        Trước khi Run All:

        1. Chọn **Accelerator: None**.
        2. Attach private G2.4-K bundle dataset được tạo bởi `prepare_bundle.ps1`.
        3. Attach chính xác một portable Linux x86_64 archive cho mỗi tool Java 21.0.13, MySQL 8.4.13 và k6 0.55.2, trừ khi Kaggle image đã báo cáo đúng phiên bản đó.
        4. Không attach credentials hoặc shared database. Tải evidence ZIP trước khi session hết hạn.

        Runner chỉ probe root/apt/Docker như các capability; không giả định hoặc yêu cầu chúng.
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
        ## Diễn giải kết quả

        Chỉ một notebook màu xanh là chưa đủ. Hãy giữ lại `smoke-result.json`, `manifest/run-manifest.json`, raw W1/W2 JSON, W3 result, resource/DB/JVM logs và `SHA256SUMS.txt` từ file ZIP. Smoke PASS chỉ xác minh orchestration; đó không phải kết quả performance chính thức của Pha 1.

        Trước G2.5, hãy so sánh session manifest và từ chối các run có CPU model, core quota, RAM quota, OS image hoặc toolchain/configuration/workload hashes khác nhau. Chỉ chạy standard profile theo official protocol đã được phê duyệt riêng.
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
