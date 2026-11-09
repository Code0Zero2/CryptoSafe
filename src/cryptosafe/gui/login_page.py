"""Login page prototype with visible simulation markers (M1)."""

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
    """Prototype Login Page with explicit DEMO labelling."""

    login_requested = Signal(str)

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
        card.setMaximumWidth(460)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(14)

        # Title & Subtitle
        title = QLabel("CRYPTOSAFE")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; letter-spacing: 1px;")
        card_layout.addWidget(title)

        subtitle = QLabel("Multi-Factor Cryptographic Demonstrator")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        card_layout.addWidget(subtitle)

        # Prominent Demo Banner
        demo_banner = QLabel("STATUS: M1 GUI PROTOTYPE (SIMULASI)\nAutentikasi riil belum aktif.")
        demo_banner.setAlignment(Qt.AlignCenter)
        demo_banner.setStyleSheet(
            "background-color: #FEF3C7; color: #92400E; border: 1px solid #F59E0B; "
            "padding: 8px; border-radius: 4px; font-weight: 600; font-size: 11px;"
        )
        card_layout.addWidget(demo_banner)

        # Input fields
        card_layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Masukkan username")
        card_layout.addWidget(self.username_input)

        card_layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Masukkan password")
        self.password_input.setEchoMode(QLineEdit.Password)
        card_layout.addWidget(self.password_input)

        # Simulated Factors Status Box
        factors_box = QGroupBox("Status Faktor Autentikasi Tambahan (Simulasi M1)")
        factors_layout = QVBoxLayout(factors_box)
        factors_layout.setSpacing(6)

        self.usb_status_label = QLabel("USB Token: Belum Terpasang (SIMULASI / DEMO)")
        self.usb_status_label.setStyleSheet("color: #B45309; font-size: 11px;")
        factors_layout.addWidget(self.usb_status_label)

        self.face_status_label = QLabel("Face Recognition: Belum Diverifikasi (SIMULASI / DEMO)")
        self.face_status_label.setStyleSheet("color: #B45309; font-size: 11px;")
        factors_layout.addWidget(self.face_status_label)

        card_layout.addWidget(factors_box)

        # Error / Validation Label
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: 500;")
        self.error_label.setVisible(False)
        card_layout.addWidget(self.error_label)

        # Action Button
        self.login_button = QPushButton("Masuk (Demo)")
        self.login_button.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 10px; "
            "font-weight: bold; border-radius: 4px; font-size: 13px;"
        )
        self.login_button.clicked.connect(self._handle_login)
        card_layout.addWidget(self.login_button)

        layout.addWidget(card)

    def _handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.error_label.setText("Username dan password tidak boleh kosong.")
            self.error_label.setVisible(True)
            return

        self.error_label.setVisible(False)
        self.login_requested.emit(username)

    def reset_fields(self):
        """Reset inputs and clear errors upon logout."""
        self.username_input.clear()
        self.password_input.clear()
        self.error_label.setVisible(False)

