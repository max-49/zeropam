#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${CFLAGS:-}" ]]; then
  export CFLAGS="${CFLAGS} -I/usr/local/include"
else
  export CFLAGS="-I/usr/local/include"
fi

if [[ -n "${LDFLAGS:-}" ]]; then
  export LDFLAGS="${LDFLAGS} -L/usr/local/lib -lldpasswd"
else
  export LDFLAGS="-L/usr/local/lib -lldpasswd"
fi

exec "$@"
