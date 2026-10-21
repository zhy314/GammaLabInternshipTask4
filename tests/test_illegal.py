"""Unit tests for illegal-value handling."""
from __future__ import annotations

import pandas as pd
import pytest

from dataclean.cleaners.illegal import apply_illegal
from dataclean.exit_codes import IllegalRatioExceeded
from dataclean.rules import ColumnRule, IllegalRule


def test_dtype_coerce_sets_nan():
    df = pd.DataFrame({"age": ["10", "abc", "30"]})
    rules = {"age": ColumnRule(dtype="int", range=[0, 120])}
    out, stats = apply_illegal(df, rules, IllegalRule(on_violation="coerce", max_ratio=1.0))
    assert pd.isna(out.loc[1, "age"])
    assert stats["per_column"]["age"] == 1


def test_out_of_range_coerced():
    df = pd.DataFrame({"age": ["10", "999", "30"]})
    rules = {"age": ColumnRule(dtype="int", range=[0, 120])}
    out, _ = apply_illegal(df, rules, IllegalRule(on_violation="coerce", max_ratio=1.0))
    assert pd.isna(out.loc[1, "age"])


def test_enum_violation_drops_row():
    df = pd.DataFrame({"sex": ["Male", "Unknown", "Female"]})
    rules = {"sex": ColumnRule(dtype="string", enum=["Male", "Female"])}
    out, stats = apply_illegal(df, rules, IllegalRule(on_violation="drop", max_ratio=1.0))
    assert len(out) == 2
    assert stats["rows_dropped"] == 1


def test_ratio_exceeded_raises():
    df = pd.DataFrame({"age": ["abc", "xyz", "qqq", "40"]})
    rules = {"age": ColumnRule(dtype="int", range=[0, 120])}
    with pytest.raises(IllegalRatioExceeded):
        apply_illegal(df, rules, IllegalRule(on_violation="coerce", max_ratio=0.1))


def test_fail_mode_raises_on_any_violation():
    df = pd.DataFrame({"age": ["10", "abc"]})
    rules = {"age": ColumnRule(dtype="int")}
    with pytest.raises(IllegalRatioExceeded):
        apply_illegal(df, rules, IllegalRule(on_violation="fail", max_ratio=1.0))


def test_regex_check():
    df = pd.DataFrame({"zip": ["12345", "9999", "abcde"]})
    rules = {"zip": ColumnRule(dtype="string", regex=r"\d{5}")}
    out, stats = apply_illegal(df, rules, IllegalRule(on_violation="coerce", max_ratio=1.0))
    assert pd.isna(out.loc[1, "zip"])
    assert pd.isna(out.loc[2, "zip"])
    assert stats["per_column"]["zip"] == 2
