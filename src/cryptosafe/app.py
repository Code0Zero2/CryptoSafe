"""Application entry point and foundation initialization for CRYPTOSAFE."""

import sys
from cryptosafe import __version__
from cryptosafe.config import APP_NAME, APP_MODE
from cryptosafe.common.logging_config import setup_logging

def init_app() -> int:
    """Initialize application logging and environment for M0 foundation."""
    logger = setup_logging()
    logger.info("Initializing %s v%s [Mode: %s]", APP_NAME, __version__, APP_MODE)
    logger.info("M0 Foundation initialized successfully.")
    print(f"{APP_NAME} v{__version__} ({APP_MODE}) - Project Foundation Ready")
    return 0

def main() -> int:
    """Main CLI entry point."""
    return init_app()

if __name__ == "__main__":
    sys.exit(main())

