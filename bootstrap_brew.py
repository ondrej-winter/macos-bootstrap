#!/usr/bin/env python3
"""macOS Homebrew Brewfile installation phase implemented in Python."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from modules.homebrew import BrewfileInstaller, add_homebrew_arguments
from modules.utils import (
    check_macos,
    get_audit_log_path,
    initialize_audit_logger,
    log_audit_event,
    log_error,
    log_info,
    log_success,
    log_warning,
    setup_logging,
)


def print_banner() -> None:
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║               macOS Bootstrap Brew Phase                  ║")
    print("║                                                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install packages listed in the split Brewfiles under configuration_homebrew/",
    )
    add_homebrew_arguments(parser)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    logger = setup_logging(verbose=args.verbose)
    script_dir = Path(__file__).resolve().parent
    initialize_audit_logger(
        logger,
        script_dir=script_dir,
        command_name="bootstrap-brew",
        dry_run=False,
    )

    print_banner()
    log_audit_event(
        logger,
        phase="brew",
        action="run-started",
        status="ok",
        summary="Brew bootstrap run started",
    )

    if not check_macos():
        log_error(logger, "This script is designed for macOS only!")
        log_audit_event(
            logger,
            phase="brew",
            action="platform-check",
            status="failed",
            summary="Brew bootstrap aborted because platform is not macOS",
        )
        return 1

    log_info(logger, "Starting Brewfile installation phase...")
    print()

    if args.reinstall_existing:
        log_info(logger, "Repair mode enabled: already-installed formulae and casks will be reinstalled")
    else:
        log_info(logger, "Default mode enabled: already-installed formulae and casks will be skipped")

    print()

    from shutil import which

    if which("brew") is None:
        log_error(logger, "Homebrew not found. This script only handles Brewfile installation.")
        log_info(logger, "Run entrypoint.sh to install prerequisites and orchestrate the full bootstrap process.")
        log_audit_event(
            logger,
            phase="brew",
            action="dependency-check",
            status="failed",
            target="brew",
            summary="Homebrew is not available",
        )
        return 1

    log_success(logger, "Homebrew is available")

    installer = BrewfileInstaller(
        logger=logger,
        script_dir=script_dir,
        reinstall_existing=args.reinstall_existing,
    )
    status = installer.run()

    print()
    if status == 0:
        log_success(logger, "════════════════════════════════════════════════════════════")
        log_success(logger, "Brew phase complete! 🎉")
        log_success(logger, "════════════════════════════════════════════════════════════")
        audit_log = get_audit_log_path(logger)
        if audit_log is not None:
            log_info(logger, f"Audit log: {audit_log}")
        log_audit_event(
            logger,
            phase="brew",
            action="run-completed",
            status="ok",
            summary="Brew bootstrap run completed successfully",
            details=[f"audit_log: {audit_log}"] if audit_log is not None else None,
        )
        print()
        return 0

    log_warning(logger, "════════════════════════════════════════════════════════════")
    log_warning(logger, "Brew phase completed with warnings")
    log_warning(logger, "════════════════════════════════════════════════════════════")
    if installer.log_file is not None:
        log_warning(logger, f"Some Brewfile entries failed during install/reinstall. Review: {installer.log_file}")
    audit_log = get_audit_log_path(logger)
    if audit_log is not None:
        log_info(logger, f"Audit log: {audit_log}")
    log_audit_event(
        logger,
        phase="brew",
        action="run-completed",
        status="failed",
        summary="Brew bootstrap run completed with warnings or failures",
        details=[
            f"audit_log: {audit_log}",
            f"brew_log: {installer.log_file}",
        ] if audit_log is not None else [f"brew_log: {installer.log_file}"],
    )
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())