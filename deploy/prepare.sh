#!/usr/bin/env bash
# Run before building the image: folds hunch's WAL into hunch.db so the copied file is complete.
# Stop `hunch serve` first or the checkpoint can't truncate.
set -euo pipefail
cd "$(dirname "$0")/.."
sqlite3 data/hunch.db "PRAGMA wal_checkpoint(TRUNCATE);"
for f in data/cases.jsonl data/cases.npy data/cases.npy.meta data/hunch.db; do test -s "$f" || { echo "missing $f"; exit 1; }; done
echo "ready: $(du -h data/hunch.db | cut -f1) hunch.db"
