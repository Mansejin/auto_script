#!/usr/bin/env bash
# web/admin → deploy/tools-site-admin (mansejin.com GitHub Pages용)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/web/admin"
DEST="$ROOT/deploy/tools-site-admin/admin/saenggibu"

mkdir -p "$DEST"
cp -r "$SRC/css" "$SRC/js" "$SRC/samples" "$DEST/"

sed \
  -e 's|href="/admin-static/css/|href="css/|g' \
  -e 's|src="/admin-static/js/|src="js/|g' \
  -e 's|data-api-base="" data-assets-base="/admin-static"|data-api-base="https://sgb.mansejin.com" data-assets-base=""|' \
  "$SRC/index.html" > "$DEST/index.html"

echo "deploy 번들 갱신: $DEST"
