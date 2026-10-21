"""Duplicate detection and removal stage."""
from __future__ import annotations

import pandas as pd

from ..rules import DuplicateRule


def _normalize_keep(keep):  # noqa: ANN001
    if keep in ("false", "False", False):
        return False
    return keep  # "first" or "last"


def dedupe(df: pd.DataFrame, rule: DuplicateRule) -> tuple[pd.DataFrame, dict]:
    """Remove duplicates according to the configured subset and keep policy.

    Returns (cleaned_df, stats) where stats carries:
      duplicates_found, rows_dropped, subset
    """
    subset = rule.subset
    if subset:
        missing = [c for c in subset if c not in df.columns]
        if missing:
            # Fail soft: ignore columns that do not exist (treat as full-row dedupe)
            subset = [c for c in subset if c in df.columns] or None

    keep = _normalize_keep(rule.keep)
    mask_dup = df.duplicated(subset=subset, keep=keep)
    dups = int(mask_dup.sum())
    out = df.loc[~mask_dup].reset_index(drop=True)
    return out, {
        "duplicates_found": dups,
        "rows_dropped": dups,
        "subset": subset,
        "keep": str(rule.keep),
    }
