#!/usr/bin/env bash

# Shared shell logging helpers for bootstrap scripts.

readonly LOG_COLOR_RED='\033[0;31m'
readonly LOG_COLOR_GREEN='\033[0;32m'
readonly LOG_COLOR_YELLOW='\033[1;33m'
readonly LOG_COLOR_BLUE='\033[0;34m'
readonly LOG_COLOR_RESET='\033[0m'

log_info() {
    echo -e "${LOG_COLOR_BLUE}[INFO]${LOG_COLOR_RESET} $1"
}

log_success() {
    echo -e "${LOG_COLOR_GREEN}[SUCCESS]${LOG_COLOR_RESET} $1"
}

log_warning() {
    echo -e "${LOG_COLOR_YELLOW}[WARNING]${LOG_COLOR_RESET} $1"
}

log_error() {
    echo -e "${LOG_COLOR_RED}[ERROR]${LOG_COLOR_RESET} $1"
}