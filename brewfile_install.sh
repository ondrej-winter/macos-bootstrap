#!/usr/bin/env bash

################################################################################
# macOS Brewfile installation phase
# Installs packages listed in the split Brewfiles under configuration_homebrew/
# Intended to be called by bootstrap.sh
################################################################################

set -e  # Exit on error

# Repository paths and Brewfile logging
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BREWFILE_DIR="${SCRIPT_DIR}/configuration_homebrew"
BREWFILE_PATHS=(
    "${BREWFILE_DIR}/Brewfile.core"
    "${BREWFILE_DIR}/Brewfile.dev"
    "${BREWFILE_DIR}/Brewfile.apps"
    "${BREWFILE_DIR}/Brewfile.mas"
    "${BREWFILE_DIR}/Brewfile.extra"
)
LOG_DIR="${SCRIPT_DIR}/logs"
BREWFILE_LOG_FILE=""
APP_DIR="${HOME}/Applications"
REINSTALL_EXISTING=false

BREW_INSTALLED_ITEMS=()
BREW_REINSTALLED_ITEMS=()
BREW_SKIPPED_ITEMS=()
BREW_FAILED_ITEMS=()
BREW_UNPARSED_ITEMS=()

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
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

log_brew_item_status() {
    local status="$1"
    local message="$2"
    local color="$NC"

    case "$status" in
        OK)
            color="$GREEN"
            ;;
        SKIP)
            color="$BLUE"
            ;;
        FAIL)
            color="$RED"
            ;;
        WARN)
            color="$YELLOW"
            ;;
    esac

    printf "%b[%-4s]%b %s\n" "$color" "$status" "$NC" "$message"
}

append_brew_log_status() {
    local status="$1"
    local message="$2"

    if [ -n "$BREWFILE_LOG_FILE" ]; then
        printf '[%s] [%-4s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$status" "$message" >> "$BREWFILE_LOG_FILE"
    fi
}

record_brew_outcome() {
    local status="$1"
    local message="$2"
    local bucket="$3"

    log_brew_item_status "$status" "$message"
    append_brew_log_status "$status" "$message"

    case "$bucket" in
        installed)
            BREW_INSTALLED_ITEMS+=("${message}")
            ;;
        reinstalled)
            BREW_REINSTALLED_ITEMS+=("${message}")
            ;;
        skipped)
            BREW_SKIPPED_ITEMS+=("${message}")
            ;;
        failed)
            BREW_FAILED_ITEMS+=("${message}")
            ;;
        unparsed)
            BREW_UNPARSED_ITEMS+=("${message}")
            ;;
    esac
}

prepare_brewfile_log() {
    mkdir -p "$LOG_DIR"
    BREWFILE_LOG_FILE="${LOG_DIR}/brew-install-$(date +%Y%m%d-%H%M%S).log"

    {
        echo "macOS Bootstrap Brewfile Log"
        echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Processed Brewfiles:"
        local brewfile_path=""
        for brewfile_path in "${BREWFILE_PATHS[@]}"; do
            echo "  - ${brewfile_path}"
        done
        echo ""
    } > "$BREWFILE_LOG_FILE"

    log_info "Detailed Brewfile output will be written to: $BREWFILE_LOG_FILE"
}

run_logged_command() {
    local description="$1"
    shift
    local temp_output=""

    {
        echo ""
        echo "=== $(date '+%Y-%m-%d %H:%M:%S') | ${description} ==="
        printf 'Command:'
        printf ' %q' "$@"
        echo ""
    } >> "$BREWFILE_LOG_FILE"

    temp_output="$(mktemp)"

    local exit_code=0
    if "$@" </dev/null > "$temp_output" 2>&1; then
        exit_code=0
    else
        exit_code=$?
    fi

    if [ -s "$temp_output" ]; then
        {
            echo "--- command output ---"
            cat "$temp_output"
            echo "--- end command output ---"
        } >> "$BREWFILE_LOG_FILE"
    fi

    rm -f "$temp_output"

    {
        echo "Exit code: ${exit_code}"
        echo "=== end ==="
    } >> "$BREWFILE_LOG_FILE"

    return "$exit_code"
}

print_brew_summary_section() {
    local title="$1"
    shift

    if [ "$#" -eq 0 ]; then
        return 0
    fi

    echo ""
    log_info "${title} ($#)"

    local item=""
    for item in "$@"; do
        echo "  - ${item}"
    done
}

is_formula_installed() {
    brew list --formula "$1" >/dev/null 2>&1
}

is_cask_installed() {
    brew list --cask "$1" >/dev/null 2>&1
}

is_tap_installed() {
    brew tap | grep -Fxq "$1"
}

is_mas_app_installed() {
    local app_id="$1"

    if ! command -v mas &>/dev/null; then
        return 1
    fi

    mas list 2>/dev/null | awk '{print $1}' | grep -qx "$app_id"
}

install_formula_from_brewfile() {
    local formula_name="$1"
    local item_label="brew ${formula_name}"

    if is_formula_installed "$formula_name"; then
        if [ "$REINSTALL_EXISTING" = true ]; then
            if run_logged_command "reinstall ${item_label}" brew reinstall "$formula_name"; then
                record_brew_outcome "OK" "${item_label} (reinstalled)" "reinstalled"
            else
                record_brew_outcome "FAIL" "${item_label} (reinstall failed)" "failed"
            fi
        else
            record_brew_outcome "SKIP" "${item_label} (already installed)" "skipped"
        fi
        return 0
    fi

    if run_logged_command "install ${item_label}" brew install "$formula_name"; then
        record_brew_outcome "OK" "${item_label} (installed)" "installed"
    else
        record_brew_outcome "FAIL" "${item_label} (install failed)" "failed"
    fi

    return 0
}

install_cask_from_brewfile() {
    local cask_name="$1"
    local item_label="cask ${cask_name}"

    mkdir -p "$APP_DIR"

    if is_cask_installed "$cask_name"; then
        if [ "$REINSTALL_EXISTING" = true ]; then
            if run_logged_command "reinstall ${item_label}" brew reinstall --cask --appdir "$APP_DIR" "$cask_name"; then
                record_brew_outcome "OK" "${item_label} (reinstalled)" "reinstalled"
            else
                record_brew_outcome "FAIL" "${item_label} (reinstall failed)" "failed"
            fi
        else
            record_brew_outcome "SKIP" "${item_label} (already installed)" "skipped"
        fi
        return 0
    fi

    if run_logged_command "install ${item_label}" brew install --cask --appdir "$APP_DIR" "$cask_name"; then
        record_brew_outcome "OK" "${item_label} (installed)" "installed"
    else
        record_brew_outcome "FAIL" "${item_label} (install failed)" "failed"
    fi

    return 0
}

install_tap_from_brewfile() {
    local tap_name="$1"
    local item_label="tap ${tap_name}"

    if is_tap_installed "$tap_name"; then
        record_brew_outcome "SKIP" "${item_label} (already tapped)" "skipped"
        return 0
    fi

    if run_logged_command "$item_label" brew tap "$tap_name"; then
        record_brew_outcome "OK" "$item_label" "installed"
    else
        record_brew_outcome "FAIL" "$item_label" "failed"
    fi

    return 0
}

install_mas_app_from_brewfile() {
    local app_name="$1"
    local app_id="$2"
    local item_label="mas ${app_name} (${app_id})"

    if ! command -v mas &>/dev/null; then
        record_brew_outcome "FAIL" "${item_label} (mas CLI not available)" "failed"
        return 0
    fi

    if is_mas_app_installed "$app_id"; then
        record_brew_outcome "SKIP" "${item_label} (already installed)" "skipped"
        return 0
    fi

    if run_logged_command "$item_label" mas install "$app_id"; then
        record_brew_outcome "OK" "$item_label" "installed"
    else
        record_brew_outcome "FAIL" "$item_label" "failed"
    fi

    return 0
}

print_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║             macOS Homebrew Brewfile Installation           ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

print_help() {
    cat <<EOF_HELP
Usage: ./brewfile_install.sh [options]

Options:
  --reinstall-existing    Reinstall already-installed formulae and casks
  -h, --help              Show this help message and exit

Default behavior installs only missing Brewfile items and skips formulae/casks
that are already installed.
EOF_HELP
}

parse_arguments() {
    local arg=""

    for arg in "$@"; do
        case "$arg" in
            --reinstall-existing)
                REINSTALL_EXISTING=true
                ;;
            -h|--help)
                print_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $arg"
                print_help
                exit 1
                ;;
        esac
    done
}

check_homebrew() {
    log_info "Checking for Homebrew..."

    if ! command -v brew &>/dev/null; then
        log_error "Homebrew not found. This script only handles Brewfile installation."
        log_info "Run bootstrap.sh to install prerequisites and orchestrate the full bootstrap process."
        return 1
    fi

    log_success "Homebrew is available"
}

# Install packages from the split Brewfiles.
install_brewfile() {
    log_info "Processing Brewfile entries (continuing past individual failures)..."

    if [ ! -d "$BREWFILE_DIR" ]; then
        log_warning "Brewfile directory not found at $BREWFILE_DIR; skipping"
        return 0
    fi

    BREW_INSTALLED_ITEMS=()
    BREW_REINSTALLED_ITEMS=()
    BREW_SKIPPED_ITEMS=()
    BREW_FAILED_ITEMS=()
    BREW_UNPARSED_ITEMS=()

    prepare_brewfile_log

    local line=""
    local line_number=0
    local total_entries=0
    local unparsed_message=""
    local brewfile_path=""
    local processed_files=0

    for brewfile_path in "${BREWFILE_PATHS[@]}"; do
        if [ ! -f "$brewfile_path" ]; then
            log_warning "Brewfile not found at $brewfile_path; skipping"
            append_brew_log_status "WARN" "Missing Brewfile: ${brewfile_path}"
            continue
        fi

        processed_files=$((processed_files + 1))
        line_number=0
        log_info "Processing $(basename "$brewfile_path")"
        append_brew_log_status "INFO" "Processing Brewfile: ${brewfile_path}"

        while IFS= read -r line || [ -n "$line" ]; do
            line_number=$((line_number + 1))

            if [[ "$line" =~ ^[[:space:]]*$ ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
                continue
            fi

            total_entries=$((total_entries + 1))

            if [[ "$line" =~ ^[[:space:]]*brew[[:space:]]+\"([^\"]+)\" ]]; then
                install_formula_from_brewfile "${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^[[:space:]]*cask[[:space:]]+\"([^\"]+)\" ]]; then
                install_cask_from_brewfile "${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^[[:space:]]*tap[[:space:]]+\"([^\"]+)\" ]]; then
                install_tap_from_brewfile "${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^[[:space:]]*mas[[:space:]]+\"([^\"]+)\"[[:space:]]*,[[:space:]]*id:[[:space:]]*([0-9]+) ]]; then
                install_mas_app_from_brewfile "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
            else
                unparsed_message="$(basename "$brewfile_path"): line ${line_number}: ${line}"
                record_brew_outcome "WARN" "Unparsed Brewfile entry (${unparsed_message})" "unparsed"
            fi
        done < "$brewfile_path"
    done

    if [ "$processed_files" -eq 0 ]; then
        log_warning "No Brewfiles were found to process; skipping"
        append_brew_log_status "WARN" "No Brewfiles were found to process"
        return 0
    fi

    {
        echo ""
        echo "=== Summary ==="
        echo "Processed Brewfiles: ${processed_files}"
        echo "Processed entries: ${total_entries}"
        echo "Installed: ${#BREW_INSTALLED_ITEMS[@]}"
        for line in "${BREW_INSTALLED_ITEMS[@]}"; do
            echo "  - ${line}"
        done
        echo "Reinstalled: ${#BREW_REINSTALLED_ITEMS[@]}"
        for line in "${BREW_REINSTALLED_ITEMS[@]}"; do
            echo "  - ${line}"
        done
        echo "Skipped: ${#BREW_SKIPPED_ITEMS[@]}"
        for line in "${BREW_SKIPPED_ITEMS[@]}"; do
            echo "  - ${line}"
        done
        echo "Failed: ${#BREW_FAILED_ITEMS[@]}"
        for line in "${BREW_FAILED_ITEMS[@]}"; do
            echo "  - ${line}"
        done
        echo "Unparsed: ${#BREW_UNPARSED_ITEMS[@]}"
        for line in "${BREW_UNPARSED_ITEMS[@]}"; do
            echo "  - ${line}"
        done
    } >> "$BREWFILE_LOG_FILE"

    echo ""
    log_info "Brewfile installation summary"
    log_info "Processed ${processed_files} Brewfile files and ${total_entries} Brewfile entries"
    log_info "Detailed log: $BREWFILE_LOG_FILE"

    print_brew_summary_section "Installed" "${BREW_INSTALLED_ITEMS[@]}"
    print_brew_summary_section "Reinstalled" "${BREW_REINSTALLED_ITEMS[@]}"
    print_brew_summary_section "Skipped" "${BREW_SKIPPED_ITEMS[@]}"

    if [ "${#BREW_FAILED_ITEMS[@]}" -gt 0 ]; then
        echo ""
        log_warning "Failed entries (${#BREW_FAILED_ITEMS[@]})"
        for line in "${BREW_FAILED_ITEMS[@]}"; do
            echo "  - ${line}"
        done
    fi

    if [ "${#BREW_UNPARSED_ITEMS[@]}" -gt 0 ]; then
        echo ""
        log_warning "Unparsed Brewfile entries (${#BREW_UNPARSED_ITEMS[@]})"
        for line in "${BREW_UNPARSED_ITEMS[@]}"; do
            echo "  - ${line}"
        done
    fi

    if [ "${#BREW_FAILED_ITEMS[@]}" -gt 0 ] || [ "${#BREW_UNPARSED_ITEMS[@]}" -gt 0 ]; then
        log_warning "Brewfile processing completed with some issues. Review the summary above and the detailed log."
        return 1
    fi

    log_success "All Brewfile entries were processed successfully"
    return 0
}

# Main execution
main() {
    print_banner
    local brewfile_status=0

    parse_arguments "$@"

    log_info "Starting Brewfile installation phase..."
    echo ""

    if [ "$REINSTALL_EXISTING" = true ]; then
        log_info "Repair mode enabled: already-installed formulae and casks will be reinstalled"
    else
        log_info "Default mode enabled: already-installed formulae and casks will be skipped"
    fi

    echo ""

    check_homebrew || return $?

    if install_brewfile; then
        brewfile_status=0
    else
        brewfile_status=$?
    fi

    echo ""

    if [ "$brewfile_status" -eq 0 ]; then
        log_success "════════════════════════════════════════════════════════════"
        log_success "Brewfile phase complete! 🎉"
        log_success "════════════════════════════════════════════════════════════"
        echo ""
        return 0
    fi

    log_warning "════════════════════════════════════════════════════════════"
    log_warning "Brewfile phase completed with warnings"
    log_warning "════════════════════════════════════════════════════════════"
    if [ -n "$BREWFILE_LOG_FILE" ]; then
        log_warning "Some Brewfile entries failed during install/reinstall. Review: $BREWFILE_LOG_FILE"
    fi
    echo ""
    return 1
}

# Run main function with all script arguments
main "$@"
exit $?
