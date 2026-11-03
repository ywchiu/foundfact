#!/usr/bin/env bash
# Copy shared UI modules into the extension (Chrome can't load files outside the extension dir).
# Usage: extension/build.sh [--release BACKEND_URL]  → also writes dist/foundfact.zip with that default backend.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$here/shared" && mkdir -p "$here/shared"
cp "$here/../shared/"*.js "$here/../shared/"*.css "$here/shared/"
cp -R "$here/../shared/fonts" "$here/shared/fonts"
if [[ "${1:-}" == "--release" ]]; then
  url="${2:?backend url required}"
  out="$here/../dist"; mkdir -p "$out"; tmp="$(mktemp -d)"
  rsync -a --exclude tests --exclude build.sh "$here/" "$tmp/foundfact/"
  sed -i '' "s#http://127.0.0.1:8000#${url}#g" "$tmp/foundfact/config.js"
  # Store build: only the public backend host, no localhost permissions.
  python3 - "$tmp/foundfact/manifest.json" "${url%/}/*" <<'PY'
import json, sys
p, host = sys.argv[1], sys.argv[2]
m = json.load(open(p))
m["host_permissions"] = [h for h in m["host_permissions"]
                         if not any(k in h for k in ("127.0.0.1", "localhost", "run.app")) and h != host] + [host]
json.dump(m, open(p, "w"), ensure_ascii=False, indent=2)
PY
  (cd "$tmp/foundfact" && zip -qr "$out/foundfact.zip" .)
  echo "wrote $out/foundfact.zip (backend $url)"
fi
