"""CLI tests: assert exit codes and side-effects."""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from dataclean import exit_codes as ec
from dataclean.cli import main


def test_version_runs():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "dataclean" in result.output


def test_clean_happy_path(tiny_csv_with_markers: Path, minimal_config: Path, tmp_path):
    out = tmp_path / "cleaned.csv"
    report = tmp_path / "manifest.json"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "clean",
            "--input", str(tiny_csv_with_markers),
            "--output", str(out),
            "--config", str(minimal_config),
            "--report", str(report),
        ],
    )
    assert result.exit_code == ec.OK, result.output
    assert out.exists()
    manifest = json.loads(report.read_text(encoding="utf-8"))
    assert manifest["exit_code"] == ec.OK
    assert manifest["input"]["rows"] == 6


def test_input_not_found_exit_12(minimal_config: Path, tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "clean",
            "--input", str(tmp_path / "nope.csv"),
            "--output", str(tmp_path / "o.csv"),
            "--config", str(minimal_config),
        ],
    )
    assert result.exit_code == ec.INPUT_NOT_FOUND


def test_config_invalid_exit_11(tiny_csv_with_markers: Path, tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema:\n  columns:\n    age: {dtype: nope}\n", encoding="utf-8"
    )
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "clean",
            "--input", str(tiny_csv_with_markers),
            "--output", str(tmp_path / "o.csv"),
            "--config", str(bad),
        ],
    )
    assert result.exit_code == ec.CONFIG_INVALID


def test_illegal_ratio_exceeded_exit_20(tiny_csv_with_markers: Path, minimal_config: Path, tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "clean",
            "--input", str(tiny_csv_with_markers),
            "--output", str(tmp_path / "o.csv"),
            "--config", str(minimal_config),
            "--max-illegal-ratio", "0.0",
            "--on-illegal", "fail",
        ],
    )
    assert result.exit_code == ec.ILLEGAL_RATIO_EXCEEDED


def test_inspect_prints_json(tiny_csv_with_markers: Path):
    runner = CliRunner()
    result = runner.invoke(main, ["inspect", "--input", str(tiny_csv_with_markers)])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["rows"] == 6
    assert "dtypes" in payload


def test_validate_dry_run(tiny_csv_with_markers: Path, minimal_config: Path, tmp_path):
    out_before = list(tmp_path.iterdir())
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["validate", "--input", str(tiny_csv_with_markers), "--config", str(minimal_config)],
    )
    assert result.exit_code == ec.OK
    # no output file should be created
    assert list(tmp_path.iterdir()) == out_before
