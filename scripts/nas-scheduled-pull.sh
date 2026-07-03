#!/bin/sh
# DSM Task Scheduler: run every 10 minutes (user: root recommended)
#
# Script:
#   /volume1/docker/saenggibu/scripts/nas-scheduled-pull.sh

REPO_DIR="/volume1/docker/saenggibu"
LOCK="/tmp/saenggibu-deploy.lock"
MAX_AGE=1800
BRANCH="cursor/saenggibu-writer-5821"

if [ -f "$REPO_DIR/.env" ]; then
  line=$(grep -E '^SGB_DEPLOY_BRANCH=' "$REPO_DIR/.env" 2>/dev/null | tail -n 1 || true)
  if [ -n "$line" ]; then
    BRANCH=$(echo "${line#SGB_DEPLOY_BRANCH=}" | tr -d '\r' | tr -d '"' | tr -d "'")
  fi
fi

if [ -f "$LOCK" ]; then
  age=$(( $(date +%s) - $(stat -c %Y "$LOCK" 2>/dev/null || stat -f %m "$LOCK") ))
  if [ "$age" -lt "$MAX_AGE" ]; then
    exit 0
  fi
  rm -f "$LOCK"
fi

touch "$LOCK"
trap 'rm -f "$LOCK"' EXIT INT TERM

export PATH="/usr/local/bin:/var/packages/ContainerManager/target/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
export SGB_BRANCH="$BRANCH"
export SGB_DOCKER_SUDO=1

mkdir -p "$REPO_DIR/logs"

if command -v curl >/dev/null 2>&1; then
  curl -fsSL "https://raw.githubusercontent.com/Mansejin/auto_script/${BRANCH}/scripts/nas-docker-update.sh" \
    -o /tmp/sgb-deploy.sh
  sed -i 's/\r$//' /tmp/sgb-deploy.sh 2>/dev/null || true
  sh /tmp/sgb-deploy.sh >> "$REPO_DIR/logs/scheduled-pull.log" 2>&1
else
  echo "ERROR: curl not found" >> "$REPO_DIR/logs/scheduled-pull.log"
  exit 1
fi
