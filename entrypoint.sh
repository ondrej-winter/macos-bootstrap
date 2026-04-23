#!/usr/bin/env bash

################################################################################
# macOS bootstrap entrypoint
# Prepares repository-local uv/Python, runs the Brew phase, and launches
# the Python configuration phase.
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
BOOTSTRAP_ARGS=()
SKIP_BREWFILE=0

print_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║                macOS Bootstrap Entrypoint                 ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

print_help() {
    cat <<EOF_HELP
Usage: ./entrypoint.sh [options]

Initializes repository-local uv and the required local Python under
.bootstrap-tools, then runs the Brew phase followed by the Python
configuration phase.

Wrapper options:
  --skip-brewfile         Skip the Brew phase
  --reinstall-existing    Reinstall already-installed formulae and casks
  --config PATH           Path to configuration file or directory
  --skip-dotfiles         Skip dotfiles installation
  --skip-macos-settings   Skip macOS system settings
  --skip-directories      Skip directory creation
  --dry-run               Show what would be done without making changes
  --log-file PATH         Write bootstrap_config.py logs to PATH
  --verbose               Enable verbose logging
  -h, --help              Show this help message and exit

Examples:
  ./entrypoint.sh
  ./entrypoint.sh --reinstall-existing --verbose
  ./entrypoint.sh --skip-brewfile --dry-run
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
    log_info "Running Python-based Brew phase..."
    UV_PYTHON_INSTALL_DIR="$LOCAL_PYTHON_DIR" "$LOCAL_UV_BIN" run --python 3.13 python "$SCRIPT_DIR/bootstrap_brew.py" "${BREWFILE_ARGS[@]}"
}

run_bootstrap_configuration() {
    log_info "Running Python-based configuration phase..."
    UV_PYTHON_INSTALL_DIR="$LOCAL_PYTHON_DIR" "$LOCAL_UV_BIN" run --python 3.13 python "$SCRIPT_DIR/bootstrap_config.py" "${BOOTSTRAP_ARGS[@]}"
}

parse_arguments() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            -h|--help)
                print_help
                exit 0
                ;;
            --skip-brewfile)
                SKIP_BREWFILE=1
                ;;
            --reinstall-existing)
                BREWFILE_ARGS+=("$1")
                ;;
            --config|--log-file)
                if [ "$#" -lt 2 ]; then
                    log_error "Missing value for argument: $1"
                    echo ""
                    print_help
                    exit 1
                fi
                BOOTSTRAP_ARGS+=("$1" "$2")
                shift
                ;;
            --skip-dotfiles|--skip-macos-settings|--skip-directories|--dry-run)
                BOOTSTRAP_ARGS+=("$1")
                ;;
            --verbose)
                BREWFILE_ARGS+=("$1")
                BOOTSTRAP_ARGS+=("$1")
                ;;
            *)
                log_error "Unsupported argument: $1"
                echo ""
                print_help
                exit 1
                ;;
        esac
        shift
    done
}

main() {
    parse_arguments "$@"

    print_banner

    log_info "Starting macOS bootstrap entrypoint..."

    print_phase "Phase 1: Repository-local uv"

    ensure_local_uv
    ensure_local_python

    if [ "$SKIP_BREWFILE" -eq 1 ]; then
        print_phase "Phase 2: Homebrew Brew installation"
        log_warning "Skipping Brew phase"
    else
        print_phase "Phase 2: Homebrew Brew installation"
        run_brewfile_install
    fi

    print_phase "Phase 3: Python configuration"
    run_bootstrap_configuration

    echo ""
    log_success "════════════════════════════════════════════════════════════"
    log_success "Bootstrap entrypoint complete! 🎉"
    log_success "════════════════════════════════════════════════════════════"
    echo ""
}

main "$@"