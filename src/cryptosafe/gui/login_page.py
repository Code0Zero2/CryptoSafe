"""Login page with authentication and MFA hardware indicators."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QGroupBox,
)

class LoginPage(QWidget):
    """Login Page with real SQLite + Argon2id auth and simulated USB/Face markers."""

    login_requested = Signal(str, str)
    switch_to_register_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        # Central Card Container
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setMaximumWidth(440)
        card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; }"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(16)

        # Header with Logo Mark
        title = QLabel("CryptoSafe")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 26px; font-weight: 800; color: #0F172A; letter-spacing: -0.5px; border: none;"
        )
        card_layout.addWidget(title)

        subtitle = QLabel("Sistem Manajemen Dokumen Kontrak Rahasia")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500; border: none;")
        card_layout.addWidget(subtitle)

        # Input fields
        user_lbl = QLabel("Nama Pengguna")
        user_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155; border: none;")
        card_layout.addWidget(user_lbl)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Masukkan username Anda")
        self.username_input.setMinimumHeight(40)
        card_layout.addWidget(self.username_input)

        pass_lbl = QLabel("Kata Sandi")
        pass_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155; border: none;")
        card_layout.addWidget(pass_lbl)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Masukkan kata sandi")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(40)
        card_layout.addWidget(self.password_input)

        # Security Devices Box (Sleek Hardware Indicators)
        devices_card = QFrame()
        devices_card.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; }"
        )
        devices_layout = QVBoxLayout(devices_card)
        devices_layout.setSpacing(6)
        devices_layout.setContentsMargins(10, 8, 10, 8)

        self.usb_status_label = QLabel("USB Token: Tidak Terdeteksi")
        self.usb_status_label.setStyleSheet("color: #FF0000; font-size: 11px; font-weight: 500; border: none;")
        devices_layout.addWidget(self.usb_status_label)

        self.face_status_label = QLabel("Face Recognition: Siap diverifikasi")
        self.face_status_label.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500; border: none;")
        devices_layout.addWidget(self.face_status_label)

        card_layout.addWidget(devices_card)

        # Error / Validation Label
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #E11D48; font-size: 12px; font-weight: 500; border: none;")
        self.error_label.setVisible(False)
        card_layout.addWidget(self.error_label)

        # Action Buttons
        self.login_button = QPushButton("Masuk ke Sistem")
        self.login_button.setMinimumHeight(42)
        self.login_button.setStyleSheet(
            "QPushButton { background-color: #4F46E5; color: white; border: none; "
            "font-weight: 600; border-radius: 6px; font-size: 13px; }"
            "QPushButton:hover { background-color: #4338CA; }"
            "QPushButton:pressed { background-color: #3730A3; }"
        )
        self.login_button.clicked.connect(self._handle_login)
        card_layout.addWidget(self.login_button)

        self.register_switch_button = QPushButton("Belum memiliki akun? Daftar di sini")
        self.register_switch_button.setStyleSheet(
            "QPushButton { background: transparent; color: #4F46E5; font-size: 12px; font-weight: 500; border: none; }"
            "QPushButton:hover { text-decoration: underline; color: #3730A3; }"
        )
        self.register_switch_button.clicked.connect(self.switch_to_register_requested.emit)
        card_layout.addWidget(self.register_switch_button)

        layout.addWidget(card)

    def _handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.show_error("Username dan password tidak boleh kosong.")
            return

        self.error_label.setVisible(False)
        self.login_requested.emit(username, password)

    def show_error(self, message: str):
        """Display error message to user."""
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def set_usb_status(self, is_detected: bool, info: str = ""):
        """Update USB detection status on the login UI."""
        if is_detected:
            self.usb_status_label.setText(f"USB Token: Terdeteksi ({info or 'Siap diverifikasi'})")
            self.usb_status_label.setStyleSheet("color: #059669; font-size: 11px; font-weight: 600; border: none;")
        else:
            self.usb_status_label.setText("USB Token: Tidak Terdeteksi (Pasang token jika akun menggunakan USB 2FA)")
            self.usb_status_label.setStyleSheet("color: #FF0000; font-size: 11px; font-weight: 500; border: none;")

    def reset_fields(self):
        """Reset inputs and clear errors upon logout."""
        self.username_input.clear()
        self.password_input.clear()
        self.error_label.setVisible(False)

