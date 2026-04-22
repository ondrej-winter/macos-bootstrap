#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/logging.sh"
ENTRYPOINT_SCRIPT="${SCRIPT_DIR}/entrypoint.sh"

if [ ! -f "$ENTRYPOINT_SCRIPT" ]; then
    log_error "entrypoint.sh not found: $ENTRYPOINT_SCRIPT"
    exit 1
fi

log_warning "bootstrap.sh is deprecated; forwarding to entrypoint.sh"
exec bash "$ENTRYPOINT_SCRIPT" "$@"