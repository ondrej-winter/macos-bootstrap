"""Homebrew Brewfile installation support."""

from __future__ import annotations

import argparse
import logging
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TextIO

from modules.utils import log_audit_event, log_error, log_info, log_success, log_warning


BREWFILE_NAMES = (
    "Brewfile.core",
    "Brewfile.dev",
    "Brewfile.apps",
    "Brewfile.mas",
    "Brewfile.extra",
)

BREW_PATTERN = re.compile(r'^\s*brew\s+"([^"]+)"')
CASK_PATTERN = re.compile(r'^\s*cask\s+"([^"]+)"')
TAP_PATTERN = re.compile(r'^\s*tap\s+"([^"]+)"')
MAS_PATTERN = re.compile(r'^\s*mas\s+"([^"]+)"\s*,\s*id:\s*([0-9]+)')


@dataclass(slots=True)
class BrewfileEntry:
    """Parsed Brewfile entry."""

    kind: str
    name: str
    app_id: str | None = None


@dataclass(slots=True)
class BrewInstallSummary:
    """Aggregated Brewfile processing results."""

    processed_files: int = 0
    total_entries: int = 0
    installed: list[str] = field(default_factory=list)
    reinstalled: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)


class BrewfileInstaller:
    """Install Homebrew items from split Brewfiles."""

    def __init__(
        self,
        logger: logging.Logger,
        script_dir: Path,
        reinstall_existing: bool = False,
    ) -> None:
        self.logger = logger
        self.script_dir = script_dir
        self.reinstall_existing = reinstall_existing
        self.brewfile_dir = script_dir / "configuration_homebrew"
        self.brewfile_paths = [self.brewfile_dir / name for name in BREWFILE_NAMES]
        self.log_dir = script_dir / "logs"
        self.app_dir = Path.home() / "Applications"
        self.log_file: Path | None = None
        self.summary = BrewInstallSummary()

    def run(self) -> int:
        """Execute the Brewfile installation phase."""
        log_info(self.logger, "Processing Brewfile entries (continuing past individual failures)...")
        log_audit_event(
            self.logger,
            phase="brew",
            action="brewfile-batch-started",
            status="started",
            summary="Processing split Brewfiles",
            details=[f"brewfile_count: {len(self.brewfile_paths)}", f"reinstall_existing: {self.reinstall_existing}"],
        )

        if not self.brewfile_dir.is_dir():
            log_warning(self.logger, f"Brewfile directory not found at {self.brewfile_dir}; skipping")
            log_audit_event(self.logger, phase="brew", action="brewfile-directory-check", status="skipped", target=str(self.brewfile_dir), summary="Brewfile directory not found; brew phase skipped")
            return 0

        self.summary = BrewInstallSummary()
        self._prepare_log()

        for brewfile_path in self.brewfile_paths:
            if not brewfile_path.is_file():
                message = f"Brewfile not found at {brewfile_path}; skipping"
                log_warning(self.logger, message)
                self._append_log_status("WARN", f"Missing Brewfile: {brewfile_path}")
                log_audit_event(self.logger, phase="brew", action="brewfile-check", status="skipped", target=str(brewfile_path), summary="Configured Brewfile was not found")
                continue

            self.summary.processed_files += 1
            self._process_brewfile(brewfile_path)

        if self.summary.processed_files == 0:
            log_warning(self.logger, "No Brewfiles were found to process; skipping")
            self._append_log_status("WARN", "No Brewfiles were found to process")
            log_audit_event(self.logger, phase="brew", action="brewfile-batch-completed", status="skipped", summary="No Brewfiles were available to process")
            return 0

        self._write_summary_to_log()
        self._print_summary()

        if self.summary.failed or self.summary.unparsed:
            log_warning(
                self.logger,
                "Brewfile processing completed with some issues. Review the summary above and the detailed log.",
            )
            log_audit_event(
                self.logger,
                phase="brew",
                action="brewfile-batch-completed",
                status="failed",
                summary="Brewfile processing completed with some issues",
                details=[
                    f"processed_files: {self.summary.processed_files}",
                    f"processed_entries: {self.summary.total_entries}",
                    f"failed: {len(self.summary.failed)}",
                    f"unparsed: {len(self.summary.unparsed)}",
                ],
            )
            return 1

        log_success(self.logger, "All Brewfile entries were processed successfully")
        log_audit_event(
            self.logger,
            phase="brew",
            action="brewfile-batch-completed",
            status="ok",
            summary="All Brewfile entries were processed successfully",
            details=[
                f"processed_files: {self.summary.processed_files}",
                f"processed_entries: {self.summary.total_entries}",
            ],
        )
        return 0

    def _process_brewfile(self, brewfile_path: Path) -> None:
        log_info(self.logger, f"Processing {brewfile_path.name}")
        self._append_log_status("INFO", f"Processing Brewfile: {brewfile_path}")
        log_audit_event(self.logger, phase="brew", action="brewfile-started", status="started", target=str(brewfile_path), summary="Processing Brewfile")

        for line_number, line in enumerate(brewfile_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue

            self.summary.total_entries += 1
            entry = self._parse_line(line)
            if entry is None:
                message = f"{brewfile_path.name}: line {line_number}: {line}"
                self._record_outcome("WARN", f"Unparsed Brewfile entry ({message})", "unparsed")
                continue

            if entry.kind == "brew":
                self._install_formula(entry.name)
            elif entry.kind == "cask":
                self._install_cask(entry.name)
            elif entry.kind == "tap":
                self._install_tap(entry.name)
            elif entry.kind == "mas" and entry.app_id is not None:
                self._install_mas(entry.name, entry.app_id)

        log_audit_event(self.logger, phase="brew", action="brewfile-completed", status="ok", target=str(brewfile_path), summary="Finished processing Brewfile")

    def _parse_line(self, line: str) -> BrewfileEntry | None:
        for pattern, kind in (
            (BREW_PATTERN, "brew"),
            (CASK_PATTERN, "cask"),
            (TAP_PATTERN, "tap"),
        ):
            match = pattern.match(line)
            if match:
                return BrewfileEntry(kind=kind, name=match.group(1))

        match = MAS_PATTERN.match(line)
        if match:
            return BrewfileEntry(kind="mas", name=match.group(1), app_id=match.group(2))

        return None

    def _prepare_log(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"brew-install-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"

        with self.log_file.open("w", encoding="utf-8") as handle:
            handle.write("macOS Bootstrap Brewfile Log\n")
            handle.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            handle.write("Processed Brewfiles:\n")
            for brewfile_path in self.brewfile_paths:
                handle.write(f"  - {brewfile_path}\n")
            handle.write("\n")

        log_info(self.logger, f"Detailed Brewfile output will be written to: {self.log_file}")

    def _append_log_status(self, status: str, message: str) -> None:
        if self.log_file is None:
            return

        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{status:<4}] {message}\n")

    def _record_outcome(self, status: str, message: str, bucket: str) -> None:
        self._record_outcome_with_command(status, message, bucket, None)

    def _record_outcome_with_command(
        self,
        status: str,
        message: str,
        bucket: str,
        command: list[str] | None,
    ) -> None:
        color_log = {
            "OK": log_success,
            "SKIP": log_info,
            "FAIL": log_error,
            "WARN": log_warning,
        }.get(status, log_info)
        color_log(self.logger, f"[{status:<4}] {message}")
        self._append_log_status(status, message)
        getattr(self.summary, bucket).append(message)
        mapped_status = {
            "OK": "ok",
            "SKIP": "skipped",
            "FAIL": "failed",
            "WARN": "warning",
        }.get(status, status.lower())
        log_audit_event(
            self.logger,
            phase="brew",
            action="brew-entry",
            status=mapped_status,
            target=message,
            summary="Processed Brewfile entry",
            command=command,
        )

    def _write_command_log_header(self, description: str, command: list[str], handle: TextIO) -> None:
        handle.write("\n")
        handle.write(f"=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {description} ===\n")
        handle.write("Command:")
        handle.write(" ")
        handle.write(" ".join(shlex.quote(part) for part in command))
        handle.write("\n")

    def _run_logged_command(self, description: str, command: list[str]) -> bool:
        if self.log_file is None:
            raise RuntimeError("Log file is not initialized")

        with self.log_file.open("a", encoding="utf-8") as handle:
            self._write_command_log_header(description, command, handle)
            result = subprocess.run(command, text=True, capture_output=True, stdin=subprocess.DEVNULL)
            if result.stdout or result.stderr:
                handle.write("--- command output ---\n")
                if result.stdout:
                    handle.write(result.stdout)
                    if not result.stdout.endswith("\n"):
                        handle.write("\n")
                if result.stderr:
                    handle.write(result.stderr)
                    if not result.stderr.endswith("\n"):
                        handle.write("\n")
                handle.write("--- end command output ---\n")
            handle.write(f"Exit code: {result.returncode}\n")
            handle.write("=== end ===\n")
        log_audit_event(
            self.logger,
            phase="brew",
            action="brew-command",
            status="ok" if result.returncode == 0 else "failed",
            target=description,
            summary="Brew command executed",
            command=command,
            details=[f"exit_code: {result.returncode}"],
        )
        return result.returncode == 0

    def _check_command(self, command: list[str]) -> bool:
        return subprocess.run(
            command,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        ).returncode == 0

    def _check_command_output(self, command: list[str]) -> str | None:
        result = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return None
        return result.stdout

    def _is_formula_installed(self, formula_name: str) -> bool:
        return self._check_command(["brew", "list", "--formula", formula_name])

    def _is_cask_installed(self, cask_name: str) -> bool:
        return self._check_command(["brew", "list", "--cask", cask_name])

    def _is_tap_installed(self, tap_name: str) -> bool:
        output = self._check_command_output(["brew", "tap"])
        return output is not None and tap_name in {line.strip() for line in output.splitlines()}

    def _is_mas_app_installed(self, app_id: str) -> bool:
        if shutil.which("mas") is None:
            return False
        output = self._check_command_output(["mas", "list"])
        if output is None:
            return False
        installed_ids = {line.split(maxsplit=1)[0] for line in output.splitlines() if line.strip()}
        return app_id in installed_ids

    def _install_formula(self, formula_name: str) -> None:
        item_label = f"brew {formula_name}"
        if self._is_formula_installed(formula_name):
            if self.reinstall_existing:
                command = ["brew", "reinstall", formula_name]
                success = self._run_logged_command(f"reinstall {item_label}", command)
                self._record_outcome_with_command(
                    "OK" if success else "FAIL",
                    f"{item_label} ({'reinstalled' if success else 'reinstall failed'})",
                    "reinstalled" if success else "failed",
                    command,
                )
            else:
                self._record_outcome("SKIP", f"{item_label} (already installed)", "skipped")
            return

        command = ["brew", "install", formula_name]
        success = self._run_logged_command(f"install {item_label}", command)
        self._record_outcome_with_command(
            "OK" if success else "FAIL",
            f"{item_label} ({'installed' if success else 'install failed'})",
            "installed" if success else "failed",
            command,
        )

    def _install_cask(self, cask_name: str) -> None:
        item_label = f"cask {cask_name}"
        self.app_dir.mkdir(parents=True, exist_ok=True)

        if self._is_cask_installed(cask_name):
            if self.reinstall_existing:
                command = ["brew", "reinstall", "--cask", "--appdir", str(self.app_dir), cask_name]
                success = self._run_logged_command(
                    f"reinstall {item_label}",
                    command,
                )
                self._record_outcome_with_command(
                    "OK" if success else "FAIL",
                    f"{item_label} ({'reinstalled' if success else 'reinstall failed'})",
                    "reinstalled" if success else "failed",
                    command,
                )
            else:
                self._record_outcome("SKIP", f"{item_label} (already installed)", "skipped")
            return

        command = ["brew", "install", "--cask", "--appdir", str(self.app_dir), cask_name]
        success = self._run_logged_command(
            f"install {item_label}",
            command,
        )
        self._record_outcome_with_command(
            "OK" if success else "FAIL",
            f"{item_label} ({'installed' if success else 'install failed'})",
            "installed" if success else "failed",
            command,
        )

    def _install_tap(self, tap_name: str) -> None:
        item_label = f"tap {tap_name}"
        if self._is_tap_installed(tap_name):
            self._record_outcome("SKIP", f"{item_label} (already tapped)", "skipped")
            return

        command = ["brew", "tap", tap_name]
        success = self._run_logged_command(item_label, command)
        self._record_outcome_with_command("OK" if success else "FAIL", item_label, "installed" if success else "failed", command)

    def _install_mas(self, app_name: str, app_id: str) -> None:
        item_label = f"mas {app_name} ({app_id})"
        if shutil.which("mas") is None:
            self._record_outcome("FAIL", f"{item_label} (mas CLI not available)", "failed")
            return

        if self._is_mas_app_installed(app_id):
            self._record_outcome("SKIP", f"{item_label} (already installed)", "skipped")
            return

        command = ["mas", "install", app_id]
        success = self._run_logged_command(item_label, command)
        self._record_outcome_with_command("OK" if success else "FAIL", item_label, "installed" if success else "failed", command)

    def _write_summary_to_log(self) -> None:
        if self.log_file is None:
            return

        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write("\n=== Summary ===\n")
            handle.write(f"Processed Brewfiles: {self.summary.processed_files}\n")
            handle.write(f"Processed entries: {self.summary.total_entries}\n")
            for label, items in (
                ("Installed", self.summary.installed),
                ("Reinstalled", self.summary.reinstalled),
                ("Skipped", self.summary.skipped),
                ("Failed", self.summary.failed),
                ("Unparsed", self.summary.unparsed),
            ):
                handle.write(f"{label}: {len(items)}\n")
                for item in items:
                    handle.write(f"  - {item}\n")

    def _print_summary_section(self, title: str, items: list[str]) -> None:
        if not items:
            return
        print()
        log_info(self.logger, f"{title} ({len(items)})")
        for item in items:
            print(f"  - {item}")

    def _print_summary(self) -> None:
        print()
        log_info(self.logger, "Brewfile installation summary")
        log_info(
            self.logger,
            f"Processed {self.summary.processed_files} Brewfile files and {self.summary.total_entries} Brewfile entries",
        )
        if self.log_file is not None:
            log_info(self.logger, f"Detailed log: {self.log_file}")

        self._print_summary_section("Installed", self.summary.installed)
        self._print_summary_section("Reinstalled", self.summary.reinstalled)
        self._print_summary_section("Skipped", self.summary.skipped)

        if self.summary.failed:
            print()
            log_warning(self.logger, f"Failed entries ({len(self.summary.failed)})")
            for item in self.summary.failed:
                print(f"  - {item}")

        if self.summary.unparsed:
            print()
            log_warning(self.logger, f"Unparsed Brewfile entries ({len(self.summary.unparsed)})")
            for item in self.summary.unparsed:
                print(f"  - {item}")


def add_homebrew_arguments(parser: argparse.ArgumentParser) -> None:
    """Register CLI arguments for the Brewfile installer."""
    parser.add_argument(
        "--reinstall-existing",
        action="store_true",
        help="Reinstall already-installed formulae and casks",
    )
