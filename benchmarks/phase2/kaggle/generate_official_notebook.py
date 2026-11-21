#!/usr/bin/env python3
"""Generate the one-run G2.5 official Kaggle notebook."""

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
        # ByteMe Phase 2 — G2.5 official baseline run trên Kaggle CPU

        Notebook này thực hiện **đúng một** run standard chính thức cho baseline Pha 1. Chọn
        Accelerator `None`, tắt Internet, attach official bundle và Toolchain Dataset đã khóa,
        rồi dùng `Run All` từ session sạch. Không chạy lại riêng lẻ các cell workload.

        Warm-up read-only 60 giây (2/1/1 RPS) được lưu riêng và không thuộc metric chính thức.
        Evidence chỉ được công nhận khi `official-result.json` có `official_benchmark=true`.
        """),
        code("""
        import datetime as dt
        import json
        import pathlib
        import sys

        BASELINE_SHA = '510f6415b6af535ceec77213f0b0c7d5082123f7'
        runtime_files = list(pathlib.Path('/kaggle/input').rglob('benchmarks/phase2/kaggle/kaggle_runtime.py'))
        if len(runtime_files) != 1:
            raise RuntimeError(f'Expected one bundled kaggle_runtime.py, found {len(runtime_files)}: {runtime_files}')
        sys.path.insert(0, str(runtime_files[0].parent))
        from kaggle_runtime import KaggleSession, prepare_kaggle_input
        print({'runtime_module': str(runtime_files[0]), 'baseline_sha': BASELINE_SHA})
        """),
        code("""
        SOURCE_INPUT_ROOT = pathlib.Path('/kaggle/input')
        BOOTSTRAP_ROOT = pathlib.Path('/kaggle/working/byteme-g25-bootstrap')
        prepared_input_root = prepare_kaggle_input(SOURCE_INPUT_ROOT, BOOTSTRAP_ROOT)
        RUN_ID = 'g25-before-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        session = KaggleSession(input_root=prepared_input_root,
                                working_root='/kaggle/working/byteme-g25', run_id=RUN_ID)
        if session.input_root != prepared_input_root.resolve():
            raise RuntimeError(f'KaggleSession lost prepared input root: {session.input_root}')
        bootstrap_manifest = json.loads((prepared_input_root / 'bootstrap-manifest.json').read_text())
        print({'run_id': RUN_ID, 'prepared_input_root': str(prepared_input_root),
               'toolchain': {key: value.get('version') for key, value in bootstrap_manifest['components'].items()}})
        """),
        code("""
        probe = session.probe()
        if pathlib.Path(probe['prepared_input_root']) != session.input_root:
            raise RuntimeError('Probe did not preserve the prepared input root')
        print(json.dumps(probe, indent=2, ensure_ascii=False))
        """),
        code("""
        result = session.run_official(expected_application_sha=BASELINE_SHA)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        """),
        code("""
        evidence_zip = pathlib.Path(result['evidence_zip'])
        print({'evidence_zip': str(evidence_zip), 'exists': evidence_zip.is_file(),
               'status': result['status'], 'official_benchmark': result['official_benchmark']})
        if result['status'] != 'PASS' or result['official_benchmark'] is not True:
            raise RuntimeError('Official baseline run is invalid; inspect the evidence ZIP and do not aggregate it')
        """),
        markdown("""
        ## Sau khi run hoàn tất

        Tải evidence ZIP trước khi session hết hạn. Giữ nguyên ZIP gốc và kiểm tra
        `SHA256SUMS.txt`, `official-result.json`, run manifest, phase events, raw/summary W1/W2,
        W3, ba reset checksum, telemetry, cleanup và secret scan trước khi nghiệm thu Run 01.
        HTTP/performance failures hoặc W3 defects là kết quả baseline; harness/evidence failure
        mới làm run không hợp lệ.
        """),
    ],
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "Python", "version": "3"},
        "kaggle": {"accelerator": "none", "internet": False, "isGpuEnabled": False,
                   "isInternetEnabled": False},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

output = pathlib.Path(__file__).resolve().parents[3] / "kaggle/script/byteme_phase2_g25_official.ipynb"
output.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(output)
