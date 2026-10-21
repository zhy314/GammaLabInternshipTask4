#!/usr/bin/env bash
# End-to-end example for the Adult Census Income dataset.
set -euo pipefail

python scripts/fetch_datasets.py adult

dataclean clean \
  --input  data/raw/adult.csv \
  --output data/clean/adult.clean.csv \
  --config configs/adult.yaml \
  --report runs/adult.manifest.json \
  -v
