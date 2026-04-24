"""Directory creation module."""

import logging
from typing import List

from .utils import expand_path, log_audit_event, log_error, log_info, log_success


def create_directories(
    directories: List[str],
    logger: logging.Logger,
    dry_run: bool = False,
) -> bool:
    """
    Create directories from configuration.
    
    Args:
        directories: List of directory paths to create
        logger: Logger instance
        
    Returns:
        True if all directories created successfully, False otherwise
    """
    log_info(logger, "Creating directories...")
    log_audit_event(
        logger,
        phase="directories",
        action="directory-batch-started",
        status="started",
        summary=f"Preparing to process {len(directories)} configured directories",
    )
    
    success = True
    created_dirs = []
    
    for directory in directories:
        try:
            dir_path = expand_path(directory)
            
            if dir_path.exists():
                logger.debug(f"Directory already exists: {dir_path}")
                log_audit_event(
                    logger,
                    phase="directories",
                    action="directory-check",
                    status="skipped",
                    target=str(dir_path),
                    summary="Directory already exists",
                )
            else:
                if dry_run:
                    log_info(logger, f"[dry-run] Would create directory: {dir_path}")
                    log_audit_event(
                        logger,
                        phase="directories",
                        action="directory-create",
                        status="dry-run",
                        target=str(dir_path),
                        summary="Directory would be created in dry-run mode",
                    )
                else:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    log_audit_event(
                        logger,
                        phase="directories",
                        action="directory-create",
                        status="ok",
                        target=str(dir_path),
                        summary="Directory created",
                    )
                created_dirs.append(str(dir_path))
                logger.debug(f"Created directory: {dir_path}")
        
        except Exception as e:
            log_error(logger, f"Failed to create directory {directory}: {e}")
            log_audit_event(
                logger,
                phase="directories",
                action="directory-create",
                status="failed",
                target=directory,
                summary="Directory creation failed",
                details=str(e),
            )
            success = False
    
    if created_dirs:
        log_success(logger, f"Created {len(created_dirs)} directories")
        log_audit_event(
            logger,
            phase="directories",
            action="directory-batch-completed",
            status="ok" if success else "failed",
            summary=f"Processed directories with {len(created_dirs)} created entries",
            details=[f"created: {directory}" for directory in created_dirs],
        )
        for d in created_dirs:
            logger.debug(f"  - {d}")
    else:
        log_info(logger, "All directories already exist")
        log_audit_event(
            logger,
            phase="directories",
            action="directory-batch-completed",
            status="ok" if success else "failed",
            summary="No new directories were created",
        )
    
    return success
