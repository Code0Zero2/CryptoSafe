"""Main application window container (M5)."""

import logging
from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox
from cryptosafe.config import DATA_DIR
from cryptosafe.gui.login_page import LoginPage
from cryptosafe.gui.register_page import RegisterPage
from cryptosafe.gui.dashboard_page import DashboardPage
from cryptosafe.gui.text_page import TextPage
from cryptosafe.gui.file_page import FilePage
from cryptosafe.auth.auth_service import AuthService
from cryptosafe.auth.usb_token_service import UsbTokenService
from cryptosafe.auth.face_service import FaceService
from cryptosafe.crypto.text_crypto_service import TextCryptoService
from cryptosafe.crypto.file_crypto_service import FileCryptoService
from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.database.usb_repository import UsbRepository
from cryptosafe.database.face_repository import FaceRepository
from cryptosafe.common.errors import AuthenticationError, ValidationError

logger = logging.getLogger("cryptosafe.gui")

class MainWindow(QMainWindow):
    """Main Application Window hosting Login, Register, Dashboard, and Feature pages."""

    def __init__(
        self,
        auth_service: AuthService | None = None,
        usb_service: UsbTokenService | None = None,
        face_service: FaceService | None = None,
        text_crypto_service: TextCryptoService | None = None,
        file_crypto_service: FileCryptoService | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("CRYPTOSAFE — Multi-Factor Cryptography Demonstrator [M7]")
        self.resize(960, 680)
        self.setMinimumSize(800, 560)

        if auth_service is not None:
            if usb_service is None:
                usb_service = getattr(auth_service, "_usb_service", None)
            if face_service is None:
                face_service = getattr(auth_service, "_face_service", None)

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

        self._auth_service = auth_service
        self._usb_service = usb_service
        self._face_service = face_service
        self._text_crypto_service = text_crypto_service or TextCryptoService()
        self._file_crypto_service = file_crypto_service or FileCryptoService()
        self._current_user = None

        self._setup_pages()
        self._refresh_usb_detection()

    def _refresh_usb_detection(self):
        detected = self._usb_service.detect_token_file()
        if detected:
            self.login_page.set_usb_status(True, detected.name)
        else:
            self.login_page.set_usb_status(False)

    def _setup_pages(self):
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        self.login_page = LoginPage(self)
        self.dashboard_page = DashboardPage(self)
        self.register_page = RegisterPage(self)
        self.text_page = TextPage(text_crypto_service=self._text_crypto_service, parent=self)
        self.file_page = FilePage(file_crypto_service=self._file_crypto_service, parent=self)

        self.stack.addWidget(self.login_page)       # Index 0
        self.stack.addWidget(self.dashboard_page)   # Index 1
        self.stack.addWidget(self.register_page)    # Index 2
        self.stack.addWidget(self.text_page)        # Index 3
        self.stack.addWidget(self.file_page)        # Index 4

        # Connect navigation signals
        self.login_page.login_requested.connect(self._on_login_requested)
        self.login_page.switch_to_register_requested.connect(self._on_switch_to_register)

        self.register_page.register_requested.connect(self._on_register_requested)
        self.register_page.switch_to_login_requested.connect(self._on_switch_to_login)

        self.dashboard_page.logout_requested.connect(self._on_logout_requested)
        self.dashboard_page.enroll_usb_requested.connect(self._on_enroll_usb_requested)
        self.dashboard_page.revoke_usb_requested.connect(self._on_revoke_usb_requested)
        self.dashboard_page.enroll_face_requested.connect(self._on_enroll_face_requested)
        self.dashboard_page.revoke_face_requested.connect(self._on_revoke_face_requested)
        self.dashboard_page.open_text_crypto_requested.connect(self._on_open_text_crypto)
        self.dashboard_page.open_file_crypto_requested.connect(self._on_open_file_crypto)

        self.text_page.back_to_dashboard_requested.connect(self._on_back_from_text_crypto)
        self.file_page.back_to_dashboard_requested.connect(self._on_back_from_file_crypto)

    def _on_open_text_crypto(self):
        self.text_page.clear_fields()
        self.stack.setCurrentIndex(3)

    def _on_back_from_text_crypto(self):
        self.text_page.clear_fields()
        self.stack.setCurrentIndex(1)

    def _on_open_file_crypto(self):
        self.file_page.clear_fields()
        self.stack.setCurrentIndex(4)

    def _on_back_from_file_crypto(self):
        self.file_page.clear_fields()
        self.stack.setCurrentIndex(1)

    def _on_login_requested(self, username: str, password: str):
        try:
            # Let auth_service handle password + USB + Face challenge
            user = self._auth_service.authenticate_user(username, password)
            self._current_user = user
            self.dashboard_page.set_user(user.username)
            has_usb = self._usb_service.has_active_token(user.id)
            has_face = self._face_service.has_active_profile(user.id)
            self.dashboard_page.set_usb_token_status(has_usb)
            self.dashboard_page.set_face_profile_status(has_face)
            self.login_page.reset_fields()
            self.stack.setCurrentIndex(1)
            logger.info("Session started for user: %s", user.username)
        except (AuthenticationError, ValidationError) as err:
            self.login_page.show_error(str(err))

    def _on_enroll_usb_requested(self):
        if not self._current_user:
            return
        target_dir = DATA_DIR / "tokens" / self._current_user.username
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            cred, token_path = self._usb_service.enroll_token(self._current_user.id, target_dir)
            self.dashboard_page.set_usb_token_status(True, f"Token ID: {cred.token_id[:8]}...")
            self._refresh_usb_detection()
            logger.info("Token enrolled at %s", token_path)
        except ValidationError as err:
            logger.error("Failed to enroll USB token: %s", err)

    def _on_revoke_usb_requested(self):
        if not self._current_user:
            return
        self._usb_service.revoke_token(self._current_user.id)
        self.dashboard_page.set_usb_token_status(False)
        self._refresh_usb_detection()

    def _on_enroll_face_requested(self):
        if not self._current_user:
            return
        # Informed consent confirmation
        reply = QMessageBox.question(
            self,
            "Persetujuan Biometrik Wajah",
            "Apakah Anda menyetujui pemindaian kamera dan penyimpanan template biometrik wajah terenkripsi?\n"
            "Foto mentah tidak disimpan, hanya template fitur terenkripsi lokal.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return

        try:
            frame = self._face_service.capture_camera_frame()
            self._face_service.enroll_face(self._current_user.id, frame, user_consent=True)
            self.dashboard_page.set_face_profile_status(True)
            QMessageBox.information(self, "Biometrik", "Pendaftaran profil biometrik wajah berhasil!")
        except (AuthenticationError, ValidationError) as err:
            QMessageBox.warning(self, "Gagal Pendaftaran Wajah", str(err))

    def _on_revoke_face_requested(self):
        if not self._current_user:
            return
        self._face_service.revoke_face(self._current_user.id)
        self.dashboard_page.set_face_profile_status(False)
        QMessageBox.information(self, "Biometrik", "Profil biometrik wajah berhasil dicabut.")

    def _on_switch_to_register(self):
        self.login_page.reset_fields()
        self.register_page.reset_fields()
        self.stack.setCurrentIndex(2)

    def _on_switch_to_login(self):
        self.register_page.reset_fields()
        self.login_page.reset_fields()
        self._refresh_usb_detection()
        self.stack.setCurrentIndex(0)

    def _on_register_requested(self, username: str, password: str, confirm: str):
        try:
            user = self._auth_service.register_user(username, password, confirm)
            self.register_page.reset_fields()
            self.login_page.reset_fields()
            self.login_page.username_input.setText(user.username)
            self.login_page.show_error("Registrasi berhasil! Silakan masuk dengan kata sandi Anda.")
            self.login_page.error_label.setStyleSheet("color: #059669; font-size: 12px; font-weight: 500;")
            self._refresh_usb_detection()
            self.stack.setCurrentIndex(0)
        except ValidationError as err:
            self.register_page.show_error(str(err))

    def _on_logout_requested(self):
        logged_user = self._current_user.username if self._current_user else "anonymous"
        logger.info("Session terminated for user: %s", logged_user)
        self._auth_service.logout()
        self._current_user = None
        self.login_page.reset_fields()
        self._refresh_usb_detection()
        self.stack.setCurrentIndex(0)

