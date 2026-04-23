#!/usr/bin/env python3
"""macOS directory bootstrap phase."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from modules.config_loader import get_config_list, load_config
from modules.directories import create_directories
from modules.utils import check_macos, log_error, log_info, log_success, log_warning, setup_logging


def print_banner() -> None:
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║            macOS Bootstrap Directories Phase              ║")
    print("║                                                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create configured directories for macOS bootstrap")
    parser.add_argument(
        "--config",
        type=str,
        default="configuration",
        help="Path to configuration file or directory (default: configuration)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def run_phase(*, config: dict, script_dir: Path, dry_run: bool, logger) -> bool:
    directories = get_config_list(config, "directories")
    if not directories:
        log_warning(logger, "No directories configured")
        return True
    return create_directories(directories, logger, dry_run=dry_run)


def main() -> int:
    args = parse_arguments()
    logger = setup_logging(args.log_file, verbose=args.verbose)

    print_banner()

    if not check_macos():
        log_error(logger, "This script is designed for macOS only!")
        return 1

    script_dir = Path(__file__).resolve().parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = script_dir / config_path

    try:
        log_info(logger, f"Loading configuration from {config_path}")
        config = load_config(config_path)
        log_success(logger, "Configuration loaded successfully")
    except FileNotFoundError as exc:
        log_error(logger, str(exc))
        return 1
    except yaml.YAMLError as exc:
        log_error(logger, f"Invalid YAML configuration: {exc}")
        return 1
    except Exception as exc:
        log_error(logger, f"Failed to load configuration: {exc}")
        return 1

    if args.dry_run:
        log_warning(logger, "DRY RUN MODE - No changes will be made")
        print()

    success = run_phase(config=config, script_dir=script_dir, dry_run=args.dry_run, logger=logger)

    print()
    if success:
        log_success(logger, "Directories phase complete! 🎉")
        print()
        return 0

    log_warning(logger, "Directories phase completed with some errors")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())