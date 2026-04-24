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
    script_dir = Path(__file__).resolve().parent

    logger = setup_logging(args.log_file, verbose=args.verbose)
    initialize_audit_logger(
        logger,
        script_dir=script_dir,
        command_name="bootstrap-config",
        dry_run=args.dry_run,
    )
    print_banner()

    log_audit_event(
        logger,
        phase="config",
        action="run-started",
        status="ok",
        summary="Configuration bootstrap run started",
    )

    if not check_macos():
        log_error(logger, "This script is designed for macOS only!")
        log_audit_event(
            logger,
            phase="config",
            action="platform-check",
            status="failed",
            summary="Configuration bootstrap aborted because platform is not macOS",
        )
        return 1

    log_success(logger, "Running on macOS")
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = script_dir / config_path

    try:
        log_info(logger, f"Loading configuration from {config_path}")
        log_audit_event(
            logger,
            phase="config",
            action="config-load",
            status="started",
            target=str(config_path),
            summary="Loading configuration",
        )
        config = load_config(config_path)
        log_success(logger, "Configuration loaded successfully")
        log_audit_event(
            logger,
            phase="config",
            action="config-load",
            status="ok",
            target=str(config_path),
            summary="Configuration loaded successfully",
        )
    except FileNotFoundError as exc:
        log_error(logger, str(exc))
        log_audit_event(
            logger,
            phase="config",
            action="config-load",
            status="failed",
            target=str(config_path),
            summary="Configuration file or directory was not found",
            details=str(exc),
        )
        return 1
    except yaml.YAMLError as exc:
        log_error(logger, f"Invalid YAML configuration: {exc}")
        log_audit_event(
            logger,
            phase="config",
            action="config-load",
            status="failed",
            target=str(config_path),
            summary="Configuration YAML is invalid",
            details=str(exc),
        )
        return 1
    except Exception as exc:
        log_error(logger, f"Failed to load configuration: {exc}")
        log_audit_event(
            logger,
            phase="config",
            action="config-load",
            status="failed",
            target=str(config_path),
            summary="Configuration loading failed",
            details=str(exc),
        )
        return 1

    if args.dry_run:
        log_warning(logger, "DRY RUN MODE - No changes will be made")
        print()

    success = True

    if not args.skip_directories:
        log_audit_event(
            logger,
            phase="directories",
            action="phase-started",
            status="started",
            summary="Directories phase started",
        )
        if not bootstrap_directories.run_phase(
            config=config,
            script_dir=script_dir,
            dry_run=args.dry_run,
            logger=logger,
        ):
            success = False
            log_audit_event(
                logger,
                phase="directories",
                action="phase-completed",
                status="failed",
                summary="Directories phase completed with errors",
            )
        else:
            log_audit_event(
                logger,
                phase="directories",
                action="phase-completed",
                status="ok",
                summary="Directories phase completed successfully",
            )
    else:
        log_info(logger, "Skipping directory creation")
        log_audit_event(
            logger,
            phase="directories",
            action="phase-skipped",
            status="skipped",
            summary="Directories phase skipped by CLI option",
        )

    print()

    if not args.skip_dotfiles:
        log_audit_event(
            logger,
            phase="dotfiles",
            action="phase-started",
            status="started",
            summary="Dotfiles phase started",
        )
        if not bootstrap_dotfiles.run_phase(
            config=config,
            script_dir=script_dir,
            dry_run=args.dry_run,
            logger=logger,
        ):
            success = False
            log_audit_event(
                logger,
                phase="dotfiles",
                action="phase-completed",
                status="failed",
                summary="Dotfiles phase completed with errors",
            )
        else:
            log_audit_event(
                logger,
                phase="dotfiles",
                action="phase-completed",
                status="ok",
                summary="Dotfiles phase completed successfully",
            )
    else:
        log_info(logger, "Skipping dotfiles installation")
        log_audit_event(
            logger,
            phase="dotfiles",
            action="phase-skipped",
            status="skipped",
            summary="Dotfiles phase skipped by CLI option",
        )

    print()

    if not args.skip_macos_settings:
        log_audit_event(
            logger,
            phase="macos",
            action="phase-started",
            status="started",
            summary="macOS settings phase started",
        )
        if not bootstrap_macos.run_phase(
            config=config,
            dry_run=args.dry_run,
            logger=logger,
        ):
            success = False
            log_audit_event(
                logger,
                phase="macos",
                action="phase-completed",
                status="failed",
                summary="macOS settings phase completed with errors",
            )
        else:
            log_audit_event(
                logger,
                phase="macos",
                action="phase-completed",
                status="ok",
                summary="macOS settings phase completed successfully",
            )
    else:
        log_info(logger, "Skipping macOS settings configuration")
        log_audit_event(
            logger,
            phase="macos",
            action="phase-skipped",
            status="skipped",
            summary="macOS settings phase skipped by CLI option",
        )

    print()
    if success:
        log_success(logger, "═" * 60)
        log_success(logger, "Configuration complete! 🎉")
        log_success(logger, "═" * 60)
        audit_log = get_audit_log_path(logger)
        if audit_log is not None:
            log_info(logger, f"Audit log: {audit_log}")
        log_audit_event(
            logger,
            phase="config",
            action="run-completed",
            status="ok",
            summary="Configuration bootstrap run completed successfully",
            details=[f"audit_log: {audit_log}"] if audit_log is not None else None,
        )
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
    audit_log = get_audit_log_path(logger)
    if audit_log is not None:
        log_info(logger, f"Audit log: {audit_log}")
    log_audit_event(
        logger,
        phase="config",
        action="run-completed",
        status="failed",
        summary="Configuration bootstrap run completed with errors",
        details=[f"audit_log: {audit_log}"] if audit_log is not None else None,
    )
    print()
    log_info(logger, "Check the logs above for details")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())