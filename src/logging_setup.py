from __future__ import annotations

import logging
import os
from logging.handlers import TimedRotatingFileHandler


def setup_logging(log_file_path: str, backup_days: int) -> None:
    # Determine target path; if making the directory fails (e.g., permission), fall back to ./data
    target_path = log_file_path
    directory = os.path.dirname(target_path)
    try:
        if directory:
            os.makedirs(directory, exist_ok=True)
    except Exception:
        # Fallback to a local data directory
        fallback_dir = os.path.join(os.getcwd(), "data")
        os.makedirs(fallback_dir, exist_ok=True)
        target_path = os.path.join(fallback_dir, os.path.basename(log_file_path) or "bot.log")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if re-initialized
    if logger.handlers:
        return

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(ch)

    # Daily rotating file handler with retention in days
    fh = TimedRotatingFileHandler(target_path, when="D", interval=1, backupCount=backup_days)
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)


