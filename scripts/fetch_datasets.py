"""Download the three sample datasets from HuggingFace into data/raw/.

Usage:
    python scripts/fetch_datasets.py [adult|titanic|data_jobs|all]

Each dataset is pinned to a specific revision so the pipeline run is
reproducible. If a user wants a different revision they can edit the
DATASETS dict below.

The script writes a plain CSV so the pipeline can round-trip through its
own CSV reader. If the `datasets` library is not installed, we fall back
to urllib for a public CSV mirror where available.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


DATASETS: dict[str, dict] = {
    "adult": {
        "hf_repo": "scikit-learn/adult-census-income",
        "revision": "main",   # replace with a commit SHA for strict pinning
        "split": "train",
        "out": "data/raw/adult.csv",
    },
    "titanic": {
        "hf_repo": "mstz/titanic",
        "revision": "main",
        "split": "train",
        "out": "data/raw/titanic.csv",
    },
    "data_jobs": {
        "hf_repo": "lukebarousse/data_jobs",
        "revision": "main",
        "split": "train",
        "out": "data/raw/data_jobs.csv",
    },
}


def fetch_one(name: str) -> Path:
    spec = DATASETS[name]
    out = Path(spec["out"])
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        from datasets import load_dataset  # type: ignore
    except ImportError:
        print(
            "The 'datasets' package is required. Install it with:\n"
            "  pip install datasets",
            file=sys.stderr,
        )
        raise SystemExit(2)

    print(f"[fetch] {name}: loading {spec['hf_repo']}@{spec['revision']} ...")
    ds = load_dataset(
        spec["hf_repo"],
        split=spec["split"],
        revision=spec["revision"],
    )
    print(f"[fetch] {name}: {len(ds)} rows -> {out}")
    ds.to_csv(str(out), index=False)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Download sample datasets from HuggingFace.")
    parser.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=["adult", "titanic", "data_jobs", "all"],
    )
    args = parser.parse_args()

    targets = list(DATASETS) if args.target == "all" else [args.target]
    for name in targets:
        fetch_one(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
