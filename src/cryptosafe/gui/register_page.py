"""User registration page."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
)

class RegisterPage(QWidget):
    """User registration page."""

    register_requested = Signal(str, str, str)  # username, password, confirm_password
    switch_to_login_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setMaximumWidth(440)
        card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; }"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(16)

        title = QLabel("CryptoSafe")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 26px; font-weight: 800; color: #0F172A; letter-spacing: -0.5px; border: none;"
        )
        card_layout.addWidget(title)

        subtitle = QLabel("Pendaftaran Akun Pengguna Baru")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500; border: none;")
        card_layout.addWidget(subtitle)

        # Inputs
        u_lbl = QLabel("Nama Pengguna")
        u_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155; border: none;")
        card_layout.addWidget(u_lbl)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Pilih username (3-32 karakter)")
        self.username_input.setMinimumHeight(40)
        card_layout.addWidget(self.username_input)

        p_lbl = QLabel("Kata Sandi")
        p_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155; border: none;")
        card_layout.addWidget(p_lbl)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Minimal 6 karakter")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(40)
        card_layout.addWidget(self.password_input)

        cp_lbl = QLabel("Konfirmasi Kata Sandi")
        cp_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155; border: none;")
        card_layout.addWidget(cp_lbl)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Ulangi kata sandi Anda")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setMinimumHeight(40)
        card_layout.addWidget(self.confirm_password_input)

        # Message Label
        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setVisible(False)
        card_layout.addWidget(self.message_label)

        # Action Buttons
        self.register_button = QPushButton("Buat Akun")
        self.register_button.setMinimumHeight(42)
        self.register_button.setStyleSheet(
            "QPushButton { background-color: #059669; color: white; border: none; "
            "font-weight: 600; border-radius: 6px; font-size: 13px; }"
            "QPushButton:hover { background-color: #047857; }"
            "QPushButton:pressed { background-color: #065F46; }"
        )
        self.register_button.clicked.connect(self._handle_register)
        card_layout.addWidget(self.register_button)

        self.back_button = QPushButton("Sudah memiliki akun? Masuk")
        self.back_button.setStyleSheet(
            "QPushButton { background: transparent; color: #4F46E5; font-size: 12px; font-weight: 500; border: none; }"
            "QPushButton:hover { text-decoration: underline; color: #3730A3; }"
        )
        self.back_button.clicked.connect(self._handle_back)
        card_layout.addWidget(self.back_button)

        layout.addWidget(card)

    def _handle_register(self):
        username = self.username_input.text()
        password = self.password_input.text()
        confirm = self.confirm_password_input.text()
        self.register_requested.emit(username, password, confirm)

    def _handle_back(self):
        self.reset_fields()
        self.switch_to_login_requested.emit()

    def show_error(self, message: str):
        self.message_label.setText(message)
        self.message_label.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: 500;")
        self.message_label.setVisible(True)

    def show_success(self, message: str):
        self.message_label.setText(message)
        self.message_label.setStyleSheet("color: #059669; font-size: 12px; font-weight: 500;")
        self.message_label.setVisible(True)

    def reset_fields(self):
        self.username_input.clear()
        self.password_input.clear()
        self.confirm_password_input.clear()
        self.message_label.setVisible(False)

