#!/bin/sh
# Synology NAS: git pull + docker compose rebuild
#
# Usage:
#   cd /volume1/docker/saenggibu && sh scripts/nas-docker-update.sh
#   cd /volume1/docker/saenggibu && sh scripts/nas-docker-update.sh --logs-only
#
# Branch: SGB_BRANCH=main sh scripts/nas-docker-update.sh
# Sudo:   SGB_DOCKER_SUDO=1 sh scripts/nas-docker-update.sh

set -e

REPO_DIR="/volume1/docker/saenggibu"
BRANCH="${SGB_BRANCH:-cursor/saenggibu-writer-5821}"
GIT_IMAGE="alpine/git:latest"
LOGS_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --logs-only) LOGS_ONLY=1 ;;
  esac
done

export PATH="/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

resolve_docker() {
  if [ -n "$DOCKER_BIN" ] && [ -x "$DOCKER_BIN" ]; then
    echo "$DOCKER_BIN"
    return
  fi
  for candidate in \
    /usr/local/bin/docker \
    /var/packages/ContainerManager/target/usr/bin/docker \
    /var/packages/ContainerManager/target/bin/docker \
    /var/packages/Docker/target/usr/bin/docker \
    /var/packages/Docker/target/bin/docker
  do
    if [ -x "$candidate" ]; then
      echo "$candidate"
      return
    fi
  done
  found=$(find /var/packages/ContainerManager /var/packages/Docker \
    -path '*/bin/docker' -type f 2>/dev/null | head -n 1)
  if [ -n "$found" ] && [ -x "$found" ]; then
    echo "$found"
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
  echo "Tried: /usr/local/bin/docker, ContainerManager package path"
  echo "Open DSM Container Manager and ensure it is running."
  exit 127
fi

if [ "$SGB_DOCKER_SUDO" = "1" ]; then
  DOCKER="sudo $DOCKER"
fi

echo "==> docker: $DOCKER"

cd "$REPO_DIR" || exit 1

compose_up() {
  if [ -f docker-compose.cloudflare.yml ] && grep -q '^CLOUDFLARE_TUNNEL_TOKEN=' .env 2>/dev/null; then
    $DOCKER compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d --build
  else
    $DOCKER compose up -d --build
  fi
}

if [ "$LOGS_ONLY" = "1" ]; then
  $DOCKER compose logs -f --tail=80
  exit 0
fi

if [ ! -d .git ]; then
  echo "ERROR: no .git in $REPO_DIR"
  exit 1
fi

echo "==> git pull ($BRANCH)"
if command -v git >/dev/null 2>&1; then
  git pull origin "$BRANCH"
else
  $DOCKER run --rm \
    -v "$REPO_DIR:/git" \
    -w /git \
    "$GIT_IMAGE" \
    pull origin "$BRANCH"
fi

echo ""
echo "==> docker compose up -d --build"
compose_up

echo ""
echo "==> done ($(date '+%Y-%m-%d %H:%M'))"
