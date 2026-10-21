"""Unit tests for the YAML rules loader."""
from __future__ import annotations

import pytest

from dataclean.exit_codes import ConfigError
from dataclean.rules import load_rules


def test_load_minimal(minimal_config):
    rules = load_rules(minimal_config)
    assert "age" in rules.columns
    assert rules.columns["age"].dtype == "int"
    assert rules.missing.default == "drop_row"
    assert rules.duplicates.keep == "first"
    assert rules.illegal.on_violation == "coerce"


def test_invalid_dtype(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text(
        "schema:\n  columns:\n    x: {dtype: int128}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_rules(p)


def test_bad_range(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text(
        "schema:\n  columns:\n    x: {dtype: int, range: [1]}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_rules(p)


def test_missing_file():
    with pytest.raises(ConfigError):
        load_rules("does-not-exist.yaml")


def test_project_configs_load():
    # Make sure every shipped config is syntactically valid.
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "configs"
    for yml in root.glob("*.yaml"):
        rules = load_rules(yml)
        assert rules is not None
