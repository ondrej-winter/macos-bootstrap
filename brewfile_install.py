#!/usr/bin/env python3
"""macOS Brewfile installation phase implemented in Python."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from modules.homebrew import BrewfileInstaller, add_homebrew_arguments
from modules.utils import check_macos, log_error, log_info, log_success, log_warning, setup_logging


def print_banner() -> None:
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║           macOS Homebrew Brewfile Installation             ║")
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

    print_banner()

    if not check_macos():
        log_error(logger, "This script is designed for macOS only!")
        return 1

    log_info(logger, "Starting Brewfile installation phase...")
    print()

    if args.reinstall_existing:
        log_info(logger, "Repair mode enabled: already-installed formulae and casks will be reinstalled")
    else:
        log_info(logger, "Default mode enabled: already-installed formulae and casks will be skipped")

    print()

    if Path("/opt/homebrew/bin/brew").exists() or Path("/usr/local/bin/brew").exists():
        pass

    from shutil import which

    if which("brew") is None:
        log_error(logger, "Homebrew not found. This script only handles Brewfile installation.")
        log_info(logger, "Run bootstrap.sh or entrypoint.sh to install prerequisites and orchestrate the full bootstrap process.")
        return 1

    log_success(logger, "Homebrew is available")

    installer = BrewfileInstaller(
        logger=logger,
        script_dir=Path(__file__).resolve().parent,
        reinstall_existing=args.reinstall_existing,
    )
    status = installer.run()

    print()
    if status == 0:
        log_success(logger, "════════════════════════════════════════════════════════════")
        log_success(logger, "Brewfile phase complete! 🎉")
        log_success(logger, "════════════════════════════════════════════════════════════")
        print()
        return 0

    log_warning(logger, "════════════════════════════════════════════════════════════")
    log_warning(logger, "Brewfile phase completed with warnings")
    log_warning(logger, "════════════════════════════════════════════════════════════")
    if installer.log_file is not None:
        log_warning(logger, f"Some Brewfile entries failed during install/reinstall. Review: {installer.log_file}")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
