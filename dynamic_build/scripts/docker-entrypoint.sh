#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${CFLAGS:-}" ]]; then
  export CFLAGS="${CFLAGS} -I/usr/local/include"
else
  export CFLAGS="-I/usr/local/include"
fi

if [[ -n "${LDFLAGS:-}" ]]; then
  export LDFLAGS="${LDFLAGS} -L/usr/local/lib"
else
  export LDFLAGS="-L/usr/local/lib"
fi

if [[ -n "${LIBS:-}" ]]; then
  export LIBS="${LIBS} -lldpasswd -lm"
else
  export LIBS="-lldpasswd -lm"
fi

exec "$@"
