#!/bin/sh
# DSM Task Scheduler wrapper — see nas-dsm-task.sh for the full script.
exec sh "$(dirname "$0")/nas-dsm-task.sh"
