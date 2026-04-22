"""Utility functions for bootstrap setup."""

import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# ANSI color codes for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


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
    
    # Console handler with color
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
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
    """Log info message with color."""
    logger.info(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")


def log_success(logger: logging.Logger, message: str) -> None:
    """Log success message with color."""
    logger.info(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")


def log_warning(logger: logging.Logger, message: str) -> None:
    """Log warning message with color."""
    logger.warning(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")


def log_error(logger: logging.Logger, message: str) -> None:
    """Log error message with color."""
    logger.error(f"{Colors.RED}[ERROR]{Colors.NC} {message}")


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
    command: str,
    logger: logging.Logger,
    check: bool = True,
    shell: bool = True,
    capture_output: bool = False
) -> subprocess.CompletedProcess:
    """
    Run a shell command with proper error handling.
    
    Args:
        command: Command to run
        logger: Logger instance
        check: Raise exception on non-zero exit code
        shell: Run command in shell
        capture_output: Capture stdout/stderr
        
    Returns:
        CompletedProcess instance
        
    Raises:
        subprocess.CalledProcessError: If command fails and check=True
    """
    try:
        logger.debug(f"Running command: {command}")
        result = subprocess.run(
            command,
            shell=shell,
            check=check,
            capture_output=capture_output,
            text=True
        )
        if not check and result.returncode != 0:
            logger.debug(f"Command returned non-zero exit code {result.returncode}: {command}")
            if capture_output and result.stderr:
                logger.debug(result.stderr.strip())
        return result
    except subprocess.CalledProcessError as e:
        log_error(logger, f"Command failed: {command}")
        log_error(logger, f"Exit code: {e.returncode}")
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
            f'killall "{app_name}"',
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
            print("Please answer 'y' or 'n'")
