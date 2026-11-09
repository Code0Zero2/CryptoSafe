"""Main application window container (M2)."""

import logging
from PySide6.QtWidgets import QMainWindow, QStackedWidget
from cryptosafe.gui.login_page import LoginPage
from cryptosafe.gui.register_page import RegisterPage
from cryptosafe.gui.dashboard_page import DashboardPage
from cryptosafe.auth.auth_service import AuthService
from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.common.errors import AuthenticationError, ValidationError

logger = logging.getLogger("cryptosafe.gui")

class MainWindow(QMainWindow):
    """Main Application Window hosting Login, Register, and Dashboard pages."""

    def __init__(self, auth_service: AuthService | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CRYPTOSAFE — Multi-Factor Cryptography Demonstrator [M2]")
        self.resize(960, 680)
        self.setMinimumSize(800, 560)

        if auth_service is None:
            conn = get_connection()
            init_db(conn)
            user_repo = UserRepository(conn)
            auth_service = AuthService(user_repo)

        self._auth_service = auth_service
        self._current_user = None

        self._setup_pages()

    def _setup_pages(self):
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        self.login_page = LoginPage(self)
        self.dashboard_page = DashboardPage(self)
        self.register_page = RegisterPage(self)

        self.stack.addWidget(self.login_page)       # Index 0
        self.stack.addWidget(self.dashboard_page)   # Index 1
        self.stack.addWidget(self.register_page)    # Index 2

        # Connect navigation signals
        self.login_page.login_requested.connect(self._on_login_requested)
        self.login_page.switch_to_register_requested.connect(self._on_switch_to_register)

        self.register_page.register_requested.connect(self._on_register_requested)
        self.register_page.switch_to_login_requested.connect(self._on_switch_to_login)

        self.dashboard_page.logout_requested.connect(self._on_logout_requested)

    def _on_login_requested(self, username: str, password: str):
        try:
            user = self._auth_service.authenticate_user(username, password)
            self._current_user = user
            self.dashboard_page.set_user(user.username)
            self.login_page.reset_fields()
            self.stack.setCurrentIndex(1)
            logger.info("Session started for user: %s", user.username)
        except (AuthenticationError, ValidationError) as err:
            self.login_page.show_error(str(err))

    def _on_switch_to_register(self):
        self.login_page.reset_fields()
        self.register_page.reset_fields()
        self.stack.setCurrentIndex(2)

    def _on_switch_to_login(self):
        self.register_page.reset_fields()
        self.login_page.reset_fields()
        self.stack.setCurrentIndex(0)

    def _on_register_requested(self, username: str, password: str, confirm: str):
        try:
            user = self._auth_service.register_user(username, password, confirm)
            self.register_page.reset_fields()
            self.login_page.reset_fields()
            self.login_page.username_input.setText(user.username)
            self.login_page.show_error("Registrasi berhasil! Silakan masuk dengan kata sandi Anda.")
            # Set to green style for success note
            self.login_page.error_label.setStyleSheet("color: #059669; font-size: 12px; font-weight: 500;")
            self.stack.setCurrentIndex(0)
        except ValidationError as err:
            self.register_page.show_error(str(err))

    def _on_logout_requested(self):
        logged_user = self._current_user.username if self._current_user else "anonymous"
        logger.info("Session terminated for user: %s", logged_user)
        self._current_user = None
        self.login_page.reset_fields()
        self.stack.setCurrentIndex(0)

