#!/bin/sh
# Container entrypoint.
#
#   (no args) | daemon [--log-format=json]  -> the audit/anchor daemon, foreground
#   anything else                           -> passed to the `sov` CLI
#
# The daemon reads SOV_DAEMON_* from the environment (see compose.yaml).
# `sov daemon start` is not used here: it detaches, and a container needs
# its server in the foreground so signals and restarts reach it.
set -eu

if [ "$#" -eq 0 ]; then
  set -- daemon
fi

if [ "$1" = "daemon" ]; then
  shift
  case "${1:-}" in
    start|stop|status)
      echo "sov-entrypoint: 'daemon $1' manages a detached host process." >&2
      echo "In the container, run 'daemon' and manage it with docker compose (up / stop / ps)." >&2
      exit 64
      ;;
  esac
  exec python -m sov_daemon "$@"
fi

exec sov "$@"
