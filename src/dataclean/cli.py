"""Click entrypoint for the dataclean CLI."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from . import __version__, exit_codes as ec
from .logging_utils import setup_logger, get_logger


# -----------------------------------------------------------------------------
# Shared helpers
# -----------------------------------------------------------------------------
def _handle(exc: Exception) -> int:
    """Translate exceptions to an exit code and log the message."""
    log = get_logger()
    if isinstance(exc, ec.DataCleanError):
        log.error("%s: %s", type(exc).__name__, exc)
        return exc.exit_code
    log.exception("Unhandled error: %s", exc)
    return ec.GENERIC_ERROR


# -----------------------------------------------------------------------------
# CLI group
# -----------------------------------------------------------------------------
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="dataclean")
@click.option("-v", "--verbose", count=True, help="Increase verbosity (-v, -vv).")
@click.pass_context
def main(ctx: click.Context, verbose: int) -> None:
    """dataclean: a reproducible data cleaning pipeline."""
    ctx.ensure_object(dict)
    ctx.obj["verbosity"] = verbose
    setup_logger(verbose)


# -----------------------------------------------------------------------------
# clean
# -----------------------------------------------------------------------------
@main.command("clean")
@click.option("--input", "input_path", required=True, type=click.Path(dir_okay=False),
              help="Input file path (CSV or JSON/JSONL).")
@click.option("--output", "output_path", required=True, type=click.Path(dir_okay=False),
              help="Output file path.")
@click.option("--config", "config_path", required=True, type=click.Path(dir_okay=False, exists=True),
              help="YAML rules file.")
@click.option("--format", "fmt", type=click.Choice(["auto", "csv", "json", "jsonl"]),
              default="auto", show_default=True)
@click.option("--encoding", default="auto", show_default=True,
              help="Input encoding; 'auto' uses chardet.")
@click.option("--on-illegal", type=click.Choice(["fail", "drop", "coerce"]), default=None,
              help="Override illegal-value strategy from the config.")
@click.option("--max-illegal-ratio", type=float, default=None,
              help="Override maximum tolerated illegal-value ratio (0..1).")
@click.option("--report", "report_path", type=click.Path(dir_okay=False), default=None,
              help="Write run_manifest.json to this path.")
@click.pass_context
def cmd_clean(
    ctx: click.Context,
    input_path: str,
    output_path: str,
    config_path: str,
    fmt: str,
    encoding: str,
    on_illegal: str | None,
    max_illegal_ratio: float | None,
    report_path: str | None,
) -> None:
    """Run the full cleaning pipeline and write a cleaned output file."""
    # Imported lazily so --help works without pandas installed.
    from .pipeline import run_pipeline

    overrides: dict = {}
    if on_illegal is not None:
        overrides["on_illegal"] = on_illegal
    if max_illegal_ratio is not None:
        overrides["max_illegal_ratio"] = max_illegal_ratio

    try:
        code = run_pipeline(
            input_path=input_path,
            output_path=output_path,
            config_path=config_path,
            fmt=fmt,
            encoding=encoding,
            report_path=report_path,
            overrides=overrides,
        )
    except Exception as exc:  # noqa: BLE001
        code = _handle(exc)
    ctx.exit(code)


# -----------------------------------------------------------------------------
# inspect
# -----------------------------------------------------------------------------
@main.command("inspect")
@click.option("--input", "input_path", required=True, type=click.Path(dir_okay=False, exists=True))
@click.option("--format", "fmt", type=click.Choice(["auto", "csv", "json", "jsonl"]),
              default="auto", show_default=True)
@click.option("--encoding", default="auto", show_default=True)
@click.pass_context
def cmd_inspect(ctx: click.Context, input_path: str, fmt: str, encoding: str) -> None:
    """Print basic statistics: detected encoding, dtypes, missing counts."""
    from .io_utils import detect_encoding, read_any

    try:
        enc = detect_encoding(input_path) if encoding == "auto" else encoding
        df = read_any(input_path, fmt=fmt, encoding=enc)
        report = {
            "path": str(input_path),
            "encoding": enc,
            "rows": int(len(df)),
            "columns": int(df.shape[1]),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "missing_counts": {c: int(df[c].isna().sum()) for c in df.columns},
        }
        click.echo(json.dumps(report, indent=2, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        ctx.exit(_handle(exc))


# -----------------------------------------------------------------------------
# validate
# -----------------------------------------------------------------------------
@main.command("validate")
@click.option("--input", "input_path", required=True, type=click.Path(dir_okay=False, exists=True))
@click.option("--config", "config_path", required=True, type=click.Path(dir_okay=False, exists=True))
@click.option("--format", "fmt", type=click.Choice(["auto", "csv", "json", "jsonl"]),
              default="auto", show_default=True)
@click.option("--encoding", default="auto", show_default=True)
@click.pass_context
def cmd_validate(
    ctx: click.Context,
    input_path: str,
    config_path: str,
    fmt: str,
    encoding: str,
) -> None:
    """Run cleaning in dry-run mode: no output written, exit code reflects outcome."""
    from .pipeline import run_pipeline

    try:
        code = run_pipeline(
            input_path=input_path,
            output_path=None,  # dry-run
            config_path=config_path,
            fmt=fmt,
            encoding=encoding,
            report_path=None,
            overrides={},
        )
    except Exception as exc:  # noqa: BLE001
        code = _handle(exc)
    ctx.exit(code)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main.main(standalone_mode=False) or 0)
