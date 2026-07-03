#!/bin/sh
# DSM Task Scheduler: run every 10 minutes (user: root recommended)
#
# Script field in DSM:
#   sh /volume1/docker/saenggibu/scripts/nas-scheduled-pull.sh
#
# Log: /volume1/docker/saenggibu/logs/scheduled-pull.log

REPO_DIR="/volume1/docker/saenggibu"
LOG_FILE="$REPO_DIR/logs/scheduled-pull.log"
LOCK="/tmp/saenggibu-deploy.lock"
MAX_AGE=1800
BRANCH="cursor/saenggibu-writer-5821"

mkdir -p "$REPO_DIR/logs"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') scheduled pull start ===" >> "$LOG_FILE"

if [ -f "$REPO_DIR/.env" ]; then
  line=$(grep -E '^SGB_DEPLOY_BRANCH=' "$REPO_DIR/.env" 2>/dev/null | tail -n 1 || true)
  if [ -n "$line" ]; then
    BRANCH=$(echo "${line#SGB_DEPLOY_BRANCH=}" | tr -d '\r' | tr -d '"' | tr -d "'")
  fi
fi

if [ -f "$LOCK" ]; then
  age=$(( $(date +%s) - $(stat -c %Y "$LOCK" 2>/dev/null || stat -f %m "$LOCK") ))
  if [ "$age" -lt "$MAX_AGE" ]; then
    echo "skip: lock active" >> "$LOG_FILE"
    exit 0
  fi
  rm -f "$LOCK"
fi

touch "$LOCK"
trap 'rm -f "$LOCK"' EXIT INT TERM

export PATH="/usr/local/bin:/var/packages/ContainerManager/target/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
export SGB_BRANCH="$BRANCH"
export SGB_DOCKER_SUDO=1

if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: curl not found" >> "$LOG_FILE"
  exit 1
fi

if ! curl -fsSL "https://raw.githubusercontent.com/Mansejin/auto_script/${BRANCH}/scripts/nas-docker-update.sh" \
  -o /tmp/sgb-deploy.sh; then
  echo "ERROR: curl deploy script failed" >> "$LOG_FILE"
  exit 1
fi

sed -i 's/\r$//' /tmp/sgb-deploy.sh 2>/dev/null || true
sh /tmp/sgb-deploy.sh >> "$LOG_FILE" 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S') scheduled pull end (exit $?) ===" >> "$LOG_FILE"
