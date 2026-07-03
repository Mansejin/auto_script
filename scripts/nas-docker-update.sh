#!/bin/sh
# 시놀로지 나스에서 코드 pull + Docker 재빌드 (한 줄 업데이트)
#
# 수동 실행:
#   cd /volume1/docker/saenggibu && sh scripts/nas-docker-update.sh
#
# 자동화 (한 번만 설정):
#   DSM → 제어판 → 작업 스케줄러 → 생성 → 예약된 작업 → 사용자 정의 스크립트
#   작업: 매일 새벽 3시 (또는 원하는 주기)
#   스크립트: /volume1/docker/saenggibu/scripts/nas-docker-update.sh
#
# 브랜치 변경: SGB_BRANCH=main sh scripts/nas-docker-update.sh

set -e

REPO_DIR="/volume1/docker/saenggibu"
BRANCH="${SGB_BRANCH:-main}"
GIT_IMAGE="alpine/git:latest"

cd "$REPO_DIR" || exit 1

if [ ! -d .git ]; then
  echo "오류: $REPO_DIR 에 .git 폴더가 없습니다."
  echo ""
  echo "처음 한 번만 아래를 실행하세요 (기존 .env·data/saenggibu 는 유지됨):"
  echo ""
  echo "  cd /volume1/docker"
  echo "  mv saenggibu saenggibu_backup"
  echo "  docker run --rm -v /volume1/docker:/git -w /git $GIT_IMAGE clone -b $BRANCH https://github.com/Mansejin/auto_script.git saenggibu"
  echo "  cp saenggibu_backup/.env saenggibu/.env 2>/dev/null || true"
  echo "  cp -a saenggibu_backup/data/saenggibu/. saenggibu/data/saenggibu/ 2>/dev/null || true"
  exit 1
fi

echo "==> git pull ($BRANCH)"
docker run --rm \
  -v "$REPO_DIR:/git" \
  -w /git \
  "$GIT_IMAGE" \
  pull origin "$BRANCH"

echo ""
echo "==> docker compose up -d --build"
if [ -f docker-compose.cloudflare.yml ] && grep -q '^CLOUDFLARE_TUNNEL_TOKEN=' .env 2>/dev/null; then
  docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d --build
else
  docker compose up -d --build
fi

echo ""
echo "==> 완료 ($(date '+%Y-%m-%d %H:%M'))"
