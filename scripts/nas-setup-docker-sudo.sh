#!/bin/sh
# One-time NAS setup: passwordless docker for deploy user (run as root)
#
# DSM Task Scheduler -> User-defined script -> User: root -> Run once:
#   sh /volume1/docker/saenggibu/scripts/nas-setup-docker-sudo.sh
#
# Or SSH as root (if enabled).

set -e

DEPLOY_USER="${NAS_DEPLOY_USER:-ohola}"
SUDOERS_FILE="/etc/sudoers.d/saenggibu-deploy"

if [ "$(id -u)" != "0" ]; then
  echo "ERROR: run as root (DSM Task Scheduler user: root)"
  exit 1
fi

DOCKER_PATHS="/usr/local/bin/docker"
for p in \
  /var/packages/ContainerManager/target/usr/bin/docker \
  /var/packages/Docker/target/usr/bin/docker
do
  if [ -x "$p" ]; then
    DOCKER_PATHS="$DOCKER_PATHS, $p"
  fi
done

cat > "$SUDOERS_FILE" <<EOF
# saenggibu deploy — passwordless docker for $DEPLOY_USER
$DEPLOY_USER ALL=(ALL) NOPASSWD: $DOCKER_PATHS
EOF
chmod 440 "$SUDOERS_FILE"

if command -v visudo >/dev/null 2>&1; then
  visudo -c
fi

echo "OK: $DEPLOY_USER can run docker without password"
echo "File: $SUDOERS_FILE"
echo "Test as $DEPLOY_USER: sudo -n /usr/local/bin/docker ps"
