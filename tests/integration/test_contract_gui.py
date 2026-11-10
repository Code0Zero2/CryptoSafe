import os
import sys
import unittest
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PySide6.QtWidgets import QApplication
from cryptosafe.gui.main_window import MainWindow
from cryptosafe.gui.dashboard_page import DashboardPage
from cryptosafe.gui.contract_page import ContractPage
from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.database.contract_repository import ContractRepository
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.auth.auth_service import AuthService


class TestContractGuiIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)
        self.user_repo = UserRepository(self.conn)
        self.contract_repo = ContractRepository(self.conn)
        self.pwd_service = PasswordService(time_cost=1, memory_cost=8192, parallelism=1)
        self.auth_service = AuthService(self.user_repo, self.pwd_service)

        self.alice = self.auth_service.register_user("alice", "Secret123!", "Secret123!")
        self.bob = self.auth_service.register_user("bob", "Secret123!", "Secret123!")

        # Seed contracts for Alice and Bob
        self.contract_repo.create_contract(
            contract_number="CTR-ALICE-001",
            title="Perjanjian Rahasia Alice",
            parties="Alice & Partner Corp",
            created_by=self.alice.id,
            status="Draft",
        )
        self.contract_repo.create_contract(
            contract_number="CTR-BOB-001",
            title="Perjanjian Rahasia Bob",
            parties="Bob & Vendor Ltd",
            created_by=self.bob.id,
            status="Signed",
        )

        self.window = MainWindow(auth_service=self.auth_service)
        self.window.show()

        # Simulate Alice login
        self.window._on_login_requested("alice", "Secret123!")

    def tearDown(self):
        self.window.close()
        self.conn.close()

    def test_navigation_to_contract_page_and_back(self):
        # Starts on Dashboard (Index 1)
        self.assertEqual(self.window.stack.currentIndex(), 1)
        self.assertIsInstance(self.window.stack.currentWidget(), DashboardPage)

        # Click Contract Management button on header
        self.window.dashboard_page.btn_open_contract.click()

        # Should navigate to ContractPage at Index 5
        self.assertEqual(self.window.stack.currentIndex(), 5)
        self.assertIsInstance(self.window.stack.currentWidget(), ContractPage)

        # Click back button on ContractPage
        self.window.contract_page.back_button.click()

        # Should return to Dashboard at Index 1
        self.assertEqual(self.window.stack.currentIndex(), 1)
        self.assertIsInstance(self.window.stack.currentWidget(), DashboardPage)

    def test_navigation_via_card_button(self):
        self.assertEqual(self.window.stack.currentIndex(), 1)

        # Click button on dashboard feature card
        self.window.dashboard_page.btn_open_contract_card.click()

        self.assertEqual(self.window.stack.currentIndex(), 5)
        self.assertIsInstance(self.window.stack.currentWidget(), ContractPage)

    def test_unauthenticated_user_cannot_access_contract_page(self):
        # Log out Alice
        self.window.dashboard_page.logout_button.click()
        self.assertEqual(self.window.stack.currentIndex(), 0)

        # Force dashboard to unauthenticated guest state
        self.window._current_user = None
        self.window.dashboard_page.set_user("")
        self.window.stack.setCurrentIndex(1)

        # Attempt to open ContractPage as guest
        self.window.dashboard_page.btn_open_contract.click()

        # Navigation should be denied (not on Index 5)
        self.assertNotEqual(self.window.stack.currentIndex(), 5)

    def test_contract_data_isolated_by_active_user(self):
        # Alice is logged in: navigate to ContractPage
        self.window.dashboard_page.btn_open_contract.click()
        self.assertEqual(self.window.stack.currentIndex(), 5)

        # Only Alice's contract should be shown
        alice_table = self.window.contract_page.contract_table
        self.assertEqual(alice_table.rowCount(), 1)
        self.assertEqual(alice_table.item(0, 1).text(), "CTR-ALICE-001")
        self.assertEqual(alice_table.item(0, 2).text(), "Perjanjian Rahasia Alice")

        # Back to dashboard and logout
        self.window.contract_page.back_button.click()
        self.window.dashboard_page.logout_button.click()

        # Log in as Bob
        self.window._on_login_requested("bob", "Secret123!")
        self.window.dashboard_page.btn_open_contract.click()

        # Only Bob's contract should be shown
        bob_table = self.window.contract_page.contract_table
        self.assertEqual(bob_table.rowCount(), 1)
        self.assertEqual(bob_table.item(0, 1).text(), "CTR-BOB-001")
        self.assertEqual(bob_table.item(0, 2).text(), "Perjanjian Rahasia Bob")

    def test_logout_clears_contract_page(self):
        # Alice is logged in and opens contract page
        self.window.dashboard_page.btn_open_contract.click()
        self.assertEqual(self.window.contract_page.contract_table.rowCount(), 1)

        # Back and logout
        self.window.contract_page.back_button.click()
        self.window.dashboard_page.logout_button.click()

        # Verify contract_page is cleared
        self.assertIsNone(self.window.contract_page._user_id)
        self.assertEqual(self.window.contract_page.contract_table.rowCount(), 0)


if __name__ == "__main__":
    unittest.main()

