"""Unit tests for the text-encoding / NFKC normalization cleaner."""
from __future__ import annotations

import pandas as pd

from dataclean.cleaners.encoding import normalize_text


def test_strip_and_collapse_whitespace():
    df = pd.DataFrame({"name": ["  alice  ", "bob\tsmith", "  "], "age": [1, 2, 3]})
    out, stats = normalize_text(df)
    assert out["name"].tolist() == ["alice", "bob smith", ""]
    assert stats["cells_changed"] >= 2
    # numeric column should be untouched
    assert out["age"].tolist() == [1, 2, 3]


def test_nfkc_normalization():
    # Full-width digits/letters -> half-width
    df = pd.DataFrame({"col": ["ＡＢＣ", "１２３"]})
    out, _ = normalize_text(df)
    assert out["col"].tolist() == ["ABC", "123"]


def test_non_string_columns_unchanged():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    out, stats = normalize_text(df)
    assert out["x"].tolist() == [1.0, 2.0, 3.0]
    assert stats["cells_changed"] == 0


def test_empty_frame():
    df = pd.DataFrame({"a": [], "b": []})
    out, stats = normalize_text(df)
    assert out.empty
    assert stats["cells_changed"] == 0
