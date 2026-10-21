"""Missing-value handling stage.

Two steps:
1) Replace all configured marker strings (e.g. "?", "", "NA") with NaN.
2) Impute remaining NaN per-column using the configured strategy
   (drop_row, mean, median, mode, constant, keep).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..rules import MissingRule


def mark_missing(df: pd.DataFrame, rule: MissingRule) -> tuple[pd.DataFrame, dict]:
    """Replace marker strings with NaN. Operates column-wise on object dtypes."""
    out = df.copy()
    markers = set(rule.markers)
    before_na = int(out.isna().sum().sum())
    for col in out.columns:
        s = out[col]
        if s.dtype == object or pd.api.types.is_string_dtype(s):
            out[col] = s.where(~s.isin(markers), other=np.nan)
    after_na = int(out.isna().sum().sum())
    return out, {"markers_replaced": after_na - before_na}


def _impute_column(series: pd.Series, strategy: str, constant_value=None) -> pd.Series:
    if strategy == "keep":
        return series
    if strategy == "mean":
        try:
            numeric = pd.to_numeric(series, errors="coerce")
            return series.fillna(numeric.mean())
        except Exception:  # noqa: BLE001
            return series
    if strategy == "median":
        numeric = pd.to_numeric(series, errors="coerce")
        return series.fillna(numeric.median())
    if strategy == "mode":
        mode = series.mode(dropna=True)
        if len(mode) == 0:
            return series
        return series.fillna(mode.iloc[0])
    if strategy == "constant":
        return series.fillna(constant_value)
    # drop_row is handled at frame level
    return series


def impute(df: pd.DataFrame, rule: MissingRule) -> tuple[pd.DataFrame, dict]:
    """Apply per-column imputation strategies; drop rows for 'drop_row'."""
    out = df.copy()
    stats: dict = {"imputed_per_column": {}, "rows_dropped": 0}

    drop_cols: list[str] = []
    for col in out.columns:
        strat = rule.strategy.get(col, rule.default)
        if strat == "drop_row":
            drop_cols.append(col)
            continue
        na_before = int(out[col].isna().sum())
        if na_before == 0:
            continue
        constant_value = rule.constant.get(col)
        out[col] = _impute_column(out[col], strat, constant_value=constant_value)
        na_after = int(out[col].isna().sum())
        stats["imputed_per_column"][col] = na_before - na_after

    if drop_cols:
        before = len(out)
        out = out.dropna(subset=drop_cols)
        stats["rows_dropped"] = before - len(out)

    return out.reset_index(drop=True), stats
