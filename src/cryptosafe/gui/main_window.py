"""Main application window container (M1)."""

import logging
from PySide6.QtWidgets import QMainWindow, QStackedWidget
from cryptosafe.gui.login_page import LoginPage
from cryptosafe.gui.dashboard_page import DashboardPage

logger = logging.getLogger("cryptosafe.gui")

class MainWindow(QMainWindow):
    """Main Application Window hosting Login and Dashboard pages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CRYPTOSAFE — Multi-Factor Cryptography Demonstrator [DEMO]")
        self.resize(960, 680)
        self.setMinimumSize(800, 560)

        self._setup_pages()

    def _setup_pages(self):
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        self.login_page = LoginPage(self)
        self.dashboard_page = DashboardPage(self)

        self.stack.addWidget(self.login_page)       # Index 0
        self.stack.addWidget(self.dashboard_page)   # Index 1

        # Connect navigation signals
        self.login_page.login_requested.connect(self._on_login_requested)
        self.dashboard_page.logout_requested.connect(self._on_logout_requested)

    def _on_login_requested(self, username: str):
        logger.info("Demo user navigation to dashboard triggered.")
        self.dashboard_page.set_user(username)
        self.stack.setCurrentIndex(1)

    def _on_logout_requested(self):
        logger.info("User logged out; returning to login page.")
        self.login_page.reset_fields()
        self.stack.setCurrentIndex(0)

