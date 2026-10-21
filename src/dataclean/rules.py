"""YAML rules loader and lightweight schema validation."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .exit_codes import ConfigError


SUPPORTED_DTYPES = {"int", "float", "string", "bool"}
SUPPORTED_MISSING_STRATEGIES = {"drop_row", "mean", "median", "mode", "constant", "keep"}
SUPPORTED_ON_VIOLATION = {"fail", "drop", "coerce"}


@dataclass
class ColumnRule:
    dtype: str | None = None
    range: list | None = None  # [min, max] inclusive, for int/float
    enum: list | None = None  # allowed values
    regex: str | None = None  # for string columns


@dataclass
class MissingRule:
    markers: list[str] = field(default_factory=lambda: ["", "NA", "null", "None", "NaN"])
    strategy: dict[str, str] = field(default_factory=dict)  # column -> strategy
    default: str = "drop_row"
    constant: dict[str, Any] = field(default_factory=dict)  # column -> fill value when strategy=constant


@dataclass
class DuplicateRule:
    subset: list[str] | None = None
    keep: str = "first"  # first | last | false


@dataclass
class IllegalRule:
    on_violation: str = "coerce"
    max_ratio: float = 0.05


@dataclass
class Rules:
    columns: dict[str, ColumnRule] = field(default_factory=dict)
    missing: MissingRule = field(default_factory=MissingRule)
    duplicates: DuplicateRule = field(default_factory=DuplicateRule)
    illegal: IllegalRule = field(default_factory=IllegalRule)
    encoding_normalize: bool = True  # strip + NFKC + collapse whitespace


def load_rules(path: str | Path) -> Rules:
    """Parse a YAML rules file and return a validated Rules object."""
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"config file not found: {path}")
    try:
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"invalid YAML: {e}") from e

    if not isinstance(data, dict):
        raise ConfigError("top-level config must be a mapping")

    # Columns
    columns: dict[str, ColumnRule] = {}
    schema = data.get("schema", {}) or {}
    for name, spec in (schema.get("columns", {}) or {}).items():
        if not isinstance(spec, dict):
            raise ConfigError(f"schema.columns.{name} must be a mapping")
        dtype = spec.get("dtype")
        if dtype is not None and dtype not in SUPPORTED_DTYPES:
            raise ConfigError(
                f"schema.columns.{name}.dtype '{dtype}' not in {sorted(SUPPORTED_DTYPES)}"
            )
        rng = spec.get("range")
        if rng is not None and (not isinstance(rng, list) or len(rng) != 2):
            raise ConfigError(f"schema.columns.{name}.range must be [min, max]")
        columns[name] = ColumnRule(
            dtype=dtype,
            range=rng,
            enum=spec.get("enum"),
            regex=spec.get("regex"),
        )

    # Missing
    missing_cfg = data.get("missing", {}) or {}
    strategy = missing_cfg.get("strategy", {}) or {}
    default_strategy = str(strategy.pop("default", missing_cfg.get("default", "drop_row")))
    if default_strategy not in SUPPORTED_MISSING_STRATEGIES:
        raise ConfigError(
            f"missing.default '{default_strategy}' not in {sorted(SUPPORTED_MISSING_STRATEGIES)}"
        )
    for col, strat in strategy.items():
        if strat not in SUPPORTED_MISSING_STRATEGIES:
            raise ConfigError(
                f"missing.strategy.{col}='{strat}' not in {sorted(SUPPORTED_MISSING_STRATEGIES)}"
            )
    missing = MissingRule(
        markers=list(missing_cfg.get("markers", ["", "NA", "null", "None", "NaN"])),
        strategy=dict(strategy),
        default=default_strategy,
        constant=dict(missing_cfg.get("constant", {}) or {}),
    )

    # Duplicates
    dup_cfg = data.get("duplicates", {}) or {}
    keep = str(dup_cfg.get("keep", "first"))
    if keep not in {"first", "last", "false", "False", False}:
        raise ConfigError(f"duplicates.keep '{keep}' invalid; use first|last|false")
    duplicates = DuplicateRule(
        subset=dup_cfg.get("subset"),
        keep=keep,
    )

    # Illegal
    ill_cfg = data.get("illegal", {}) or {}
    on_violation = str(ill_cfg.get("on_violation", "coerce"))
    if on_violation not in SUPPORTED_ON_VIOLATION:
        raise ConfigError(
            f"illegal.on_violation '{on_violation}' not in {sorted(SUPPORTED_ON_VIOLATION)}"
        )
    max_ratio = float(ill_cfg.get("max_ratio", 0.05))
    if not 0.0 <= max_ratio <= 1.0:
        raise ConfigError(f"illegal.max_ratio must be in [0,1], got {max_ratio}")
    illegal = IllegalRule(on_violation=on_violation, max_ratio=max_ratio)

    encoding_normalize = bool(data.get("encoding_normalize", True))

    return Rules(
        columns=columns,
        missing=missing,
        duplicates=duplicates,
        illegal=illegal,
        encoding_normalize=encoding_normalize,
    )
