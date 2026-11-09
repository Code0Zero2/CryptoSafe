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
        card.setMaximumWidth(460)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(14)

        title = QLabel("CRYPTOSAFE")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; letter-spacing: 1px;")
        card_layout.addWidget(title)

        subtitle = QLabel("Pendaftaran Akun Baru")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #64748B; font-size: 13px; font-weight: 500;")
        card_layout.addWidget(subtitle)

        # Inputs
        card_layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Masukkan username (3-32 karakter)")
        card_layout.addWidget(self.username_input)

        card_layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Minimal 6 karakter")
        self.password_input.setEchoMode(QLineEdit.Password)
        card_layout.addWidget(self.password_input)

        card_layout.addWidget(QLabel("Konfirmasi Password:"))
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Ulangi password")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        card_layout.addWidget(self.confirm_password_input)

        # Message Label
        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setVisible(False)
        card_layout.addWidget(self.message_label)

        # Action Buttons
        self.register_button = QPushButton("Daftar Akun")
        self.register_button.setStyleSheet(
            "background-color: #10B981; color: white; padding: 10px; "
            "font-weight: bold; border-radius: 4px; font-size: 13px;"
        )
        self.register_button.clicked.connect(self._handle_register)
        card_layout.addWidget(self.register_button)

        self.back_button = QPushButton("Sudah punya akun? Masuk")
        self.back_button.setStyleSheet(
            "background: transparent; color: #2563EB; font-size: 12px; text-decoration: underline; border: none;"
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
