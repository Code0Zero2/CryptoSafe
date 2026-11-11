"""Integration tests for Contract Management with Blockchain SHA-256 via GUI."""

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
from cryptosafe.database.blockchain_repository import BlockchainRepository
from cryptosafe.database.connection import get_connection
from cryptosafe.database.contract_repository import ContractRepository
from cryptosafe.database.contract_service import ContractService
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.gui.contract_page import ContractPage
from cryptosafe.gui.main_window import MainWindow


class TestContractBlockchainIntegration(unittest.TestCase):
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

        self.contract_repo = ContractRepository(self.conn)
        self.blockchain_repo = BlockchainRepository(self.conn)
        self.blockchain_service = BlockchainService(self.blockchain_repo)
        self.blockchain_service.ensure_genesis_block()

        self.contract_service = ContractService(
            contract_repository=self.contract_repo,
            blockchain_service=self.blockchain_service,
        )

        self.window = MainWindow(
            auth_service=self.auth_service,
            contract_service=self.contract_service,
            blockchain_service=self.blockchain_service,
            conn=self.conn,
        )
        self.window.show()

        # Log in Alice
        self.window._on_login_requested("alice", "Secret123!")
        # Open contract page
        self.window.dashboard_page.btn_open_contract.click()

    def tearDown(self):
        self.window.close()
        self.conn.close()

    def test_gui_create_and_update_contract_records_blockchain(self):
        """Verify adding contract and updating status via ContractPage creates valid blocks."""
        page = self.window.contract_page
        self.assertIsInstance(page, ContractPage)

        # Simulate adding contract via dialog
        def mock_dialog_exec(dialog_self):
            # Fill form inputs
            layout = dialog_self.layout()
            # Find inputs
            layout.itemAt(1).widget().setText("CTR-GUI-001")     # number
            layout.itemAt(3).widget().setText("Kontrak GUI")     # title
            layout.itemAt(5).widget().setText("Alice & Mitra")   # parties
            layout.itemAt(7).widget().setText("2026-01-01")      # start
            layout.itemAt(9).widget().setText("2026-12-31")      # end
            layout.itemAt(11).widget().setCurrentText("Draft")   # status
            return QDialog.DialogCode.Accepted

        with patch.object(QDialog, "exec", mock_dialog_exec), \
             patch.object(QMessageBox, "information"):
            page.add_contract_button.click()

        # Verify contract table has 1 row
        self.assertEqual(page.contract_table.rowCount(), 1)
        contract_id = page.contract_table.item(0, 0).data(0x0100)  # UserRole

        # Verify blockchain has CONTRACT_CREATED block
        blocks = self.blockchain_repo.find_by_asset_id(f"contract:{contract_id}")
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].event_type, "CONTRACT_CREATED")

        # Now select the contract and update status to "Review"
        page.contract_table.selectRow(0)
        page.status_combo.setCurrentText("Review")
        page.update_status_button.click()

        # Check blockchain now has CONTRACT_STATUS_UPDATED
        blocks_after = self.blockchain_repo.find_by_asset_id(f"contract:{contract_id}")
        self.assertEqual(len(blocks_after), 2)
        self.assertEqual(blocks_after[1].event_type, "CONTRACT_STATUS_UPDATED")
        payload = json.loads(blocks_after[1].payload_json)
        self.assertEqual(payload["previous_status"], "Draft")
        self.assertEqual(payload["new_status"], "Review")

        # Check chain integrity
        ver = self.blockchain_service.verify_chain_integrity()
        self.assertTrue(ver.is_valid)

    def test_gui_delete_contract_records_blockchain(self):
        """Verify deleting a contract via GUI records CONTRACT_DELETED."""
        page = self.window.contract_page

        # Create contract directly via service
        contract = self.contract_service.create_contract(
            contract_number="CTR-GUI-DEL",
            title="Hapus via GUI",
            parties="Alice & Partner",
            created_by=self.alice.id,
        )
        page.refresh_contracts()
        self.assertEqual(page.contract_table.rowCount(), 1)

        page.contract_table.selectRow(0)

        # Simulate user clicking Yes on confirmation dialog
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            page.delete_contract_button.click()

        # Table should now be empty
        self.assertEqual(page.contract_table.rowCount(), 0)

        # Blockchain must contain CONTRACT_DELETED
        blocks = self.blockchain_repo.find_by_asset_id(f"contract:{contract.id}")
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[1].event_type, "CONTRACT_DELETED")
        payload = json.loads(blocks[1].payload_json)
        self.assertEqual(payload["action"], "DELETED")

        ver = self.blockchain_service.verify_chain_integrity()
        self.assertTrue(ver.is_valid)


if __name__ == "__main__":
    unittest.main()
