"""GUI page for LSB Steganography combined with Super-Encryption (M9)."""

from pathlib import Path
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
    QFileDialog,
    QApplication,
    QScrollArea,
    QFrame,
)
from cryptosafe.common.errors import CryptoSafeError
from cryptosafe.crypto.steganography_service import SteganographyService


class StegoPage(QWidget):
    """Page hosting PNG LSB Steganography and text super-encryption."""

    back_to_dashboard_requested = Signal()

    def __init__(
        self,
        stego_service: SteganographyService | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._stego_service = stego_service or SteganographyService()
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header bar
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("Steganografi Citra (LSB + Super-Enkripsi)")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #1E293B;")
        title_box.addWidget(title_lbl)

        desc_lbl = QLabel(
            "Sisipkan pesan rahasia terenkripsi (Vigenère + AES-256-GCM) ke dalam citra PNG tanpa merusak citra asli."
        )
        desc_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(desc_lbl)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        self.back_button = QPushButton("← Kembali ke Dashboard")
        self.back_button.setStyleSheet(
            "background-color: #4B5563; color: white; padding: 6px 14px; "
            "font-weight: bold; border-radius: 4px; font-size: 12px;"
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

        # Tabs for Embed and Extract
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_embed_tab(), "Sisipkan Pesan (Embed)")
        self.tabs.addTab(self._create_extract_tab(), "Ekstrak Pesan (Extract)")
        main_layout.addWidget(self.tabs)

    def _create_embed_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        # 1. Source Image
        layout.addWidget(QLabel("1. Pilih Citra PNG Asli (RGB / RGBA):"))
        src_row = QHBoxLayout()
        self.embed_src_input = QLineEdit()
        self.embed_src_input.setPlaceholderText("Pilih berkas PNG...")
        src_row.addWidget(self.embed_src_input)

        self.embed_src_btn = QPushButton("Pilih Citra...")
        self.embed_src_btn.clicked.connect(self._browse_embed_src)
        src_row.addWidget(self.embed_src_btn)
        layout.addLayout(src_row)

        self.embed_capacity_lbl = QLabel("Kapasitas payload citra: -")
        self.embed_capacity_lbl.setStyleSheet("font-size: 11px; color: #0D9488; font-weight: bold;")
        layout.addWidget(self.embed_capacity_lbl)

        # 2. Plaintext Message
        layout.addWidget(QLabel("2. Pesan Rahasia yang Ingin Disisipkan:"))
        self.embed_msg_input = QTextEdit()
        self.embed_msg_input.setPlaceholderText("Ketikkan pesan rahasia di sini...")
        self.embed_msg_input.setMaximumHeight(90)
        layout.addWidget(self.embed_msg_input)

        # 3. Keys
        layout.addWidget(QLabel("3. Kunci Super-Enkripsi (Vigenère & AES):"))
        keys_card = QFrame()
        keys_card.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px;"
        )
        keys_layout = QVBoxLayout(keys_card)
        keys_layout.setSpacing(8)

        # Vigenere Key Row
        vig_row = QHBoxLayout()
        vig_lbl = QLabel("Vigenère Key:")
        vig_lbl.setMinimumWidth(110)
        vig_row.addWidget(vig_lbl)
        self.embed_vig_key = QLineEdit()
        self.embed_vig_key.setPlaceholderText("Hanya huruf A-Z...")
        vig_row.addWidget(self.embed_vig_key)
        self.embed_copy_vig_btn = QPushButton("Salin")
        self.embed_copy_vig_btn.clicked.connect(lambda: self._copy_to_clipboard(self.embed_vig_key.text()))
        vig_row.addWidget(self.embed_copy_vig_btn)
        keys_layout.addLayout(vig_row)

        # AES Key Row
        aes_row = QHBoxLayout()
        aes_lbl = QLabel("AES Passphrase:")
        aes_lbl.setMinimumWidth(110)
        aes_row.addWidget(aes_lbl)
        self.embed_aes_key = QLineEdit()
        self.embed_aes_key.setPlaceholderText("Passphrase atau 64-karakter hex...")
        self.embed_aes_key.setEchoMode(QLineEdit.EchoMode.Password)
        aes_row.addWidget(self.embed_aes_key)
        self.embed_copy_aes_btn = QPushButton("Salin")
        self.embed_copy_aes_btn.clicked.connect(lambda: self._copy_to_clipboard(self.embed_aes_key.text()))
        aes_row.addWidget(self.embed_copy_aes_btn)
        keys_layout.addLayout(aes_row)

        # Generate Key button
        gen_btn_layout = QHBoxLayout()
        self.embed_gen_key_btn = QPushButton("Generate Key")
        self.embed_gen_key_btn.setStyleSheet(
            "background-color: #0284C7; color: white; padding: 5px 14px; font-weight: bold; border-radius: 4px;"
        )
        self.embed_gen_key_btn.clicked.connect(self._on_generate_keys_clicked)
        gen_btn_layout.addWidget(self.embed_gen_key_btn)
        gen_btn_layout.addStretch()
        keys_layout.addLayout(gen_btn_layout)

        layout.addWidget(keys_card)

        # 4. Output Stego Image Destination
        layout.addWidget(QLabel("4. Lokasi Berkas Citra Stego Output (PNG):"))
        dst_row = QHBoxLayout()
        self.embed_dst_input = QLineEdit()
        self.embed_dst_input.setPlaceholderText("Simpan sebagai berkas PNG baru...")
        dst_row.addWidget(self.embed_dst_input)

        self.embed_dst_btn = QPushButton("Pilih Lokasi...")
        self.embed_dst_btn.clicked.connect(self._browse_embed_dst)
        dst_row.addWidget(self.embed_dst_btn)
        layout.addLayout(dst_row)

        # Embed Action Button
        self.embed_action_btn = QPushButton("Sisipkan & Enkripsi Pesan")
        self.embed_action_btn.setStyleSheet(
            "background-color: #059669; color: white; padding: 10px; font-weight: bold; "
            "border-radius: 4px; font-size: 13px;"
        )
        self.embed_action_btn.clicked.connect(self._on_embed_clicked)
        layout.addWidget(self.embed_action_btn)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _create_extract_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        # 1. Stego Image
        layout.addWidget(QLabel("1. Pilih Citra Stego PNG yang Memuat Pesan:"))
        src_row = QHBoxLayout()
        self.extract_src_input = QLineEdit()
        self.extract_src_input.setPlaceholderText("Pilih berkas PNG steganografi...")
        src_row.addWidget(self.extract_src_input)

        self.extract_src_btn = QPushButton("Pilih Citra...")
        self.extract_src_btn.clicked.connect(self._browse_extract_src)
        src_row.addWidget(self.extract_src_btn)
        layout.addLayout(src_row)

        # 2. Keys
        layout.addWidget(QLabel("2. Kunci Dekripsi (Vigenère & AES):"))
        keys_card = QFrame()
        keys_card.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px;"
        )
        keys_layout = QVBoxLayout(keys_card)
        keys_layout.setSpacing(8)

        vig_row = QHBoxLayout()
        vig_lbl = QLabel("Vigenère Key:")
        vig_lbl.setMinimumWidth(110)
        vig_row.addWidget(vig_lbl)
        self.extract_vig_key = QLineEdit()
        self.extract_vig_key.setPlaceholderText("Kunci Vigenère...")
        vig_row.addWidget(self.extract_vig_key)
        keys_layout.addLayout(vig_row)

        aes_row = QHBoxLayout()
        aes_lbl = QLabel("AES Passphrase:")
        aes_lbl.setMinimumWidth(110)
        aes_row.addWidget(aes_lbl)
        self.extract_aes_key = QLineEdit()
        self.extract_aes_key.setPlaceholderText("Passphrase atau 64-karakter hex...")
        self.extract_aes_key.setEchoMode(QLineEdit.EchoMode.Password)
        aes_row.addWidget(self.extract_aes_key)
        keys_layout.addLayout(aes_row)

        layout.addWidget(keys_card)

        # Extract Action Button
        self.extract_action_btn = QPushButton("Ekstrak & Dekripsi Pesan")
        self.extract_action_btn.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 10px; font-weight: bold; "
            "border-radius: 4px; font-size: 13px;"
        )
        self.extract_action_btn.clicked.connect(self._on_extract_clicked)
        layout.addWidget(self.extract_action_btn)

        # 3. Decrypted Plaintext Output
        layout.addWidget(QLabel("3. Pesan Rahasia Terdekripsi:"))
        self.extract_output = QTextEdit()
        self.extract_output.setReadOnly(True)
        self.extract_output.setPlaceholderText("Pesan hasil ekstraksi dan dekripsi akan muncul di sini...")
        self.extract_output.setMaximumHeight(100)
        layout.addWidget(self.extract_output)

        out_btn_row = QHBoxLayout()
        self.extract_copy_btn = QPushButton("Salin Pesan Terdekripsi")
        self.extract_copy_btn.clicked.connect(lambda: self._copy_to_clipboard(self.extract_output.toPlainText()))
        out_btn_row.addWidget(self.extract_copy_btn)
        out_btn_row.addStretch()
        layout.addLayout(out_btn_row)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _browse_embed_src(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Citra Asli (PNG)", "", "PNG Images (*.png);;All Files (*)"
        )
        if file_path:
            self.embed_src_input.setText(file_path)
            try:
                cap = self._stego_service.get_image_capacity(file_path)
                self.embed_capacity_lbl.setText(f"Kapasitas payload citra: {cap:,} byte")
            except Exception as err:
                self.embed_capacity_lbl.setText(f"Gagal membaca citra: {err}")

    def _browse_embed_dst(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Simpan Citra Stego (PNG)", "", "PNG Images (*.png)"
        )
        if file_path:
            if not file_path.lower().endswith(".png"):
                file_path += ".png"
            self.embed_dst_input.setText(file_path)

    def _browse_extract_src(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Citra Stego (PNG)", "", "PNG Images (*.png);;All Files (*)"
        )
        if file_path:
            self.extract_src_input.setText(file_path)

    def _on_generate_keys_clicked(self):
        vig_key, aes_key = self._stego_service.generate_keys()
        self.embed_vig_key.setText(vig_key)
        self.embed_aes_key.setText(aes_key)
        self._show_message("Kunci Vigenère dan AES berhasil dibuat secara otomatis.", is_error=False)

    def _on_embed_clicked(self):
        src = self.embed_src_input.text().strip()
        dst = self.embed_dst_input.text().strip()
        msg = self.embed_msg_input.toPlainText()
        vig_key = self.embed_vig_key.text().strip()
        aes_key = self.embed_aes_key.text().strip()

        if not src or not dst:
            self._show_message("Silakan tentukan berkas citra sumber dan berkas output.", is_error=True)
            return

        if not msg:
            self._show_message("Pesan rahasia tidak boleh kosong.", is_error=True)
            return

        if not vig_key or not aes_key:
            self._show_message("Kunci Vigenère dan kunci AES wajib diisi.", is_error=True)
            return

        try:
            self._stego_service.embed_message(
                image_path=src,
                output_path=dst,
                plaintext=msg,
                vigenere_key=vig_key,
                aes_key_material=aes_key,
            )
            self._show_message(
                f"Pesan berhasil dienkripsi dan disisipkan ke citra stego:\n{dst}",
                is_error=False,
            )
        except CryptoSafeError as err:
            self._show_message(str(err), is_error=True)
        except Exception as err:
            self._show_message(f"Terjadi kesalahan saat menyisipkan pesan: {err}", is_error=True)

    def _on_extract_clicked(self):
        src = self.extract_src_input.text().strip()
        vig_key = self.extract_vig_key.text().strip()
        aes_key = self.extract_aes_key.text().strip()

        if not src:
            self._show_message("Silakan pilih berkas citra stego.", is_error=True)
            return

        if not vig_key or not aes_key:
            self._show_message("Kunci Vigenère dan kunci AES wajib diisi untuk dekripsi.", is_error=True)
            return

        try:
            plaintext = self._stego_service.extract_message(
                image_path=src,
                vigenere_key=vig_key,
                aes_key_material=aes_key,
            )
            self.extract_output.setPlainText(plaintext)
            self._show_message("Pesan rahasia berhasil diekstrak dan didekripsi dengan sukses!", is_error=False)
        except CryptoSafeError as err:
            self.extract_output.clear()
            self._show_message(str(err), is_error=True)
        except Exception as err:
            self.extract_output.clear()
            self._show_message(f"Terjadi kesalahan saat mengekstrak pesan: {err}", is_error=True)

    def _show_message(self, message: str, is_error: bool = False):
        color = "#DC2626" if is_error else "#059669"
        bg = "#FEE2E2" if is_error else "#D1FAE5"
        border = "#EF4444" if is_error else "#10B981"
        self.message_label.setText(message)
        self.message_label.setStyleSheet(
            f"color: {color}; background-color: {bg}; border: 1px solid {border}; "
            "padding: 8px; border-radius: 4px; font-weight: bold; font-size: 12px;"
        )
        self.message_label.setVisible(True)

    def _copy_to_clipboard(self, text: str):
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self._show_message("Disalin ke clipboard!", is_error=False)

    def clear_fields(self):
        """Reset inputs and clear banners when navigating to this page."""
        self.tabs.setCurrentIndex(0)
        self.embed_src_input.clear()
        self.embed_dst_input.clear()
        self.embed_msg_input.clear()
        self.embed_vig_key.clear()
        self.embed_aes_key.clear()
        self.embed_capacity_lbl.setText("Kapasitas payload citra: -")
        self.extract_src_input.clear()
        self.extract_vig_key.clear()
        self.extract_aes_key.clear()
        self.extract_output.clear()
        self.message_label.setText("")
        self.message_label.setVisible(False)
