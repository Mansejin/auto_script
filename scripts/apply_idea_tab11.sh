#!/usr/bin/env bash
# 레노버 아이디어 탭 11 콘티 마무리 반영 스크립트
set -euo pipefail
cd "$(dirname "$0")/.."

export WORKSHEET_NAME="${WORKSHEET_NAME:-레노버 아이디어 탭 11}"

echo "==> 행 24, 29 장면/사이즈 보완"
python3 cli.py update changes/idea_tab11_update.json

echo "==> 행 78~99 액세서리·총평 구간 교체"
python3 cli.py replace-range 78 99 changes/idea_tab11_finish.tsv

echo "==> 반영 결과 확인"
python3 cli.py read --part 총평
