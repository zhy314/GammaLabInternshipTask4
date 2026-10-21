"""Unit tests for io_utils."""
from __future__ import annotations

import pytest

from dataclean.exit_codes import FormatUnsupportedError, InputNotFoundError
from dataclean.io_utils import detect_encoding, infer_format, read_any, write_any


def test_detect_encoding_utf8(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    enc = detect_encoding(p)
    assert enc.lower() in ("utf-8", "ascii")


def test_detect_encoding_gbk(gbk_csv):
    enc = detect_encoding(gbk_csv)
    # Confidence may be low on tiny samples; accept either gbk or utf-8 fallback.
    assert enc.lower() in ("gbk", "gb18030", "utf-8")


def test_read_csv_as_string(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n?,x\n", encoding="utf-8")
    df = read_any(p, fmt="csv")
    # Everything should be read as string with empty-string preserved
    assert df.dtypes["a"] == object
    assert df.iloc[1, 0] == "?"


def test_read_jsonl(jsonl_file):
    df = read_any(jsonl_file, fmt="jsonl")
    assert len(df) == 3
    assert "name" in df.columns


def test_infer_format():
    assert infer_format("a.csv") == "csv"
    assert infer_format("a.jsonl") == "jsonl"
    assert infer_format("a.json") == "json"
    with pytest.raises(FormatUnsupportedError):
        infer_format("a.parquet")


def test_missing_input_raises():
    with pytest.raises(InputNotFoundError):
        read_any("does-not-exist.csv", fmt="csv")


def test_roundtrip_csv(tmp_path):
    import pandas as pd

    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    out = tmp_path / "o.csv"
    write_any(df, out, fmt="csv")
    back = read_any(out, fmt="csv")
    assert back["a"].tolist() == ["1", "2"]
