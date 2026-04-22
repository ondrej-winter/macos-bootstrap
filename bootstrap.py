#!/usr/bin/env python3
"""
macOS Bootstrap Setup Script (Python)
Handles configuration after Homebrew installation.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from modules.utils import (
    setup_logging,
    check_macos,
    log_info,
    log_success,
    log_error,
    log_warning
)
from modules.directories import create_directories
from modules.dotfiles import DotfilesManager
from modules.macos_settings import MacOSSettingsManager


def print_banner() -> None:
    """Print welcome banner."""
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║           macOS Bootstrap Configuration (Python)           ║")
    print("║                                                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()


def load_config(config_path: Path) -> dict:
    """
    Load configuration from a YAML file or configuration directory.
    
    Args:
        config_path: Path to a legacy YAML config file or split config directory
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If config path doesn't exist
        yaml.YAMLError: If config file is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration path not found: {config_path}")

    if config_path.is_dir():
        return load_split_config(config_path)

    return load_legacy_config_file(config_path)


def load_legacy_config_file(config_path: Path) -> dict[str, Any]:
    """Load the legacy monolithic YAML configuration file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    if config is None:
        return {}
    if not isinstance(config, dict):
        raise ValueError("Configuration root must be a mapping/object")

    return config


def load_split_config(config_dir: Path) -> dict[str, Any]:
    """Load split configuration files from a directory."""
    section_files = {
        'directories': ('directories.yaml', list),
        'dotfiles': ('dotfiles.yaml', list),
        'special_commands': ('special_commands.yaml', list),
        'restart_applications': ('restart_applications.yaml', list),
    }

    config: dict[str, Any] = {}

    for section, (filename, expected_type) in section_files.items():
        value = _load_optional_yaml_file(config_dir / filename, expected_type)
        if value is None:
            value = expected_type()
        config[section] = value

    config['macos_defaults'] = load_split_macos_defaults(config_dir)

    return config


def load_split_macos_defaults(config_dir: Path) -> dict[str, Any]:
    """Load macOS defaults from a single YAML file or a directory of YAML files."""
    defaults_dir = config_dir / 'macos_defaults'
    defaults_file = config_dir / 'macos_defaults.yaml'

    if defaults_dir.exists() and defaults_file.exists():
        raise ValueError(
            "Split config cannot contain both 'macos_defaults/' and 'macos_defaults.yaml'"
        )

    if defaults_dir.exists():
        if not defaults_dir.is_dir():
            raise ValueError("Configuration path 'macos_defaults' must be a directory")
        return _load_macos_defaults_directory(defaults_dir)

    value = _load_optional_yaml_file(defaults_file, dict)
    if value is None:
        return {}
    return value


def _load_macos_defaults_directory(defaults_dir: Path) -> dict[str, Any]:
    """Load and merge macOS defaults categories from multiple YAML files."""
    merged: dict[str, Any] = {}

    for path in sorted(defaults_dir.glob('*.yaml')):
        with open(path, 'r', encoding='utf-8') as f:
            value = yaml.safe_load(f)

        if value is None:
            continue
        if not isinstance(value, dict):
            raise ValueError(
                f"Configuration file '{path.relative_to(defaults_dir.parent)}' must contain "
                "a top-level mapping/object"
            )

        for category, settings in value.items():
            if category in merged:
                raise ValueError(
                    f"Duplicate macOS defaults category '{category}' found in '{path.name}'"
                )
            if not isinstance(settings, list):
                raise ValueError(
                    f"macOS defaults category '{category}' in '{path.name}' must be a list"
                )
            merged[category] = settings

    return merged


def _load_optional_yaml_file(path: Path, expected_type: type) -> Any:
    """Load an optional YAML file and validate its top-level type."""
    if not path.exists():
        return None

    with open(path, 'r', encoding='utf-8') as f:
        value = yaml.safe_load(f)

    if value is None:
        return expected_type()
    if not isinstance(value, expected_type):
        expected_name = 'mapping/object' if expected_type is dict else 'list'
        raise ValueError(
            f"Configuration file '{path.name}' must contain a top-level {expected_name}"
        )

    return value


def main() -> int:
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='macOS Bootstrap Configuration Script'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='configuration',
        help='Path to configuration file or directory (default: configuration)'
    )
    parser.add_argument(
        '--skip-dotfiles',
        action='store_true',
        help='Skip dotfiles installation'
    )
    parser.add_argument(
        '--skip-macos-settings',
        action='store_true',
        help='Skip macOS system settings'
    )
    parser.add_argument(
        '--skip-directories',
        action='store_true',
        help='Skip directory creation'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        help='Path to log file'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_file, verbose=args.verbose)
    
    # Print banner
    print_banner()
    
    # Check if running on macOS
    if not check_macos():
        log_error(logger, "This script is designed for macOS only!")
        return 1
    
    log_success(logger, "Running on macOS")
    
    # Get script directory and config path
    script_dir = Path(__file__).resolve().parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = script_dir / config_path

    # Load configuration
    try:
        log_info(logger, f"Loading configuration from {config_path}")
        config = load_config(config_path)
        log_success(logger, "Configuration loaded successfully")
    except FileNotFoundError as e:
        log_error(logger, str(e))
        return 1
    except yaml.YAMLError as e:
        log_error(logger, f"Invalid YAML configuration: {e}")
        return 1
    except Exception as e:
        log_error(logger, f"Failed to load configuration: {e}")
        return 1

    if args.dry_run:
        log_warning(logger, "DRY RUN MODE - No changes will be made")
        print()

    success = True

    directories = _get_config_list(config, 'directories')
    dotfiles = _get_config_list(config, 'dotfiles')
    macos_defaults = _get_config_mapping(config, 'macos_defaults')
    special_commands = _get_config_list(config, 'special_commands')
    restart_apps = _get_config_list(config, 'restart_applications')

    # Create directories
    if not args.skip_directories:
        if directories:
            if not create_directories(directories, logger, dry_run=args.dry_run):
                success = False
        else:
            log_warning(logger, "No directories configured")
    else:
        log_info(logger, "Skipping directory creation")

    print()

    # Install dotfiles
    if not args.skip_dotfiles:
        if dotfiles:
            dotfiles_manager = DotfilesManager(logger, script_dir, dry_run=args.dry_run)
            if not dotfiles_manager.install_dotfiles(dotfiles):
                success = False
        else:
            log_warning(logger, "No dotfiles configured")
    else:
        log_info(logger, "Skipping dotfiles installation")

    print()

    # Apply macOS settings
    if not args.skip_macos_settings:
        if macos_defaults or special_commands or restart_apps:
            settings_manager = MacOSSettingsManager(logger, dry_run=args.dry_run)

            if macos_defaults and not settings_manager.apply_all_settings(macos_defaults):
                success = False

            if macos_defaults and special_commands:
                print()

            if special_commands and not settings_manager.run_special_commands(special_commands):
                success = False

            if restart_apps:
                print()
                settings_manager.restart_applications(restart_apps)
        else:
            log_warning(logger, "No macOS settings configured")
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


def _get_config_list(config: dict[str, Any], key: str) -> list[Any]:
    value = config.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Configuration key '{key}' must be a list")
    return value


def _get_config_mapping(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Configuration key '{key}' must be a mapping/object")
    return value


if __name__ == '__main__':
    sys.exit(main())
