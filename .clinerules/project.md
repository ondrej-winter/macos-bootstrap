# Project Context

## Purpose
- This repository automates setup of a fresh Apple Silicon macOS machine.
- The workflow is split into shell bootstrap, Homebrew installation, and Python-driven configuration phases.

## Primary Entry Points
- `entrypoint.sh` is the public shell entrypoint and bootstrap orchestrator.
- `brewfile_install.py` handles Homebrew Brewfile processing.
- `bootstrap.py` loads configuration and applies directory, dotfile, and macOS settings changes.

## Repository Structure
- `configuration/` contains split YAML configuration files.
- `configuration/macos_defaults/` contains multiple YAML files that are merged at runtime.
- `configuration_homebrew/` contains split Brewfiles by concern.
- `modules/` contains Python implementation modules.
- `dotfiles/` contains templates installed into the user environment.

## Project Assumptions
- Target platform is macOS only.
- Target hardware is Apple Silicon only.
- Prefer repository-local, explicit tooling behavior over hidden global assumptions.

## Editing Expectations
- Keep changes small, local, and consistent with the existing phased bootstrap design.
- Preserve the current separation of concerns between shell orchestration, Brewfile installation, and Python configuration.
- When behavior changes, update README usage and architecture notes if needed.