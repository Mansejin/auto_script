#!/bin/sh
# Synology NAS: git pull + docker compose rebuild
#
# Usage:
#   cd /volume1/docker/saenggibu && sh scripts/nas-docker-update.sh
#   cd /volume1/docker/saenggibu && sh scripts/nas-docker-update.sh --logs-only
#   cd /volume1/docker/saenggibu && sh scripts/nas-docker-update.sh --no-build
#
# Branch: SGB_BRANCH=main sh scripts/nas-docker-update.sh
#        (or set SGB_DEPLOY_BRANCH in .env)
# Sudo:   SGB_DOCKER_SUDO=1 sh scripts/nas-docker-update.sh

set -e

REPO_DIR="/volume1/docker/saenggibu"
GIT_IMAGE="alpine/git:latest"
LOGS_ONLY=0
NO_BUILD=0

for arg in "$@"; do
  case "$arg" in
    --logs-only) LOGS_ONLY=1 ;;
    --no-build) NO_BUILD=1 ;;
  esac
done

export PATH="/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

log() {
  echo "$@"
  if [ -n "$LOG_FILE" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG_FILE"
  fi
}

read_deploy_branch() {
  if [ -n "$SGB_BRANCH" ]; then
    echo "$SGB_BRANCH"
    return
  fi
  if [ -f "$REPO_DIR/.env" ]; then
    line=$(grep -E '^SGB_DEPLOY_BRANCH=' "$REPO_DIR/.env" 2>/dev/null | tail -n 1 || true)
    if [ -n "$line" ]; then
      echo "${line#SGB_DEPLOY_BRANCH=}" | tr -d '\r' | tr -d '"' | tr -d "'"
      return
    fi
  fi
  echo "main"
}

BRANCH=$(read_deploy_branch)
LOG_DIR="$REPO_DIR/logs"
LOG_FILE="$LOG_DIR/deploy.log"

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

resolve_git() {
  if command -v git >/dev/null 2>&1; then
    command -v git
    return
  fi
  for candidate in \
    /usr/bin/git \
    /usr/local/bin/git \
    /var/packages/Git/target/usr/bin/git
  do
    if [ -x "$candidate" ]; then
      echo "$candidate"
      return
    fi
  done
  echo ""
}

docker_can_run() {
  $DOCKER info >/dev/null 2>&1
}

ensure_docker_access() {
  if docker_can_run; then
    return
  fi
  if [ "$SGB_DOCKER_SUDO" = "1" ] || [ "$SGB_DOCKER_SUDO" = "true" ]; then
    DOCKER="sudo $DOCKER"
    if docker_can_run; then
      log "==> docker (sudo): $DOCKER"
      return
    fi
  fi
  if sudo $DOCKER info >/dev/null 2>&1; then
    DOCKER="sudo $DOCKER"
    log "==> docker (sudo, auto): $DOCKER"
    return
  fi
  log "ERROR: cannot access docker daemon (try SGB_DOCKER_SUDO=1)"
  exit 126
}

DOCKER=$(resolve_docker)
if [ -z "$DOCKER" ]; then
  log "ERROR: docker not found."
  log "Open DSM Container Manager and ensure it is running."
  exit 127
fi

if [ "$SGB_DOCKER_SUDO" = "1" ]; then
  DOCKER="sudo $DOCKER"
fi

mkdir -p "$LOG_DIR"
log "==> deploy start (branch=$BRANCH)"

cd "$REPO_DIR" || exit 1

ensure_docker_access
log "==> docker: $DOCKER"

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
  log "ERROR: no .git in $REPO_DIR"
  exit 1
fi

GIT=$(resolve_git)
log "==> git pull ($BRANCH)"
if [ -n "$GIT" ]; then
  "$GIT" fetch origin "$BRANCH"
  "$GIT" checkout "$BRANCH" 2>/dev/null || "$GIT" checkout -B "$BRANCH" "origin/$BRANCH"
  "$GIT" pull origin "$BRANCH"
else
  $DOCKER run --rm \
    -v "$REPO_DIR:/git" \
    -w /git \
    "$GIT_IMAGE" \
    pull origin "$BRANCH"
fi

if [ "$NO_BUILD" = "1" ]; then
  log "==> skip rebuild (--no-build)"
else
  log "==> docker compose up -d --build"
  compose_up
fi

if command -v curl >/dev/null 2>&1; then
  if curl -sf "http://127.0.0.1:${SGB_PORT:-8787}/health" >/dev/null 2>&1; then
    log "==> health OK"
  else
    log "WARN: health check failed (container may still be starting)"
  fi
fi

log "==> done ($(date '+%Y-%m-%d %H:%M'))"
