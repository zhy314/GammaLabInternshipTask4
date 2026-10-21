"""IO helpers: encoding detection and CSV / JSON(L) readers & writers."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

from .exit_codes import (
    EncodingError,
    FormatUnsupportedError,
    InputNotFoundError,
)
from .logging_utils import get_logger

Format = Literal["auto", "csv", "json", "jsonl"]


# -----------------------------------------------------------------------------
# Encoding detection
# -----------------------------------------------------------------------------
def detect_encoding(path: str | Path, sample_bytes: int = 262_144) -> str:
    """Detect file encoding using chardet on a leading byte sample.

    Normalizes a few common aliases and defaults to utf-8 when the detector
    is not confident.
    """
    try:
        import chardet
    except ImportError as e:  # pragma: no cover
        raise EncodingError(f"chardet is required for encoding auto-detection: {e}") from e

    p = Path(path)
    if not p.exists():
        raise InputNotFoundError(f"input file not found: {path}")
    with p.open("rb") as f:
        head = f.read(sample_bytes)
    if not head:
        return "utf-8"
    guess = chardet.detect(head) or {}
    enc = (guess.get("encoding") or "utf-8").lower()
    conf = float(guess.get("confidence") or 0.0)
    # Normalize common aliases
    aliases = {
        "ascii": "utf-8",
        "utf-8-sig": "utf-8-sig",
        "gb2312": "gbk",
        "windows-1252": "cp1252",
    }
    enc = aliases.get(enc, enc)
    if conf < 0.5:
        get_logger().warning(
            "low-confidence encoding guess (%.2f) for %s; defaulting to utf-8", conf, path
        )
        enc = "utf-8"
    return enc


# -----------------------------------------------------------------------------
# Format detection
# -----------------------------------------------------------------------------
def infer_format(path: str | Path) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    if suffix in {"csv", "tsv"}:
        return "csv"
    if suffix in {"json"}:
        return "json"
    if suffix in {"jsonl", "ndjson"}:
        return "jsonl"
    raise FormatUnsupportedError(
        f"cannot infer format from suffix '{suffix}'; pass --format explicitly"
    )


# -----------------------------------------------------------------------------
# Readers
# -----------------------------------------------------------------------------
def read_any(path: str | Path, fmt: Format = "auto", encoding: str = "utf-8") -> pd.DataFrame:
    """Read a tabular file into a DataFrame.

    Everything is loaded as object/string first; type coercion happens in the
    illegal-value cleaner so that malformed cells can be reported precisely.
    """
    p = Path(path)
    if not p.exists():
        raise InputNotFoundError(f"input file not found: {path}")

    actual_fmt = infer_format(p) if fmt == "auto" else fmt
    sep = "\t" if p.suffix.lower() == ".tsv" else ","

    try:
        if actual_fmt == "csv":
            # Read everything as string so the illegal/missing cleaners decide types.
            return pd.read_csv(p, encoding=encoding, sep=sep, dtype=str, keep_default_na=False)
        if actual_fmt == "jsonl":
            return pd.read_json(p, lines=True, encoding=encoding, dtype=False)
        if actual_fmt == "json":
            return pd.read_json(p, encoding=encoding, dtype=False)
    except UnicodeDecodeError as e:
        raise EncodingError(f"failed to decode {path} with encoding={encoding}: {e}") from e
    except ValueError as e:
        # pandas raises ValueError for malformed JSON / CSV parse errors.
        raise FormatUnsupportedError(f"failed to parse {path} as {actual_fmt}: {e}") from e

    raise FormatUnsupportedError(f"unsupported format: {actual_fmt}")


# -----------------------------------------------------------------------------
# Writers
# -----------------------------------------------------------------------------
def write_any(df: pd.DataFrame, path: str | Path, fmt: Format = "auto") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    actual_fmt = infer_format(p) if fmt == "auto" else fmt

    if actual_fmt == "csv":
        df.to_csv(p, index=False, encoding="utf-8")
        return
    if actual_fmt == "jsonl":
        df.to_json(p, orient="records", lines=True, force_ascii=False)
        return
    if actual_fmt == "json":
        df.to_json(p, orient="records", force_ascii=False, indent=2)
        return
    raise FormatUnsupportedError(f"unsupported output format: {actual_fmt}")
