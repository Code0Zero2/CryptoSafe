"""Application entry point and GUI initialization for CRYPTOSAFE."""

import sys
from PySide6.QtWidgets import QApplication
from cryptosafe import __version__
from cryptosafe.config import APP_NAME, APP_MODE
from cryptosafe.common.logging_config import setup_logging
from cryptosafe.gui.main_window import MainWindow

def create_app(args: list[str] | None = None) -> tuple[QApplication, MainWindow]:
    """Create or reuse QApplication and instantiate MainWindow."""
    setup_logging()
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(args if args is not None else sys.argv)

    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)

    window = MainWindow()
    return app, window

def main(args: list[str] | None = None) -> int:
    """Main CLI entry point running the PySide6 event loop."""
    passed_args = args if args is not None else sys.argv[1:]
    if "--cli-info" in passed_args:
        logger = setup_logging()
        logger.info("Initializing %s v%s [Mode: %s]", APP_NAME, __version__, APP_MODE)
        print(f"{APP_NAME} v{__version__} ({APP_MODE}) - GUI Ready")
        return 0

    app, window = create_app(args)
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

