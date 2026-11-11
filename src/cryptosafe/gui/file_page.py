"""GUI page for File Encryption and Decryption (ChaCha20-Poly1305)."""

from pathlib import Path
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QFileDialog,
)
from cryptosafe.common.errors import CryptoSafeError
from cryptosafe.crypto.file_crypto_service import FileCryptoService
from cryptosafe.crypto.key_manager import generate_random_aes_key


class FilePage(QWidget):
    """Page hosting File Encryption and Decryption using ChaCha20-Poly1305."""

    back_to_dashboard_requested = Signal()

    def __init__(self, file_crypto_service: FileCryptoService | None = None, parent=None):
        super().__init__(parent)
        self._crypto_service = file_crypto_service or FileCryptoService()
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(18)

        # Header bar
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title_lbl = QLabel("Enkripsi Berkas Dokumen")
        title_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
        title_box.addWidget(title_lbl)

        desc_lbl = QLabel(
            "Proteksi berkas biner dan teks performa tinggi menggunakan ChaCha20-Poly1305 dengan integritas terverifikasi."
        )
        desc_lbl.setStyleSheet("font-size: 13px; color: #64748B; font-weight: 500;")
        title_box.addWidget(desc_lbl)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        self.back_button = QPushButton("← Kembali ke Dashboard")
        self.back_button.setStyleSheet(
            "QPushButton {"
            "   background-color: #FFFFFF; color: #475569; border: 1.5px solid #CBD5E1;"
            "   padding: 7px 16px; font-weight: 600; border-radius: 6px; font-size: 12px;"
            "}"
            "QPushButton:hover {"
            "   background-color: #F1F5F9; color: #0F172A;"
            "}"
        )
        self.back_button.clicked.connect(self.back_to_dashboard_requested.emit)
        header_layout.addWidget(self.back_button)

        main_layout.addLayout(header_layout)

        # Message Banner
        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setVisible(False)
        main_layout.addWidget(self.message_label)

        # Tabs for Encrypt and Decrypt
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_encrypt_tab(), "Enkripsi Berkas")
        self.tabs.addTab(self._create_decrypt_tab(), "Dekripsi Berkas")
        main_layout.addWidget(self.tabs)

    def _create_encrypt_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        btn_browse_style = (
            "QPushButton { background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; padding: 7px 14px; font-weight: 600; border-radius: 5px; font-size: 12px; } QPushButton:hover { background-color: #E2E8F0; }"
        )

        # Source File
        layout.addWidget(QLabel("1. Berkas Asli yang Ingin Dienkripsi:"))
        src_row = QHBoxLayout()
        self.enc_source_input = QLineEdit()
        self.enc_source_input.setPlaceholderText("Pilih berkas sumber...")
        src_row.addWidget(self.enc_source_input)

        self.btn_browse_enc_source = QPushButton("Pilih Berkas...")
        self.btn_browse_enc_source.setStyleSheet(btn_browse_style)
        self.btn_browse_enc_source.clicked.connect(self._browse_enc_source)
        src_row.addWidget(self.btn_browse_enc_source)
        layout.addLayout(src_row)

        # Destination File
        layout.addWidget(QLabel("2. Lokasi Simpan Berkas Terenkripsi (.enc):"))
        dst_row = QHBoxLayout()
        self.enc_dest_input = QLineEdit()
        self.enc_dest_input.setPlaceholderText("Pilih lokasi berkas terenkripsi...")
        dst_row.addWidget(self.enc_dest_input)

        self.btn_browse_enc_dest = QPushButton("Pilih Lokasi...")
        self.btn_browse_enc_dest.setStyleSheet(btn_browse_style)
        self.btn_browse_enc_dest.clicked.connect(self._browse_enc_dest)
        dst_row.addWidget(self.btn_browse_enc_dest)
        layout.addLayout(dst_row)

        # Key Input
        layout.addWidget(QLabel("3. Kunci Rahasia / Passphrase:"))
        key_row = QHBoxLayout()
        self.enc_key_input = QLineEdit()
        self.enc_key_input.setPlaceholderText("Passphrase atau 64-karakter kunci hexadesimal acak")
        key_row.addWidget(self.enc_key_input)

        self.btn_gen_key = QPushButton("Buat Kunci Acak")
        self.btn_gen_key.setStyleSheet(btn_browse_style)
        self.btn_gen_key.clicked.connect(self._generate_random_key_clicked)
        key_row.addWidget(self.btn_gen_key)
        layout.addLayout(key_row)

        # Action Button
        self.encrypt_button = QPushButton("Jalankan Enkripsi Berkas")
        self.encrypt_button.setStyleSheet(
            "QPushButton {"
            "   background-color: #4F46E5; color: white; padding: 10px; font-weight: 600; border-radius: 6px; font-size: 13px; border: none;"
            "}"
            "QPushButton:hover { background-color: #4338CA; }"
        )
        self.encrypt_button.clicked.connect(self._handle_encrypt)
        layout.addWidget(self.encrypt_button)

        layout.addStretch()
        return widget

    def _create_decrypt_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        btn_browse_style = (
            "QPushButton { background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; padding: 7px 14px; font-weight: 600; border-radius: 5px; font-size: 12px; } QPushButton:hover { background-color: #E2E8F0; }"
        )

        # Source File
        layout.addWidget(QLabel("1. Berkas Terenkripsi (.enc):"))
        src_row = QHBoxLayout()
        self.dec_source_input = QLineEdit()
        self.dec_source_input.setPlaceholderText("Pilih berkas terenkripsi...")
        src_row.addWidget(self.dec_source_input)

        self.btn_browse_dec_source = QPushButton("Pilih Berkas...")
        self.btn_browse_dec_source.setStyleSheet(btn_browse_style)
        self.btn_browse_dec_source.clicked.connect(self._browse_dec_source)
        src_row.addWidget(self.btn_browse_dec_source)
        layout.addLayout(src_row)

        # Destination File
        layout.addWidget(QLabel("2. Lokasi Simpan Berkas Pulih (Plaintext):"))
        dst_row = QHBoxLayout()
        self.dec_dest_input = QLineEdit()
        self.dec_dest_input.setPlaceholderText("Pilih lokasi berkas hasil dekripsi...")
        dst_row.addWidget(self.dec_dest_input)

        self.btn_browse_dec_dest = QPushButton("Pilih Lokasi...")
        self.btn_browse_dec_dest.setStyleSheet(btn_browse_style)
        self.btn_browse_dec_dest.clicked.connect(self._browse_dec_dest)
        dst_row.addWidget(self.btn_browse_dec_dest)
        layout.addLayout(dst_row)

        # Key Input
        layout.addWidget(QLabel("3. Kunci Rahasia / Passphrase:"))
        self.dec_key_input = QLineEdit()
        self.dec_key_input.setPlaceholderText("Masukkan kunci atau passphrase yang sama")
        layout.addWidget(self.dec_key_input)

        # Action Button
        self.decrypt_button = QPushButton("Jalankan Dekripsi Berkas")
        self.decrypt_button.setStyleSheet(
            "QPushButton {"
            "   background-color: #059669; color: white; padding: 10px; font-weight: 600; border-radius: 6px; font-size: 13px; border: none;"
            "}"
            "QPushButton:hover { background-color: #047857; }"
        )
        self.decrypt_button.clicked.connect(self._handle_decrypt)
        layout.addWidget(self.decrypt_button)
        layout.addWidget(self.decrypt_button)

        layout.addStretch()
        return widget

    def _browse_enc_source(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih Berkas Asli")
        if file_path:
            self.enc_source_input.setText(file_path)
            if not self.enc_dest_input.text():
                self.enc_dest_input.setText(f"{file_path}.enc")

    def _browse_enc_dest(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Tentukan Lokasi Berkas Terenkripsi", filter="Encrypted Files (*.enc);;All Files (*)")
        if file_path:
            self.enc_dest_input.setText(file_path)

    def _browse_dec_source(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih Berkas Terenkripsi", filter="Encrypted Files (*.enc);;All Files (*)")
        if file_path:
            self.dec_source_input.setText(file_path)
            if not self.dec_dest_input.text():
                p = Path(file_path)
                if p.suffix == ".enc":
                    self.dec_dest_input.setText(str(p.with_suffix("")))
                else:
                    self.dec_dest_input.setText(f"{file_path}.dec")

    def _browse_dec_dest(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Tentukan Lokasi Berkas Hasil Dekripsi")
        if file_path:
            self.dec_dest_input.setText(file_path)

    def _generate_random_key_clicked(self):
        new_key = generate_random_aes_key()
        self.enc_key_input.setText(new_key)
        self.show_message("Kunci acak 256-bit berhasil dibuat. Simpan kunci ini untuk proses dekripsi!", is_error=False)

    def _handle_encrypt(self):
        src = self.enc_source_input.text().strip()
        dst = self.enc_dest_input.text().strip()
        key = self.enc_key_input.text().strip()

        try:
            self._crypto_service.encrypt_file(src, dst, key)
            self.show_message(f"Enkripsi berkas berhasil! Berkas terenkripsi disimpan di:\n{dst}", is_error=False)
        except CryptoSafeError as err:
            self.show_message(str(err), is_error=True)
        except Exception as err:
            self.show_message(f"Kesalahan sistem saat enkripsi: {err}", is_error=True)

    def _handle_decrypt(self):
        src = self.dec_source_input.text().strip()
        dst = self.dec_dest_input.text().strip()
        key = self.dec_key_input.text().strip()

        try:
            self._crypto_service.decrypt_file(src, dst, key)
            self.show_message(f"Dekripsi berkas berhasil diverifikasi dan disimpan di:\n{dst}", is_error=False)
        except CryptoSafeError as err:
            self.show_message(str(err), is_error=True)
        except Exception as err:
            self.show_message(f"Kesalahan sistem saat dekripsi: {err}", is_error=True)

    def show_message(self, message: str, is_error: bool = False):
        self.message_label.setText(message)
        if is_error:
            self.message_label.setStyleSheet("color: #DC2626; background: #FEE2E2; padding: 8px; border-radius: 4px; font-weight: 500;")
        else:
            self.message_label.setStyleSheet("color: #065F46; background: #D1FAE5; padding: 8px; border-radius: 4px; font-weight: 500;")
        self.message_label.setVisible(True)

    def clear_fields(self):
        self.enc_source_input.clear()
        self.enc_dest_input.clear()
        self.enc_key_input.clear()
        self.dec_source_input.clear()
        self.dec_dest_input.clear()
        self.dec_key_input.clear()
        self.message_label.setVisible(False)

