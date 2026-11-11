"""User registration page with integrated USB Token and Face ID biometric enrollment."""

from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QComboBox,
    QFileDialog,
    QScrollArea,
    QDialog,
)
from cryptosafe.gui.face_capture_dialog import FaceCaptureDialog


class RegisterPage(QWidget):
    """User registration page with integrated USB token and Face ID setup."""

    register_requested = Signal(str, str, str)  # username, password, confirm_password
    switch_to_login_requested = Signal()

    def __init__(self, parent=None, usb_service=None, face_service=None):
        super().__init__(parent)
        self._usb_service = usb_service
        self._face_service = face_service
        self.selected_usb_path: Path | None = None
        self.captured_face_frame = None
        self._setup_ui()

    def set_services(self, usb_service=None, face_service=None):
        """Update reference to USB and Face services."""
        if usb_service is not None:
            self._usb_service = usb_service
            self._refresh_usb_drives()
        if face_service is not None:
            self._face_service = face_service

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setContentsMargins(16, 16, 16, 16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setAlignment(Qt.AlignCenter)
        c_layout.setContentsMargins(0, 8, 0, 8)

        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setMaximumWidth(480)
        card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; }"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(14)

        # Header
        title = QLabel("CryptoSafe")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 26px; font-weight: 800; color: #0F172A; letter-spacing: -0.5px; border: none;"
        )
        card_layout.addWidget(title)

        subtitle = QLabel("Pendaftaran Akun Baru & Kredensial Keamanan")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500; border: none;")
        card_layout.addWidget(subtitle)

        # --- Section 1: Basic Credentials ---
        user_lbl = QLabel("Nama Pengguna")
        user_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155; border: none;")
        card_layout.addWidget(user_lbl)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Pilih username (3-32 karakter)")
        self.username_input.setMinimumHeight(38)
        card_layout.addWidget(self.username_input)

        pass_lbl = QLabel("Kata Sandi")
        pass_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155; border: none;")
        card_layout.addWidget(pass_lbl)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Minimal 6 karakter")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(38)
        card_layout.addWidget(self.password_input)

        cpass_lbl = QLabel("Konfirmasi Kata Sandi")
        cpass_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155; border: none;")
        card_layout.addWidget(cpass_lbl)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Ulangi kata sandi Anda")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setMinimumHeight(38)
        card_layout.addWidget(self.confirm_password_input)

        # Helper button styles
        btn_action_style = (
            "QPushButton {"
            "   background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1;"
            "   padding: 6px 12px; font-weight: 600; border-radius: 5px; font-size: 11px;"
            "}"
            "QPushButton:hover { background-color: #E2E8F0; }"
        )

        # --- Section 2: USB Device Token Setup ---
        usb_card = QFrame()
        usb_card.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; }"
        )
        usb_layout = QVBoxLayout(usb_card)
        usb_layout.setSpacing(6)
        usb_layout.setContentsMargins(10, 8, 10, 8)

        usb_title = QLabel("Token Perangkat USB (Kunci Fisik 2FA)")
        usb_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #0F172A; border: none;")
        usb_layout.addWidget(usb_title)

        self.usb_status_label = QLabel("USB Token: Belum dipilih (Opsional)")
        self.usb_status_label.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500; border: none;")
        usb_layout.addWidget(self.usb_status_label)

        self.usb_drive_combo = QComboBox()
        self.usb_drive_combo.setMinimumHeight(30)
        self.usb_drive_combo.currentIndexChanged.connect(self._on_drive_combo_changed)
        usb_layout.addWidget(self.usb_drive_combo)

        usb_btn_row = QHBoxLayout()
        self.btn_refresh_usb = QPushButton("Pindai Drive")
        self.btn_refresh_usb.setStyleSheet(btn_action_style)
        self.btn_refresh_usb.clicked.connect(self._refresh_usb_drives)
        usb_btn_row.addWidget(self.btn_refresh_usb)

        self.btn_browse_usb = QPushButton("Pilih Folder Lain...")
        self.btn_browse_usb.setStyleSheet(btn_action_style)
        self.btn_browse_usb.clicked.connect(self._browse_custom_folder)
        usb_btn_row.addWidget(self.btn_browse_usb)

        self.btn_clear_usb = QPushButton("Hapus")
        self.btn_clear_usb.setStyleSheet(
            "QPushButton {"
            "   background-color: #FFFFFF; color: #DC2626; border: 1px solid #FECACA;"
            "   padding: 6px 10px; font-weight: 600; border-radius: 5px; font-size: 11px;"
            "}"
            "QPushButton:hover { background-color: #FEF2F2; }"
        )
        self.btn_clear_usb.clicked.connect(self._clear_usb)
        usb_btn_row.addWidget(self.btn_clear_usb)
        usb_layout.addLayout(usb_btn_row)

        card_layout.addWidget(usb_card)

        # --- Section 3: Face ID Biometric Setup ---
        face_card = QFrame()
        face_card.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; }"
        )
        face_layout = QVBoxLayout(face_card)
        face_layout.setSpacing(6)
        face_layout.setContentsMargins(10, 8, 10, 8)

        face_title = QLabel("Biometrik Wajah (Face ID 2FA)")
        face_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #0F172A; border: none;")
        face_layout.addWidget(face_title)

        self.face_status_label = QLabel("Face ID: Belum dipindai (Opsional)")
        self.face_status_label.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500; border: none;")
        face_layout.addWidget(self.face_status_label)

        face_btn_row = QHBoxLayout()
        self.btn_scan_face = QPushButton("Buka Kamera & Pindai Wajah")
        self.btn_scan_face.setStyleSheet(
            "QPushButton {"
            "   background-color: #2563EB; color: white; border: none;"
            "   padding: 7px 14px; font-weight: 600; border-radius: 5px; font-size: 11px;"
            "}"
            "QPushButton:hover { background-color: #1D4ED8; }"
        )
        self.btn_scan_face.clicked.connect(self._scan_face)
        face_btn_row.addWidget(self.btn_scan_face)

        self.btn_clear_face = QPushButton("Hapus")
        self.btn_clear_face.setStyleSheet(
            "QPushButton {"
            "   background-color: #FFFFFF; color: #DC2626; border: 1px solid #FECACA;"
            "   padding: 6px 10px; font-weight: 600; border-radius: 5px; font-size: 11px;"
            "}"
            "QPushButton:hover { background-color: #FEF2F2; }"
        )
        self.btn_clear_face.clicked.connect(self._clear_face)
        self.btn_clear_face.setEnabled(False)
        face_btn_row.addWidget(self.btn_clear_face)
        face_layout.addLayout(face_btn_row)

        card_layout.addWidget(face_card)

        # Message Label
        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setVisible(False)
        card_layout.addWidget(self.message_label)

        # Action Buttons
        self.register_button = QPushButton("Buat Akun & Daftarkan Kredensial")
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

        c_layout.addWidget(card)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self._refresh_usb_drives()

    def _refresh_usb_drives(self):
        """Scan available removable drives and populate dropdown."""
        self.usb_drive_combo.blockSignals(True)
        self.usb_drive_combo.clear()
        self.usb_drive_combo.addItem("— Lewati / Tanpa USB Token —", userData=None)

        if self._usb_service:
            try:
                drives = self._usb_service.get_available_drives()
                for d in drives:
                    label = f"{d.label} ({d.root_path})"
                    self.usb_drive_combo.addItem(label, userData=d.root_path)
            except Exception:
                pass

        # If a custom path was previously selected and is not in combo, add it
        if self.selected_usb_path:
            found = False
            for i in range(self.usb_drive_combo.count()):
                if self.usb_drive_combo.itemData(i) == self.selected_usb_path:
                    self.usb_drive_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self.usb_drive_combo.addItem(f"Kustom: {self.selected_usb_path.name}", userData=self.selected_usb_path)
                self.usb_drive_combo.setCurrentIndex(self.usb_drive_combo.count() - 1)
        else:
            self.usb_drive_combo.setCurrentIndex(0)

        self.usb_drive_combo.blockSignals(False)

    def _on_drive_combo_changed(self, index: int):
        path = self.usb_drive_combo.itemData(index)
        if path:
            self.selected_usb_path = Path(path)
            self.usb_status_label.setText(f"✓ USB Terpilih: {self.selected_usb_path.name}")
            self.usb_status_label.setStyleSheet("color: #059669; font-size: 11px; font-weight: 600; border: none;")
        else:
            self.selected_usb_path = None
            self.usb_status_label.setText("USB Token: Belum dipilih (Opsional)")
            self.usb_status_label.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500; border: none;")

    def _browse_custom_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Drive / Folder Flashdisk USB")
        if folder:
            path = Path(folder)
            self.selected_usb_path = path
            self.usb_status_label.setText(f"✓ USB Terpilih: {path.name}")
            self.usb_status_label.setStyleSheet("color: #059669; font-size: 11px; font-weight: 600; border: none;")
            self._refresh_usb_drives()

    def _clear_usb(self):
        self.selected_usb_path = None
        self.usb_status_label.setText("USB Token: Belum dipilih (Opsional)")
        self.usb_status_label.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500; border: none;")
        self.usb_drive_combo.setCurrentIndex(0)

    def _scan_face(self):
        if not self._face_service:
            self.show_error("Layanan biometrik wajah tidak tersedia.")
            return

        dialog = FaceCaptureDialog(self._face_service, mode="enroll", parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.captured_frame is not None:
            self.captured_face_frame = dialog.captured_frame
            self.face_status_label.setText("✓ Biometrik Wajah Berhasil Diambil")
            self.face_status_label.setStyleSheet("color: #059669; font-size: 11px; font-weight: 600; border: none;")
            self.btn_clear_face.setEnabled(True)

    def _clear_face(self):
        self.captured_face_frame = None
        self.face_status_label.setText("Face ID: Belum dipindai (Opsional)")
        self.face_status_label.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500; border: none;")
        self.btn_clear_face.setEnabled(False)

    def _handle_register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_password_input.text()
        self.register_requested.emit(username, password, confirm)

    def _handle_back(self):
        self.reset_fields()
        self.switch_to_login_requested.emit()

    def show_error(self, message: str):
        self.message_label.setText(message)
        self.message_label.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: 500; border: none;")
        self.message_label.setVisible(True)

    def show_success(self, message: str):
        self.message_label.setText(message)
        self.message_label.setStyleSheet("color: #059669; font-size: 12px; font-weight: 500; border: none;")
        self.message_label.setVisible(True)

    def reset_fields(self):
        self.username_input.clear()
        self.password_input.clear()
        self.confirm_password_input.clear()
        self.message_label.setVisible(False)
        self._clear_usb()
        self._clear_face()
