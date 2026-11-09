"""USB Token Challenge-Response authentication service using cryptography library."""

import json
import logging
import secrets
import string
import sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hmac as std_hmac
from cryptography.hazmat.primitives import hashes, hmac
from cryptosafe.common.errors import AuthenticationError, ValidationError
from cryptosafe.database.usb_repository import UsbRepository, UsbCredential

logger = logging.getLogger("cryptosafe.usb")

TOKEN_FILENAME = "cryptosafe_token.key"
TOKEN_VERSION = 1
CLIENT_KEY_CONTEXT = b"cryptosafe-usb-client-key"

@dataclass(frozen=True)
class UsbChallenge:
    challenge_id: str
    user_id: int
    challenge_bytes: bytes
    expires_at: datetime

class UsbTokenService:
    """Service managing USB token detection, enrollment, and HMAC-SHA256 challenge-response."""

    def __init__(self, usb_repo: UsbRepository):
        self._repo = usb_repo
        self._active_challenges: dict[str, UsbChallenge] = {}

    def get_candidate_drive_roots(self) -> list[Path]:
        """Detect potential removable drive roots or common mount points."""
        candidates: list[Path] = []
        if sys.platform.startswith("win"):
            # Scan Windows drive letters D: through Z:
            for letter in string.ascii_uppercase[3:]:
                drive_path = Path(f"{letter}:\\")
                if drive_path.exists():
                    candidates.append(drive_path)
        else:
            # Linux / macOS common mount points
            for mount_root in [Path("/media"), Path("/mnt"), Path("/Volumes")]:
                if mount_root.exists():
                    for sub in mount_root.iterdir():
                        if sub.is_dir():
                            candidates.append(sub)
        return candidates

    def detect_token_file(self, search_paths: list[Path] | None = None) -> Path | None:
        """Scan specified paths or candidate drives for a valid token file."""
        paths_to_check = search_paths if search_paths is not None else self.get_candidate_drive_roots()
        for candidate in paths_to_check:
            token_path = candidate / TOKEN_FILENAME if candidate.is_dir() else candidate
            if token_path.is_file():
                try:
                    with open(token_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("version") == TOKEN_VERSION and "token_id" in data and "token_secret" in data:
                        return token_path
                except (json.JSONDecodeError, OSError):
                    continue
        return None

    def enroll_token(self, user_id: int, target_dir: Path) -> tuple[UsbCredential, Path]:
        """Generate a new token secret, write to target media, and persist verifier in DB."""
        if not target_dir.exists() or not target_dir.is_dir():
            raise ValidationError("Direktori drive USB target tidak valid atau tidak dapat diakses.")

        token_id = secrets.token_hex(16)
        raw_secret = secrets.token_bytes(32)

        # Derive ClientKey = HMAC(raw_secret, CLIENT_KEY_CONTEXT)
        h_client = hmac.HMAC(raw_secret, hashes.SHA256())
        h_client.update(CLIENT_KEY_CONTEXT)
        client_key = h_client.finalize()

        # Derive StoredKey = SHA256(ClientKey) -> stored as verifier in DB
        digest = hashes.Hash(hashes.SHA256())
        digest.update(client_key)
        stored_key = digest.finalize()

        # Write token file to USB media
        token_file_path = target_dir / TOKEN_FILENAME
        payload = {
            "version": TOKEN_VERSION,
            "token_id": token_id,
            "token_secret": raw_secret.hex(),
        }
        try:
            with open(token_file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except OSError as err:
            raise ValidationError(f"Gagal menulis file token ke media USB: {err}")

        # Persist verifier in database (never raw_secret)
        credential = self._repo.create_credential(user_id, token_id, stored_key.hex())
        logger.info("USB token enrolled successfully for user_id=%s [token_id=%s]", user_id, token_id)
        return credential, token_file_path

    def has_active_token(self, user_id: int) -> bool:
        """Check if user has an active enrolled USB token."""
        return self._repo.get_active_by_user_id(user_id) is not None

    def revoke_token(self, user_id: int) -> bool:
        """Revoke active USB token for user."""
        success = self._repo.revoke_by_user_id(user_id)
        if success:
            logger.info("USB token revoked for user_id=%s", user_id)
        return success

    def create_challenge(self, user_id: int, ttl_seconds: int = 60) -> UsbChallenge:
        """Create a cryptographically random, one-time, time-bound challenge."""
        now = datetime.now(timezone.utc)
        challenge = UsbChallenge(
            challenge_id=secrets.token_hex(16),
            user_id=user_id,
            challenge_bytes=secrets.token_bytes(32),
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        self._active_challenges[challenge.challenge_id] = challenge
        return challenge

    def verify_token(self, user_id: int, challenge_id: str, token_path: Path) -> bool:
        """Authenticate USB token via HMAC-SHA256 challenge-response."""
        # 1. Challenge validation & single-use consumption
        if challenge_id not in self._active_challenges:
            raise AuthenticationError("Challenge USB tidak valid atau sudah digunakan (replay detected).")

        challenge = self._active_challenges.pop(challenge_id)
        now = datetime.now(timezone.utc)
        if now > challenge.expires_at:
            raise AuthenticationError("Challenge USB telah kedaluwarsa.")

        if challenge.user_id != user_id:
            raise AuthenticationError("Challenge USB tidak cocok dengan akun pengguna.")

        # 2. Token file validation
        if not token_path.is_file():
            raise AuthenticationError("File token USB tidak ditemukan pada media.")

        try:
            with open(token_path, "r", encoding="utf-8") as f:
                token_data = json.load(f)
            token_id = token_data["token_id"]
            raw_secret = bytes.fromhex(token_data["token_secret"])
            if len(raw_secret) != 32:
                raise ValueError("Panjang secret tidak valid.")
        except Exception:
            raise AuthenticationError("Format file token USB rusak atau tidak valid.")

        # 3. Database credential check
        credential = self._repo.get_active_by_user_id(user_id)
        if not credential:
            # Check if it was revoked
            revoked_cred = self._repo.get_by_token_id(token_id)
            if revoked_cred and revoked_cred.revoked_at is not None:
                raise AuthenticationError("Token USB ini telah dicabut (revoked) dan tidak dapat digunakan.")
            raise AuthenticationError("Akun tidak memiliki token USB aktif yang terdaftar.")

        if credential.token_id != token_id:
            raise AuthenticationError("Token USB tidak cocok dengan akun yang sedang login.")

        # 4. RFC 5802 HMAC-SHA256 Challenge-Response Verification
        # Client side computation:
        h_client = hmac.HMAC(raw_secret, hashes.SHA256())
        h_client.update(CLIENT_KEY_CONTEXT)
        client_key = h_client.finalize()

        stored_key = bytes.fromhex(credential.verifier)

        h_sig = hmac.HMAC(stored_key, hashes.SHA256())
        h_sig.update(challenge.challenge_bytes)
        client_sig = h_sig.finalize()

        proof = bytes(a ^ b for a, b in zip(client_key, client_sig))

        # Server side verification:
        h_expected = hmac.HMAC(stored_key, hashes.SHA256())
        h_expected.update(challenge.challenge_bytes)
        expected_sig = h_expected.finalize()

        recovered_key = bytes(a ^ b for a, b in zip(proof, expected_sig))

        digest = hashes.Hash(hashes.SHA256())
        digest.update(recovered_key)
        recovered_stored = digest.finalize()

        if not std_hmac.compare_digest(recovered_stored, stored_key):
            logger.warning("USB token verification failed: secret mismatch for user_id=%s", user_id)
            raise AuthenticationError("Verifikasi secret token USB gagal.")

        logger.info("USB token authenticated successfully for user_id=%s", user_id)
        return True
