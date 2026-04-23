# Python Rules

## Scope
- Applies to `bootstrap.py` and files in `modules/`.

## Style
- Follow existing Python style already present in the repository.
- Preserve type hints and add them for new public helpers when practical.
- Prefer small helper functions over deeply nested logic.

## Configuration Handling
- Treat YAML input as untrusted and validate top-level shapes.
- Preserve backward compatibility where the code already supports both split and legacy config formats.
- Keep path handling explicit with `pathlib.Path`.

## Logging and UX
- Use the existing logging helpers from `modules.utils` instead of ad hoc printing for operational messages.
- Keep CLI output clear and operator-friendly.
- Preserve `--dry-run`, `--verbose`, and related CLI behavior when modifying execution paths.

## Safety
- Avoid destructive filesystem changes unless they are already part of the documented bootstrap behavior.
- Do not silently remove compatibility checks for macOS constraints.
- Prefer explicit exceptions and actionable error messages over implicit failures.