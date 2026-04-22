#!/usr/bin/env bash

################################################################################
# macOS bootstrap orchestrator
# Coordinates prerequisites, the Brewfile phase, and the Python entrypoint
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BREW_PHASE_SCRIPT="${SCRIPT_DIR}/brewfile_install.sh"
PYTHON_SETUP_SCRIPT="${SCRIPT_DIR}/bootstrap.py"
SKIP_BREWFILE=false
REINSTALL_EXISTING=false
SHOW_HELP=false
PYTHON_ARGS=()

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║               macOS Bootstrap Setup Script                 ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

print_help() {
    cat <<EOF_HELP
Usage: ./bootstrap.sh [options] [python-options]

macOS bootstrap orchestrator that prepares the system, optionally runs the
Homebrew Brewfile phase, and then launches the Python bootstrap script.

Wrapper options:
  --skip-brewfile         Skip the Brewfile installation phase
  --reinstall-existing    Reinstall already-installed Brewfile formulae and casks
  -h, --help              Show this help message and exit

Python bootstrap options are forwarded to bootstrap.py, for example:
  --config PATH           Path to configuration file or directory
  --skip-dotfiles         Skip dotfiles installation
  --skip-macos-settings   Skip macOS system settings
  --skip-directories      Skip directory creation
  --dry-run               Show what would be done without making changes
  --log-file PATH         Path to log file
  --verbose               Enable verbose logging

Examples:
  ./bootstrap.sh
  ./bootstrap.sh --skip-brewfile
  ./bootstrap.sh --dry-run --verbose
  ./bootstrap.sh --config my-config.yaml
  ./bootstrap.sh --config configuration
EOF_HELP
}

check_macos() {
    log_info "Checking operating system and architecture..."

    if [[ "$OSTYPE" != "darwin"* ]]; then
        log_error "This script is designed for macOS only!"
        exit 1
    fi

    if [[ $(uname -m) != 'arm64' ]]; then
        log_error "This script only supports Apple Silicon Macs (M1/M2/M3)!"
        log_error "Detected architecture: $(uname -m)"
        log_info "For Intel Macs, please modify the script or use a different setup."
        exit 1
    fi

    log_success "Running on macOS with Apple Silicon"
}

check_command_line_tools() {
    log_info "Checking for Xcode Command Line Tools..."

    if xcode-select -p &>/dev/null; then
        log_success "Command Line Tools already installed"
    else
        log_warning "Command Line Tools not found. Installing..."
        xcode-select --install
        log_info "Please complete the installation in the dialog and re-run this script"
        exit 0
    fi
}

install_homebrew() {
    log_info "Checking for Homebrew..."

    if command -v brew &>/dev/null; then
        log_success "Homebrew already installed"
        log_info "Updating Homebrew..."
        brew update
    else
        log_warning "Homebrew not found. Installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        if [[ $(uname -m) == 'arm64' ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi

        log_success "Homebrew installed successfully"
    fi
}

run_brewfile_phase() {
    log_info "Running Brewfile installation phase..."
    echo ""

    if [ ! -f "$BREW_PHASE_SCRIPT" ]; then
        log_error "Brewfile phase script not found: $BREW_PHASE_SCRIPT"
        return 1
    fi

    if [ "$REINSTALL_EXISTING" = true ]; then
        bash "$BREW_PHASE_SCRIPT" --reinstall-existing
    else
        bash "$BREW_PHASE_SCRIPT"
    fi
}

check_python() {
    log_info "Checking Python and UV installation..."

    if ! command -v python3 &>/dev/null; then
        log_warning "Python 3 not found. Installing via Homebrew..."
        brew install python@3.13
    fi

    log_success "Python 3 is available"

    if ! command -v uv &>/dev/null; then
        log_warning "uv not found. Installing via Homebrew..."
        brew install uv
    fi

    log_success "uv is available (dependencies will be auto-managed)"
}

run_python_setup() {
    log_info "Running Python bootstrap script..."
    echo ""

    if [ ! -f "$PYTHON_SETUP_SCRIPT" ]; then
        log_error "bootstrap.py not found: $PYTHON_SETUP_SCRIPT"
        return 1
    fi

    uv run "$PYTHON_SETUP_SCRIPT" "$@"
}

parse_arguments() {
    local arg=""

    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                SHOW_HELP=true
                ;;
            --skip-brewfile)
                SKIP_BREWFILE=true
                ;;
            --reinstall-existing)
                REINSTALL_EXISTING=true
                ;;
            *)
                PYTHON_ARGS+=("$arg")
                ;;
        esac
    done
}

main() {
    print_banner
    local brewfile_status=0
    local python_setup_status=0

    parse_arguments "$@"

    if [ "$SHOW_HELP" = true ]; then
        print_help
        return 0
    fi

    log_info "Starting macOS bootstrap process..."
    echo ""

    log_info "═══════════════════════════════════════════════════════════"
    log_info "Phase 1: System Prerequisites"
    log_info "═══════════════════════════════════════════════════════════"
    echo ""

    check_macos
    check_command_line_tools
    install_homebrew

    echo ""

    log_info "═══════════════════════════════════════════════════════════"
    log_info "Phase 2: Homebrew Brewfile Installation"
    log_info "═══════════════════════════════════════════════════════════"
    echo ""

    if [ "$SKIP_BREWFILE" = true ]; then
        log_warning "Skipping Brewfile installation phase (--skip-brewfile)"
        brewfile_status=0
    else
        if run_brewfile_phase; then
            brewfile_status=0
        else
            brewfile_status=$?
        fi
    fi

    echo ""

    log_info "═══════════════════════════════════════════════════════════"
    log_info "Phase 3: Python Bootstrap Script"
    log_info "═══════════════════════════════════════════════════════════"
    echo ""

    check_python

    echo ""

    if run_python_setup "${PYTHON_ARGS[@]}"; then
        python_setup_status=0
    else
        python_setup_status=$?
    fi

    echo ""

    if [ "$brewfile_status" -eq 0 ] && [ "$python_setup_status" -eq 0 ]; then
        log_success "════════════════════════════════════════════════════════════"
        log_success "Bootstrap complete! 🎉"
        log_success "════════════════════════════════════════════════════════════"
        echo ""
        return 0
    fi

    if [ "$python_setup_status" -eq 0 ]; then
        log_warning "════════════════════════════════════════════════════════════"
        log_warning "Bootstrap completed with Brewfile warnings"
        log_warning "════════════════════════════════════════════════════════════"
        echo ""
        return 1
    fi

    log_error "════════════════════════════════════════════════════════════"
    log_error "Bootstrap completed with errors"
    log_error "════════════════════════════════════════════════════════════"
    echo ""
    return 1
}

main "$@"
exit $?