#!/usr/bin/env python3
"""macOS Bootstrap configuration orchestrator implemented in Python."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

import bootstrap_directories
import bootstrap_dotfiles
import bootstrap_macos
from modules.config_loader import load_config
from modules.utils import check_macos, log_error, log_info, log_success, log_warning, setup_logging


def print_banner() -> None:
    """Print welcome banner."""
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║              macOS Bootstrap Config Phase                 ║")
    print("║                                                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()


def parse_arguments() -> argparse.Namespace:
    """Parse CLI arguments for the configuration phase."""
    parser = argparse.ArgumentParser(description="macOS Bootstrap Configuration Script")
    parser.add_argument(
        "--config",
        type=str,
        default="configuration",
        help="Path to configuration file or directory (default: configuration)",
    )
    parser.add_argument(
        "--skip-dotfiles",
        action="store_true",
        help="Skip dotfiles installation",
    )
    parser.add_argument(
        "--skip-macos-settings",
        action="store_true",
        help="Skip macOS system settings",
    )
    parser.add_argument(
        "--skip-directories",
        action="store_true",
        help="Skip directory creation",
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


def main() -> int:
    """Main execution function."""
    args = parse_arguments()

    logger = setup_logging(args.log_file, verbose=args.verbose)
    print_banner()

    if not check_macos():
        log_error(logger, "This script is designed for macOS only!")
        return 1

    log_success(logger, "Running on macOS")

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

    success = True

    if not args.skip_directories:
        if not bootstrap_directories.run_phase(
            config=config,
            script_dir=script_dir,
            dry_run=args.dry_run,
            logger=logger,
        ):
            success = False
    else:
        log_info(logger, "Skipping directory creation")

    print()

    if not args.skip_dotfiles:
        if not bootstrap_dotfiles.run_phase(
            config=config,
            script_dir=script_dir,
            dry_run=args.dry_run,
            logger=logger,
        ):
            success = False
    else:
        log_info(logger, "Skipping dotfiles installation")

    print()

    if not args.skip_macos_settings:
        if not bootstrap_macos.run_phase(
            config=config,
            dry_run=args.dry_run,
            logger=logger,
        ):
            success = False
    else:
        log_info(logger, "Skipping macOS settings configuration")

    print()
    if success:
        log_success(logger, "═" * 60)
        log_success(logger, "Configuration complete! 🎉")
        log_success(logger, "═" * 60)
        print()
        log_info(logger, "Next steps:")
        print("  1. Restart your terminal to apply shell changes")
        print("  2. Review dotfiles in your home directory")
        print("  3. Some macOS changes may require logout/restart")
        print()
        return 0

    log_warning(logger, "═" * 60)
    log_warning(logger, "Configuration completed with some errors")
    log_warning(logger, "═" * 60)
    print()
    log_info(logger, "Check the logs above for details")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())