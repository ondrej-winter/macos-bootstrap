#!/usr/bin/env bash

################################################################################
# Local Python initialization entrypoint
# Prepares a repository-local uv installation and ensures local Python is available.
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/logging.sh"
LOCAL_TOOLS_DIR="${SCRIPT_DIR}/.bootstrap-tools"
LOCAL_BIN_DIR="${LOCAL_TOOLS_DIR}/bin"
LOCAL_UV_BIN="${LOCAL_BIN_DIR}/uv"
LOCAL_PYTHON_DIR="${LOCAL_TOOLS_DIR}/python"
SHOW_HELP=false
UV_DOWNLOAD_URL="https://astral.sh/uv/install.sh"

print_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║              Local Python Initialization Entry             ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

print_help() {
    cat <<EOF_HELP
Usage: ./entrypoint.sh

Initializes repository-local uv and ensures the required local Python is
available locally for this repository under .bootstrap-tools.

Wrapper options:
  -h, --help              Show this help message and exit

Examples:
  ./entrypoint.sh
EOF_HELP
}

install_local_uv() {
    log_info "Checking for repository-local uv bootstrap..."

    if [ -x "$LOCAL_UV_BIN" ]; then
        log_success "Repository-local uv already available at $LOCAL_UV_BIN"
        return 0
    fi

    log_info "Installing repository-local uv into $LOCAL_TOOLS_DIR"
    mkdir -p "$LOCAL_BIN_DIR"

    env \
        UV_INSTALL_DIR="$LOCAL_BIN_DIR" \
        UV_UNMANAGED_INSTALL=1 \
        /bin/sh -c "$(curl -fsSL "$UV_DOWNLOAD_URL")"

    if [ ! -x "$LOCAL_UV_BIN" ]; then
        log_error "Failed to install repository-local uv at $LOCAL_UV_BIN"
        return 1
    fi

    log_success "Repository-local uv installed successfully"
}

install_python_with_local_uv() {
    log_info "Installing required Python via repository-local uv..."
    mkdir -p "$LOCAL_PYTHON_DIR"
    UV_PYTHON_INSTALL_DIR="$LOCAL_PYTHON_DIR" "$LOCAL_UV_BIN" python install --no-bin 3.13
    log_success "Python 3.13 is available through repository-local uv"
}

parse_arguments() {
    local arg=""

    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                SHOW_HELP=true
                ;;
            *)
                log_error "Unsupported argument: $arg"
                echo ""
                print_help
                exit 1
                ;;
        esac
    done
}

main() {
    print_banner

    parse_arguments "$@"

    if [ "$SHOW_HELP" = true ]; then
        print_help
        return 0
    fi

    log_info "Starting local Python initialization entrypoint..."
    echo ""

    log_info "═══════════════════════════════════════════════════════════"
    log_info "Phase 1: Repository-local uv"
    log_info "═══════════════════════════════════════════════════════════"
    echo ""

    install_local_uv
    install_python_with_local_uv

    echo ""
    log_success "════════════════════════════════════════════════════════════"
    log_success "Local Python initialization complete! 🎉"
    log_success "════════════════════════════════════════════════════════════"
    echo ""
}

main "$@"
exit $?