#!/usr/bin/env bash
set -euo pipefail

python scripts/fetch_datasets.py data_jobs

dataclean clean \
  --input  data/raw/data_jobs.csv \
  --output data/clean/data_jobs.clean.csv \
  --config configs/data_jobs.yaml \
  --report runs/data_jobs.manifest.json \
  -v
