# Configuration Rules

## YAML Configuration
- Keep split configuration files focused by concern.
- Maintain consistent YAML formatting and human-readable descriptions.
- Do not mix incompatible configuration shapes in a single file.

## macOS Defaults
- Add new defaults in the most appropriate file under `configuration/macos_defaults/`.
- Avoid duplicate category keys across split macOS defaults files.
- Use stable naming and grouping so merged runtime behavior remains easy to reason about.

## Homebrew Configuration
- Place packages in the most appropriate Brewfile under `configuration_homebrew/`.
- Keep related packages grouped logically.
- Avoid unnecessary churn in Brewfiles when only a small targeted change is needed.

## Dotfiles and Directories
- Keep dotfile mappings explicit and readable.
- Preserve user-safety behavior such as backups when changing dotfile installation logic.