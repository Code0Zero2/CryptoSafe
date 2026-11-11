"""Modern enterprise Dashboard page with cryptographic services and MFA management."""

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
    """Modern enterprise Dashboard Page with quick access to cryptographic services."""

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
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(24)

        # Top Bar
        header_layout = QHBoxLayout()

        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        self.title_label = QLabel("Dashboard")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
        title_box.addWidget(self.title_label)

        self.user_label = QLabel("Pengguna: Tamu")
        self.user_label.setStyleSheet("color: #64748B; font-size: 13px; font-weight: 500;")
        title_box.addWidget(self.user_label)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Contract Management Quick Action Button
        self.btn_open_contract = QPushButton("Manajemen Kontrak")
        self.btn_open_contract.setStyleSheet(
            "QPushButton {"
            "   background-color: #0F766E; color: #FFFFFF; padding: 8px 18px;"
            "   font-weight: 600; border-radius: 6px; font-size: 12px; border: none;"
            "}"
            "QPushButton:hover {"
            "   background-color: #0D9488;"
            "}"
        )
        self.btn_open_contract.clicked.connect(self.open_contract_requested.emit)
        self.contract_button = self.btn_open_contract
        self.contract_management_button = self.btn_open_contract
        self.btn_contract = self.btn_open_contract
        header_layout.addWidget(self.btn_open_contract)

        # Logout button
        self.logout_button = QPushButton("Keluar")
        self.logout_button.setStyleSheet(
            "QPushButton {"
            "   background-color: #FFFFFF; color: #DC2626; border: 1.5px solid #FECACA;"
            "   padding: 7px 18px; font-weight: 600; border-radius: 6px; font-size: 12px;"
            "}"
            "QPushButton:hover {"
            "   background-color: #FEF2F2; border-color: #F87171;"
            "}"
        )
        self.logout_button.clicked.connect(self._handle_logout)
        header_layout.addWidget(self.logout_button)

        main_layout.addLayout(header_layout)

        # Subtle separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("border: none; border-top: 1px solid #E2E8F0;")
        main_layout.addWidget(line)

        # Features grid inside scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        grid = QGridLayout(container)
        grid.setSpacing(20)
        grid.setContentsMargins(0, 4, 0, 8)

        # Cards definition: (Key, Category Tag, Title, Description)
        feature_configs = [
            (
                "text",
                "KRIPTOGRAFI TEKS",
                "Super-Enkripsi Teks",
                "Kombinasi sandi klasik Vigenère dan cipher AEAD modern AES-256-GCM untuk keamanan data pesan rahasia bertingkat.",
            ),
            (
                "file",
                "KEAMANAN BERKAS",
                "Enkripsi Berkas Dokumen",
                "Enkripsi berkas biner dan teks performa tinggi menggunakan ChaCha20-Poly1305 dengan envelope ber-versi dan verifikasi integritas.",
            ),
            (
                "contract",
                "DATA & DOKUMEN",
                "Penyimpanan Kontrak Terenkripsi",
                "Manajemen dokumen kontrak legal, metadata rahasia, dan catatan terenkripsi AES-256-GCM ke dalam basis data SQLite terlindungi.",
            ),
            (
                "stego",
                "STEGANOGRAFI CITRA",
                "Steganografi Gambar (LSB)",
                "Penyisipan muatan rahasia terenkripsi AES-GCM ke dalam citra PNG melalui Least Significant Bit tanpa mengubah kualitas visual citra.",
            ),
            (
                "audit",
                "INTEGRITAS & AUDIT",
                "Buku Besar Audit Blockchain",
                "Rantai hash SHA-256 lokal yang merekam secara permanen (append-only) setiap mutasi kontrak, catatan terenkripsi, dan lampiran berkas.",
            ),
        ]

        for idx, (f_key, tag, title, desc) in enumerate(feature_configs):
            row = idx // 2
            col = idx % 2
            card = self._create_service_card(f_key, tag, title, desc)
            grid.addWidget(card, row, col)

        # MFA Card in grid slot (2, 1)
        mfa_card = self._create_mfa_card()
        grid.addWidget(mfa_card, 2, 1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_service_card(self, f_key: str, tag: str, title: str, description: str) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame {"
            "   background-color: #FFFFFF;"
            "   border: 1px solid #E2E8F0;"
            "   border-radius: 10px;"
            "   padding: 18px;"
            "}"
            "QFrame:hover {"
            "   border: 1px solid #CBD5E1;"
            "}"
        )
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 18)

        # Category Tag
        tag_lbl = QLabel(tag)
        tag_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #6366F1; "
            "letter-spacing: 0.5px; background: transparent;"
        )
        layout.addWidget(tag_lbl)

        # Title
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F172A; background: transparent;")
        layout.addWidget(title_lbl)

        # Description
        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 12px; color: #64748B; line-height: 1.4; background: transparent;")
        layout.addWidget(desc_lbl)

        layout.addStretch()

        # Action Button based on feature key
        btn_style_primary = (
            "QPushButton {"
            "   background-color: #4F46E5; color: #FFFFFF; padding: 8px 16px;"
            "   border-radius: 6px; font-weight: 600; font-size: 12px; border: none;"
            "}"
            "QPushButton:hover {"
            "   background-color: #4338CA;"
            "}"
        )
        btn_style_teal = (
            "QPushButton {"
            "   background-color: #0F766E; color: #FFFFFF; padding: 8px 16px;"
            "   border-radius: 6px; font-weight: 600; font-size: 12px; border: none;"
            "}"
            "QPushButton:hover {"
            "   background-color: #0D9488;"
            "}"
        )

        if f_key == "text":
            self.btn_open_text_crypto = QPushButton("Buka Super-Enkripsi Teks →")
            self.btn_open_text_crypto.setStyleSheet(btn_style_primary)
            self.btn_open_text_crypto.clicked.connect(self.open_text_crypto_requested.emit)
            layout.addWidget(self.btn_open_text_crypto)
        elif f_key == "file":
            self.btn_open_file_crypto = QPushButton("Buka Enkripsi Berkas →")
            self.btn_open_file_crypto.setStyleSheet(btn_style_primary)
            self.btn_open_file_crypto.clicked.connect(self.open_file_crypto_requested.emit)
            layout.addWidget(self.btn_open_file_crypto)
        elif f_key == "contract":
            self.btn_open_contract_card = QPushButton("Buka Manajemen Kontrak →")
            self.btn_open_contract_card.setStyleSheet(btn_style_teal)
            self.btn_open_contract_card.clicked.connect(self.open_contract_requested.emit)
            layout.addWidget(self.btn_open_contract_card)
        elif f_key == "stego":
            self.btn_open_steganography = QPushButton("Buka Steganografi Gambar →")
            self.btn_open_steganography.setStyleSheet(btn_style_primary)
            self.btn_open_steganography.clicked.connect(self.open_steganography_requested.emit)
            layout.addWidget(self.btn_open_steganography)
        elif f_key == "audit":
            self.btn_open_audit = QPushButton("Buka Audit Blockchain →")
            self.btn_open_audit.setStyleSheet(
                "QPushButton {"
                "   background-color: #0284C7; color: #FFFFFF; padding: 8px 16px;"
                "   border-radius: 6px; font-weight: 600; font-size: 12px; border: none;"
                "}"
                "QPushButton:hover {"
                "   background-color: #0369A1;"
                "}"
            )
            self.btn_open_audit.clicked.connect(self.open_audit_requested.emit)
            layout.addWidget(self.btn_open_audit)

        return card

    def _create_mfa_card(self) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame {"
            "   background-color: #FFFFFF;"
            "   border: 1px solid #E2E8F0;"
            "   border-radius: 10px;"
            "   padding: 18px;"
            "}"
            "QFrame:hover {"
            "   border: 1px solid #CBD5E1;"
            "}"
        )
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 18)

        # Category Tag
        tag_lbl = QLabel("AUTENTIKASI & KREDENSIAL")
        tag_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #059669; "
            "letter-spacing: 0.5px; background: transparent;"
        )
        layout.addWidget(tag_lbl)

        title_lbl = QLabel("Autentikasi Multi-Faktor (MFA)")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F172A; background: transparent;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel("Kelola token perangkat USB dan biometrik wajah untuk proteksi akses akun.")
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 12px; color: #64748B; background: transparent;")
        layout.addWidget(desc_lbl)

        # USB section container
        usb_box = QFrame()
        usb_box.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px; }"
        )
        usb_layout = QVBoxLayout(usb_box)
        usb_layout.setSpacing(6)
        usb_layout.setContentsMargins(8, 8, 8, 8)

        self.usb_token_status_label = QLabel("Status Token USB: Belum Terdaftar")
        self.usb_token_status_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #D97706; border: none;")
        usb_layout.addWidget(self.usb_token_status_label)

        usb_btn_layout = QHBoxLayout()
        self.enroll_usb_btn = QPushButton("Enroll USB")
        self.enroll_usb_btn.setStyleSheet(
            "QPushButton {"
            "   background-color: #059669; color: white; padding: 6px 12px; border-radius: 5px; font-weight: 600; font-size: 11px; border: none;"
            "}"
            "QPushButton:hover {"
            "   background-color: #047857;"
            "}"
        )
        self.enroll_usb_btn.clicked.connect(self.enroll_usb_requested.emit)
        usb_btn_layout.addWidget(self.enroll_usb_btn)

        self.revoke_usb_btn = QPushButton("Revoke USB")
        self.revoke_usb_btn.setStyleSheet(
            "QPushButton {"
            "   background-color: #F1F5F9; color: #DC2626; border: 1px solid #FECACA; padding: 6px 12px; border-radius: 5px; font-weight: 600; font-size: 11px;"
            "}"
            "QPushButton:hover {"
            "   background-color: #FEF2F2;"
            "}"
            "QPushButton:disabled {"
            "   background-color: #F8FAFC; color: #CBD5E1; border-color: #E2E8F0;"
            "}"
        )
        self.revoke_usb_btn.clicked.connect(self.revoke_usb_requested.emit)
        self.revoke_usb_btn.setEnabled(False)
        usb_btn_layout.addWidget(self.revoke_usb_btn)
        usb_layout.addLayout(usb_btn_layout)
        layout.addWidget(usb_box)

        # Face section container
        face_box = QFrame()
        face_box.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px; }"
        )
        face_layout = QVBoxLayout(face_box)
        face_layout.setSpacing(6)
        face_layout.setContentsMargins(8, 8, 8, 8)

        self.face_status_label = QLabel("Status Wajah: Belum Terdaftar")
        self.face_status_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #D97706; border: none;")
        face_layout.addWidget(self.face_status_label)

        face_btn_layout = QHBoxLayout()
        self.enroll_face_btn = QPushButton("Enroll Wajah")
        self.enroll_face_btn.setStyleSheet(
            "QPushButton {"
            "   background-color: #2563EB; color: white; padding: 6px 12px; border-radius: 5px; font-weight: 600; font-size: 11px; border: none;"
            "}"
            "QPushButton:hover {"
            "   background-color: #1D4ED8;"
            "}"
        )
        self.enroll_face_btn.clicked.connect(self.enroll_face_requested.emit)
        face_btn_layout.addWidget(self.enroll_face_btn)

        self.revoke_face_btn = QPushButton("Revoke Wajah")
        self.revoke_face_btn.setStyleSheet(
            "QPushButton {"
            "   background-color: #F1F5F9; color: #DC2626; border: 1px solid #FECACA; padding: 6px 12px; border-radius: 5px; font-weight: 600; font-size: 11px;"
            "}"
            "QPushButton:hover {"
            "   background-color: #FEF2F2;"
            "}"
            "QPushButton:disabled {"
            "   background-color: #F8FAFC; color: #CBD5E1; border-color: #E2E8F0;"
            "}"
        )
        self.revoke_face_btn.clicked.connect(self.revoke_face_requested.emit)
        self.revoke_face_btn.setEnabled(False)
        face_btn_layout.addWidget(self.revoke_face_btn)
        face_layout.addLayout(face_btn_layout)
        layout.addWidget(face_box)

        return card

    def set_usb_token_status(self, is_enrolled: bool, info: str = ""):
        """Update USB token registration status."""
        if is_enrolled:
            self.usb_token_status_label.setText(f"Status Token: Terdaftar ({info or 'Aktif'})")
            self.usb_token_status_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #059669; border: none;")
            self.enroll_usb_btn.setText("Ganti Token (Re-enroll)")
            self.revoke_usb_btn.setEnabled(True)
        else:
            self.usb_token_status_label.setText("Status Token: Belum Terdaftar")
            self.usb_token_status_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #D97706; border: none;")
            self.enroll_usb_btn.setText("Enroll USB")
            self.revoke_usb_btn.setEnabled(False)

    def set_face_profile_status(self, is_enrolled: bool, info: str = ""):
        """Update Face biometric registration status."""
        if is_enrolled:
            self.face_status_label.setText(f"Status Wajah: Terdaftar ({info or 'Aktif'})")
            self.face_status_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #059669; border: none;")
            self.enroll_face_btn.setText("Pindai Ulang Wajah")
            self.revoke_face_btn.setEnabled(True)
        else:
            self.face_status_label.setText("Status Wajah: Belum Terdaftar")
            self.face_status_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #D97706; border: none;")
            self.enroll_face_btn.setText("Enroll Wajah")
            self.revoke_face_btn.setEnabled(False)

    def set_user(self, username: str):
        """Update dashboard for the authenticated user session."""
        self.username = username
        if username:
            self.user_label.setText(f"Pengguna: {username}")
        else:
            self.user_label.setText("Pengguna: Tamu")

    def _handle_logout(self):
        self.username = ""
        self.user_label.setText("Pengguna: Tamu")
        self.logout_requested.emit()
