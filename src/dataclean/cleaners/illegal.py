"""Illegal-value detection and handling stage.

For each configured column we check:
- dtype coercibility (int / float / bool / string)
- numeric range (inclusive [min, max])
- enum membership
- regex match (for string columns)

Behaviour on violation is one of:
- fail     -> raise IllegalRatioExceeded if any violation (strict)
- drop     -> drop offending rows
- coerce   -> replace offending cell with NaN

A ratio = total_violations / (rows * checked_columns). When it exceeds
max_ratio the pipeline exits with ILLEGAL_RATIO_EXCEEDED.
"""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from ..exit_codes import IllegalRatioExceeded
from ..rules import ColumnRule, IllegalRule


def _coerce_dtype(series: pd.Series, dtype: str) -> tuple[pd.Series, pd.Series]:
    """Return (coerced_series, invalid_mask). invalid_mask marks cells that were
    non-null before coercion but became null after (i.e. could not be parsed).
    """
    before_notna = series.notna()
    if dtype == "int":
        coerced = pd.to_numeric(series, errors="coerce")
        # Reject non-integer floats like 3.5
        non_int = coerced.notna() & (coerced != coerced.round())
        coerced = coerced.where(~non_int, other=np.nan)
    elif dtype == "float":
        coerced = pd.to_numeric(series, errors="coerce")
    elif dtype == "bool":
        truthy = {"1", "true", "True", "yes", "Y", "y", True, 1}
        falsy = {"0", "false", "False", "no", "N", "n", False, 0}
        def _map(x: Any):
            if x is None or (isinstance(x, float) and pd.isna(x)):
                return np.nan
            if x in truthy:
                return True
            if x in falsy:
                return False
            return np.nan
        coerced = series.map(_map)
    else:  # string / unknown -> leave as-is but cast
        coerced = series.astype("object")
    invalid = before_notna & coerced.isna()
    return coerced, invalid


def _check_column(
    series: pd.Series, rule: ColumnRule
) -> tuple[pd.Series, pd.Series]:
    """Return (processed_series, violation_mask) for one column."""
    out = series
    violations = pd.Series(False, index=series.index)

    if rule.dtype:
        out, invalid_dtype = _coerce_dtype(out, rule.dtype)
        violations = violations | invalid_dtype

    # Numeric range
    if rule.range is not None and rule.dtype in {"int", "float"}:
        lo, hi = rule.range
        numeric = pd.to_numeric(out, errors="coerce")
        oor = numeric.notna() & ((numeric < lo) | (numeric > hi))
        violations = violations | oor

    # Enum
    if rule.enum is not None:
        allowed = set(rule.enum)
        bad = out.notna() & ~out.isin(allowed)
        violations = violations | bad

    # Regex
    if rule.regex is not None:
        pattern = re.compile(rule.regex)
        def _match(x: Any) -> bool:
            if x is None or (isinstance(x, float) and pd.isna(x)):
                return True  # NaN is not a regex violation (missing handled elsewhere)
            return bool(pattern.fullmatch(str(x)))
        matched = out.map(_match)
        violations = violations | ~matched

    return out, violations


def apply_illegal(
    df: pd.DataFrame,
    column_rules: dict[str, ColumnRule],
    rule: IllegalRule,
) -> tuple[pd.DataFrame, dict]:
    """Validate columns, apply the configured strategy, and return stats.

    Raises IllegalRatioExceeded when the global violation ratio exceeds
    rule.max_ratio.
    """
    out = df.copy()
    per_col: dict[str, int] = {}
    checked_cols = 0

    row_mask = pd.Series(False, index=out.index)
    coerced_frame = out.copy()

    for col, crule in column_rules.items():
        if col not in out.columns:
            continue
        checked_cols += 1
        new_series, violations = _check_column(out[col], crule)
        count = int(violations.sum())
        per_col[col] = count

        if rule.on_violation == "coerce":
            new_series = new_series.where(~violations, other=np.nan)
            coerced_frame[col] = new_series
        else:
            coerced_frame[col] = new_series
            if rule.on_violation == "drop":
                row_mask = row_mask | violations

    total_violations = int(sum(per_col.values()))
    denom = max(1, len(out) * max(1, checked_cols))
    ratio = total_violations / denom

    stats: dict = {
        "per_column": per_col,
        "total_violations": total_violations,
        "checked_columns": checked_cols,
        "ratio": ratio,
        "on_violation": rule.on_violation,
        "max_ratio": rule.max_ratio,
        "rows_dropped": 0,
    }

    if rule.on_violation == "fail" and total_violations > 0:
        raise IllegalRatioExceeded(
            f"illegal values found with on_violation=fail: {total_violations}"
        )

    if ratio > rule.max_ratio:
        raise IllegalRatioExceeded(
            f"illegal-value ratio {ratio:.4f} exceeds max_ratio {rule.max_ratio}"
        )

    out = coerced_frame
    if rule.on_violation == "drop" and bool(row_mask.any()):
        before = len(out)
        out = out.loc[~row_mask].reset_index(drop=True)
        stats["rows_dropped"] = before - len(out)

    return out, stats
