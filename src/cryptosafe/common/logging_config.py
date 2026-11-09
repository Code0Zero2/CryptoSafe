import logging
import sys
from pathlib import Path
from cryptosafe.config import LOGS_DIR, DEFAULT_LOG_PATH, LOG_LEVEL

def setup_logging(log_file: Path | None = None, level: str | None = None, force: bool = False) -> logging.Logger:
    """Configure structured, security-conscious application logging."""
    logger = logging.getLogger("cryptosafe")
    
    if logger.handlers and not force:
        return logger

    if force:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    log_level_str = (level or LOG_LEVEL).upper()
    numeric_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(numeric_level)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s.%(module)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    target_log_path = log_file or DEFAULT_LOG_PATH
    try:
        target_log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(target_log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        logger.warning("Could not initialize file logging handler. Logging to console only.")

    return logger
