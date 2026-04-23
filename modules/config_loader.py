"""Shared configuration loading helpers for bootstrap entrypoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from a YAML file or configuration directory."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration path not found: {config_path}")

    if config_path.is_dir():
        return load_split_config(config_path)

    return load_legacy_config_file(config_path)


def load_legacy_config_file(config_path: Path) -> dict[str, Any]:
    """Load the legacy monolithic YAML configuration file."""
    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    if config is None:
        return {}
    if not isinstance(config, dict):
        raise ValueError("Configuration root must be a mapping/object")

    return config


def load_split_config(config_dir: Path) -> dict[str, Any]:
    """Load split configuration files from a directory."""
    section_files = {
        "directories": ("directories.yaml", list),
        "dotfiles": ("dotfiles.yaml", list),
        "special_commands": ("special_commands.yaml", list),
        "restart_applications": ("restart_applications.yaml", list),
    }

    config: dict[str, Any] = {}

    for section, (filename, expected_type) in section_files.items():
        value = _load_optional_yaml_file(config_dir / filename, expected_type)
        if value is None:
            value = expected_type()
        config[section] = value

    config["macos_defaults"] = load_split_macos_defaults(config_dir)
    return config


def load_split_macos_defaults(config_dir: Path) -> dict[str, Any]:
    """Load macOS defaults from a single YAML file or a directory of YAML files."""
    defaults_dir = config_dir / "macos_defaults"
    defaults_file = config_dir / "macos_defaults.yaml"

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


def get_config_list(config: dict[str, Any], key: str) -> list[Any]:
    """Return a configuration list value, validating the top-level shape."""
    value = config.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Configuration key '{key}' must be a list")
    return value


def get_config_mapping(config: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a configuration mapping value, validating the top-level shape."""
    value = config.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Configuration key '{key}' must be a mapping/object")
    return value


def _load_macos_defaults_directory(defaults_dir: Path) -> dict[str, Any]:
    """Load and merge macOS defaults categories from multiple YAML files."""
    merged: dict[str, Any] = {}

    for path in sorted(defaults_dir.glob("*.yaml")):
        with open(path, "r", encoding="utf-8") as handle:
            value = yaml.safe_load(handle)

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

    with open(path, "r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)

    if value is None:
        return expected_type()
    if not isinstance(value, expected_type):
        expected_name = "mapping/object" if expected_type is dict else "list"
        raise ValueError(
            f"Configuration file '{path.name}' must contain a top-level {expected_name}"
        )

    return value