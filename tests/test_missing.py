"""Unit tests for missing-value handling."""
from __future__ import annotations

import pandas as pd

from dataclean.cleaners.missing import impute, mark_missing
from dataclean.rules import MissingRule


def test_mark_missing_replaces_markers():
    df = pd.DataFrame({"a": ["1", "?", "NA", "3"], "b": ["x", "y", "", "z"]})
    rule = MissingRule(markers=["?", "NA", ""])
    out, stats = mark_missing(df, rule)
    assert out["a"].isna().tolist() == [False, True, True, False]
    assert out["b"].isna().tolist() == [False, False, True, False]
    assert stats["markers_replaced"] == 3


def test_impute_median_and_mode():
    df = pd.DataFrame({"age": ["10", None, "30", None], "cat": ["a", "a", None, "b"]})
    rule = MissingRule(strategy={"age": "median", "cat": "mode"}, default="keep")
    out, stats = impute(df, rule)
    assert out["age"].isna().sum() == 0
    assert out["cat"].isna().sum() == 0
    assert stats["imputed_per_column"]["age"] == 2
    assert stats["imputed_per_column"]["cat"] == 1


def test_impute_drop_row():
    df = pd.DataFrame({"a": [1, None, 3], "b": [1, 2, None]})
    rule = MissingRule(strategy={"a": "drop_row", "b": "keep"}, default="keep")
    out, stats = impute(df, rule)
    assert len(out) == 2
    assert stats["rows_dropped"] == 1


def test_impute_constant():
    df = pd.DataFrame({"name": ["x", None, "y"]})
    rule = MissingRule(
        strategy={"name": "constant"}, default="keep", constant={"name": "unknown"}
    )
    out, _ = impute(df, rule)
    assert out["name"].tolist() == ["x", "unknown", "y"]
