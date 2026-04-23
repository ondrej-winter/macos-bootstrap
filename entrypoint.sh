#!/usr/bin/env bash

################################################################################
# Local Python initialization entrypoint
# Prepares a repository-local uv installation and ensures local Python is available.
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/logging.sh"

readonly LOCAL_TOOLS_DIR="${SCRIPT_DIR}/.bootstrap-tools"
readonly LOCAL_BIN_DIR="${LOCAL_TOOLS_DIR}/bin"
readonly LOCAL_UV_BIN="${LOCAL_BIN_DIR}/uv"
readonly LOCAL_PYTHON_DIR="${LOCAL_TOOLS_DIR}/python"
readonly UV_DOWNLOAD_URL="https://astral.sh/uv/install.sh"
BREWFILE_ARGS=()

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
Usage: ./entrypoint.sh [options]

Initializes repository-local uv and ensures the required local Python is
available locally for this repository under .bootstrap-tools, then runs the
Python-based Brewfile installation phase.

Wrapper options:
  --reinstall-existing    Reinstall already-installed formulae and casks
  -h, --help              Show this help message and exit

Examples:
  ./entrypoint.sh
EOF_HELP
}

print_phase() {
    echo ""
    log_info "═══════════════════════════════════════════════════════════"
    log_info "$1"
    log_info "═══════════════════════════════════════════════════════════"
    echo ""
}

ensure_local_uv() {
    log_info "Checking for repository-local uv bootstrap..."

    if [ -x "$LOCAL_UV_BIN" ]; then
        log_success "Repository-local uv already available at $LOCAL_UV_BIN"
        return
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

ensure_local_python() {
    log_info "Installing required Python via repository-local uv..."
    mkdir -p "$LOCAL_PYTHON_DIR"
    UV_PYTHON_INSTALL_DIR="$LOCAL_PYTHON_DIR" "$LOCAL_UV_BIN" python install --no-bin 3.13
    log_success "Python 3.13 is available through repository-local uv"
}

run_brewfile_install() {
    log_info "Running Python-based Brewfile installation..."
    UV_PYTHON_INSTALL_DIR="$LOCAL_PYTHON_DIR" "$LOCAL_UV_BIN" run --python 3.13 python "$SCRIPT_DIR/brewfile_install.py" "${BREWFILE_ARGS[@]}"
}

parse_arguments() {
    local arg

    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                print_help
                exit 0
                ;;
            --reinstall-existing)
                BREWFILE_ARGS+=("$arg")
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
    parse_arguments "$@"

    print_banner

    log_info "Starting local Python initialization entrypoint..."

    print_phase "Phase 1: Repository-local uv"

    ensure_local_uv
    ensure_local_python

    print_phase "Phase 2: Homebrew Brewfile installation"
    run_brewfile_install

    echo ""
    log_success "════════════════════════════════════════════════════════════"
    log_success "Entrypoint initialization complete! 🎉"
    log_success "════════════════════════════════════════════════════════════"
    echo ""
}

main "$@"