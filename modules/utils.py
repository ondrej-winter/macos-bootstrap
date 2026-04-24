"""Utility functions for bootstrap setup."""

import logging
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Sequence


class LogStyles:
    """Shared terminal styling and level labels for console logging."""

    RESET = '\033[0m'
    LEVEL_PREFIX = {
        logging.INFO: ('\033[0;34m', '[INFO]'),
        logging.WARNING: ('\033[1;33m', '[WARNING]'),
        logging.ERROR: ('\033[0;31m', '[ERROR]'),
    }
    SUCCESS_PREFIX = ('\033[0;32m', '[SUCCESS]')


class ConsoleLogFormatter(logging.Formatter):
    """Formatter that prepends consistent colored level labels for console output."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()

        if getattr(record, 'success', False):
            color, prefix = LogStyles.SUCCESS_PREFIX
        else:
            color, prefix = LogStyles.LEVEL_PREFIX.get(
                record.levelno,
                ('', f'[{record.levelname}]'),
            )

        if color:
            return f"{color}{prefix}{LogStyles.RESET} {message}"
        return f"{prefix} {message}"


class AuditLogger:
    """Human-readable audit logger for business-level bootstrap events."""

    def __init__(self, log_file: Path, run_id: str, command_name: str, dry_run: bool = False) -> None:
        self.log_file = log_file
        self.run_id = run_id
        self.command_name = command_name
        self.dry_run = dry_run
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        with self.log_file.open('w', encoding='utf-8') as handle:
            handle.write("macOS Bootstrap Audit Log\n")
            handle.write(f"Run ID: {self.run_id}\n")
            handle.write(f"Command: {self.command_name}\n")
            handle.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            handle.write(f"Dry Run: {'yes' if self.dry_run else 'no'}\n")
            handle.write("\n")

    def log_event(
        self,
        *,
        phase: str,
        action: str,
        status: str,
        target: str | None = None,
        summary: str | None = None,
        command: str | Sequence[str] | None = None,
        details: str | Sequence[str] | None = None,
    ) -> None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        detail_lines: list[str] = []
        rendered_command = render_command(command) if command is not None else None

        if isinstance(details, str):
            detail_lines = details.splitlines() or [details]
        elif details is not None:
            for item in details:
                detail_lines.extend(str(item).splitlines() or [str(item)])

        with self.log_file.open('a', encoding='utf-8') as handle:
            handle.write("=== EVENT START ===\n")
            handle.write(f"Time: {timestamp}\n")
            handle.write(f"Run ID: {self.run_id}\n")
            handle.write(f"Command: {self.command_name}\n")
            handle.write(f"Phase: {phase}\n")
            handle.write(f"Action: {action}\n")
            if target:
                handle.write(f"Target: {target}\n")
            handle.write(f"Status: {status}\n")
            handle.write(f"Dry Run: {'yes' if self.dry_run else 'no'}\n")
            if summary:
                handle.write(f"Summary: {summary}\n")
            if rendered_command:
                handle.write("Command:\n")
                handle.write(f"  {rendered_command}\n")
            if detail_lines:
                handle.write("Details:\n")
                for line in detail_lines:
                    handle.write(f"  {line}\n")
            handle.write("=== EVENT END ===\n\n")


def initialize_audit_logger(
    logger: logging.Logger,
    *,
    script_dir: Path,
    command_name: str,
    dry_run: bool = False,
) -> AuditLogger:
    """Create and attach a human-readable audit logger to the bootstrap logger."""
    run_id = datetime.now().strftime('%Y%m%d-%H%M%S')
    audit_file = script_dir / 'logs' / f'audit-{command_name}-{run_id}.log'
    audit_logger = AuditLogger(audit_file, run_id=run_id, command_name=command_name, dry_run=dry_run)
    setattr(logger, 'audit_logger', audit_logger)
    return audit_logger


def log_audit_event(
    logger: logging.Logger,
    *,
    phase: str,
    action: str,
    status: str,
    target: str | None = None,
    summary: str | None = None,
    command: str | Sequence[str] | None = None,
    details: str | Sequence[str] | None = None,
) -> None:
    """Write a business-level audit event when audit logging is enabled."""
    audit_logger = getattr(logger, 'audit_logger', None)
    if audit_logger is None:
        return
    audit_logger.log_event(
        phase=phase,
        action=action,
        status=status,
        target=target,
        summary=summary,
        command=command,
        details=details,
    )


def get_audit_log_path(logger: logging.Logger) -> Path | None:
    """Return the attached audit log path if available."""
    audit_logger = getattr(logger, 'audit_logger', None)
    if audit_logger is None:
        return None
    return audit_logger.log_file


def setup_logging(log_file: Optional[str] = None, verbose: bool = False) -> logging.Logger:
    """
    Setup logging configuration.
    
    Args:
        log_file: Optional path to log file
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('bootstrap')
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.handlers:
        logger.handlers.clear()
    
    # Console handler with consistent colored prefixes
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_formatter = ConsoleLogFormatter()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def log_info(logger: logging.Logger, message: str) -> None:
    """Log info message."""
    logger.info(message)


def log_success(logger: logging.Logger, message: str) -> None:
    """Log success message."""
    logger.info(message, extra={'success': True})


def log_warning(logger: logging.Logger, message: str) -> None:
    """Log warning message."""
    logger.warning(message)


def log_error(logger: logging.Logger, message: str) -> None:
    """Log error message."""
    logger.error(message)


def format_audit_details(details: dict[str, Any]) -> list[str]:
    """Format a simple mapping into readable audit detail lines."""
    lines: list[str] = []
    for key, value in details.items():
        if value is None:
            continue
        lines.append(f"{key}: {value}")
    return lines


def render_command(command: str | Sequence[str]) -> str:
    """Render a command into a human-readable shell-safe string."""
    if isinstance(command, str):
        return command
    return ' '.join(shlex.quote(part) for part in command)


def expand_path(path: str) -> Path:
    """
    Expand user path and return Path object.
    
    Args:
        path: Path string potentially containing ~ or environment variables
        
    Returns:
        Expanded Path object
    """
    return Path(os.path.expanduser(os.path.expandvars(path)))


def backup_file(file_path: Path, backup_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Backup a file to a backup directory.
    
    Args:
        file_path: Path to file to backup
        backup_dir: Optional backup directory (defaults to ~/.dotfiles_backup_TIMESTAMP)
        
    Returns:
        Path to backup file or None if file doesn't exist
    """
    if not file_path.exists():
        return None
    
    if backup_dir is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = Path.home() / f'.dotfiles_backup_{timestamp}'
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / file_path.name
    
    shutil.copy2(file_path, backup_path)
    return backup_path


def run_command(
    command: str | Sequence[str],
    logger: logging.Logger,
    check: bool = True,
    shell: bool = False,
    capture_output: bool = False,
    audit_phase: str | None = None,
    audit_action: str | None = None,
    audit_target: str | None = None,
) -> subprocess.CompletedProcess:
    """
    Run a command with proper error handling.
    
    Args:
        command: Command string or argument list to run
        logger: Logger instance
        check: Raise exception on non-zero exit code
        shell: Run command in shell (must be explicitly enabled)
        capture_output: Capture stdout/stderr
        
    Returns:
        CompletedProcess instance
        
    Raises:
        subprocess.CalledProcessError: If command fails and check=True
    """
    command_display = command if isinstance(command, str) else ' '.join(command)
    try:
        logger.debug(f"Running command: {command_display}")
        if audit_phase and audit_action:
            log_audit_event(
                logger,
                phase=audit_phase,
                action=audit_action,
                status='started',
                target=audit_target,
                summary='Executing command',
                command=command,
            )
        result = subprocess.run(
            command,
            shell=shell,
            check=check,
            capture_output=capture_output,
            text=True
        )
        if audit_phase and audit_action:
            log_audit_event(
                logger,
                phase=audit_phase,
                action=audit_action,
                status='ok' if result.returncode == 0 else 'failed',
                target=audit_target,
                summary='Command execution finished',
                command=command,
                details=[f'exit_code: {result.returncode}'],
            )
        if not check and result.returncode != 0:
            logger.debug(
                f"Command returned non-zero exit code {result.returncode}: {command_display}"
            )
            if capture_output and result.stderr:
                logger.debug(result.stderr.strip())
        return result
    except subprocess.CalledProcessError as e:
        log_error(logger, f"Command failed: {command_display}")
        log_error(logger, f"Exit code: {e.returncode}")
        if audit_phase and audit_action:
            log_audit_event(
                logger,
                phase=audit_phase,
                action=audit_action,
                status='failed',
                target=audit_target,
                summary='Command execution raised an error',
                command=command,
                details=[f'exit_code: {e.returncode}'],
            )
        if capture_output and e.stderr:
            log_error(logger, f"Error output: {e.stderr}")
        raise


def check_macos() -> bool:
    """
    Check if running on macOS.
    
    Returns:
        True if on macOS, False otherwise
    """
    import platform
    return platform.system() == 'Darwin'


def restart_application(app_name: str, logger: logging.Logger) -> bool:
    """
    Restart a macOS application.
    
    Args:
        app_name: Name of the application to restart
        logger: Logger instance
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Kill the application
        run_command(
            ['killall', app_name],
            logger,
            check=False,
            capture_output=True
        )
        log_info(logger, f"Restarted {app_name}")
        return True
    except Exception as e:
        log_warning(logger, f"Could not restart {app_name}: {e}")
        return False


def confirm_action(prompt: str, default: bool = True) -> bool:
    """
    Ask user for confirmation.
    
    Args:
        prompt: Prompt message
        default: Default response if user just presses Enter
        
    Returns:
        True if user confirms, False otherwise
    """
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{default_str}]: ").strip().lower()
        
        if not response:
            return default
        
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            logging.getLogger('bootstrap').warning("Please answer 'y' or 'n'")
