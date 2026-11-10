"""Dialog for USB flashdisk selection and token enrollment."""

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QFrame,
)
from cryptosafe.auth.usb_token_service import UsbDriveInfo, UsbTokenService


class UsbEnrollDialog(QDialog):
    """Dialog allowing user to choose a target flashdisk/drive and verify password to enroll USB."""

    def __init__(self, usb_service: UsbTokenService, username: str, parent=None):
        super().__init__(parent)
        self._usb_service = usb_service
        self._username = username
        self.selected_path: Path | None = None
        self.confirmed_password: str = ""
        self._setup_ui()
        self._refresh_drives()

    def _setup_ui(self):
        self.setWindowTitle("Registrasi USB Dongle (Flashdisk)")
        self.resize(520, 390)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title_lbl = QLabel("Pilih Media USB / Flashdisk")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E293B;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(
            "Pilih drive flashdisk yang akan dijadikan USB Dongle untuk akun Anda.\n"
            "CryptoSafe akan menyimpan file token di folder '.cryptosafe/token.dat'.\n"
            "Flashdisk TIDAK akan diformat dan file lain di dalamnya tidak akan terganggu."
        )
        desc_lbl.setStyleSheet("font-size: 12px; color: #475569;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        # Drive selection row
        drive_box = QVBoxLayout()
        drive_box.addWidget(QLabel("Daftar Flashdisk / Drive Terdeteksi:"))

        drive_row = QHBoxLayout()
        self.drive_combo = QComboBox()
        self.drive_combo.setMinimumHeight(32)
        drive_row.addWidget(self.drive_combo, stretch=1)

        self.btn_refresh = QPushButton("Pindai Ulang")
        self.btn_refresh.setToolTip("Pindai ulang drive setelah memasang flashdisk")
        self.btn_refresh.clicked.connect(self._refresh_drives)
        drive_row.addWidget(self.btn_refresh)

        self.btn_browse = QPushButton("Pilih Folder Lain...")
        self.btn_browse.clicked.connect(self._browse_custom_folder)
        drive_row.addWidget(self.btn_browse)

        drive_box.addLayout(drive_row)
        layout.addLayout(drive_box)

        # Password confirmation for security
        pwd_box = QVBoxLayout()
        pwd_box.addWidget(QLabel("Konfirmasi Kata Sandi Akun:"))
        self.pwd_input = QLineEdit()
        self.pwd_input.setPlaceholderText("Masukkan kata sandi akun untuk otorisasi pendaftaran")
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setMinimumHeight(32)
        pwd_box.addWidget(self.pwd_input)
        layout.addLayout(pwd_box)

        # Security disclaimer notice box
        notice_frame = QFrame()
        notice_frame.setStyleSheet(
            "background-color: #FFFBEB; border: 1px solid #F59E0B; border-radius: 6px; padding: 10px;"
        )
        notice_layout = QVBoxLayout(notice_frame)
        notice_layout.setContentsMargins(6, 6, 6, 6)
        notice_lbl = QLabel(
            "⚠️ Catatan Keamanan:\n"
            "Flashdisk biasa tidak memiliki hardware anti-tamper. "
            "Secret token dapat disalin jika flashdisk dipinjamkan atau dikloning secara fisik. "
            "Gunakan flashdisk pribadi dan simpan dengan aman."
        )
        notice_lbl.setStyleSheet("color: #92400E; font-size: 11px;")
        notice_lbl.setWordWrap(True)
        notice_layout.addWidget(notice_lbl)
        layout.addWidget(notice_frame)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Batal")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.enroll_btn = QPushButton("Daftarkan USB Dongle")
        self.enroll_btn.setStyleSheet(
            "background-color: #059669; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px;"
        )
        self.enroll_btn.clicked.connect(self._on_submit)
        btn_layout.addWidget(self.enroll_btn)

        layout.addLayout(btn_layout)

    def _refresh_drives(self):
        self.drive_combo.clear()
        drives = self._usb_service.get_available_drives()
        if not drives:
            self.drive_combo.addItem("Tidak ada drive yang terdeteksi (Gunakan 'Pilih Folder Lain...')", None)
            return

        for d in drives:
            removable_tag = "[Flashdisk / USB]" if d.is_removable else f"[{d.drive_type}]"
            token_tag = " (Memiliki Token)" if d.has_token else ""
            display_text = f"{d.root_path} — {d.label} {removable_tag}{token_tag}"
            self.drive_combo.addItem(display_text, d.root_path)

    def _browse_custom_folder(self):
        chosen = QFileDialog.getExistingDirectory(self, "Pilih Drive atau Direktori Flashdisk")
        if chosen:
            p = Path(chosen).resolve()
            display_text = f"{p} (Kustom / Manual)"
            self.drive_combo.insertItem(0, display_text, p)
            self.drive_combo.setCurrentIndex(0)

    def _on_submit(self):
        target = self.drive_combo.currentData()
        if target is None:
            QMessageBox.warning(self, "Peringatan", "Pilih drive atau folder flashdisk yang valid.")
            return

        pwd = self.pwd_input.text()
        if not pwd:
            QMessageBox.warning(self, "Peringatan", "Masukkan kata sandi akun Anda untuk konfirmasi.")
            return

        self.selected_path = Path(target)
        self.confirmed_password = pwd
        self.accept()

