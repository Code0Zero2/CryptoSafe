"""Interactive dialog for blockchain ledger inspection, integrity verification, and audit export."""

from __future__ import annotations

import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QFrame,
    QSplitter,
)
from cryptosafe.crypto.blockchain_service import BlockchainService


class AuditDialog(QDialog):
    """Dialog displaying immutable blockchain audit ledger, integrity verifier, and export tools."""

    def __init__(self, blockchain_service: BlockchainService, parent=None):
        super().__init__(parent)
        self._blockchain_service = blockchain_service
        self._blocks = []
        self._setup_ui()
        self._refresh_blocks()

    def _setup_ui(self):
        self.setWindowTitle("Buku Besar Audit Blockchain (SHA-256 Hash Chain)")
        self.resize(880, 560)
        self.setMinimumSize(740, 480)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # Header Title
        title_box = QVBoxLayout()
        title_lbl = QLabel("Buku Besar Audit Kriptografi (Blockchain)")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E293B;")
        title_box.addWidget(title_lbl)

        desc_lbl = QLabel(
            "Catatan append-only yang merekam setiap peristiwa siklus hidup kontrak, catatan terenkripsi, "
            "dan berkas vault secara berantai menggunakan digest SHA-256 kanonis."
        )
        desc_lbl.setStyleSheet("font-size: 12px; color: #475569;")
        desc_lbl.setWordWrap(True)
        title_box.addWidget(desc_lbl)
        main_layout.addLayout(title_box)

        # Status Bar / Alert Box
        self.status_box = QFrame()
        self.status_box.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 6px 12px;"
        )
        status_layout = QHBoxLayout(self.status_box)
        status_layout.setContentsMargins(0, 0, 0, 0)
        self.status_lbl = QLabel("Memuat data blok...")
        self.status_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155;")
        status_layout.addWidget(self.status_lbl)
        main_layout.addWidget(self.status_box)

        # Splitter: Table above, JSON payload viewer below
        splitter = QSplitter(Qt.Vertical)

        # Blocks Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Index",
            "Waktu (UTC)",
            "Peristiwa (Event)",
            "Asset ID",
            "Asset Hash",
            "Block Hash",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        splitter.addWidget(self.table)

        # Detail Viewer
        detail_container = QFrame()
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 6, 0, 0)
        detail_lbl = QLabel("Detail Payload Blok:")
        detail_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #475569;")
        detail_layout.addWidget(detail_lbl)

        self.payload_viewer = QTextEdit()
        self.payload_viewer.setReadOnly(True)
        self.payload_viewer.setStyleSheet(
            "font-family: monospace; font-size: 11px; background-color: #F1F5F9; border: 1px solid #CBD5E1;"
        )
        detail_layout.addWidget(self.payload_viewer)
        splitter.addWidget(detail_container)
        splitter.setSizes([320, 140])

        main_layout.addWidget(splitter, stretch=1)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.verify_btn = QPushButton("✓ Verifikasi Integritas Rantai")
        self.verify_btn.setStyleSheet(
            "background-color: #059669; color: white; padding: 7px 16px; font-weight: bold; font-size: 12px; border-radius: 4px;"
        )
        self.verify_btn.clicked.connect(self._on_verify_chain)
        btn_layout.addWidget(self.verify_btn)

        self.export_json_btn = QPushButton("Ekspor JSON")
        self.export_json_btn.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 7px 14px; font-weight: bold; font-size: 12px; border-radius: 4px;"
        )
        self.export_json_btn.clicked.connect(self._on_export_json)
        btn_layout.addWidget(self.export_json_btn)

        self.export_csv_btn = QPushButton("Ekspor CSV")
        self.export_csv_btn.setStyleSheet(
            "background-color: #0D9488; color: white; padding: 7px 14px; font-weight: bold; font-size: 12px; border-radius: 4px;"
        )
        self.export_csv_btn.clicked.connect(self._on_export_csv)
        btn_layout.addWidget(self.export_csv_btn)

        btn_layout.addStretch()

        self.close_btn = QPushButton("Tutup")
        self.close_btn.setStyleSheet(
            "padding: 7px 18px; font-weight: 500; font-size: 12px; border-radius: 4px; border: 1px solid #CBD5E1;"
        )
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        main_layout.addLayout(btn_layout)

    def _refresh_blocks(self):
        """Fetch all blocks from repository and populate table."""
        self._blockchain_service.ensure_genesis_block()
        self._blocks = self._blockchain_service.repository.get_all_blocks()
        self.table.setRowCount(len(self._blocks))

        for row, b in enumerate(self._blocks):
            item_idx = QTableWidgetItem(str(b.block_index))
            item_idx.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_idx)

            time_str = b.timestamp[:19].replace("T", " ") if b.timestamp else ""
            item_time = QTableWidgetItem(time_str)
            item_time.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, item_time)

            item_event = QTableWidgetItem(b.event_type)
            item_event.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, item_event)

            self.table.setItem(row, 3, QTableWidgetItem(b.asset_id))
            self.table.setItem(row, 4, QTableWidgetItem(b.asset_hash))
            self.table.setItem(row, 5, QTableWidgetItem(b.block_hash))

        self.status_lbl.setText(f"Total Blok Tercatat: {len(self._blocks)} blok. Siap diverifikasi.")
        if self._blocks:
            self.table.selectRow(0)

    def _on_row_selected(self):
        """Display payload details when a table row is clicked."""
        selected = self.table.selectedItems()
        if not selected:
            self.payload_viewer.clear()
            return
        row = selected[0].row()
        if 0 <= row < len(self._blocks):
            b = self._blocks[row]
            try:
                parsed = json.loads(b.payload_json) if b.payload_json else {}
                pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
            except Exception:
                pretty = b.payload_json or "(Kosong)"

            info_text = (
                f"Block Index   : {b.block_index}\n"
                f"Timestamp     : {b.timestamp}\n"
                f"Event Type    : {b.event_type}\n"
                f"Asset ID      : {b.asset_id}\n"
                f"Asset Hash    : {b.asset_hash}\n"
                f"Previous Hash : {b.previous_hash}\n"
                f"Block Hash    : {b.block_hash}\n"
                f"Created By    : {b.created_by}\n\n"
                f"--- PAYLOAD JSON ---\n{pretty}"
            )
            self.payload_viewer.setText(info_text)

    def _on_verify_chain(self):
        """Run full SHA-256 chain recalculation and report result."""
        result = self._blockchain_service.verify_chain_integrity()
        if result.is_valid:
            self.status_lbl.setText(f"✓ Integritas Valid: Seluruh {result.total_blocks} blok terverifikasi tanpa anomali.")
            self.status_box.setStyleSheet(
                "background-color: #ECFDF5; border: 1px solid #10B981; border-radius: 6px; padding: 6px 12px;"
            )
            QMessageBox.information(
                self,
                "Integritas Rantai Valid",
                f"Verifikasi Berhasil!\n\n"
                f"Total Blok      : {result.total_blocks}\n"
                f"Kondisi Rantai  : LENGKAP & KONSISTEN\n"
                f"Status Hash     : Tidak ditemukan modifikasi atau kerusakan pada seluruh blok.",
            )
        else:
            self.status_lbl.setText(f"⚠ Integritas Rusak pada Blok {result.tampered_index}!")
            self.status_box.setStyleSheet(
                "background-color: #FEF2F2; border: 1px solid #EF4444; border-radius: 6px; padding: 6px 12px;"
            )
            QMessageBox.critical(
                self,
                "Integritas Rantai Rusak",
                f"PERINGATAN KEAMANAN!\n\n"
                f"Blok Terindikasi : {result.tampered_index}\n"
                f"Detail Kerusakan : {result.error_detail}\n\n"
                f"Data pada buku besar telah mengalami perubahan di luar aplikasi!",
            )

    def _on_export_json(self):
        """Export ledger to JSON file via file dialog."""
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Ekspor Ledger Blockchain ke JSON",
            "cryptosafe_blockchain_audit.json",
            "JSON Files (*.json)",
        )
        if not save_path:
            return
        try:
            exported = self._blockchain_service.export_chain_to_json(save_path)
            QMessageBox.information(
                self,
                "Ekspor Berhasil",
                f"Buku besar blockchain berhasil diekspor ke:\n{exported}",
            )
        except Exception as err:
            QMessageBox.critical(self, "Galat Ekspor", f"Gagal mengekspor berkas JSON: {err}")

    def _on_export_csv(self):
        """Export ledger to CSV file via file dialog."""
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Ekspor Ledger Blockchain ke CSV",
            "cryptosafe_blockchain_audit.csv",
            "CSV Files (*.csv)",
        )
        if not save_path:
            return
        try:
            exported = self._blockchain_service.export_chain_to_csv(save_path)
            QMessageBox.information(
                self,
                "Ekspor Berhasil",
                f"Buku besar blockchain berhasil diekspor ke:\n{exported}",
            )
        except Exception as err:
            QMessageBox.critical(self, "Galat Ekspor", f"Gagal mengekspor berkas CSV: {err}")
