"""macOS system preferences configuration module."""

import logging
from typing import Any, Dict, List

from .utils import (
    log_audit_event,
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
                log_audit_event(
                    self.logger,
                    phase="macos",
                    action="setting-apply",
                    status="dry-run",
                    target=f"{domain}.{key}",
                    summary="macOS setting would be applied in dry-run mode",
                    command=command,
                    details=[f"description: {description}", f"value_type: {value_type}", f"value: {converted_value}"],
                )
            else:
                run_command(command, self.logger, check=True, capture_output=True)
                log_audit_event(
                    self.logger,
                    phase="macos",
                    action="setting-apply",
                    status="ok",
                    target=f"{domain}.{key}",
                    summary="macOS setting applied",
                    command=command,
                    details=[f"description: {description}", f"value_type: {value_type}", f"value: {converted_value}"],
                )
            
            return True
        
        except Exception as e:
            log_error(
                self.logger,
                f"Failed to apply setting '{description}': {e}"
            )
            log_audit_event(
                self.logger,
                phase="macos",
                action="setting-apply",
                status="failed",
                target=f"{domain}.{key}",
                summary="Failed to apply macOS setting",
                command=command,
                details=[f"description: {description}", f"error: {e}"],
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
        log_audit_event(
            self.logger,
            phase="macos",
            action="settings-category-started",
            status="started",
            target=category,
            summary=f"Applying settings category '{category}'",
            details=[f"setting_count: {len(settings)}"],
        )
        
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
                log_audit_event(
                    self.logger,
                    phase="macos",
                    action="setting-validate",
                    status="failed",
                    target=category,
                    summary="Invalid macOS setting configuration",
                    details=str(setting),
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
        
        log_audit_event(
            self.logger,
            phase="macos",
            action="settings-category-completed",
            status="ok" if fail_count == 0 else "failed",
            target=category,
            summary=f"Completed settings category '{category}'",
            details=[f"successful: {success_count}", f"failed: {fail_count}"],
        )
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
        log_audit_event(
            self.logger,
            phase="macos",
            action="settings-batch-started",
            status="started",
            summary="Applying configured macOS settings",
            details=[f"category_count: {len(macos_defaults)}"],
        )
        
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
                log_audit_event(
                    self.logger,
                    phase="macos",
                    action="settings-category-validate",
                    status="failed",
                    target=category,
                    summary="Skipping invalid macOS settings category because it is not a list",
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
            log_audit_event(
                self.logger,
                phase="macos",
                action="settings-batch-completed",
                status="ok",
                summary="Applied all configured macOS settings successfully",
                details=[f"successful: {total_success}", f"failed: {total_fail}"],
            )
            return True
        else:
            log_warning(
                self.logger,
                f"Applied {total_success} settings, {total_fail} failed"
            )
            log_audit_event(
                self.logger,
                phase="macos",
                action="settings-batch-completed",
                status="failed",
                summary="Applied macOS settings with some failures",
                details=[f"successful: {total_success}", f"failed: {total_fail}"],
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
        log_audit_event(
            self.logger,
            phase="macos",
            action="special-commands-started",
            status="started",
            summary="Running special macOS configuration commands",
            details=[f"command_count: {len(commands)}"],
        )
        
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
                log_audit_event(self.logger, phase="macos", action="special-command-validate", status="failed", summary="Invalid special command configuration: both command and shell_command were provided", details=str(cmd_config))
                fail_count += 1
                continue

            if command:
                if not isinstance(command, list) or not all(isinstance(arg, str) for arg in command):
                    log_error(
                        self.logger,
                        f"Invalid command configuration ('command' must be a list of strings): {cmd_config}"
                    )
                    log_audit_event(self.logger, phase="macos", action="special-command-validate", status="failed", summary="Invalid special command list configuration", details=str(cmd_config))
                    fail_count += 1
                    continue
                command = [str(expand_path(arg)) if '~' in arg else arg for arg in command]
            elif shell_command:
                if not isinstance(shell_command, str):
                    log_error(
                        self.logger,
                        f"Invalid command configuration ('shell_command' must be a string): {cmd_config}"
                    )
                    log_audit_event(self.logger, phase="macos", action="special-command-validate", status="failed", summary="Invalid special shell command configuration", details=str(cmd_config))
                    fail_count += 1
                    continue
            else:
                log_error(self.logger, f"Invalid command configuration: {cmd_config}")
                log_audit_event(self.logger, phase="macos", action="special-command-validate", status="failed", summary="Invalid special command configuration", details=str(cmd_config))
                fail_count += 1
                continue
            
            try:
                self.logger.debug(f"Running: {description}")
                
                if requires_sudo:
                    log_info(self.logger, f"Running with sudo: {description}")
                
                if self.dry_run:
                    log_info(self.logger, f"[dry-run] Would run command: {description}")
                    log_audit_event(
                        self.logger,
                        phase="macos",
                        action="special-command-run",
                        status="dry-run",
                        target=str(description),
                        summary="Special command would be executed in dry-run mode",
                        command=command if command else shell_command,
                        details=[f"requires_sudo: {requires_sudo}"],
                    )
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
                        log_audit_event(
                            self.logger,
                            phase="macos",
                            action="special-command-run",
                            status="ok",
                            target=str(description),
                            summary="Special command executed successfully",
                            command=command if command else shell_command,
                            details=[f"requires_sudo: {requires_sudo}"],
                        )
                        success_count += 1
                    else:
                        log_error(
                            self.logger,
                            f"Command returned exit code {result.returncode}: {description}"
                        )
                        log_audit_event(
                            self.logger,
                            phase="macos",
                            action="special-command-run",
                            status="failed",
                            target=str(description),
                            summary="Special command returned a non-zero exit code",
                            command=command if command else shell_command,
                            details=[f"exit_code: {result.returncode}", f"requires_sudo: {requires_sudo}"],
                        )
                        fail_count += 1
            
            except Exception as e:
                log_error(self.logger, f"Failed to run '{description}': {e}")
                log_audit_event(self.logger, phase="macos", action="special-command-run", status="failed", target=str(description), summary="Special command execution failed", command=command if command else shell_command, details=str(e))
                fail_count += 1
        
        if fail_count == 0:
            log_success(
                self.logger,
                f"Successfully ran all {success_count} special commands"
            )
            log_audit_event(self.logger, phase="macos", action="special-commands-completed", status="ok", summary="All special commands completed successfully", details=[f"successful: {success_count}", f"failed: {fail_count}"])
            return True
        else:
            log_warning(
                self.logger,
                f"Ran {success_count} commands, {fail_count} failed"
            )
            log_audit_event(self.logger, phase="macos", action="special-commands-completed", status="failed", summary="Special commands completed with failures", details=[f"successful: {success_count}", f"failed: {fail_count}"])
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
        log_audit_event(
            self.logger,
            phase="macos",
            action="application-restart-batch-started",
            status="started",
            summary="Restarting applications to apply settings",
            details=[f"application_count: {len(applications)}"],
        )
        
        for app in applications:
            if self.dry_run:
                log_info(self.logger, f"[dry-run] Would restart application: {app}")
                log_audit_event(self.logger, phase="macos", action="application-restart", status="dry-run", target=app, summary="Application would be restarted in dry-run mode")
            else:
                restarted = restart_application(app, self.logger)
                log_audit_event(self.logger, phase="macos", action="application-restart", status="ok" if restarted else "failed", target=app, summary="Application restart attempted")

        log_audit_event(
            self.logger,
            phase="macos",
            action="application-restart-batch-completed",
            status="ok",
            summary="Application restart processing completed",
        )
