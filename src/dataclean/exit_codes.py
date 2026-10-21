"""Centralized exit codes for the dataclean CLI.

Keep these stable: downstream shell scripts and CI pipelines rely on them.
"""
from __future__ import annotations


# Success
OK = 0

# Generic / unexpected
GENERIC_ERROR = 1

# CLI misuse is handled by click itself and uses code 2.

# Input / IO errors (10-19)
ENCODING_ERROR = 10
CONFIG_INVALID = 11
INPUT_NOT_FOUND = 12
FORMAT_UNSUPPORTED = 13

# Semantic / data quality errors (20-29)
ILLEGAL_RATIO_EXCEEDED = 20

# Pipeline semantic errors (30-39)
EMPTY_AFTER_CLEAN = 30


class DataCleanError(Exception):
    """Base exception that carries a specific exit code."""

    exit_code: int = GENERIC_ERROR

    def __init__(self, message: str, exit_code: int | None = None) -> None:
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


class EncodingError(DataCleanError):
    exit_code = ENCODING_ERROR


class ConfigError(DataCleanError):
    exit_code = CONFIG_INVALID


class InputNotFoundError(DataCleanError):
    exit_code = INPUT_NOT_FOUND


class FormatUnsupportedError(DataCleanError):
    exit_code = FORMAT_UNSUPPORTED


class IllegalRatioExceeded(DataCleanError):
    exit_code = ILLEGAL_RATIO_EXCEEDED


class EmptyAfterCleanError(DataCleanError):
    exit_code = EMPTY_AFTER_CLEAN
