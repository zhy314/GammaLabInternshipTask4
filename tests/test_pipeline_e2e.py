"""End-to-end pipeline tests exercising the full stage sequence."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from dataclean import exit_codes as ec
from dataclean.pipeline import run_pipeline


def test_e2e_adult_like(tiny_csv_with_markers: Path, minimal_config: Path, tmp_path):
    out = tmp_path / "out.csv"
    report = tmp_path / "manifest.json"
    code = run_pipeline(
        input_path=str(tiny_csv_with_markers),
        output_path=str(out),
        config_path=str(minimal_config),
        report_path=str(report),
    )
    assert code == ec.OK
    assert out.exists()

    cleaned = pd.read_csv(out)
    # duplicate row removed
    assert len(cleaned) < 6
    # out-of-range '999' was coerced to NaN by the illegal stage
    ages = pd.to_numeric(cleaned["age"], errors="coerce").dropna()
    assert (ages <= 120).all()
    # the NaN produced by coercion remains (illegal runs after impute by design)
    assert cleaned["age"].isna().sum() >= 1

    manifest = json.loads(report.read_text(encoding="utf-8"))
    assert "stages" in manifest
    assert manifest["input"]["sha256"]
    assert manifest["output"]["sha256"]


def test_e2e_empty_input(tmp_path, minimal_config: Path):
    empty = tmp_path / "empty.csv"
    empty.write_text("age,sex,workclass\n", encoding="utf-8")  # header only
    out = tmp_path / "o.csv"
    code = run_pipeline(
        input_path=str(empty),
        output_path=str(out),
        config_path=str(minimal_config),
    )
    # No rows in / no rows out is fine (no EMPTY_AFTER_CLEAN since input_rows == 0)
    assert code == ec.OK


def test_e2e_jsonl(jsonl_file: Path, tmp_path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "schema:\n"
        "  columns:\n"
        "    id: {dtype: int, range: [0, 1000]}\n"
        "    name: {dtype: string}\n"
        "missing:\n"
        "  markers: [\"\"]\n"
        "  strategy: {default: keep}\n"
        "duplicates:\n"
        "  subset: [id]\n"
        "  keep: first\n"
        "illegal:\n"
        "  on_violation: coerce\n"
        "  max_ratio: 0.5\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    code = run_pipeline(
        input_path=str(jsonl_file),
        output_path=str(out),
        config_path=str(cfg),
    )
    assert code == ec.OK
    assert out.exists()
    # The duplicate id=2 should be dropped
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
