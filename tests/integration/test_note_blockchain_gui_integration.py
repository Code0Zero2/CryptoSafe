"""Integration tests for Encrypted Notes with Blockchain SHA-256 via GUI."""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from cryptosafe.auth.auth_service import AuthService
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.crypto.blockchain_service import BlockchainService
from cryptosafe.crypto.text_crypto_service import TextCryptoService
from cryptosafe.database.blockchain_repository import BlockchainRepository
from cryptosafe.database.connection import get_connection
from cryptosafe.database.contract_repository import ContractRepository
from cryptosafe.database.contract_service import ContractService
from cryptosafe.database.encrypted_message_repository import EncryptedMessageRepository
from cryptosafe.database.encrypted_message_service import EncryptedMessageService
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.gui.main_window import MainWindow


class TestNoteBlockchainGuiIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)

        self.user_repo = UserRepository(self.conn)
        self.pwd_service = PasswordService(time_cost=1, memory_cost=8192, parallelism=1)
        self.auth_service = AuthService(self.user_repo, self.pwd_service)

        self.alice = self.auth_service.register_user("alice", "Secret123!", "Secret123!")

        self.blockchain_repo = BlockchainRepository(self.conn)
        self.blockchain_service = BlockchainService(self.blockchain_repo)
        self.blockchain_service.ensure_genesis_block()

        self.contract_repo = ContractRepository(self.conn)
        self.contract_service = ContractService(
            contract_repository=self.contract_repo,
            blockchain_service=self.blockchain_service,
        )

        self.text_crypto = TextCryptoService()
        self.message_repo = EncryptedMessageRepository(self.conn)
        self.message_service = EncryptedMessageService(
            repository=self.message_repo,
            crypto_service=self.text_crypto,
            blockchain_service=self.blockchain_service,
        )

        # Create contract for Alice
        self.contract = self.contract_service.create_contract(
            contract_number="CTR-GUI-NOTE",
            title="Kontrak GUI Note",
            parties="Alice & Partner",
            created_by=self.alice.id,
            status="Draft",
        )

        self.window = MainWindow(
            auth_service=self.auth_service,
            contract_service=self.contract_service,
            message_service=self.message_service,
            blockchain_service=self.blockchain_service,
            text_crypto_service=self.text_crypto,
            conn=self.conn,
        )
        self.window.show()

        # Log in Alice and open contract page
        self.window._on_login_requested("alice", "Secret123!")
        self.window.dashboard_page.btn_open_contract.click()

    def tearDown(self):
        self.window.close()
        self.conn.close()

    def test_gui_create_and_delete_note_records_blockchain(self):
        """Verify adding and deleting encrypted notes via ContractPage creates valid blocks."""
        page = self.window.contract_page
        page.refresh_contracts()
        self.assertEqual(page.contract_table.rowCount(), 1)
        page.contract_table.selectRow(0)

        # 1. Add Note via GUI Dialog
        def mock_dialog_exec(dialog_self):
            layout = dialog_self.layout()
            layout.itemAt(1).widget().setCurrentText("clause")       # type
            layout.itemAt(3).widget().setText("Klausul Pembayaran")   # label
            layout.itemAt(5).widget().setPlainText("Bayar tepat waktu.")  # plaintext
            layout.itemAt(7).widget().setText("VIGKEY")              # vigenere
            layout.itemAt(9).widget().setText("AESPASS123")          # aes
            return QDialog.DialogCode.Accepted

        with patch.object(QDialog, "exec", mock_dialog_exec), \
             patch.object(QMessageBox, "information"):
            page.add_message_button.click()

        # Note table must now have 1 row
        self.assertEqual(page.message_table.rowCount(), 1)
        note_id = page.message_table.item(0, 0).data(0x0100)

        # Blockchain must contain NOTE_CREATED block
        blocks = self.blockchain_repo.find_by_asset_id(f"note:{note_id}")
        self.assertEqual(len(blocks), 1)

        create_block = blocks[0]
        self.assertEqual(create_block.event_type, "NOTE_CREATED")
        payload = json.loads(create_block.payload_json)
        self.assertEqual(payload["label"], "Klausul Pembayaran")
        self.assertEqual(payload["content_type"], "clause")

        # 2. Delete Note via GUI
        page.message_table.selectRow(0)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            page.delete_message_button.click()

        # Note table must now be empty
        self.assertEqual(page.message_table.rowCount(), 0)

        # Blockchain must contain NOTE_DELETED block
        blocks_after = self.blockchain_repo.find_by_asset_id(f"note:{note_id}")
        self.assertEqual(len(blocks_after), 2)

        del_block = blocks_after[1]
        self.assertEqual(del_block.event_type, "NOTE_DELETED")
        del_payload = json.loads(del_block.payload_json)
        self.assertEqual(del_payload["action"], "DELETED")

        # Verify chain integrity
        ver = self.blockchain_service.verify_chain_integrity()
        self.assertTrue(ver.is_valid)


if __name__ == "__main__":
    unittest.main()
