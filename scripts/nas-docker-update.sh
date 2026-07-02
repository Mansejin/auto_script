#!/bin/sh
# 시놀로지 나스에서 git 없이 Docker로 코드 업데이트
# 사용: sh scripts/nas-docker-update.sh
# 경로: /volume1/docker/saenggibu

set -e

REPO_DIR="/volume1/docker/saenggibu"
BRANCH="${SGB_BRANCH:-cursor/saenggibu-writer-5821}"
IMAGE="alpine/git:latest"

cd "$REPO_DIR" || exit 1

if [ ! -d .git ]; then
  echo "오류: $REPO_DIR 에 .git 폴더가 없습니다."
  echo ""
  echo "처음 한 번만 아래를 실행하세요 (기존 .env·data/saenggibu 는 유지됨):"
  echo ""
  echo "  cd /volume1/docker"
  echo "  mv saenggibu saenggibu_backup"
  echo "  docker run --rm -v /volume1/docker:/git -w /git $IMAGE clone -b $BRANCH https://github.com/Mansejin/auto_script.git saenggibu"
  echo "  cp saenggibu_backup/.env saenggibu/.env 2>/dev/null || true"
  echo "  cp -a saenggibu_backup/data/saenggibu/. saenggibu/data/saenggibu/ 2>/dev/null || true"
  exit 1
fi

echo "==> git pull ($BRANCH)"
docker run --rm \
  -v "$REPO_DIR:/git" \
  -w /git \
  "$IMAGE" \
  pull origin "$BRANCH"

echo ""
echo "==> 완료. Container Manager에서 saenggibu 프로젝트를 재시작하세요."
echo "    (설정/Dockerfile 바뀌었으면 '다시 빌드' 후 실행)"
