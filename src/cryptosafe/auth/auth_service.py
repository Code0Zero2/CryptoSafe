"""Authentication application service orchestrating user registration and verification."""

import re
import logging
from cryptosafe.common.errors import AuthenticationError, ValidationError
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.database.user_repository import UserRepository, User

logger = logging.getLogger("cryptosafe.auth")

class AuthService:
    """Service handling registration and credential verification."""

    def __init__(self, user_repo: UserRepository, password_service: PasswordService | None = None):
        self._user_repo = user_repo
        self._password_service = password_service or PasswordService()

    def register_user(self, username: str, password: str, password_confirm: str) -> User:
        """Register a new user account."""
        clean_username = username.strip()
        if not clean_username or len(clean_username) < 3 or len(clean_username) > 32:
            raise ValidationError("Username harus memiliki panjang antara 3 hingga 32 karakter.")

        if not re.match(r"^[a-zA-Z0-9_-]+$", clean_username):
            raise ValidationError("Username hanya boleh memuat huruf, angka, tanda minus (-), atau garis bawah (_).")

        if password != password_confirm:
            raise ValidationError("Konfirmasi password tidak cocok.")

        password_hash = self._password_service.hash_password(password)
        user = self._user_repo.create_user(clean_username, password_hash)
        logger.info("User registered successfully: %s", user.username)
        return user

    def authenticate_user(self, username: str, password: str) -> User:
        """Authenticate user by username and password.

        Uses generic error messages to prevent username enumeration.
        """
        clean_username = username.strip()
        if not clean_username or not password:
            raise AuthenticationError("Username atau password salah.")

        user = self._user_repo.get_by_username(clean_username)
        if not user or not user.is_active:
            # Dummy verify could be done to mitigate timing attacks if needed,
            # but Argon2id verify returns false directly.
            logger.warning("Authentication failed for provided username credentials.")
            raise AuthenticationError("Username atau password salah.")

        if not self._password_service.verify_password(password, user.password_hash):
            logger.warning("Authentication failed: invalid credentials.")
            raise AuthenticationError("Username atau password salah.")

        logger.info("User authenticated successfully: %s", user.username)
        return user
