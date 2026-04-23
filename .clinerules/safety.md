# Change Safety Rules

## Platform Constraints
- Assume this repository is for Apple Silicon macOS only unless the repository itself is intentionally expanded.
- Do not introduce cross-platform abstractions unless explicitly requested.

## Bootstrap Stability
- Avoid large architectural rewrites of the phased bootstrap flow.
- Preserve the contract between `entrypoint.sh`, `brewfile_install.py`, and `bootstrap.py`.
- Prefer incremental changes that keep the bootstrap recoverable and understandable.

## Operational Safety
- Be careful with filesystem writes, shell commands, package installation logic, and macOS defaults changes.
- Preserve dry-run behavior wherever supported.
- Avoid adding hidden side effects or surprising implicit actions.

## Documentation Sync
- If command-line behavior, config layout, or bootstrap phases change, update `README.md` accordingly.
- Keep examples aligned with actual supported flags and file structure.