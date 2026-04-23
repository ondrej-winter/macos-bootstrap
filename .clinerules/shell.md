# Shell Rules

## Scope
- Applies to `entrypoint.sh` and shell helpers such as `lib/logging.sh`.

## Style
- Preserve Bash compatibility and existing script style.
- Keep `set -euo pipefail` safety guarantees unless there is a strong reason not to.
- Quote variables consistently and prefer explicit absolute or repository-derived paths.

## Command Execution
- Prefer non-interactive and automation-safe command patterns.
- Keep bootstrap commands idempotent where possible.
- Be careful with network downloads, install steps, and environment variable usage.

## Argument Handling
- Keep CLI parsing predictable and minimal.
- If adding flags, ensure help text and downstream forwarding behavior stay accurate.

## Logging
- Reuse existing logging functions and phase banners.
- Keep operator-visible messages concise and useful during long bootstrap runs.