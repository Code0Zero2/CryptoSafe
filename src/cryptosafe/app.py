"""Application entry point and GUI initialization for CRYPTOSAFE."""

import sys
from PySide6.QtWidgets import QApplication
from cryptosafe import __version__
from cryptosafe.config import APP_NAME, APP_MODE
from cryptosafe.common.logging_config import setup_logging
from cryptosafe.gui.main_window import MainWindow
from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.database.usb_repository import UsbRepository
from cryptosafe.database.face_repository import FaceRepository
from cryptosafe.auth.auth_service import AuthService
from cryptosafe.auth.usb_token_service import UsbTokenService
from cryptosafe.auth.face_service import FaceService

def create_app(
    args: list[str] | None = None,
    auth_service: AuthService | None = None,
    usb_service: UsbTokenService | None = None,
    face_service: FaceService | None = None,
) -> tuple[QApplication, MainWindow]:
    """Create or reuse QApplication and instantiate MainWindow."""
    setup_logging()
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(args if args is not None else sys.argv)

    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)

    if auth_service is None or usb_service is None or face_service is None:
        conn = get_connection()
        init_db(conn)
        user_repo = UserRepository(conn)
        usb_repo = UsbRepository(conn)
        face_repo = FaceRepository(conn)
        if usb_service is None:
            usb_service = UsbTokenService(usb_repo)
        if face_service is None:
            face_service = FaceService(face_repo)
        if auth_service is None:
            auth_service = AuthService(user_repo, usb_service=usb_service, face_service=face_service)

    window = MainWindow(auth_service=auth_service, usb_service=usb_service, face_service=face_service)
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

