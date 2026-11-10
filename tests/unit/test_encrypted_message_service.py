import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from cryptosafe.common.errors import ValidationError
from cryptosafe.crypto.text_crypto_service import TextCryptoService
from cryptosafe.database.encrypted_message_service import EncryptedMessageService


class TestEncryptedMessageService(unittest.TestCase):

    def setUp(self):
        self.repository = Mock()
        self.crypto_service = TextCryptoService()
        self.service = EncryptedMessageService(
            repository=self.repository,
            crypto_service=self.crypto_service,
        )

        self.contract_id = 1
        self.user_id = 10
        self.vigenere_key = "RAHASIA"
        self.aes_key = "correct horse battery staple"
        self.plaintext = "Isi kontrak bersifat rahasia."

    def test_create_encrypts_before_saving(self):
        self.service.create_encrypted_message(
            contract_id=self.contract_id,
            user_id=self.user_id,
            content_type="note",
            label="Catatan rahasia",
            plaintext=self.plaintext,
            vigenere_key=self.vigenere_key,
            aes_key_material=self.aes_key,
        )

        self.repository.create_message.assert_called_once()

        saved_ciphertext = self.repository.create_message.call_args.kwargs[
            "ciphertext"
        ]

        self.assertNotEqual(saved_ciphertext, self.plaintext)
        self.assertIsInstance(saved_ciphertext, str)

    def test_decrypt_returns_original_plaintext(self):
        envelope = self.crypto_service.encrypt(
            plaintext=self.plaintext,
            vigenere_key=self.vigenere_key,
            aes_key_material=self.aes_key,
        )

        message = SimpleNamespace(
            id=1,
            ciphertext=envelope,
        )
        self.repository.get_by_id.return_value = message

        result_message, decrypted_text = self.service.get_decrypted_message(
            message_id=1,
            user_id=self.user_id,
            vigenere_key=self.vigenere_key,
            aes_key_material=self.aes_key,
        )

        self.assertEqual(result_message, message)
        self.assertEqual(decrypted_text, self.plaintext)
        self.repository.get_by_id.assert_called_once_with(1, self.user_id)

    def test_wrong_aes_key_fails_decryption(self):
        envelope = self.crypto_service.encrypt(
            plaintext=self.plaintext,
            vigenere_key=self.vigenere_key,
            aes_key_material=self.aes_key,
        )

        self.repository.get_by_id.return_value = SimpleNamespace(
            id=1,
            ciphertext=envelope,
        )

        with self.assertRaises(Exception):
            self.service.get_decrypted_message(
                message_id=1,
                user_id=self.user_id,
                vigenere_key=self.vigenere_key,
                aes_key_material="wrong password",
            )

    def test_missing_message_is_rejected(self):
        self.repository.get_by_id.return_value = None

        with self.assertRaises(ValidationError):
            self.service.get_decrypted_message(
                message_id=999,
                user_id=self.user_id,
                vigenere_key=self.vigenere_key,
                aes_key_material=self.aes_key,
            )

    def test_empty_plaintext_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.service.create_encrypted_message(
                contract_id=self.contract_id,
                user_id=self.user_id,
                content_type="note",
                label="Catatan kosong",
                plaintext="   ",
                vigenere_key=self.vigenere_key,
                aes_key_material=self.aes_key,
            )

        self.repository.create_message.assert_not_called()

    def test_list_messages_delegates_to_repository(self):
        expected = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        self.repository.list_by_contract.return_value = expected

        result = self.service.list_by_contract(
            self.contract_id,
            self.user_id,
        )

        self.assertEqual(result, expected)
        self.repository.list_by_contract.assert_called_once_with(
            self.contract_id,
            self.user_id,
        )

    def test_delete_message_delegates_to_repository(self):
        self.repository.delete_message.return_value = True

        result = self.service.delete_message(1, self.user_id)

        self.assertTrue(result)
        self.repository.delete_message.assert_called_once_with(
            1,
            self.user_id,
        )


if __name__ == "__main__":
    unittest.main()
