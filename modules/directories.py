"""Directory creation module."""

import logging
from typing import List

from .utils import expand_path, log_info, log_success, log_error


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
    
    success = True
    created_dirs = []
    
    for directory in directories:
        try:
            dir_path = expand_path(directory)
            
            if dir_path.exists():
                logger.debug(f"Directory already exists: {dir_path}")
            else:
                if dry_run:
                    log_info(logger, f"[dry-run] Would create directory: {dir_path}")
                else:
                    dir_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(str(dir_path))
                logger.debug(f"Created directory: {dir_path}")
        
        except Exception as e:
            log_error(logger, f"Failed to create directory {directory}: {e}")
            success = False
    
    if created_dirs:
        log_success(logger, f"Created {len(created_dirs)} directories")
        for d in created_dirs:
            logger.debug(f"  - {d}")
    else:
        log_info(logger, "All directories already exist")
    
    return success
