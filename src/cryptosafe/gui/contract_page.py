"""Contract management page with encrypted notes."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QLineEdit, QTextEdit, QComboBox, QMessageBox,
    QInputDialog, QFileDialog, QScrollArea, QFrame,
)

from cryptosafe.database.contract_repository import VALID_STATUSES
from cryptosafe.common.errors import ValidationError


class ContractPage(QWidget):
    """Manage contracts and their encrypted notes."""

    back_to_dashboard_requested = Signal()

    def __init__(
        self,
        contract_service,
        message_service,
        file_service=None,
        parent=None,
    ):
        super().__init__(parent)
        self._contract_service = contract_service
        self._contract_repository = getattr(contract_service, "repository", contract_service)
        self._message_service = message_service
        self._file_service = file_service
        self._user_id = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(18)

        # Header bar
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Manajemen Kontrak")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
        title_box.addWidget(title)

        subtitle = QLabel("Penyimpanan kontrak hukum terenkripsi AES-256-GCM, catatan rahasia, dan brankas berkas.")
        subtitle.setStyleSheet("font-size: 13px; color: #64748B; font-weight: 500;")
        title_box.addWidget(subtitle)
        header.addLayout(title_box)

        header.addStretch()

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
        header.addWidget(self.back_button)

        main_layout.addLayout(header)

        # Scroll Area for the three cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(container)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(0, 0, 0, 12)

        # Helper styles
        card_style = (
            "QFrame {"
            "   background-color: #FFFFFF;"
            "   border: 1px solid #E2E8F0;"
            "   border-radius: 10px;"
            "   padding: 16px;"
            "}"
        )
        btn_teal = (
            "QPushButton {"
            "   background-color: #0F766E; color: #FFFFFF; padding: 7px 16px;"
            "   font-weight: 600; border-radius: 6px; font-size: 12px; border: none;"
            "}"
            "QPushButton:hover { background-color: #0D9488; }"
        )
        btn_indigo = (
            "QPushButton {"
            "   background-color: #4F46E5; color: #FFFFFF; padding: 7px 16px;"
            "   font-weight: 600; border-radius: 6px; font-size: 12px; border: none;"
            "}"
            "QPushButton:hover { background-color: #4338CA; }"
        )
        btn_danger = (
            "QPushButton {"
            "   background-color: #FFFFFF; color: #DC2626; border: 1.5px solid #FECACA;"
            "   padding: 7px 16px; font-weight: 600; border-radius: 6px; font-size: 12px;"
            "}"
            "QPushButton:hover { background-color: #FEF2F2; border-color: #F87171; }"
        )

        # Card 1: Contracts
        contract_card = QFrame()
        contract_card.setStyleSheet(card_style)
        c_layout = QVBoxLayout(contract_card)
        c_layout.setSpacing(12)
        c_layout.setContentsMargins(18, 18, 18, 18)

        c_header = QHBoxLayout()
        c_title_box = QVBoxLayout()
        c_title_box.setSpacing(2)
        c_title = QLabel("Daftar Dokumen Kontrak")
        c_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A; border: none;")
        c_title_box.addWidget(c_title)
        c_desc = QLabel("Pilih kontrak dari tabel di bawah untuk melihat catatan terenkripsi dan berkas terkait.")
        c_desc.setStyleSheet("font-size: 12px; color: #64748B; border: none;")
        c_title_box.addWidget(c_desc)
        c_header.addLayout(c_title_box)
        c_header.addStretch()

        self.add_contract_button = QPushButton("Tambah Kontrak")
        self.add_contract_button.setStyleSheet(btn_teal)
        self.add_contract_button.clicked.connect(self._add_contract)
        c_header.addWidget(self.add_contract_button)

        self.delete_contract_button = QPushButton("Hapus Kontrak")
        self.delete_contract_button.setStyleSheet(btn_danger)
        self.delete_contract_button.clicked.connect(self._delete_contract)
        c_header.addWidget(self.delete_contract_button)
        c_layout.addLayout(c_header)

        self.contract_table = QTableWidget(0, 6)
        self.contract_table.setHorizontalHeaderLabels([
            "ID", "Nomor Kontrak", "Judul", "Pihak Terkait",
            "Tanggal Mulai", "Status",
        ])
        self.contract_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.contract_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.contract_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.contract_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.contract_table.setMinimumHeight(180)
        self.contract_table.itemSelectionChanged.connect(
            self._on_contract_selected
        )
        c_layout.addWidget(self.contract_table)

        status_layout = QHBoxLayout()
        status_lbl = QLabel("Ubah Status Kontrak Terpilih:")
        status_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569; border: none;")
        status_layout.addWidget(status_lbl)

        self.status_combo = QComboBox()
        self.status_combo.addItems(VALID_STATUSES)
        self.status_combo.setMinimumWidth(160)
        status_layout.addWidget(self.status_combo)

        self.update_status_button = QPushButton("Simpan Status")
        self.update_status_button.setStyleSheet(
            "QPushButton {"
            "   background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1;"
            "   padding: 7px 16px; font-weight: 600; border-radius: 6px; font-size: 12px;"
            "}"
            "QPushButton:hover { background-color: #E2E8F0; }"
        )
        self.update_status_button.clicked.connect(self._update_status)
        status_layout.addWidget(self.update_status_button)
        status_layout.addStretch()
        c_layout.addLayout(status_layout)

        content_layout.addWidget(contract_card)

        # Card 2: Encrypted Notes
        msg_card = QFrame()
        msg_card.setStyleSheet(card_style)
        m_layout = QVBoxLayout(msg_card)
        m_layout.setSpacing(12)
        m_layout.setContentsMargins(18, 18, 18, 18)

        m_header = QHBoxLayout()
        m_title_box = QVBoxLayout()
        m_title_box.setSpacing(2)
        m_title = QLabel("Catatan Kontrak Terenkripsi (AES-256-GCM)")
        m_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A; border: none;")
        m_title_box.addWidget(m_title)
        m_desc = QLabel("Isi dan klausul catatan disimpan terenkripsi di database dengan kunci derivasi pengguna.")
        m_desc.setStyleSheet("font-size: 12px; color: #64748B; border: none;")
        m_title_box.addWidget(m_desc)
        m_header.addLayout(m_title_box)
        m_header.addStretch()

        self.add_message_button = QPushButton("Tambah Catatan")
        self.add_message_button.setStyleSheet(btn_teal)
        self.add_message_button.clicked.connect(self._add_message)
        m_header.addWidget(self.add_message_button)

        self.open_message_button = QPushButton("Buka Catatan")
        self.open_message_button.setStyleSheet(btn_indigo)
        self.open_message_button.clicked.connect(self._open_message)
        m_header.addWidget(self.open_message_button)

        self.delete_message_button = QPushButton("Hapus Catatan")
        self.delete_message_button.setStyleSheet(btn_danger)
        self.delete_message_button.clicked.connect(self._delete_message)
        m_header.addWidget(self.delete_message_button)
        m_layout.addLayout(m_header)

        self.message_table = QTableWidget(0, 4)
        self.message_table.setHorizontalHeaderLabels([
            "ID", "Jenis", "Label", "Tanggal Dibuat",
        ])
        self.message_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.message_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.message_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.message_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.message_table.setMinimumHeight(150)
        m_layout.addWidget(self.message_table)

        content_layout.addWidget(msg_card)

        # Card 3: Secure File Vault
        file_card = QFrame()
        file_card.setStyleSheet(card_style)
        f_layout = QVBoxLayout(file_card)
        f_layout.setSpacing(12)
        f_layout.setContentsMargins(18, 18, 18, 18)

        f_header = QHBoxLayout()
        f_title_box = QVBoxLayout()
        f_title_box.setSpacing(2)
        f_title = QLabel("Lampiran Berkas Kontrak (Secure File Vault)")
        f_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A; border: none;")
        f_title_box.addWidget(f_title)
        f_desc = QLabel("Berkas fisik dienkripsi dengan ChaCha20-Poly1305 dan hash SHA-256 dicatat di blockchain ledger.")
        f_desc.setStyleSheet("font-size: 12px; color: #64748B; border: none;")
        f_title_box.addWidget(f_desc)
        f_header.addLayout(f_title_box)
        f_header.addStretch()

        self.add_file_button = QPushButton("Tambah Lampiran")
        self.add_file_button.setStyleSheet(btn_teal)
        self.add_file_button.clicked.connect(self._add_file)
        f_header.addWidget(self.add_file_button)

        self.download_file_button = QPushButton("Unduh / Dekripsi Berkas")
        self.download_file_button.setStyleSheet(btn_indigo)
        self.download_file_button.clicked.connect(self._download_file)
        f_header.addWidget(self.download_file_button)

        self.delete_file_button = QPushButton("Hapus Lampiran")
        self.delete_file_button.setStyleSheet(btn_danger)
        self.delete_file_button.clicked.connect(self._delete_file)
        f_header.addWidget(self.delete_file_button)
        f_layout.addLayout(f_header)

        self.file_table = QTableWidget(0, 5)
        self.file_table.setHorizontalHeaderLabels([
            "ID", "Nama Berkas", "Ukuran", "Algoritma", "Tanggal Dibuat",
        ])
        self.file_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.file_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.file_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.file_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.file_table.setMinimumHeight(150)
        f_layout.addWidget(self.file_table)

        content_layout.addWidget(file_card)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def set_user(self, user_id: int):
        """Set the authenticated user and refresh their contracts."""
        self._user_id = user_id
        self.refresh_contracts()

    def refresh_contracts(self):
        self.contract_table.setRowCount(0)
        self.message_table.setRowCount(0)
        self.file_table.setRowCount(0)

        if self._user_id is None:
            return

        contracts = self._contract_service.list_by_user(self._user_id)

        for contract in contracts:
            row = self.contract_table.rowCount()
            self.contract_table.insertRow(row)

            values = [
                contract.id,
                contract.contract_number,
                contract.title,
                contract.parties,
                contract.start_date or "-",
                contract.status,
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, contract.id)
                self.contract_table.setItem(row, column, item)

    def _selected_contract_id(self):
        row = self.contract_table.currentRow()
        if row < 0:
            return None

        item = self.contract_table.item(row, 0)
        if item is None:
            return None

        return item.data(Qt.ItemDataRole.UserRole)

    def _selected_message_id(self):
        row = self.message_table.currentRow()
        if row < 0:
            return None

        item = self.message_table.item(row, 0)
        if item is None:
            return None

        return item.data(Qt.ItemDataRole.UserRole)

    def _add_contract(self):
        if self._user_id is None:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Tambah Kontrak")
        form = QFormLayout(dialog)

        number_input = QLineEdit()
        title_input = QLineEdit()
        parties_input = QLineEdit()
        start_input = QLineEdit()
        end_input = QLineEdit()

        start_input.setPlaceholderText("YYYY-MM-DD (opsional)")
        end_input.setPlaceholderText("YYYY-MM-DD (opsional)")

        status_input = QComboBox()
        status_input.addItems(VALID_STATUSES)

        form.addRow("Nomor Kontrak:", number_input)
        form.addRow("Judul:", title_input)
        form.addRow("Pihak Terkait:", parties_input)
        form.addRow("Tanggal Mulai:", start_input)
        form.addRow("Tanggal Selesai:", end_input)
        form.addRow("Status:", status_input)

        buttons = QHBoxLayout()
        save_button = QPushButton("Simpan")
        cancel_button = QPushButton("Batal")

        save_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        form.addRow(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            self._contract_service.create_contract(
                contract_number=number_input.text(),
                title=title_input.text(),
                parties=parties_input.text(),
                created_by=self._user_id,
                start_date=start_input.text().strip() or None,
                end_date=end_input.text().strip() or None,
                status=status_input.currentText(),
            )

            self.refresh_contracts()
            QMessageBox.information(
                self, "Berhasil", "Kontrak berhasil ditambahkan."
            )

        except (ValidationError, ValueError) as err:
            QMessageBox.warning(self, "Gagal", str(err))

    def _delete_contract(self):
        contract_id = self._selected_contract_id()

        if contract_id is None:
            QMessageBox.warning(
                self, "Peringatan", "Pilih kontrak terlebih dahulu."
            )
            return

        reply = QMessageBox.question(
            self,
            "Konfirmasi",
            "Hapus kontrak ini beserta seluruh catatan terkait?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self._contract_service.delete_contract(
                contract_id, self._user_id
            )
            self.refresh_contracts()
        except ValidationError as err:
            QMessageBox.warning(self, "Gagal", str(err))

    def _update_status(self):
        contract_id = self._selected_contract_id()

        if contract_id is None:
            QMessageBox.warning(
                self, "Peringatan", "Pilih kontrak terlebih dahulu."
            )
            return

        try:
            self._contract_service.update_status(
                contract_id,
                self._user_id,
                self.status_combo.currentText(),
            )
            self.refresh_contracts()
        except ValidationError as err:
            QMessageBox.warning(self, "Gagal", str(err))

    def _refresh_messages(self):
        self.message_table.setRowCount(0)

        contract_id = self._selected_contract_id()
        if contract_id is None or self._user_id is None:
            return

        messages = self._message_service.list_by_contract(
            contract_id, self._user_id
        )

        for message in messages:
            row = self.message_table.rowCount()
            self.message_table.insertRow(row)

            values = [
                message.id,
                message.content_type,
                message.label,
                message.created_at,
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, message.id)
                self.message_table.setItem(row, column, item)

    def _add_message(self):
        contract_id = self._selected_contract_id()

        if contract_id is None:
            QMessageBox.warning(
                self, "Peringatan", "Pilih kontrak terlebih dahulu."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Tambah Catatan Terenkripsi")
        form = QFormLayout(dialog)

        type_input = QComboBox()
        type_input.addItems(["note", "clause", "draft"])

        label_input = QLineEdit()
        plaintext_input = QTextEdit()
        plaintext_input.setMinimumHeight(130)

        vigenere_input = QLineEdit()
        vigenere_input.setEchoMode(QLineEdit.EchoMode.Password)

        aes_input = QLineEdit()
        aes_input.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Jenis Catatan:", type_input)
        form.addRow("Label:", label_input)
        form.addRow("Isi Catatan:", plaintext_input)
        form.addRow("Kunci Vigenère:", vigenere_input)
        form.addRow("Passphrase AES:", aes_input)

        buttons = QHBoxLayout()
        save_button = QPushButton("Enkripsi dan Simpan")
        cancel_button = QPushButton("Batal")

        save_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        form.addRow(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            self._message_service.create_encrypted_message(
                contract_id=contract_id,
                user_id=self._user_id,
                content_type=type_input.currentText(),
                label=label_input.text(),
                plaintext=plaintext_input.toPlainText(),
                vigenere_key=vigenere_input.text(),
                aes_key_material=aes_input.text(),
            )

            self._refresh_messages()
            QMessageBox.information(
                self,
                "Berhasil",
                "Catatan berhasil dienkripsi dan disimpan.",
            )

        except (ValidationError, ValueError) as err:
            QMessageBox.warning(self, "Gagal", str(err))

    def _open_message(self):
        message_id = self._selected_message_id()

        if message_id is None:
            QMessageBox.warning(
                self, "Peringatan", "Pilih catatan terlebih dahulu."
            )
            return

        vigenere_key, accepted = QInputDialog.getText(
            self,
            "Dekripsi Catatan",
            "Masukkan kunci Vigenère:",
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return

        aes_key, accepted = QInputDialog.getText(
            self,
            "Dekripsi Catatan",
            "Masukkan passphrase AES:",
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return

        try:
            message, plaintext = self._message_service.get_decrypted_message(
                message_id=message_id,
                user_id=self._user_id,
                vigenere_key=vigenere_key,
                aes_key_material=aes_key,
            )

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Catatan: {message.label}")
            dialog.resize(600, 400)

            layout = QVBoxLayout(dialog)
            text_output = QTextEdit()
            text_output.setReadOnly(True)
            text_output.setPlainText(plaintext)
            layout.addWidget(text_output)

            close_button = QPushButton("Tutup")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)

            dialog.exec()

        except Exception as err:
            QMessageBox.warning(
                self,
                "Gagal Dekripsi",
                "Catatan tidak dapat dibuka. Periksa kembali kedua kunci.\n\n"
                + str(err),
            )

    def _delete_message(self):
        message_id = self._selected_message_id()

        if message_id is None:
            QMessageBox.warning(
                self, "Peringatan", "Pilih catatan terlebih dahulu."
            )
            return

        reply = QMessageBox.question(
            self,
            "Konfirmasi",
            "Yakin ingin menghapus catatan ini?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self._message_service.delete_message(
                message_id, self._user_id
            )
            self._refresh_messages()
        except ValidationError as err:
            QMessageBox.warning(self, "Gagal", str(err))

    def _on_contract_selected(self):
        self._refresh_messages()
        self._refresh_files()

    def _selected_file_id(self):
        row = self.file_table.currentRow()
        if row < 0:
            return None

        item = self.file_table.item(row, 0)
        if item is None:
            return None

        return item.data(Qt.ItemDataRole.UserRole)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _refresh_files(self):
        self.file_table.setRowCount(0)

        contract_id = self._selected_contract_id()
        if contract_id is None or self._user_id is None or self._file_service is None:
            return

        files = self._file_service.list_by_contract(
            contract_id, self._user_id
        )

        for file_item in files:
            row = self.file_table.rowCount()
            self.file_table.insertRow(row)

            values = [
                file_item.id,
                file_item.original_filename,
                self._format_size(file_item.size_bytes),
                file_item.algorithm,
                file_item.created_at,
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, file_item.id)
                self.file_table.setItem(row, column, item)

    def _add_file(self):
        contract_id = self._selected_contract_id()
        if contract_id is None:
            QMessageBox.warning(
                self, "Peringatan", "Pilih kontrak terlebih dahulu."
            )
            return

        if self._file_service is None:
            QMessageBox.warning(
                self, "Peringatan", "Layanan file vault belum tersedia."
            )
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Berkas Lampiran Kontrak"
        )
        if not file_path:
            return

        key_material, accepted = QInputDialog.getText(
            self,
            "Enkripsi Lampiran Berkas",
            "Masukkan Passphrase atau Hex Key (ChaCha20-Poly1305):",
            QLineEdit.EchoMode.Password,
        )
        if not accepted or not key_material.strip():
            return

        try:
            record = self._file_service.attach_file(
                contract_id=contract_id,
                user_id=self._user_id,
                source_path=file_path,
                key_material=key_material.strip(),
            )
            self._refresh_files()
            QMessageBox.information(
                self,
                "Berhasil",
                f"Berkas '{record.original_filename}' berhasil dienkripsi dan disimpan ke vault.",
            )
        except Exception as err:
            QMessageBox.warning(self, "Gagal Melampirkan Berkas", str(err))

    def _download_file(self):
        file_id = self._selected_file_id()
        if file_id is None:
            QMessageBox.warning(
                self, "Peringatan", "Pilih berkas lampiran terlebih dahulu."
            )
            return

        if self._file_service is None:
            return

        file_record = self._file_service.get_file(file_id, self._user_id)
        if file_record is None:
            QMessageBox.warning(
                self, "Gagal", "Data lampiran tidak ditemukan."
            )
            return

        suggested_name = file_record.original_filename
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Berkas Hasil Dekripsi",
            suggested_name,
        )
        if not save_path:
            return

        key_material, accepted = QInputDialog.getText(
            self,
            "Dekripsi Lampiran Berkas",
            "Masukkan Passphrase atau Hex Key (ChaCha20-Poly1305):",
            QLineEdit.EchoMode.Password,
        )
        if not accepted or not key_material.strip():
            return

        try:
            self._file_service.export_decrypted_file(
                file_id=file_id,
                user_id=self._user_id,
                destination_path=save_path,
                key_material=key_material.strip(),
            )
            QMessageBox.information(
                self,
                "Berhasil",
                f"Berkas berhasil didekripsi dan disimpan ke:\n{save_path}",
            )
        except Exception as err:
            QMessageBox.warning(
                self,
                "Gagal Dekripsi Berkas",
                f"Gagal mendekripsi berkas: {err}",
            )

    def _delete_file(self):
        file_id = self._selected_file_id()
        if file_id is None:
            QMessageBox.warning(
                self, "Peringatan", "Pilih berkas lampiran terlebih dahulu."
            )
            return

        if self._file_service is None:
            return

        reply = QMessageBox.question(
            self,
            "Konfirmasi",
            "Yakin ingin menghapus berkas lampiran ini dari vault?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self._file_service.delete_file(file_id, self._user_id)
            self._refresh_files()
            QMessageBox.information(
                self, "Berhasil", "Berkas lampiran berhasil dihapus dari vault."
            )
        except Exception as err:
            QMessageBox.warning(self, "Gagal Menghapus Berkas", str(err))
