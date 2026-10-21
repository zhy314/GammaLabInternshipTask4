"""Shared pytest fixtures."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def tiny_csv_with_markers(tmp_path: Path) -> Path:
    """Small CSV with '?' as missing marker, dup row, out-of-range age."""
    p = tmp_path / "tiny.csv"
    p.write_text(
        "age,sex,workclass\n"
        "25,Male,Private\n"
        "?,Female,Private\n"
        "40,Male,?\n"
        "25,Male,Private\n"       # duplicate of row 1
        "999,Female,Private\n"    # out-of-range age
        "30,Unknown,Private\n",  # enum violation on sex
        encoding="utf-8",
    )
    return p


@pytest.fixture
def gbk_csv(tmp_path: Path) -> Path:
    p = tmp_path / "gbk.csv"
    content = "name,note\n张三,备注\n李四,  中文  \n"
    p.write_bytes(content.encode("gbk"))
    return p


@pytest.fixture
def jsonl_file(tmp_path: Path) -> Path:
    p = tmp_path / "data.jsonl"
    p.write_text(
        '{"id": 1, "name": "  alice  "}\n'
        '{"id": 2, "name": "bob"}\n'
        '{"id": 2, "name": "bob"}\n',  # duplicate id
        encoding="utf-8",
    )
    return p


@pytest.fixture
def minimal_config(tmp_path: Path) -> Path:
    p = tmp_path / "cfg.yaml"
    p.write_text(
        "schema:\n"
        "  columns:\n"
        "    age: {dtype: int, range: [0, 120]}\n"
        "    sex: {dtype: string, enum: [\"Male\", \"Female\"]}\n"
        "    workclass: {dtype: string}\n"
        "missing:\n"
        "  markers: [\"?\", \"\"]\n"
        "  strategy:\n"
        "    age: median\n"
        "    workclass: mode\n"
        "    default: drop_row\n"
        "duplicates:\n"
        "  subset: null\n"
        "  keep: first\n"
        "illegal:\n"
        "  on_violation: coerce\n"
        "  max_ratio: 0.5\n",
        encoding="utf-8",
    )
    return p
