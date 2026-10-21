#!/usr/bin/env bash
set -euo pipefail

python scripts/fetch_datasets.py titanic

dataclean clean \
  --input  data/raw/titanic.csv \
  --output data/clean/titanic.clean.csv \
  --config configs/titanic.yaml \
  --report runs/titanic.manifest.json \
  -v
