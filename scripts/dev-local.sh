#!/bin/sh
# Local dev server — test admin UI/API without NAS docker restart
#   ./scripts/dev-local.sh

set -e
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  cp config.example.env .env
  echo "Created .env — set ADMIN_PASSWORD and GEMINI_API_KEY"
fi

export SGB_HOST=127.0.0.1
export SGB_PORT="${SGB_PORT:-8787}"
export SGB_RELOAD=1
export SGB_PLAN=admin
export SGB_ALLOWED_ORIGINS="${SGB_ALLOWED_ORIGINS:-http://127.0.0.1:${SGB_PORT},http://localhost:${SGB_PORT}}"

if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "Installing dependencies..."
  python3 -m pip install -q -r requirements.txt
fi

echo ""
echo "생기부 로컬 테스트 서버"
echo "  Admin UI: http://127.0.0.1:${SGB_PORT}/admin/saenggibu"
echo "  Health:   http://127.0.0.1:${SGB_PORT}/health"
echo ""
echo "· UI(web/admin) 수정 → 저장 후 브라우저 새로고침"
echo "· Python API 수정 → 자동 재시작 (SGB_RELOAD=1)"
echo "· NAS 배포는 기능 확인 후 하루 1~2회만"
echo ""

exec python3 server.py
