#!/bin/sh
# One-time: fix dirty git tree on NAS (no native git required)
# Run on NAS as root or with sudo password in NAS_SUDO_PASSWORD
#
#   sh scripts/nas-one-time-git-reset.sh

set -e
REPO="/volume1/docker/saenggibu"
BRANCH="${SGB_BRANCH:-cursor/saenggibu-writer-5821}"

if [ -f "$REPO/.env" ]; then
  line=$(grep -E '^SGB_DEPLOY_BRANCH=' "$REPO/.env" 2>/dev/null | tail -n 1 || true)
  if [ -n "$line" ]; then
    BRANCH=$(echo "${line#SGB_DEPLOY_BRANCH=}" | tr -d '\r' | tr -d '"' | tr -d "'")
  fi
fi

export PATH="/usr/local/bin:/var/packages/ContainerManager/target/usr/bin:$PATH"
DOCKER="/usr/local/bin/docker"
[ -x "$DOCKER" ] || DOCKER=$(command -v docker)

echo "==> reset $REPO to origin/$BRANCH"
$DOCKER run --rm --entrypoint sh \
  -v "$REPO:/git" -w /git \
  alpine/git:latest \
  -ec "
    git config --global --add safe.directory /git
    git fetch origin '$BRANCH'
    git clean -fd -e .env -e logs
    git reset --hard 'origin/$BRANCH'
    git rev-parse --short HEAD
  "
echo "==> done. Next: curl deploy script or wait for DSM task"
