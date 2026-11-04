#!/usr/bin/env bash
# Bundle UI and static reference data. --release writes the standalone BYOK ZIP.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$here/shared" && mkdir -p "$here/shared" "$here/data"
cp "$here/../shared/"*.js "$here/../shared/"*.css "$here/shared/"
cp -R "$here/../shared/fonts" "$here/shared/fonts"
cp "$here/../data/blocklist.tsv" "$here/../data/cases.jsonl" "$here/data/"
if [[ "${1:-}" == "--release" ]]; then
  out="$here/../dist"; mkdir -p "$out"; tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  rsync -a --exclude tests --exclude build.sh "$here/" "$tmp/foundfact/"
  rm -f "$out/foundfact.zip"
  (cd "$tmp/foundfact" && zip -qr "$out/foundfact.zip" .)
  echo "wrote $out/foundfact.zip (standalone BYOK)"
fi
