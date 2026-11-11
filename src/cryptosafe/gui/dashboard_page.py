"""Dashboard page prototype with feature cards (M1)."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
)

class DashboardPage(QWidget):
    """Dashboard Page with feature cards and USB/Face MFA management."""

    logout_requested = Signal()
    enroll_usb_requested = Signal()
    revoke_usb_requested = Signal()
    enroll_face_requested = Signal()
    revoke_face_requested = Signal()
    open_text_crypto_requested = Signal()
    open_file_crypto_requested = Signal()
    open_contract_requested = Signal()
    open_steganography_requested = Signal()
    open_audit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = ""
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Header bar
        header_layout = QHBoxLayout()
        
        title_box = QVBoxLayout()
        self.title_label = QLabel("CRYPTOSAFE — Dashboard")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        title_box.addWidget(self.title_label)

        self.user_label = QLabel("Pengguna Aktif: Tamu (Sesi Simulasi)")
        self.user_label.setStyleSheet("color: #4B5563; font-size: 13px;")
        title_box.addWidget(self.user_label)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Contract Management button
        self.btn_open_contract = QPushButton("Manajemen Kontrak")
        self.btn_open_contract.setStyleSheet(
            "background-color: #0D9488; color: white; padding: 6px 14px; "
            "font-weight: bold; border-radius: 4px; font-size: 12px;"
        )
        self.btn_open_contract.clicked.connect(self.open_contract_requested.emit)
        self.contract_button = self.btn_open_contract
        self.contract_management_button = self.btn_open_contract
        self.btn_contract = self.btn_open_contract
        header_layout.addWidget(self.btn_open_contract)

        # Demo Mode Badge
        demo_badge = QLabel("PROTOTYPE DEMO")
        demo_badge.setStyleSheet(
            "background-color: #FEF3C7; color: #92400E; border: 1px solid #F59E0B; "
            "padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 11px;"
        )
        header_layout.addWidget(demo_badge)

        # Logout button
        self.logout_button = QPushButton("Logout")
        self.logout_button.setStyleSheet(
            "background-color: #EF4444; color: white; padding: 6px 16px; "
            "font-weight: bold; border-radius: 4px; font-size: 12px;"
        )
        self.logout_button.clicked.connect(self._handle_logout)
        header_layout.addWidget(self.logout_button)

        main_layout.addLayout(header_layout)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # Features grid inside scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(16)

        features = [
            (
                "Super-Enkripsi Teks",
                "Kombinasi Vigenère cipher edukatif dan enkripsi modern AES-256-GCM.",
                "Milestone M6 — Aktif"
            ),
            (
                "Enkripsi Berkas",
                "Enkripsi berkas biner/teks dengan ChaCha20-Poly1305 dan envelope ber-versi.",
                "Milestone M7 — Aktif"
            ),
            (
                "Penyimpanan Database Terenkripsi",
                "Penyimpanan data kontrak dan catatan sensitif terenkripsi AES-256-GCM ke SQLite.",
                "Aktif"
            ),
            (
                "Steganografi Gambar",
                "Penyisipan payload terenkripsi AES-GCM ke citra PNG via LSB.",
                "Milestone M9 — Aktif"
            ),
            (
                "Verifikasi Integritas Aset",
                "Ledger lokal hash chain berbasis SHA-256 untuk mendeteksi perubahan aset.",
                "Milestone M10 — Aktif"
            ),
        ]

        for idx, (title, desc, status) in enumerate(features):
            row = idx // 2
            col = idx % 2
            card = self._create_feature_card(title, desc, status)
            grid.addWidget(card, row, col)

        # Dedicated M3 USB Credential Card
        mfa_card = self._create_mfa_card()
        grid.addWidget(mfa_card, 2, 1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_mfa_card(self) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 12px; }"
        )
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        title_lbl = QLabel("Manajemen Kredensial MFA (M5)")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #1E293B;")
        layout.addWidget(title_lbl)

        # USB section
        self.usb_token_status_label = QLabel("Status Token USB: Belum Terdaftar")
        self.usb_token_status_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #B45309;")
        layout.addWidget(self.usb_token_status_label)

        usb_btn_layout = QHBoxLayout()
        self.enroll_usb_btn = QPushButton("Enroll USB")
        self.enroll_usb_btn.setStyleSheet(
            "background-color: #059669; color: white; padding: 5px; border-radius: 4px; font-weight: bold; font-size: 11px;"
        )
        self.enroll_usb_btn.clicked.connect(self.enroll_usb_requested.emit)
        usb_btn_layout.addWidget(self.enroll_usb_btn)

        self.revoke_usb_btn = QPushButton("Revoke USB")
        self.revoke_usb_btn.setStyleSheet(
            "background-color: #DC2626; color: white; padding: 5px; border-radius: 4px; font-weight: bold; font-size: 11px;"
        )
        self.revoke_usb_btn.clicked.connect(self.revoke_usb_requested.emit)
        self.revoke_usb_btn.setEnabled(False)
        usb_btn_layout.addWidget(self.revoke_usb_btn)
        layout.addLayout(usb_btn_layout)

        # Face section
        self.face_status_label = QLabel("Status Wajah: Belum Terdaftar")
        self.face_status_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #B45309;")
        layout.addWidget(self.face_status_label)

        face_btn_layout = QHBoxLayout()
        self.enroll_face_btn = QPushButton("Enroll Wajah")
        self.enroll_face_btn.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 5px; border-radius: 4px; font-weight: bold; font-size: 11px;"
        )
        self.enroll_face_btn.clicked.connect(self.enroll_face_requested.emit)
        face_btn_layout.addWidget(self.enroll_face_btn)

        self.revoke_face_btn = QPushButton("Revoke Wajah")
        self.revoke_face_btn.setStyleSheet(
            "background-color: #DC2626; color: white; padding: 5px; border-radius: 4px; font-weight: bold; font-size: 11px;"
        )
        self.revoke_face_btn.clicked.connect(self.revoke_face_requested.emit)
        self.revoke_face_btn.setEnabled(False)
        face_btn_layout.addWidget(self.revoke_face_btn)
        layout.addLayout(face_btn_layout)

        return card

    def set_usb_token_status(self, is_enrolled: bool, info: str = ""):
        """Update USB token registration status."""
        if is_enrolled:
            self.usb_token_status_label.setText(f"Status Token: Terdaftar ({info or 'Aktif'})")
            self.usb_token_status_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #059669;")
            self.enroll_usb_btn.setText("Ganti Token (Re-enroll)")
            self.revoke_usb_btn.setEnabled(True)
        else:
            self.usb_token_status_label.setText("Status Token: Belum Terdaftar")
            self.usb_token_status_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #B45309;")
            self.enroll_usb_btn.setText("Enroll USB")
            self.revoke_usb_btn.setEnabled(False)

    def set_face_profile_status(self, is_enrolled: bool, info: str = ""):
        """Update Face biometric registration status."""
        if is_enrolled:
            self.face_status_label.setText(f"Status Wajah: Terdaftar ({info or 'Aktif'})")
            self.face_status_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #059669;")
            self.enroll_face_btn.setText("Pindai Ulang Wajah")
            self.revoke_face_btn.setEnabled(True)
        else:
            self.face_status_label.setText("Status Wajah: Belum Terdaftar")
            self.face_status_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #B45309;")
            self.enroll_face_btn.setText("Enroll Wajah")
            self.revoke_face_btn.setEnabled(False)

    def _create_feature_card(self, title: str, description: str, status: str) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 12px; }"
        )
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #1E293B;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(desc_lbl)

        layout.addStretch()

        if title == "Super-Enkripsi Teks":
            self.btn_open_text_crypto = QPushButton("Buka Super-Enkripsi Teks →")
            self.btn_open_text_crypto.setStyleSheet(
                "background-color: #2563EB; color: white; padding: 6px; border-radius: 4px; font-weight: bold; font-size: 11px;"
            )
            self.btn_open_text_crypto.clicked.connect(self.open_text_crypto_requested.emit)
            layout.addWidget(self.btn_open_text_crypto)

            status_lbl = QLabel(f"Status: {status}")
            status_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #059669;")
            layout.addWidget(status_lbl)
        elif title == "Enkripsi Berkas":
            self.btn_open_file_crypto = QPushButton("Buka Enkripsi Berkas →")
            self.btn_open_file_crypto.setStyleSheet(
                "background-color: #2563EB; color: white; padding: 6px; border-radius: 4px; font-weight: bold; font-size: 11px;"
            )
            self.btn_open_file_crypto.clicked.connect(self.open_file_crypto_requested.emit)
            layout.addWidget(self.btn_open_file_crypto)

            status_lbl = QLabel(f"Status: {status}")
            status_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #059669;")
            layout.addWidget(status_lbl)
        elif title == "Steganografi Gambar":
            self.btn_open_steganography = QPushButton("Buka Steganografi Gambar →")
            self.btn_open_steganography.setStyleSheet(
                "background-color: #2563EB; color: white; padding: 6px; border-radius: 4px; font-weight: bold; font-size: 11px;"
            )
            self.btn_open_steganography.clicked.connect(self.open_steganography_requested.emit)
            layout.addWidget(self.btn_open_steganography)

            status_lbl = QLabel(f"Status: {status}")
            status_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #059669;")
            layout.addWidget(status_lbl)
        elif title in ("Penyimpanan Database Terenkripsi", "Manajemen Kontrak"):
            self.btn_open_contract_card = QPushButton("Buka Manajemen Kontrak →")
            self.btn_open_contract_card.setStyleSheet(
                "background-color: #0D9488; color: white; padding: 6px; border-radius: 4px; font-weight: bold; font-size: 11px;"
            )
            self.btn_open_contract_card.clicked.connect(self.open_contract_requested.emit)
            layout.addWidget(self.btn_open_contract_card)

            status_lbl = QLabel(f"Status: {status}")
            status_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #059669;")
            layout.addWidget(status_lbl)
        elif title == "Verifikasi Integritas Aset":
            self.btn_open_audit = QPushButton("Buka Audit Blockchain →")
            self.btn_open_audit.setStyleSheet(
                "background-color: #4F46E5; color: white; padding: 6px; border-radius: 4px; font-weight: bold; font-size: 11px;"
            )
            self.btn_open_audit.clicked.connect(self.open_audit_requested.emit)
            layout.addWidget(self.btn_open_audit)

            status_lbl = QLabel(f"Status: {status}")
            status_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #059669;")
            layout.addWidget(status_lbl)
        else:
            status_lbl = QLabel(f"Status: {status}")
            status_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569;")
            layout.addWidget(status_lbl)

        return card

    def set_user(self, username: str):
        """Update dashboard for the authenticated user session."""
        self.username = username
        self.user_label.setText(f"Pengguna Aktif: {username} (Sesi Simulasi DEMO)")

    def _handle_logout(self):
        self.username = ""
        self.user_label.setText("Pengguna Aktif: Tamu (Sesi Simulasi)")
        self.logout_requested.emit()

