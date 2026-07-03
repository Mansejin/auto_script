#!/bin/sh
# Synology NAS: git pull + docker compose rebuild
#
# Usage:
#   cd /volume1/docker/saenggibu && sh scripts/nas-docker-update.sh
#
# Branch: SGB_BRANCH=cursor/saenggibu-writer-5821 sh scripts/nas-docker-update.sh
# Sudo:   SGB_DOCKER_SUDO=1 sh scripts/nas-docker-update.sh

set -e

REPO_DIR="/volume1/docker/saenggibu"
BRANCH="${SGB_BRANCH:-cursor/saenggibu-writer-5821}"
GIT_IMAGE="alpine/git:latest"

# Synology Container Manager (non-interactive SSH often has empty PATH)
export PATH="/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

resolve_docker() {
  if [ -n "$DOCKER_BIN" ] && [ -x "$DOCKER_BIN" ]; then
    echo "$DOCKER_BIN"
    return
  fi
  if [ -x /usr/local/bin/docker ]; then
    echo /usr/local/bin/docker
    return
  fi
  if command -v docker >/dev/null 2>&1; then
    command -v docker
    return
  fi
  echo ""
}

DOCKER=$(resolve_docker)
if [ -z "$DOCKER" ]; then
  echo "ERROR: docker not found."
  echo "  - Install Container Manager on DSM"
  echo "  - Or run: export PATH=/usr/local/bin:\$PATH"
  exit 127
fi

if [ "$SGB_DOCKER_SUDO" = "1" ]; then
  DOCKER="sudo $DOCKER"
fi

echo "==> using: $DOCKER"

cd "$REPO_DIR" || exit 1

if [ ! -d .git ]; then
  echo "ERROR: no .git in $REPO_DIR"
  echo "Clone first:"
  echo "  $DOCKER run --rm -v /volume1/docker:/git -w /git $GIT_IMAGE clone -b $BRANCH https://github.com/Mansejin/auto_script.git saenggibu"
  exit 1
fi

echo "==> git pull ($BRANCH)"
$DOCKER run --rm \
  -v "$REPO_DIR:/git" \
  -w /git \
  "$GIT_IMAGE" \
  pull origin "$BRANCH"

echo ""
echo "==> docker compose up -d --build"
if [ -f docker-compose.cloudflare.yml ] && grep -q '^CLOUDFLARE_TUNNEL_TOKEN=' .env 2>/dev/null; then
  $DOCKER compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d --build
else
  $DOCKER compose up -d --build
fi

echo ""
echo "==> done ($(date '+%Y-%m-%d %H:%M'))"
