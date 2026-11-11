"""Authentication application service orchestrating user registration and verification."""

from __future__ import annotations

import re
import logging
from typing import Callable
from pathlib import Path
from cryptosafe.common.errors import AuthenticationError, AuthenticationCancelledError, ValidationError
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.auth.usb_token_service import UsbTokenService
from cryptosafe.auth.face_service import FaceService
from cryptosafe.auth.rate_limiter import LoginRateLimiter
from cryptosafe.auth.session_manager import SessionManager, UserSession
from cryptosafe.database.user_repository import UserRepository, User

logger = logging.getLogger("cryptosafe.auth")

class AuthService:
    """Service handling registration, sequential multi-factor verification, and session management."""

    def __init__(
        self,
        user_repo: UserRepository,
        password_service: PasswordService | None = None,
        usb_service: UsbTokenService | None = None,
        face_service: FaceService | None = None,
        rate_limiter: LoginRateLimiter | None = None,
        session_manager: SessionManager | None = None,
    ):
        self._user_repo = user_repo
        self._password_service = password_service or PasswordService()
        self._usb_service = usb_service
        self._face_service = face_service
        self._rate_limiter = rate_limiter or LoginRateLimiter()
        self._session_manager = session_manager or SessionManager()

    @property
    def session_manager(self) -> SessionManager:
        return self._session_manager

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

    def authenticate_user(
        self,
        username: str,
        password: str,
        usb_token_path: Path | None = None,
        face_image=None,
        face_capture_callback: Callable[[], object] | None = None,
    ) -> User:
        """Authenticate user across active MFA factors: password, USB token, and face recognition.

        Enforces sequential factor verification (Password -> USB -> Face), rate limiting/throttling,
        and establishes a UserSession only upon full success.
        """
        clean_username = username.strip()
        if not clean_username or not password:
            self._session_manager.terminate_session()
            raise AuthenticationError("Username atau password salah.")

        # Check rate limiting / lockout
        self._rate_limiter.check_rate_limit(clean_username)

        # Invalidate any prior active session before attempting new authentication
        self._session_manager.terminate_session()

        try:
            user = self._user_repo.get_by_username(clean_username)
            if not user or not user.is_active:
                logger.warning("Authentication failed for provided username credentials.")
                raise AuthenticationError("Username atau password salah.")

            # Factor 1: Password (Argon2id)
            if not self._password_service.verify_password(password, user.password_hash):
                logger.warning("Authentication failed: invalid credentials.")
                raise AuthenticationError("Username atau password salah.")

            # Factor 2: USB Token Challenge-Response (if enrolled)
            if self._usb_service and self._usb_service.has_active_token(user.id):
                target_path = usb_token_path
                if target_path is None:
                    target_path = self._usb_service.detect_token_file()

                if target_path is None or not target_path.exists():
                    raise AuthenticationError("Akun ini memerlukan USB token. Pasang token terdaftar untuk melanjutkan.")

                challenge = self._usb_service.create_challenge(user.id)
                self._usb_service.verify_token(user.id, challenge.challenge_id, target_path)
                logger.info("MFA Step 2 (USB) passed for user: %s", user.username)

            # Factor 3: Face Recognition Biometrics (if enrolled)
            if self._face_service and self._face_service.has_active_profile(user.id):
                target_image = face_image
                liveness_frames = None
                if target_image is None and face_capture_callback is not None:
                    try:
                        captured_result = face_capture_callback()
                        if isinstance(captured_result, tuple):
                            target_image, liveness_frames = captured_result
                        else:
                            target_image = captured_result
                    except AuthenticationCancelledError:
                        raise
                    except Exception as err:
                        logger.warning("Face capture callback failed: %s", err)
                        raise AuthenticationError(f"Gagal memindai wajah: {err}")

                    if target_image is None:
                        raise AuthenticationCancelledError("Verifikasi wajah dibatalkan. Login tidak dapat dilanjutkan.")

                if target_image is None:
                    target_image = self._face_service.capture_camera_frame()

                self._face_service.verify_face(
                    user.id, target_image, password=password, liveness_frames=liveness_frames
                )
                logger.info("MFA Step 3 (Face Biometrics) passed for user: %s", user.username)

            # All active factors verified -> clear failures and establish session
            self._rate_limiter.record_success(clean_username)
            self._session_manager.create_session(user.id, user.username)
            logger.info("All authentication factors passed successfully for user: %s", user.username)
            return user

        except AuthenticationCancelledError:
            self._session_manager.terminate_session()
            # Do NOT record failure on rate limiter for voluntary user cancellation
            logger.info("Authentication cancelled by user during biometric step.")
            raise
        except AuthenticationError:
            self._session_manager.terminate_session()
            self._rate_limiter.record_failure(clean_username)
            raise

    def logout(self) -> None:
        """Terminate the active session and destroy temporary session credentials."""
        session = self._session_manager.get_current_session()
        if session:
            logger.info("Logging out user: %s", session.username)
        self._session_manager.terminate_session()

