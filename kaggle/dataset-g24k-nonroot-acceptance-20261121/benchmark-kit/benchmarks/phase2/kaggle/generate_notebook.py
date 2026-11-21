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

        Notebook này điều phối bộ công cụ G2.4 đã được khóa phiên bản mà không thay đổi business workload. Đây **chỉ là smoke test**, không phải official baseline G2.5.

        Trước khi Run All:

        1. Chọn **Accelerator: None**.
        2. Attach private G2.4-K bundle dataset được tạo bởi `prepare_bundle.ps1`.
        3. Attach Toolchain Dataset chứa đúng Java 21.0.13, MySQL 8.4.13, k6 0.55.2 và `libaio1t64_0.3.113-6build1.1_amd64.deb`.
        4. Java/k6 có thể còn ở dạng archive hoặc đã được Kaggle tự giải nén; bootstrap chính thức sẽ tự nhận diện, staging và kiểm tra phiên bản.
        5. Không attach credentials hoặc shared database. Tải evidence ZIP trước khi session hết hạn.

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
        from kaggle_runtime import KaggleSession, prepare_kaggle_input

        print({'runtime_module': str(runtime_files[0])})
        """),
        code("""
        # Chuẩn hóa đúng một input root trước khi tạo session. Không cần cell staging thủ công.
        SOURCE_INPUT_ROOT = pathlib.Path('/kaggle/input')
        BOOTSTRAP_ROOT = pathlib.Path('/kaggle/working/byteme-g24k-bootstrap')
        prepared_input_root = prepare_kaggle_input(SOURCE_INPUT_ROOT, BOOTSTRAP_ROOT)

        RUN_ID = 'g24k-smoke-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        session = KaggleSession(input_root=prepared_input_root, run_id=RUN_ID)
        if session.input_root != prepared_input_root.resolve():
            raise RuntimeError(f'KaggleSession lost prepared input root: {session.input_root}')
        bootstrap_manifest = json.loads((prepared_input_root / 'bootstrap-manifest.json').read_text())
        print({'run_id': RUN_ID, 'prepared_input_root': str(prepared_input_root),
               'toolchain': {key: value.get('version') for key, value in bootstrap_manifest['components'].items()}})
        """),
        code("""
        # Hardware/runtime fingerprint records the same prepared input root used by smoke.
        probe = session.probe()
        if pathlib.Path(probe['prepared_input_root']) != session.input_root:
            raise RuntimeError('Probe did not preserve the prepared input root')
        print(json.dumps(probe, indent=2, ensure_ascii=False))
        """),
        code("""
        # Preflight toolchain runs before MySQL; the method always attempts cleanup and evidence export.
        result = session.run_smoke()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        """),
        code("""
        # Evidence ZIP is produced for PASS and, when feasible, for FAIL.
        evidence_zip = pathlib.Path(result['evidence_zip'])
        print({'evidence_zip': str(evidence_zip), 'exists': evidence_zip.is_file(), 'status': result['status']})
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
        "language_info": {"name": "Python", "version": "3"},
        "kaggle": {"accelerator": "none", "internet": False, "isGpuEnabled": False, "isInternetEnabled": False},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

output = pathlib.Path(__file__).resolve().parents[3] / "kaggle/script/byteme_phase2_g24k.ipynb"
output.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(output)
