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

# Re-run as root when PC passes NAS_SUDO_PASSWORD (Synology SSH sudo needs password)
if [ "$(id -u)" != "0" ] && [ -n "$NAS_SUDO_PASSWORD" ] && [ -z "$SGB_DEPLOY_AS_ROOT" ]; then
  export SGB_DEPLOY_AS_ROOT=1
  printf '%s\n' "$NAS_SUDO_PASSWORD" | sudo -S -E env \
    SGB_BRANCH="${SGB_BRANCH:-}" \
    SGB_DOCKER_SUDO="${SGB_DOCKER_SUDO:-}" \
    NAS_SUDO_PASSWORD="$NAS_SUDO_PASSWORD" \
    SGB_DEPLOY_AS_ROOT=1 \
    sh "$0" "$@"
  exit $?
fi

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
  for candidate in \
    /usr/bin/git \
    /usr/local/bin/git \
    /var/packages/Git/target/usr/bin/git \
    /var/packages/Git/target/bin/git
  do
    if [ -x "$candidate" ]; then
      echo "$candidate"
      return
    fi
  done
  if command -v git >/dev/null 2>&1; then
    command -v git
    return
  fi
  echo ""
}

git_sync_deploy() {
  GIT=$(resolve_git)
  if [ -n "$GIT" ]; then
    log "==> git sync ($BRANCH) via $GIT"
    "$GIT" fetch origin "$BRANCH" || "$GIT" fetch origin
    "$GIT" clean -fd -e .env -e logs
    "$GIT" reset --hard "origin/$BRANCH"
    log "==> git at $("$GIT" rev-parse --short HEAD)"
    return
  fi

  log "==> git sync ($BRANCH) via docker (no native git on NAS)"
  ensure_docker_access
  short=$($DOCKER run --rm \
    -v "$REPO_DIR:/git" \
    -w /git \
    "$GIT_IMAGE" \
    sh -ec "
      git config --global --add safe.directory /git
      git fetch origin '$BRANCH'
      git clean -fd -e .env -e logs
      git reset --hard 'origin/$BRANCH'
      git rev-parse --short HEAD
    ")
  log "==> git at $short"
}

docker_can_run() {
  # shellcheck disable=SC2086
  $DOCKER info >/dev/null 2>&1
}

ensure_docker_access() {
  if docker_can_run; then
    return
  fi

  base=$DOCKER
  for prefix in "sudo -n" "sudo"; do
    DOCKER="$prefix $base"
    if docker_can_run; then
      log "==> docker ($prefix): $DOCKER"
      return
    fi
  done

  log "ERROR: cannot access docker daemon."
  log "  1) One-time (root): sh scripts/nas-setup-docker-sudo.sh"
  log "  2) PC config: NAS_SUDO_PASSWORD in config/nas-pc.local.env"
  log "  3) NAS .env: SGB_DOCKER_SUDO=1"
  log "  4) DSM Task Scheduler as root"
  exit 126
}

read_env_flag() {
  key="$1"
  if [ -f "$REPO_DIR/.env" ]; then
    line=$(grep -E "^${key}=" "$REPO_DIR/.env" 2>/dev/null | tail -n 1 || true)
    if [ -n "$line" ]; then
      val=$(echo "${line#*=}" | tr -d '\r' | tr -d '"' | tr -d "'")
      if [ "$val" = "1" ] || [ "$val" = "true" ] || [ "$val" = "yes" ]; then
        echo "1"
        return
      fi
    fi
  fi
  echo ""
}

if [ -z "$SGB_DOCKER_SUDO" ]; then
  SGB_DOCKER_SUDO=$(read_env_flag SGB_DOCKER_SUDO)
fi
# default: try sudo for Synology non-root SSH users
if [ -z "$SGB_DOCKER_SUDO" ]; then
  SGB_DOCKER_SUDO=1
fi

DOCKER=$(resolve_docker)
if [ -z "$DOCKER" ]; then
  log "ERROR: docker not found."
  log "Open DSM Container Manager and ensure it is running."
  exit 127
fi

mkdir -p "$LOG_DIR"
log "==> deploy start (branch=$BRANCH)"

cd "$REPO_DIR" || exit 1

compose_up() {
  if [ -f docker-compose.cloudflare.yml ] && grep -q '^CLOUDFLARE_TUNNEL_TOKEN=' .env 2>/dev/null; then
    $DOCKER compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d --build
  else
    $DOCKER compose up -d --build
  fi
}

if [ "$LOGS_ONLY" = "1" ]; then
  ensure_docker_access
  log "==> docker: $DOCKER"
  $DOCKER compose logs -f --tail=80
  exit 0
fi

if [ ! -d .git ]; then
  log "ERROR: no .git in $REPO_DIR"
  exit 1
fi

git_sync_deploy

if [ "$NO_BUILD" = "1" ]; then
  log "==> skip rebuild (--no-build)"
else
  ensure_docker_access
  log "==> docker: $DOCKER"
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
