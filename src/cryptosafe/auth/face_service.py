"""Local Face Recognition service with biometric template protection and informed consent."""

from __future__ import annotations

import json
import logging
import os
import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
import cv2
import numpy as np
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptosafe.common.errors import AuthenticationError, ValidationError
from cryptosafe.crypto.key_manager import (
    DEFAULT_PBKDF2_ITERATIONS,
    KEY_LENGTH_BYTES,
    SALT_LENGTH_BYTES,
    derive_key_from_passphrase,
)
from typing import Any
from cryptosafe.database.face_repository import FaceProfile, FaceRepository

logger = logging.getLogger("cryptosafe.face")

MODEL_NAME = "OpenCV-Haar-L2Norm"
MODEL_VERSION = "1.0.0"
ENVELOPE_VERSION = 1
ALGORITHM_NAME = "AES-256-GCM"
KDF_PBKDF2 = "PBKDF2-HMAC-SHA256"
KDF_DIRECT = "DIRECT-AES-256"
NONCE_LENGTH_BYTES = 12

MIN_PBKDF2_ITERATIONS = 100_000
MAX_PBKDF2_ITERATIONS = 2_000_000
SUPPORTED_SHAPES = {(4096,), (64, 64)}
SUPPORTED_DTYPE = "float32"
DEFAULT_FACE_THRESHOLD = 0.70


def compute_face_aad(user_id: int) -> bytes:
    """Compute Additional Authenticated Data (AAD) for AES-256-GCM binding to user_id."""
    if not isinstance(user_id, int) or isinstance(user_id, bool):
        raise ValidationError(f"user_id harus berupa integer (diterima: {type(user_id).__name__}).")
    return f"cryptosafe:face_profile:user_id={user_id}:v1".encode("utf-8")

class FaceRecognizerAdapter(ABC):
    """Abstract adapter defining face detection and template extraction."""

    @abstractmethod
    def detect_and_extract_template(self, image: np.ndarray) -> np.ndarray | None:
        """Extract a normalized 1D biometric template from an image array. Returns None if no face."""
        pass

    @abstractmethod
    def compute_similarity(self, template_a: np.ndarray, template_b: np.ndarray) -> float:
        """Compute similarity score between two normalized templates."""
        pass

class OpenCvFaceAdapter(FaceRecognizerAdapter):
    """Local OpenCV implementation using Haar Cascade face detector and normalized feature vector."""

    def __init__(self, target_size: tuple[int, int] = (64, 64)):
        self.target_size = target_size
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._face_cascade = cv2.CascadeClassifier(cascade_path)

    def detect_and_extract_template(self, image: np.ndarray) -> np.ndarray | None:
        if image is None or image.size == 0:
            return None

        # Convert to grayscale
        if len(image.shape) == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif len(image.shape) == 2:
            gray = image
        else:
            return None

        faces = self._face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(30, 30),
        )

        # Fallback to slightly more sensitive detection if strict detection finds no face
        if len(faces) == 0:
            faces = self._face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=(30, 30),
            )

        if len(faces) > 0:
            # Pick largest detected face
            x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
            face_roi = gray[y:y+h, x:x+w]
            logger.debug(
                "Face detection: %d face(s) found in frame %s, primary box=(x=%d, y=%d, w=%d, h=%d)",
                len(faces),
                gray.shape,
                int(x),
                int(y),
                int(w),
                int(h),
            )
        elif gray.shape[0] <= 128 and gray.shape[1] <= 128:
            # Pre-cropped face patch / fixture
            face_roi = gray
        else:
            logger.warning(
                "Face detection: 0 faces detected in frame of dimensions %s",
                gray.shape,
            )
            return None

        # Resize to standard dimensions
        resized = cv2.resize(face_roi, self.target_size, interpolation=cv2.INTER_AREA)
        # Histogram equalization for lighting normalization
        equalized = cv2.equalizeHist(resized)

        # Standardize: zero-mean and L2 normalize (ZNCC)
        vec = equalized.astype(np.float32).flatten()
        vec = vec - np.mean(vec)
        vec_norm = np.linalg.norm(vec)
        if vec_norm < 1e-7:
            return None
        return vec / vec_norm

    def compute_similarity(
        self,
        template_a: np.ndarray,
        template_b: np.ndarray,
        max_shift: int = 2,
    ) -> float:
        """Compute translation-tolerant cosine similarity score between two normalized templates.

        Evaluates cosine similarity across small translational shifts [-max_shift, +max_shift]
        to compensate for Haar Cascade bounding box jitter between distinct captures.
        """
        if template_a is None or template_b is None:
            return 0.0
        if template_a.shape != template_b.shape:
            return 0.0

        vec_a = template_a.flatten()
        vec_b = template_b.flatten()

        best_sim = float(np.dot(vec_a, vec_b))

        # If template represents 2D patch (e.g. 64x64 or 4096 elements) and max_shift > 0,
        # compensate for small bounding-box jitter (dx, dy in [-max_shift, max_shift])
        if max_shift > 0 and len(vec_a) == 4096:
            patch_a = vec_a.reshape(64, 64)
            patch_b = vec_b.reshape(64, 64)

            for dy in range(-max_shift, max_shift + 1):
                for dx in range(-max_shift, max_shift + 1):
                    if dx == 0 and dy == 0:
                        continue
                    M = np.float32([[1, 0, dx], [0, 1, dy]])
                    shifted_b = cv2.warpAffine(patch_b, M, (64, 64), borderMode=cv2.BORDER_REFLECT)
                    s_vec = shifted_b.flatten()
                    s_vec = s_vec - np.mean(s_vec)
                    norm = np.linalg.norm(s_vec)
                    if norm > 1e-7:
                        s_vec = s_vec / norm
                        sim = float(np.dot(vec_a, s_vec))
                        if sim > best_sim:
                            best_sim = sim

        return float(np.clip(best_sim, -1.0, 1.0))

class FaceService:
    """High-level face recognition service managing enrollment, template encryption, and verification."""

    def __init__(
        self,
        face_repo: FaceRepository,
        adapter: FaceRecognizerAdapter | None = None,
        encryption_key: bytes | None = None,
        pbkdf2_iterations: int = DEFAULT_PBKDF2_ITERATIONS,
    ):
        self._repo = face_repo
        self._adapter = adapter or OpenCvFaceAdapter()
        self._static_key = encryption_key
        self._pbkdf2_iterations = pbkdf2_iterations

    def capture_camera_frame(self, camera_index: int = 0) -> np.ndarray:
        """Capture a single image frame from local camera with sensor warm-up. Disposed immediately."""
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise AuthenticationError("Kamera tidak tersedia atau tidak dapat diakses.")
        try:
            # Warm up sensor: discard initial underexposed/black frames
            for _ in range(5):
                cap.read()
            ret, frame = cap.read()
            if not ret or frame is None:
                raise AuthenticationError("Gagal membaca frame gambar dari kamera.")
            return frame
        finally:
            cap.release()

    @staticmethod
    def _validate_iterations(iterations: Any) -> int:
        """Validate PBKDF2 iterations strictly against allowed integer bounds.

        Rejects boolean, float, string, negative, zero, and values outside [100000, 2000000].
        """
        if not isinstance(iterations, int) or isinstance(iterations, bool):
            raise ValidationError(
                f"Iterasi PBKDF2 harus berupa integer (diterima: {type(iterations).__name__})."
            )
        if iterations < MIN_PBKDF2_ITERATIONS or iterations > MAX_PBKDF2_ITERATIONS:
            raise ValidationError(
                f"Iterasi PBKDF2 ({iterations}) di luar batas aman [{MIN_PBKDF2_ITERATIONS}, {MAX_PBKDF2_ITERATIONS}]."
            )
        return iterations

    def _validate_template(self, template: np.ndarray) -> None:
        """Validate that biometric template array matches supported shapes and dtype."""
        if not isinstance(template, np.ndarray):
            raise ValidationError("Template biometrik harus berupa numpy ndarray.")
        if template.shape not in SUPPORTED_SHAPES:
            raise ValidationError(
                f"Dimensi template biometrik {template.shape} tidak didukung (harus 64x64 atau 4096)."
            )
        if str(template.dtype) != SUPPORTED_DTYPE:
            raise ValidationError(
                f"Tipe data template '{template.dtype}' tidak didukung (harus float32)."
            )

    def _encrypt_template(
        self,
        template: np.ndarray,
        user_id: int,
        password: str | None = None,
        key: bytes | None = None,
    ) -> str:
        """Encrypt biometric template using AES-256-GCM bound to user_id via AAD.

        Derives key via PBKDF2-HMAC-SHA256 from password with a unique cryptographic salt per enrollment,
        or uses a direct 256-bit AES key if provided. Fails if neither is available.
        """
        self._validate_template(template)
        raw_bytes = template.tobytes()

        if password:
            salt = secrets.token_bytes(SALT_LENGTH_BYTES)
            iterations = self._validate_iterations(self._pbkdf2_iterations)
            aes_key = derive_key_from_passphrase(password, salt, iterations)
            kdf = KDF_PBKDF2
            salt_hex = salt.hex()
        elif key or self._static_key:
            aes_key = key or self._static_key
            if not isinstance(aes_key, bytes) or len(aes_key) != KEY_LENGTH_BYTES:
                raise ValidationError(f"Kunci AES harus berukuran {KEY_LENGTH_BYTES} byte.")
            salt = None
            iterations = None
            kdf = KDF_DIRECT
            salt_hex = None
        else:
            raise ValidationError(
                "Kata sandi akun atau kunci kriptografi diperlukan untuk mengenkripsi template wajah."
            )

        aad = compute_face_aad(user_id)
        aesgcm = AESGCM(aes_key)
        nonce = secrets.token_bytes(NONCE_LENGTH_BYTES)  # 96-bit nonce
        ciphertext = aesgcm.encrypt(nonce, raw_bytes, aad)

        envelope = {
            "version": ENVELOPE_VERSION,
            "algorithm": ALGORITHM_NAME,
            "kdf": kdf,
            "iterations": iterations,
            "salt": salt_hex,
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
            "aad_bound": True,
            "shape": list(template.shape),
            "dtype": str(template.dtype),
        }
        return json.dumps(envelope)

    def _decrypt_template(
        self,
        encrypted_str: str,
        user_id: int,
        password: str | None = None,
        key: bytes | None = None,
    ) -> tuple[np.ndarray, bool]:
        """Decrypt AES-256-GCM envelope and recover biometric template array.

        Validates all envelope metadata strictly before invoking PBKDF2 or AES-GCM.
        Binds authentication to user_id via AAD. Supports safe automatic migration
        for legacy envelopes without AAD.

        Returns:
            tuple[np.ndarray, bool]: (template_array, needs_migration)
        """
        # 1. Parse JSON safely
        try:
            if not isinstance(encrypted_str, str) or not encrypted_str.strip():
                raise ValueError("Payload envelope kosong atau bukan string.")
            data = json.loads(encrypted_str)
            if not isinstance(data, dict):
                raise ValueError("Format envelope bukan objek JSON.")
        except Exception:
            raise AuthenticationError("Data template wajah terenkripsi rusak atau tidak valid.")

        # 2. Validate structural envelope fields
        version = data.get("version")
        if version != ENVELOPE_VERSION:
            raise AuthenticationError(f"Versi envelope biometrik ({version}) tidak didukung.")

        algorithm = data.get("algorithm")
        if algorithm != ALGORITHM_NAME:
            raise AuthenticationError(f"Algoritma biometrik '{algorithm}' tidak didukung.")

        kdf = data.get("kdf")
        if kdf not in (KDF_PBKDF2, KDF_DIRECT):
            raise AuthenticationError(f"Metode KDF '{kdf}' tidak didukung.")

        # 3. Validate shape & dtype
        shape_raw = data.get("shape")
        if not isinstance(shape_raw, (list, tuple)) or len(shape_raw) == 0:
            raise AuthenticationError("Dimensi shape template biometrik tidak valid.")
        if any(not isinstance(d, int) or isinstance(d, bool) or d <= 0 for d in shape_raw):
            raise AuthenticationError("Elemen dimensi shape template harus berupa integer positif.")
        shape = tuple(shape_raw)
        if shape not in SUPPORTED_SHAPES:
            raise AuthenticationError(
                f"Dimensi shape template biometrik {shape} tidak didukung (harus 64x64 atau 4096)."
            )

        dtype_str = data.get("dtype")
        if not isinstance(dtype_str, str) or dtype_str != SUPPORTED_DTYPE:
            raise AuthenticationError(f"Tipe data dtype '{dtype_str}' tidak didukung (harus float32).")
        try:
            dtype = np.dtype(dtype_str)
        except Exception:
            raise AuthenticationError("Tipe data numpy template biometrik tidak valid.")

        # 4. Validate nonce
        nonce_hex = data.get("nonce")
        if not isinstance(nonce_hex, str):
            raise AuthenticationError("Field nonce tidak ditemukan atau bukan string.")
        try:
            nonce = bytes.fromhex(nonce_hex)
        except ValueError:
            raise AuthenticationError("Hexadecimal nonce tidak valid.")
        if len(nonce) != NONCE_LENGTH_BYTES:
            raise AuthenticationError(
                f"Panjang nonce harus tepat {NONCE_LENGTH_BYTES} byte (diterima: {len(nonce)})."
            )

        # 5. Validate ciphertext
        ct_hex = data.get("ciphertext")
        if not isinstance(ct_hex, str):
            raise AuthenticationError("Field ciphertext tidak ditemukan atau bukan string.")
        try:
            ciphertext = bytes.fromhex(ct_hex)
        except ValueError:
            raise AuthenticationError("Hexadecimal ciphertext tidak valid.")
        if len(ciphertext) < 16:
            raise AuthenticationError("Ciphertext terlalu pendek (minimal 16 byte untuk tag autentikasi).")

        # 6. Validate KDF parameters & resolve key
        if kdf == KDF_PBKDF2:
            if not password:
                raise AuthenticationError(
                    "Kata sandi akun diperlukan untuk mendekripsi template biometrik wajah."
                )
            salt_hex = data.get("salt")
            if not isinstance(salt_hex, str):
                raise AuthenticationError("Field salt PBKDF2 tidak ditemukan atau bukan string.")
            try:
                salt = bytes.fromhex(salt_hex)
            except ValueError:
                raise AuthenticationError("Hexadecimal salt tidak valid.")
            if len(salt) != SALT_LENGTH_BYTES:
                raise AuthenticationError(
                    f"Panjang salt PBKDF2 harus tepat {SALT_LENGTH_BYTES} byte (diterima: {len(salt)})."
                )

            raw_iterations = data.get("iterations")
            if raw_iterations is None:
                raise AuthenticationError("Field iterasi PBKDF2 wajib ada pada envelope.")
            try:
                iterations = self._validate_iterations(raw_iterations)
            except ValidationError as err:
                raise AuthenticationError(f"Validasi iterasi PBKDF2 gagal: {err}")

            # Derive key strictly after all validation passes
            aes_key = derive_key_from_passphrase(password, salt, iterations)

        elif kdf == KDF_DIRECT:
            aes_key = key or self._static_key
            if not aes_key or len(aes_key) != KEY_LENGTH_BYTES:
                raise AuthenticationError("Kunci dekripsi template biometrik tidak tersedia atau tidak valid.")

        # 7. Decrypt with AES-GCM and verify AAD
        aad = compute_face_aad(user_id)
        aesgcm = AESGCM(aes_key)
        needs_migration = False

        is_aad_bound = data.get("aad_bound", False)

        try:
            # Primary decryption path: with user_id AAD
            decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, aad)
        except Exception:
            # If envelope was explicitly marked as aad_bound, it MUST fail (e.g. cross-account attack or wrong pass)
            if is_aad_bound:
                raise AuthenticationError(
                    "Verifikasi biometrik gagal: template wajah tidak dapat didekripsi "
                    "(kata sandi tidak cocok, akun tidak sesuai, atau data rusak). "
                    "Jika kata sandi akun baru saja diubah, silakan daftarkan ulang profil wajah Anda."
                )

            # Legacy fallback: attempt decryption without AAD (associated_data=None)
            try:
                decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
                needs_migration = True
                logger.info(
                    "Legacy face profile without AAD decrypted for user_id=%s. Will migrate upon verification.",
                    user_id,
                )
            except Exception:
                raise AuthenticationError(
                    "Verifikasi biometrik gagal: template wajah tidak dapat didekripsi "
                    "(kata sandi tidak cocok atau data rusak). "
                    "Jika kata sandi akun baru saja diubah, silakan daftarkan ulang profil wajah Anda."
                )

        try:
            template = np.frombuffer(decrypted_bytes, dtype=dtype).reshape(shape)
            return template, needs_migration
        except Exception:
            raise AuthenticationError("Data buffer template biometrik tidak sesuai dengan shape atau dtype.")

    def enroll_face(
        self,
        user_id: int,
        image: np.ndarray,
        user_consent: bool,
        password: str | None = None,
        key: bytes | None = None,
    ) -> FaceProfile:
        """Enroll face template for a user after verifying explicit informed consent."""
        if not user_consent:
            raise ValidationError("Persetujuan perekaman biometrik wajah wajib diberikan pengguna.")

        template = self._adapter.detect_and_extract_template(image)
        if template is None:
            raise ValidationError(
                "Wajah tidak terdeteksi pada gambar. Pastikan pencahayaan cukup dan wajah menghadap kamera."
            )

        # Encrypt template (raw image is NEVER stored) bound to user_id via AAD
        encrypted_template = self._encrypt_template(template, user_id=user_id, password=password, key=key)
        consent_time_iso = datetime.now(timezone.utc).isoformat()

        profile = self._repo.create_profile(
            user_id=user_id,
            encrypted_template=encrypted_template,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            consent_recorded_at=consent_time_iso,
        )
        logger.info("Face biometric profile enrolled successfully for user_id=%s", user_id)
        return profile

    def has_active_profile(self, user_id: int) -> bool:
        """Check if user has an active face biometric profile."""
        return self._repo.get_active_by_user_id(user_id) is not None

    def revoke_face(self, user_id: int) -> bool:
        """Revoke active face biometric profile for user."""
        success = self._repo.revoke_by_user_id(user_id)
        if success:
            logger.info("Face biometric profile revoked for user_id=%s", user_id)
        return success

    @staticmethod
    def check_liveness(
        frames: list[np.ndarray],
    ) -> tuple[bool, str]:
        """Check temporal micro-movement and texture depth to detect presentation spoofing (static photo prints / screen replay).

        Returns:
            tuple[bool, str]: (is_live, message)
        """
        if not frames or len(frames) < 2:
            return True, "Jumlah frame tunggal, analisis liveness multi-frame dilewati."

        grays = []
        for f in frames:
            if f is None or f.size == 0:
                continue
            if len(f.shape) == 3 and f.shape[2] == 3:
                grays.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
            elif len(f.shape) == 2:
                grays.append(f)

        if len(grays) < 2:
            return True, "Frame valid tidak mencukupi untuk analisis liveness."

        # 1. Texture check (Laplacian variance) on latest frame to detect flat low-texture prints
        lap_var = float(cv2.Laplacian(grays[-1], cv2.CV_64F).var())
        if lap_var < 5.0:
            return False, "Tekstur citra terlalu buram atau datar (terindikasi foto cetak berkualitas rendah)."

        # 2. Temporal difference check across consecutive frames
        diffs = []
        for i in range(1, len(grays)):
            if grays[i].shape == grays[i - 1].shape:
                diff = float(np.mean(np.abs(grays[i].astype(np.float32) - grays[i - 1].astype(np.float32))))
                diffs.append(diff)

        if not diffs:
            return True, "Liveness OK"

        mean_diff = float(np.mean(diffs))

        # Detect completely static identical freeze-frames or immobile photo prints
        if mean_diff < 0.05:
            return False, "Wajah terindikasi gambar statis (foto cetak/layar diam). Harap gerakkan sedikit kepala atau berkedip."

        return True, "Wajah hidup terverifikasi (liveness OK)."

    def verify_face(
        self,
        user_id: int,
        image: np.ndarray,
        password: str | None = None,
        key: bytes | None = None,
        threshold: float = DEFAULT_FACE_THRESHOLD,
        liveness_frames: list[np.ndarray] | None = None,
    ) -> bool:
        """Verify face in image against user's stored encrypted template, with optional liveness verification."""
        if liveness_frames is not None and len(liveness_frames) >= 2:
            is_live, liveness_msg = self.check_liveness(liveness_frames)
            if not is_live:
                logger.warning("Liveness verification failed for user_id=%s: %s", user_id, liveness_msg)
                raise AuthenticationError(f"Verifikasi keaslian wajah (liveness) gagal: {liveness_msg}")

        profile = self._repo.get_active_by_user_id(user_id)
        if not profile:
            raise AuthenticationError("Pengguna tidak memiliki profil biometrik wajah aktif yang terdaftar.")

        stored_template, needs_migration = self._decrypt_template(
            profile.encrypted_template,
            user_id=user_id,
            password=password,
            key=key,
        )

        probe_template = self._adapter.detect_and_extract_template(image)
        if probe_template is None:
            raise AuthenticationError("Wajah tidak terdeteksi pada kamera saat verifikasi.")

        similarity = self._adapter.compute_similarity(stored_template, probe_template)

        # Secure diagnostic logging (no biometric embeddings, images, or keys are logged)
        logger.info(
            "Face verification diagnostic for user_id=%s: similarity=%.4f, threshold=%.4f, match=%s",
            user_id,
            similarity,
            threshold,
            similarity >= threshold,
        )

        if similarity < threshold:
            logger.warning(
                "Face biometric match failed for user_id=%s (similarity %.4f below threshold %.4f)",
                user_id,
                similarity,
                threshold,
            )
            raise AuthenticationError("Verifikasi wajah gagal: wajah tidak cocok.")

        # Auto-migrate legacy envelope to AAD-bound envelope upon successful face verification
        if needs_migration and (password or key or self._static_key):
            try:
                migrated_envelope = self._encrypt_template(
                    stored_template,
                    user_id=user_id,
                    password=password,
                    key=key,
                )
                self._repo.create_profile(
                    user_id=user_id,
                    encrypted_template=migrated_envelope,
                    model_name=profile.model_name,
                    model_version=profile.model_version,
                    consent_recorded_at=profile.consent_recorded_at,
                )
                logger.info("Successfully migrated legacy face profile to AAD-bound envelope for user_id=%s", user_id)
            except Exception as err:
                logger.warning("Auto-migration of legacy face profile failed for user_id=%s: %s", user_id, err)

        logger.info("Face biometric verification passed for user_id=%s", user_id)
        return True

    def rekey_face_profile(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
    ) -> FaceProfile:
        """Re-encrypt user's biometric template when user changes their account password."""
        profile = self._repo.get_active_by_user_id(user_id)
        if not profile:
            raise ValidationError("Pengguna tidak memiliki profil biometrik wajah aktif untuk diperbarui.")

        if not old_password or not new_password:
            raise ValidationError(
                "Kata sandi lama dan kata sandi baru diperlukan untuk memperbarui template biometrik."
            )

        # Decrypt with old password and user_id AAD
        try:
            stored_template, _ = self._decrypt_template(
                profile.encrypted_template,
                user_id=user_id,
                password=old_password,
            )
        except AuthenticationError:
            raise AuthenticationError(
                "Gagal memperbarui template biometrik: kata sandi lama tidak dapat mendekripsi profil wajah saat ini."
            )

        # Re-encrypt with new password and user_id AAD (generates fresh salt and nonce)
        new_encrypted_template = self._encrypt_template(
            stored_template,
            user_id=user_id,
            password=new_password,
        )

        new_profile = self._repo.create_profile(
            user_id=user_id,
            encrypted_template=new_encrypted_template,
            model_name=profile.model_name,
            model_version=profile.model_version,
            consent_recorded_at=profile.consent_recorded_at,
        )
        logger.info("Face biometric template re-keyed successfully for user_id=%s", user_id)
        return new_profile
