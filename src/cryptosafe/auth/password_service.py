"""Password hashing and verification service using Argon2id."""

import argon2
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from cryptosafe.common.errors import ValidationError

class PasswordService:
    """Argon2id password hashing and verification service."""

    def __init__(self, time_cost: int = 3, memory_cost: int = 65536, parallelism: int = 4):
        # RFC 9106 recommended parameters for Argon2id
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            type=argon2.Type.ID,
        )

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password with Argon2id using fresh salt."""
        if not password or len(password) < 6:
            raise ValidationError("Password minimal harus 6 karakter.")
        return self._hasher.hash(password)

    def verify_password(self, password: str, encoded_hash: str) -> bool:
        """Verify password against encoded Argon2id hash. Returns True on match, False otherwise."""
        if not password or not encoded_hash:
            return False
        try:
            return self._hasher.verify(encoded_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

