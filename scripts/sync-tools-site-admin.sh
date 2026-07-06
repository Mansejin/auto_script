#!/usr/bin/env bash
# deploy/tools-site-admin → tools-site 저장소로 redirect 페이지만 복사
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-}"

if [[ -z "$TARGET" ]]; then
  echo "사용법: $0 /path/to/tools-site"
  echo "예: $0 ../tools-site"
  exit 1
fi

SRC="$ROOT/deploy/tools-site-admin"
DEST="$TARGET/admin/saenggibu"

mkdir -p "$DEST"
cp "$SRC/admin/saenggibu/index.html" "$DEST/index.html"

if [[ -f "$SRC/robots.txt.snippet" ]]; then
  if [[ -f "$TARGET/robots.txt" ]]; then
    if ! grep -q 'Disallow: /admin/' "$TARGET/robots.txt"; then
      printf '\n%s\n' "$(cat "$SRC/robots.txt.snippet")" >> "$TARGET/robots.txt"
      echo "robots.txt 에 /admin/ Disallow 추가됨"
    fi
  else
    cp "$SRC/robots.txt.snippet" "$TARGET/robots.txt"
    echo "robots.txt 생성됨"
  fi
fi

echo "복사 완료: $DEST/index.html"
