"""macOS system preferences configuration module."""

import logging
from typing import Any, Dict, List

from .utils import (
    run_command,
    restart_application,
    log_info,
    log_success,
    log_warning,
    log_error,
    expand_path
)


class MacOSSettingsManager:
    """Manages macOS system preferences using defaults command."""
    
    def __init__(self, logger: logging.Logger, dry_run: bool = False):
        """
        Initialize macOS settings manager.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        self.dry_run = dry_run
    
    def _convert_value(self, value: Any, value_type: str) -> str:
        """
        Convert Python value to defaults command format.
        
        Args:
            value: Value to convert
            value_type: Type of value (bool, int, float, string)
            
        Returns:
            String representation for defaults command
        """
        if value_type == 'bool':
            return 'true' if value else 'false'
        elif value_type in ['int', 'float']:
            return str(value)
        elif value_type == 'string':
            # Expand paths if they contain ~
            if isinstance(value, str) and '~' in value:
                expanded = expand_path(value)
                return str(expanded)
            return str(value)
        else:
            return str(value)
    
    def apply_setting(
        self,
        domain: str,
        key: str,
        value: Any,
        value_type: str,
        description: str
    ) -> bool:
        """
        Apply a single macOS setting.
        
        Args:
            domain: Domain for defaults command
            key: Setting key
            value: Setting value
            value_type: Type of value (bool, int, float, string)
            description: Description of the setting
            
        Returns:
            True if successful, False otherwise
        """
        try:
            converted_value = self._convert_value(value, value_type)

            command = [
                'defaults', 'write', domain, key, f'-{value_type}', converted_value
            ]
            
            self.logger.debug(f"Applying: {description}")
            if self.dry_run:
                log_info(self.logger, f"[dry-run] Would apply setting: {description}")
            else:
                run_command(command, self.logger, check=True, capture_output=True)
            
            return True
        
        except Exception as e:
            log_error(
                self.logger,
                f"Failed to apply setting '{description}': {e}"
            )
            return False
    
    def apply_settings_category(
        self,
        category: str,
        settings: List[Dict]
    ) -> tuple[int, int]:
        """
        Apply all settings in a category.
        
        Args:
            category: Category name
            settings: List of setting configurations
            
        Returns:
            Tuple of (success_count, fail_count)
        """
        success_count = 0
        fail_count = 0
        
        log_info(self.logger, f"Applying {category} settings...")
        
        for setting in settings:
            domain = setting.get('domain')
            key = setting.get('key')
            value = setting.get('value')
            value_type = setting.get('type')
            
            if not all([domain, key, value_type is not None]):
                log_error(
                    self.logger,
                    f"Invalid setting configuration: {setting}"
                )
                fail_count += 1
                continue
            
            description = setting.get('description', f'{domain}.{key}')
            
            # Type guards ensure these are not None
            assert isinstance(domain, str)
            assert isinstance(key, str)
            assert isinstance(value_type, str)
            
            if self.apply_setting(domain, key, value, value_type, description):
                success_count += 1
            else:
                fail_count += 1
        
        return success_count, fail_count
    
    def apply_all_settings(self, macos_defaults: Dict) -> bool:
        """
        Apply all macOS settings from configuration.
        
        Args:
            macos_defaults: Dictionary of setting categories
            
        Returns:
            True if all settings applied successfully, False otherwise
        """
        log_info(self.logger, "Configuring macOS system preferences...")
        
        # Close System Preferences to avoid conflicts
        try:
            if not self.dry_run:
                run_command(
                    [
                        'osascript',
                        '-e', 'tell application "System Settings" to quit',
                        '-e', 'tell application "System Preferences" to quit',
                    ],
                    self.logger,
                    check=False,
                    capture_output=True
                )
        except Exception:
            pass  # Not critical if this fails
        
        total_success = 0
        total_fail = 0
        
        # Apply settings by category
        for category, settings in macos_defaults.items():
            if not isinstance(settings, list):
                log_warning(
                    self.logger,
                    f"Skipping invalid category: {category}"
                )
                continue
            
            success, fail = self.apply_settings_category(category, settings)
            total_success += success
            total_fail += fail
        
        # Summary
        if total_fail == 0:
            log_success(
                self.logger,
                f"Successfully applied all {total_success} settings"
            )
            return True
        else:
            log_warning(
                self.logger,
                f"Applied {total_success} settings, {total_fail} failed"
            )
            return False
    
    def run_special_commands(self, commands: List[Dict]) -> bool:
        """
        Run special commands that need custom handling.
        
        Args:
            commands: List of command configurations
            
        Returns:
            True if all commands successful, False otherwise
        """
        if not commands:
            return True
        
        log_info(self.logger, "Running special configuration commands...")
        
        success_count = 0
        fail_count = 0
        
        for cmd_config in commands:
            command = cmd_config.get('command')
            shell_command = cmd_config.get('shell_command')
            description = cmd_config.get('description', shell_command or command)
            requires_sudo = cmd_config.get('requires_sudo', False)

            if command and shell_command:
                log_error(
                    self.logger,
                    f"Invalid command configuration (choose either 'command' or 'shell_command'): {cmd_config}"
                )
                fail_count += 1
                continue

            if command:
                if not isinstance(command, list) or not all(isinstance(arg, str) for arg in command):
                    log_error(
                        self.logger,
                        f"Invalid command configuration ('command' must be a list of strings): {cmd_config}"
                    )
                    fail_count += 1
                    continue
                command = [str(expand_path(arg)) if '~' in arg else arg for arg in command]
            elif shell_command:
                if not isinstance(shell_command, str):
                    log_error(
                        self.logger,
                        f"Invalid command configuration ('shell_command' must be a string): {cmd_config}"
                    )
                    fail_count += 1
                    continue
            else:
                log_error(self.logger, f"Invalid command configuration: {cmd_config}")
                fail_count += 1
                continue
            
            try:
                self.logger.debug(f"Running: {description}")
                
                if requires_sudo:
                    log_info(self.logger, f"Running with sudo: {description}")
                
                if self.dry_run:
                    log_info(self.logger, f"[dry-run] Would run command: {description}")
                    success_count += 1
                else:
                    result = run_command(
                        command if command else shell_command,
                        self.logger,
                        check=False,
                        shell=bool(shell_command),
                        capture_output=True
                    )
                    if result.returncode == 0:
                        success_count += 1
                    else:
                        log_error(
                            self.logger,
                            f"Command returned exit code {result.returncode}: {description}"
                        )
                        fail_count += 1
            
            except Exception as e:
                log_error(self.logger, f"Failed to run '{description}': {e}")
                fail_count += 1
        
        if fail_count == 0:
            log_success(
                self.logger,
                f"Successfully ran all {success_count} special commands"
            )
            return True
        else:
            log_warning(
                self.logger,
                f"Ran {success_count} commands, {fail_count} failed"
            )
            return False
    
    def restart_applications(self, applications: List[str]) -> None:
        """
        Restart applications to apply settings.
        
        Args:
            applications: List of application names to restart
        """
        if not applications:
            return
        
        log_info(self.logger, "Restarting applications to apply settings...")
        
        for app in applications:
            if self.dry_run:
                log_info(self.logger, f"[dry-run] Would restart application: {app}")
            else:
                restart_application(app, self.logger)
