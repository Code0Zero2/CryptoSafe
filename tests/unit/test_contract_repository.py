
"""Unit tests for ContractRepository."""

import unittest
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.database.contract_repository import ContractRepository
from cryptosafe.common.errors import ValidationError


class TestContractRepository(unittest.TestCase):

    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)

        self.user_repo = UserRepository(self.conn)
        self.contract_repo = ContractRepository(self.conn)

        self.user = self.user_repo.create_user(
            "contract_owner",
            "argon2_test_hash",
        )

        self.other_user = self.user_repo.create_user(
            "other_owner",
            "argon2_test_hash",
        )

    def tearDown(self):
        self.conn.close()

    def test_create_contract(self):
        contract = self.contract_repo.create_contract(
            contract_number="CTR-001",
            title="Perjanjian Kerja Sama",
            parties="PT Alpha dan PT Beta",
            created_by=self.user.id,
        )

        self.assertIsNotNone(contract.id)
        self.assertEqual(contract.contract_number, "CTR-001")
        self.assertEqual(contract.status, "Draft")
        self.assertEqual(contract.created_by, self.user.id)

    def test_duplicate_contract_number_rejected(self):
        self.contract_repo.create_contract(
            "CTR-001",
            "Kontrak Pertama",
            "PT Alpha",
            self.user.id,
        )

        with self.assertRaises(ValidationError):
            self.contract_repo.create_contract(
                "CTR-001",
                "Kontrak Kedua",
                "PT Beta",
                self.user.id,
            )

    def test_empty_required_fields_rejected(self):
        with self.assertRaises(ValidationError):
            self.contract_repo.create_contract(
                "",
                "Judul",
                "PT Alpha",
                self.user.id,
            )

    def test_list_contracts_by_user(self):
        self.contract_repo.create_contract(
            "CTR-001",
            "Kontrak A",
            "PT Alpha",
            self.user.id,
        )

        self.contract_repo.create_contract(
            "CTR-002",
            "Kontrak B",
            "PT Beta",
            self.user.id,
        )

        self.contract_repo.create_contract(
            "CTR-003",
            "Kontrak C",
            "PT Gamma",
            self.other_user.id,
        )

        contracts = self.contract_repo.list_by_user(self.user.id)

        self.assertEqual(len(contracts), 2)
        self.assertTrue(
            all(c.created_by == self.user.id for c in contracts)
        )

    def test_user_cannot_access_other_users_contract(self):
        contract = self.contract_repo.create_contract(
            "CTR-001",
            "Kontrak Rahasia",
            "PT Alpha",
            self.user.id,
        )

        result = self.contract_repo.get_by_id(
            contract.id,
            self.other_user.id,
        )

        self.assertIsNone(result)

    def test_update_contract_status(self):
        contract = self.contract_repo.create_contract(
            "CTR-001",
            "Kontrak",
            "PT Alpha",
            self.user.id,
        )

        updated = self.contract_repo.update_status(
            contract.id,
            self.user.id,
            "Review",
        )

        self.assertEqual(updated.status, "Review")

    def test_invalid_status_rejected(self):
        contract = self.contract_repo.create_contract(
            "CTR-001",
            "Kontrak",
            "PT Alpha",
            self.user.id,
        )

        with self.assertRaises(ValidationError):
            self.contract_repo.update_status(
                contract.id,
                self.user.id,
                "Invalid",
            )

    def test_delete_contract(self):
        contract = self.contract_repo.create_contract(
            "CTR-001",
            "Kontrak",
            "PT Alpha",
            self.user.id,
        )

        deleted = self.contract_repo.delete_contract(
            contract.id,
            self.user.id,
        )

        self.assertTrue(deleted)
        self.assertIsNone(
            self.contract_repo.get_by_id(
                contract.id,
                self.user.id,
            )
        )


if __name__ == "__main__":
    unittest.main()
