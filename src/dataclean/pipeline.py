"""Pipeline orchestration: load -> encoding -> missing -> dedupe -> illegal -> write.

Returns an exit code (int) so the CLI can propagate it to the shell.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import exit_codes as ec
from .cleaners.duplicates import dedupe
from .cleaners.encoding import normalize_text
from .cleaners.illegal import apply_illegal
from .cleaners.missing import impute, mark_missing
from .io_utils import detect_encoding, read_any, write_any
from .logging_utils import build_manifest, get_logger, write_manifest
from .rules import load_rules


def run_pipeline(
    *,
    input_path: str,
    output_path: str | None,
    config_path: str,
    fmt: str = "auto",
    encoding: str = "auto",
    report_path: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> int:
    """Execute the full pipeline. Returns an integer exit code.

    When output_path is None the pipeline runs in dry-run / validate mode:
    no file is written but the manifest is still produced on report_path.
    """
    log = get_logger()
    overrides = overrides or {}

    # ------------------------------------------------------------------ config
    rules = load_rules(config_path)
    if "on_illegal" in overrides:
        rules.illegal.on_violation = overrides["on_illegal"]
    if "max_illegal_ratio" in overrides:
        rules.illegal.max_ratio = float(overrides["max_illegal_ratio"])

    # ------------------------------------------------------------------- read
    enc = detect_encoding(input_path) if encoding == "auto" else encoding
    log.info("reading %s (format=%s, encoding=%s)", input_path, fmt, enc)
    df = read_any(input_path, fmt=fmt, encoding=enc)
    input_rows = int(len(df))
    stage_stats: dict[str, Any] = {
        "input": {"rows": input_rows, "columns": int(df.shape[1]), "encoding": enc},
    }

    # ---------------------------------------------------------------- encoding
    if rules.encoding_normalize:
        df, stats = normalize_text(df)
        stage_stats["encoding"] = stats
        log.info("encoding stage: %s", stats)

    # ----------------------------------------------------------------- missing
    df, stats = mark_missing(df, rules.missing)
    stage_stats["missing_markers"] = stats
    log.info("marker->NaN: %s", stats)

    df, stats = impute(df, rules.missing)
    stage_stats["impute"] = stats
    log.info("impute: %s", stats)

    # -------------------------------------------------------------- duplicates
    df, stats = dedupe(df, rules.duplicates)
    stage_stats["duplicates"] = stats
    log.info("dedupe: %s", stats)

    # ----------------------------------------------------------------- illegal
    exit_code = ec.OK
    try:
        df, stats = apply_illegal(df, rules.columns, rules.illegal)
        stage_stats["illegal"] = stats
        log.info("illegal: %s", stats)
    except ec.IllegalRatioExceeded as e:
        log.error("illegal-value check failed: %s", e)
        stage_stats["illegal"] = {"error": str(e)}
        exit_code = e.exit_code

    output_rows = int(len(df))
    stage_stats["output"] = {"rows": output_rows}

    # -------------------------------------------------------- empty detection
    if exit_code == ec.OK and input_rows > 0 and output_rows == 0:
        log.error("cleaning produced an empty dataset")
        exit_code = ec.EMPTY_AFTER_CLEAN

    # ---------------------------------------------------------------- write
    if exit_code == ec.OK and output_path is not None:
        log.info("writing cleaned data to %s", output_path)
        write_any(df, output_path, fmt=fmt)

    # ---------------------------------------------------------------- report
    if report_path is not None:
        manifest = build_manifest(
            input_path=input_path,
            output_path=output_path if exit_code == ec.OK else None,
            config_path=config_path,
            input_rows=input_rows,
            output_rows=output_rows,
            stage_stats=stage_stats,
            exit_code=exit_code,
        )
        write_manifest(manifest, report_path)
        log.info("wrote manifest to %s", report_path)

    return exit_code
