"""Unit tests for duplicate removal."""
from __future__ import annotations

import pandas as pd

from dataclean.cleaners.duplicates import dedupe
from dataclean.rules import DuplicateRule


def test_dedupe_full_row():
    df = pd.DataFrame({"a": [1, 2, 1], "b": ["x", "y", "x"]})
    out, stats = dedupe(df, DuplicateRule(subset=None, keep="first"))
    assert len(out) == 2
    assert stats["duplicates_found"] == 1


def test_dedupe_subset():
    df = pd.DataFrame({"id": [1, 2, 1], "val": [10, 20, 30]})
    out, stats = dedupe(df, DuplicateRule(subset=["id"], keep="last"))
    assert out["val"].tolist() == [20, 30]
    assert stats["duplicates_found"] == 1


def test_dedupe_no_dups():
    df = pd.DataFrame({"a": [1, 2, 3]})
    out, stats = dedupe(df, DuplicateRule(subset=None, keep="first"))
    assert len(out) == 3
    assert stats["duplicates_found"] == 0


def test_dedupe_missing_subset_column_falls_back():
    df = pd.DataFrame({"a": [1, 1, 2]})
    # 'missing' column does not exist; should fall back to full-row dedupe
    out, _ = dedupe(df, DuplicateRule(subset=["missing"], keep="first"))
    assert len(out) == 2
