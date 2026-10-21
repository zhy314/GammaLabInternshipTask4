"""Encoding / text normalization stage.

For every string-typed column:
- strip leading / trailing whitespace
- collapse internal whitespace runs to a single space
- apply Unicode NFKC normalization (fullwidth -> halfwidth, etc.)
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd


_WS_RUN = re.compile(r"\s+")


def _normalize_scalar(x: Any) -> Any:
    if x is None:
        return x
    if isinstance(x, float) and pd.isna(x):
        return x
    if not isinstance(x, str):
        return x
    s = unicodedata.normalize("NFKC", x)
    s = _WS_RUN.sub(" ", s).strip()
    return s


def normalize_text(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Apply NFKC + whitespace normalization to every object/string column.

    Returns the cleaned DataFrame and a stats dict:
      { "columns_normalized": int, "cells_changed": int }
    """
    out = df.copy()
    cells_changed = 0
    cols_touched = 0
    for col in out.columns:
        series = out[col]
        if series.dtype != object and not pd.api.types.is_string_dtype(series):
            continue
        before = series.astype(object)
        after = before.map(_normalize_scalar)
        changed = (before.fillna("\0") != after.fillna("\0")).sum()
        if changed > 0:
            cols_touched += 1
            cells_changed += int(changed)
        out[col] = after
    return out, {"columns_normalized": cols_touched, "cells_changed": cells_changed}
