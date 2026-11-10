"""Main application window container (M5)."""

import logging
import sqlite3
from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox, QDialog, QInputDialog, QLineEdit
from cryptosafe.config import DATA_DIR
from cryptosafe.gui.login_page import LoginPage
from cryptosafe.gui.register_page import RegisterPage
from cryptosafe.gui.dashboard_page import DashboardPage
from cryptosafe.gui.text_page import TextPage
from cryptosafe.gui.file_page import FilePage
from cryptosafe.gui.contract_page import ContractPage
from cryptosafe.gui.usb_dialog import UsbEnrollDialog
from cryptosafe.gui.face_capture_dialog import FaceCaptureDialog
from cryptosafe.gui.stego_page import StegoPage
from cryptosafe.auth.auth_service import AuthService
from cryptosafe.auth.usb_token_service import UsbTokenService
from cryptosafe.auth.face_service import FaceService
from cryptosafe.crypto.text_crypto_service import TextCryptoService
from cryptosafe.crypto.file_crypto_service import FileCryptoService
from cryptosafe.crypto.steganography_service import SteganographyService
from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.database.usb_repository import UsbRepository
from cryptosafe.database.face_repository import FaceRepository
from cryptosafe.database.contract_repository import ContractRepository
from cryptosafe.database.encrypted_message_repository import EncryptedMessageRepository
from cryptosafe.database.encrypted_message_service import EncryptedMessageService
from cryptosafe.database.contract_file_repository import ContractFileRepository
from cryptosafe.database.contract_file_service import ContractFileService
from cryptosafe.common.errors import AuthenticationError, AuthenticationCancelledError, ValidationError

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
        contract_repository: ContractRepository | None = None,
        message_service: EncryptedMessageService | None = None,
        contract_file_service: ContractFileService | None = None,
        stego_service: SteganographyService | None = None,
        conn: sqlite3.Connection | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("CRYPTOSAFE — Confidential Contract Management System")
        self.resize(960, 680)
        self.setMinimumSize(800, 560)

        if auth_service is not None:
            if usb_service is None:
                usb_service = getattr(auth_service, "_usb_service", None)
            if face_service is None:
                face_service = getattr(auth_service, "_face_service", None)

        # Consistent SQLite connection resolution
        if conn is None and auth_service is not None and hasattr(auth_service, "_user_repo") and hasattr(auth_service._user_repo, "_conn"):
            conn = auth_service._user_repo._conn

        if auth_service is None or usb_service is None or face_service is None:
            if conn is None:
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
        elif conn is None:
            conn = get_connection()
            init_db(conn)

        self._conn = conn
        self._user_repo = getattr(auth_service, "_user_repo", None) or UserRepository(conn)
        self._auth_service = auth_service
        self._usb_service = usb_service
        self._face_service = face_service
        self._text_crypto_service = text_crypto_service or TextCryptoService()
        self._file_crypto_service = file_crypto_service or FileCryptoService()
        self._stego_service = stego_service or SteganographyService(text_crypto_service=self._text_crypto_service)

        if contract_repository is None:
            contract_repository = ContractRepository(conn)
        self._contract_repository = contract_repository

        if message_service is None:
            message_repo = EncryptedMessageRepository(conn)
            message_service = EncryptedMessageService(message_repo, crypto_service=self._text_crypto_service)
        self._message_service = message_service

        if contract_file_service is None:
            contract_file_repo = ContractFileRepository(conn)
            contract_file_service = ContractFileService(
                repository=contract_file_repo,
                crypto_service=self._file_crypto_service,
            )
        self._contract_file_service = contract_file_service

        self._current_user = None

        self._setup_pages()
        self._refresh_usb_detection()

    def _refresh_usb_detection(self):
        detected = self._usb_service.detect_token_file()
        if detected:
            if detected.parent.name == ".cryptosafe":
                parent_name = detected.parent.parent.name or str(detected.parent.parent)
                display_label = f"{parent_name}/.cryptosafe"
            else:
                display_label = detected.name
            self.login_page.set_usb_status(True, display_label)
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
        self.contract_page = ContractPage(
            self._contract_repository,
            self._message_service,
            file_service=self._contract_file_service,
            parent=self,
        )
        self.stego_page = StegoPage(stego_service=self._stego_service, parent=self)

        self.stack.addWidget(self.login_page)       # Index 0
        self.stack.addWidget(self.dashboard_page)   # Index 1
        self.stack.addWidget(self.register_page)    # Index 2
        self.stack.addWidget(self.text_page)        # Index 3
        self.stack.addWidget(self.file_page)        # Index 4
        self.stack.addWidget(self.contract_page)    # Index 5
        self.stack.addWidget(self.stego_page)       # Index 6

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
        self.dashboard_page.open_contract_requested.connect(self._on_open_contract)
        self.dashboard_page.open_steganography_requested.connect(self._on_open_steganography)

        self.text_page.back_to_dashboard_requested.connect(self._on_back_from_text_crypto)
        self.file_page.back_to_dashboard_requested.connect(self._on_back_from_file_crypto)
        self.contract_page.back_to_dashboard_requested.connect(self._on_back_from_contract)
        self.stego_page.back_to_dashboard_requested.connect(self._on_back_from_stego)

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

    def _on_open_contract(self):
        user = self._current_user
        if user is None:
            username = getattr(self.dashboard_page, "username", "").strip()
            if username and username.lower() not in ("tamu", "anonymous", ""):
                user = self._user_repo.get_by_username(username)
                if user:
                    self._current_user = user

        if not self._current_user:
            logger.warning("Access to Contract Management denied: no active user session.")
            self.stack.setCurrentIndex(0)
            return

        self.contract_page.set_user(self._current_user.id)
        self.stack.setCurrentIndex(5)

    def _on_back_from_contract(self):
        self.stack.setCurrentIndex(1)

    def _on_open_steganography(self):
        self.stego_page.clear_fields()
        self.stack.setCurrentIndex(6)

    def _on_back_from_stego(self):
        self.stego_page.clear_fields()
        self.stack.setCurrentIndex(1)

    def _on_login_requested(self, username: str, password: str):
        def _capture_face_callback():
            dialog = FaceCaptureDialog(self._face_service, mode="login", parent=self)
            result = dialog.exec()
            if result != QDialog.DialogCode.Accepted or dialog.captured_frame is None:
                return None
            return dialog.captured_frame

        try:
            # Let auth_service orchestrate all MFA factors sequentially
            user = self._auth_service.authenticate_user(
                username,
                password,
                face_capture_callback=_capture_face_callback,
            )
            self._current_user = user
            self.dashboard_page.set_user(user.username)
            self.contract_page.set_user(user.id)
            has_usb = self._usb_service.has_active_token(user.id) if self._usb_service else False
            has_face = self._face_service.has_active_profile(user.id) if self._face_service else False
            self.dashboard_page.set_usb_token_status(has_usb)
            self.dashboard_page.set_face_profile_status(has_face)
            self.login_page.reset_fields()
            self.stack.setCurrentIndex(1)
            logger.info("Session started for user: %s", user.username)
        except AuthenticationCancelledError as err:
            logger.info("Login cancelled during biometric step.")
            self.login_page.show_error(str(err))
        except (AuthenticationError, ValidationError) as err:
            self.login_page.show_error(str(err))

    def _on_enroll_usb_requested(self):
        if not self._current_user:
            return

        dialog = UsbEnrollDialog(self._usb_service, self._current_user.username, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.selected_path:
            return

        # Authenticate password
        if not self._auth_service._password_service.verify_password(
            dialog.confirmed_password, self._current_user.password_hash
        ):
            QMessageBox.warning(
                self,
                "Autentikasi Gagal",
                "Kata sandi yang Anda masukkan salah. Pendaftaran USB dibatalkan."
            )
            return

        try:
            cred, token_path = self._usb_service.enroll_token(self._current_user.id, dialog.selected_path)
            self.dashboard_page.set_usb_token_status(True, f"Token ID: {cred.token_id[:8]}...")
            self._refresh_usb_detection()
            QMessageBox.information(
                self,
                "Registrasi USB Dongle Berhasil",
                f"Token autentikasi berhasil dibuat dan disimpan di:\n{token_path}\n\n"
                "Flashdisk ini kini wajib terpasang saat melakukan login."
            )
            logger.info("USB token enrolled for user %s at %s", self._current_user.username, token_path.parent)
        except (ValidationError, AuthenticationError, OSError) as err:
            logger.error("Failed to enroll USB token: %s", err)
            QMessageBox.critical(self, "Gagal Mendaftarkan USB", str(err))

    def _on_revoke_usb_requested(self):
        if not self._current_user:
            return

        password, accepted = QInputDialog.getText(
            self,
            "Konfirmasi Pencabutan USB Dongle",
            "Masukkan kata sandi akun untuk mencabut USB Dongle:\n"
            "(Akun akan kembali login hanya dengan password)",
            QLineEdit.EchoMode.Password,
        )
        if not accepted or not password:
            return

        if not self._auth_service._password_service.verify_password(
            password, self._current_user.password_hash
        ):
            QMessageBox.warning(
                self,
                "Autentikasi Gagal",
                "Kata sandi salah. Pencabutan USB dibatalkan."
            )
            return

        self._usb_service.revoke_token(self._current_user.id)
        self.dashboard_page.set_usb_token_status(False)
        self._refresh_usb_detection()
        QMessageBox.information(
            self,
            "USB Dicabut",
            "USB Dongle berhasil dicabut. Akun kini dapat login tanpa USB."
        )

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

        # Password confirmation for biometric key derivation
        password, accepted = QInputDialog.getText(
            self,
            "Konfirmasi Kata Sandi",
            "Masukkan kata sandi akun Anda untuk mengamankan template biometrik wajah:",
            QLineEdit.EchoMode.Password,
        )
        if not accepted or not password:
            return

        if not self._auth_service._password_service.verify_password(
            password, self._current_user.password_hash
        ):
            QMessageBox.warning(self, "Autentikasi Gagal", "Kata sandi salah. Pendaftaran wajah dibatalkan.")
            return

        # Open camera dialog for face capture
        dialog = FaceCaptureDialog(self._face_service, mode="enroll", parent=self)
        result = dialog.exec()
        if result != QDialog.DialogCode.Accepted or dialog.captured_frame is None:
            return

        try:
            self._face_service.enroll_face(
                self._current_user.id,
                dialog.captured_frame,
                user_consent=True,
                password=password,
            )
            self.dashboard_page.set_face_profile_status(True)
            QMessageBox.information(self, "Biometrik", "Pendaftaran profil biometrik wajah berhasil!")
            logger.info("Face biometrics enrolled successfully for user: %s", self._current_user.username)
        except (AuthenticationError, ValidationError) as err:
            logger.error("Failed to enroll face profile: %s", err)
            QMessageBox.warning(self, "Gagal Pendaftaran Wajah", str(err))

    def _on_revoke_face_requested(self):
        if not self._current_user:
            return

        password, accepted = QInputDialog.getText(
            self,
            "Konfirmasi Pencabutan Wajah",
            "Masukkan kata sandi akun untuk mencabut profil wajah:",
            QLineEdit.EchoMode.Password,
        )
        if not accepted or not password:
            return

        if not self._auth_service._password_service.verify_password(
            password, self._current_user.password_hash
        ):
            QMessageBox.warning(self, "Autentikasi Gagal", "Kata sandi salah. Pencabutan wajah dibatalkan.")
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
        self.contract_page.set_user(None)
        self.dashboard_page.set_user("")
        self.login_page.reset_fields()
        self._refresh_usb_detection()
        self.stack.setCurrentIndex(0)

