"""Dotfiles installation module."""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .utils import expand_path, backup_file, log_info, log_success, log_warning, log_error


class DotfilesManager:
    """Manages dotfiles installation with backup functionality."""
    
    def __init__(self, logger: logging.Logger, script_dir: Path, dry_run: bool = False):
        """
        Initialize dotfiles manager.
        
        Args:
            logger: Logger instance
            script_dir: Directory containing the bootstrap script
        """
        self.logger = logger
        self.script_dir = script_dir
        self.backup_dir: Optional[Path] = None
        self.dry_run = dry_run
    
    def _get_backup_dir(self) -> Path:
        """Get or create backup directory."""
        if self.backup_dir is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.backup_dir = Path.home() / f'.dotfiles_backup_{timestamp}'
        return self.backup_dir
    
    def install_dotfile(
        self,
        source: str,
        destination: str,
        description: str
    ) -> bool:
        """
        Install a single dotfile.
        
        Args:
            source: Source file path (relative to script directory)
            destination: Destination path (with ~ expansion)
            description: Description of the dotfile
            
        Returns:
            True if successful, False otherwise
        """
        try:
            source_path = self.script_dir / source
            dest_path = expand_path(destination)
            
            # Check if source exists
            if not source_path.exists():
                log_error(self.logger, f"Source file not found: {source_path}")
                return False
            
            # Backup existing file if it exists
            if dest_path.exists():
                backup_path = None
                if self.dry_run:
                    log_warning(
                        self.logger,
                        f"[dry-run] Would back up existing {dest_path} to {self._get_backup_dir()}"
                    )
                else:
                    backup_path = backup_file(dest_path, self._get_backup_dir())

                if backup_path:
                    log_warning(
                        self.logger,
                        f"Backed up existing {dest_path.name} to {backup_path}"
                    )
            
            # Create parent directory if needed
            if self.dry_run:
                log_info(self.logger, f"[dry-run] Would ensure parent directory exists: {dest_path.parent}")
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            if self.dry_run:
                log_info(self.logger, f"[dry-run] Would install {description}: {source_path} -> {dest_path}")
            else:
                shutil.copy2(source_path, dest_path)
                log_success(self.logger, f"Installed {description}: {dest_path}")
            
            return True
        
        except Exception as e:
            log_error(self.logger, f"Failed to install {description}: {e}")
            return False
    
    def install_dotfiles(self, dotfiles_config: List[Dict]) -> bool:
        """
        Install all dotfiles from configuration.
        
        Args:
            dotfiles_config: List of dotfile configurations
            
        Returns:
            True if all installations successful, False otherwise
        """
        log_info(self.logger, "Installing dotfiles...")
        
        success_count = 0
        fail_count = 0
        
        for dotfile in dotfiles_config:
            source = dotfile.get('source')
            destination = dotfile.get('destination')
            description = dotfile.get('description', source or 'unknown')
            
            if not source or not destination:
                log_error(self.logger, f"Invalid dotfile configuration: {dotfile}")
                fail_count += 1
                continue
            
            if self.install_dotfile(source, destination, description):
                success_count += 1
            else:
                fail_count += 1
        
        # Summary
        if fail_count == 0:
            log_success(
                self.logger,
                f"Successfully installed all {success_count} dotfiles"
            )
            return True
        else:
            log_warning(
                self.logger,
                f"Installed {success_count} dotfiles, {fail_count} failed"
            )
            return False
