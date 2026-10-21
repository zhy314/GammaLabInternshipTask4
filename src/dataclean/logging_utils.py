"""Logging and run-manifest helpers."""
from __future__ import annotations

import hashlib
import json
import logging
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_LOGGER_NAME = "dataclean"


def setup_logger(verbosity: int = 0) -> logging.Logger:
    """Configure and return the shared package logger.

    verbosity: 0 -> WARNING, 1 -> INFO, 2+ -> DEBUG.
    Idempotent: safe to call multiple times.
    """
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


def sha256_of_file(path: str | Path, chunk: int = 1 << 20) -> str:
    """Compute SHA-256 of a file; returns empty string if the file is missing."""
    p = Path(path)
    if not p.exists():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _library_versions() -> dict[str, str]:
    versions: dict[str, str] = {"python": platform.python_version()}
    for mod in ("pandas", "click", "yaml", "chardet"):
        try:
            m = __import__(mod)
            versions[mod] = getattr(m, "__version__", "unknown")
        except Exception:  # noqa: BLE001
            versions[mod] = "not-installed"
    return versions


def build_manifest(
    *,
    input_path: str,
    output_path: str | None,
    config_path: str | None,
    input_rows: int,
    output_rows: int,
    stage_stats: dict[str, Any],
    exit_code: int,
) -> dict[str, Any]:
    """Assemble a reproducibility manifest for one pipeline run."""
    return {
        "schema": "dataclean.manifest.v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input": {
            "path": str(input_path),
            "sha256": sha256_of_file(input_path),
            "rows": input_rows,
        },
        "output": {
            "path": str(output_path) if output_path else None,
            "sha256": sha256_of_file(output_path) if output_path else "",
            "rows": output_rows,
        },
        "config": {
            "path": str(config_path) if config_path else None,
            "sha256": sha256_of_file(config_path) if config_path else "",
        },
        "environment": {
            "platform": platform.platform(),
            "libraries": _library_versions(),
        },
        "stages": stage_stats,
        "exit_code": exit_code,
    }


def write_manifest(manifest: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
