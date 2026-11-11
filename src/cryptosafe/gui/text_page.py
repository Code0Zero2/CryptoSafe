"""GUI page for Text Super-Encryption (Vigenère + AES-256-GCM)."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QTabWidget,
    QFrame,
    QApplication,
)
from cryptosafe.common.errors import CryptoSafeError
from cryptosafe.crypto.text_crypto_service import TextCryptoService
from cryptosafe.crypto.key_manager import generate_super_encryption_keys

class TextPage(QWidget):
    """Page hosting Text Super-Encryption and Decryption."""

    back_to_dashboard_requested = Signal()

    def __init__(self, text_crypto_service: TextCryptoService | None = None, parent=None):
        super().__init__(parent)
        self._crypto_service = text_crypto_service or TextCryptoService()
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(18)

        # Header bar
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title_lbl = QLabel("Super-Enkripsi Teks")
        title_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
        title_box.addWidget(title_lbl)

        desc_lbl = QLabel(
            "Perlindungan pesan bertingkat menggunakan sandi substitusi Vigenère dan cipher AEAD modern AES-256-GCM."
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

        # Message Banner (for errors or success)
        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setVisible(False)
        main_layout.addWidget(self.message_label)

        # Tab widget for Encrypt and Decrypt
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_encrypt_tab(), "Enkripsi Teks")
        self.tabs.addTab(self._create_decrypt_tab(), "Dekripsi Teks")
        main_layout.addWidget(self.tabs)

    def _create_encrypt_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        layout.addWidget(QLabel("1. Teks Asli (Plaintext):"))
        self.enc_plaintext_input = QTextEdit()
        self.enc_plaintext_input.setPlaceholderText("Masukkan pesan teks yang ingin dienkripsi...")
        self.enc_plaintext_input.setMaximumHeight(90)
        layout.addWidget(self.enc_plaintext_input)

        # Automatic Key Generator Toolbar
        gen_toolbar = QHBoxLayout()
        self.generate_key_button = QPushButton("Buat Kunci Otomatis (Generate)")
        self.generate_key_button.setStyleSheet(
            "QPushButton {"
            "   background-color: #4F46E5; color: white; padding: 7px 16px; font-weight: 600; border-radius: 6px; font-size: 12px; border: none;"
            "}"
            "QPushButton:hover { background-color: #4338CA; }"
        )
        self.generate_key_button.clicked.connect(self._generate_keys_clicked)
        gen_toolbar.addWidget(self.generate_key_button)

        key_warning_lbl = QLabel(
            "⚠️ Simpan kedua kunci secara mandiri. Demi keamanan zero-knowledge, sistem tidak menyimpan kunci."
        )
        key_warning_lbl.setStyleSheet("color: #B45309; font-size: 11px; font-weight: 500;")
        gen_toolbar.addWidget(key_warning_lbl)
        gen_toolbar.addStretch()
        layout.addLayout(gen_toolbar)

        keys_layout = QHBoxLayout()

        # Vigenere Key input
        vig_box = QVBoxLayout()
        vig_box.addWidget(QLabel("2. Kunci Vigenère (Alfabet A-Z):"))
        vig_input_row = QHBoxLayout()
        self.enc_vig_key_input = QLineEdit()
        self.enc_vig_key_input.setPlaceholderText("Contoh: RAHASIA")
        vig_input_row.addWidget(self.enc_vig_key_input)

        self.copy_vig_key_button = QPushButton("Salin")
        self.copy_vig_key_button.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; padding: 6px 12px; font-weight: 600; border-radius: 5px; font-size: 11px; } QPushButton:hover { background-color: #E2E8F0; }"
        )
        self.copy_vig_key_button.clicked.connect(self._copy_vig_key_to_clipboard)
        vig_input_row.addWidget(self.copy_vig_key_button)
        vig_box.addLayout(vig_input_row)
        keys_layout.addLayout(vig_box)

        # AES Key input
        aes_box = QVBoxLayout()
        aes_box.addWidget(QLabel("3. Kunci / Passphrase AES-256:"))
        aes_input_row = QHBoxLayout()
        self.enc_aes_key_input = QLineEdit()
        self.enc_aes_key_input.setPlaceholderText("Passphrase atau 64-karakter hex key")
        aes_input_row.addWidget(self.enc_aes_key_input)

        self.copy_aes_key_button = QPushButton("Salin")
        self.copy_aes_key_button.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; padding: 6px 12px; font-weight: 600; border-radius: 5px; font-size: 11px; } QPushButton:hover { background-color: #E2E8F0; }"
        )
        self.copy_aes_key_button.clicked.connect(self._copy_aes_key_to_clipboard)
        aes_input_row.addWidget(self.copy_aes_key_button)
        aes_box.addLayout(aes_input_row)

        keys_layout.addLayout(aes_box)
        layout.addLayout(keys_layout)

        # Action button
        self.encrypt_button = QPushButton("Jalankan Super-Enkripsi")
        self.encrypt_button.setStyleSheet(
            "QPushButton {"
            "   background-color: #4F46E5; color: white; padding: 9px; font-weight: 600; border-radius: 6px; font-size: 13px; border: none;"
            "}"
            "QPushButton:hover { background-color: #4338CA; }"
        )
        self.encrypt_button.clicked.connect(self._handle_encrypt)
        layout.addWidget(self.encrypt_button)

        layout.addWidget(QLabel("4. Hasil Ciphertext (Structured Envelope):"))
        self.enc_result_output = QTextEdit()
        self.enc_result_output.setReadOnly(True)
        self.enc_result_output.setPlaceholderText("Amplop ciphertext terenkripsi akan muncul di sini...")
        layout.addWidget(self.enc_result_output)

        copy_btn = QPushButton("Salin Ciphertext ke Clipboard")
        copy_btn.setStyleSheet(
            "QPushButton { background-color: #F8FAFC; color: #475569; border: 1px solid #CBD5E1; padding: 6px 12px; font-weight: 600; border-radius: 5px; font-size: 11px; } QPushButton:hover { background-color: #F1F5F9; }"
        )
        copy_btn.clicked.connect(self._copy_encrypted_to_clipboard)
        layout.addWidget(copy_btn)

        return widget

    def _create_decrypt_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        layout.addWidget(QLabel("1. Masukkan Amplop Ciphertext (JSON Format):"))
        self.dec_envelope_input = QTextEdit()
        self.dec_envelope_input.setPlaceholderText("Tempel amplop JSON ciphertext di sini...")
        self.dec_envelope_input.setMaximumHeight(120)
        layout.addWidget(self.dec_envelope_input)

        keys_layout = QHBoxLayout()

        # Vigenere Key input
        vig_box = QVBoxLayout()
        vig_box.addWidget(QLabel("2. Kunci Vigenère:"))
        self.dec_vig_key_input = QLineEdit()
        self.dec_vig_key_input.setPlaceholderText("Kunci Vigenère yang sama saat enkripsi")
        vig_box.addWidget(self.dec_vig_key_input)
        keys_layout.addLayout(vig_box)

        # AES Key input
        aes_box = QVBoxLayout()
        aes_box.addWidget(QLabel("3. Kunci / Passphrase AES-256:"))
        self.dec_aes_key_input = QLineEdit()
        self.dec_aes_key_input.setPlaceholderText("Passphrase atau kunci AES yang sama")
        aes_box.addWidget(self.dec_aes_key_input)
        keys_layout.addLayout(aes_box)

        layout.addLayout(keys_layout)

        # Action button
        self.decrypt_button = QPushButton("Jalankan Super-Dekripsi")
        self.decrypt_button.setStyleSheet(
            "QPushButton {"
            "   background-color: #059669; color: white; padding: 9px; font-weight: 600; border-radius: 6px; font-size: 13px; border: none;"
            "}"
            "QPushButton:hover { background-color: #047857; }"
        )
        self.decrypt_button.clicked.connect(self._handle_decrypt)
        layout.addWidget(self.decrypt_button)

        layout.addWidget(QLabel("4. Hasil Plaintext Asli:"))
        self.dec_result_output = QTextEdit()
        self.dec_result_output.setReadOnly(True)
        self.dec_result_output.setPlaceholderText("Hasil dekripsi plaintext akan muncul di sini...")
        layout.addWidget(self.dec_result_output)

        return widget

    def _generate_keys_clicked(self):
        vig_key, aes_key = generate_super_encryption_keys()
        self.enc_vig_key_input.setText(vig_key)
        self.enc_aes_key_input.setText(aes_key)
        self.show_message(
            "Kunci Vigenère dan AES berhasil dibuat secara otomatis! "
            "PERINGATAN: Simpan kedua kunci ini sekarang. Kunci TIDAK disimpan ke database atau log.",
            is_error=False,
        )

    def _copy_vig_key_to_clipboard(self):
        text = self.enc_vig_key_input.text()
        if text:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(text)
            self.show_message("Kunci Vigenère berhasil disalin ke clipboard.", is_error=False)
        else:
            self.show_message("Kunci Vigenère belum diisi.", is_error=True)

    def _copy_aes_key_to_clipboard(self):
        text = self.enc_aes_key_input.text()
        if text:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(text)
            self.show_message("Kunci / passphrase AES berhasil disalin ke clipboard.", is_error=False)
        else:
            self.show_message("Kunci / passphrase AES belum diisi.", is_error=True)

    def _copy_encrypted_to_clipboard(self):
        text = self.enc_result_output.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.show_message("Ciphertext berhasil disalin ke clipboard.", is_error=False)

    def _handle_encrypt(self):
        plaintext = self.enc_plaintext_input.toPlainText()
        vig_key = self.enc_vig_key_input.text()
        aes_key = self.enc_aes_key_input.text()

        try:
            envelope = self._crypto_service.encrypt(plaintext, vig_key, aes_key)
            self.enc_result_output.setPlainText(envelope)
            self.show_message("Super-enkripsi teks berhasil!", is_error=False)
        except CryptoSafeError as err:
            self.show_message(str(err), is_error=True)

    def _handle_decrypt(self):
        envelope = self.dec_envelope_input.toPlainText()
        vig_key = self.dec_vig_key_input.text()
        aes_key = self.dec_aes_key_input.text()

        try:
            decrypted = self._crypto_service.decrypt(envelope, vig_key, aes_key)
            self.dec_result_output.setPlainText(decrypted)
            self.show_message("Super-dekripsi teks berhasil diverifikasi dan dikembalikan!", is_error=False)
        except CryptoSafeError as err:
            self.dec_result_output.clear()
            self.show_message(str(err), is_error=True)

    def show_message(self, message: str, is_error: bool = False):
        self.message_label.setText(message)
        if is_error:
            self.message_label.setStyleSheet("color: #DC2626; background: #FEE2E2; padding: 6px; border-radius: 4px; font-weight: 500;")
        else:
            self.message_label.setStyleSheet("color: #065F46; background: #D1FAE5; padding: 6px; border-radius: 4px; font-weight: 500;")
        self.message_label.setVisible(True)

    def clear_fields(self):
        self.enc_plaintext_input.clear()
        self.enc_vig_key_input.clear()
        self.enc_aes_key_input.clear()
        self.enc_result_output.clear()
        self.dec_envelope_input.clear()
        self.dec_vig_key_input.clear()
        self.dec_aes_key_input.clear()
        self.dec_result_output.clear()
        self.message_label.setVisible(False)

