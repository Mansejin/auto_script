#!/bin/sh
# DSM Task Scheduler: run every 5-15 minutes as backup when GitHub Actions is unavailable.
#
# DSM -> Control Panel -> Task Scheduler -> Create -> Scheduled task -> User-defined script
# Schedule: every 10 minutes (or daily 3 AM)
# User: root (or a user in docker group)
# Script:
#   /volume1/docker/saenggibu/scripts/nas-scheduled-pull.sh
#
# Lock file prevents overlapping runs.

REPO_DIR="/volume1/docker/saenggibu"
LOCK="/tmp/saenggibu-deploy.lock"
MAX_AGE=1800

if [ -f "$LOCK" ]; then
  age=$(( $(date +%s) - $(stat -c %Y "$LOCK" 2>/dev/null || stat -f %m "$LOCK") ))
  if [ "$age" -lt "$MAX_AGE" ]; then
    exit 0
  fi
  rm -f "$LOCK"
fi

touch "$LOCK"
trap 'rm -f "$LOCK"' EXIT INT TERM

cd "$REPO_DIR" || exit 1
export PATH="/usr/local/bin:/var/packages/ContainerManager/target/usr/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
sh scripts/nas-docker-update.sh >> logs/scheduled-pull.log 2>&1
