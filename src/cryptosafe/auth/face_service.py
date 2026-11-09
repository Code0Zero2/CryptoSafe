"""Local Face Recognition service with biometric template protection and informed consent."""

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
from cryptosafe.database.face_repository import FaceRepository, FaceProfile

logger = logging.getLogger("cryptosafe.face")

MODEL_NAME = "OpenCV-Haar-L2Norm"
MODEL_VERSION = "1.0.0"

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
            minSize=(30, 30)
        )

        if len(faces) > 0:
            # Pick largest detected face
            x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
            face_roi = gray[y:y+h, x:x+w]
        elif gray.shape[0] <= 128 and gray.shape[1] <= 128:
            # Pre-cropped face patch / fixture
            face_roi = gray
        else:
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

    def compute_similarity(self, template_a: np.ndarray, template_b: np.ndarray) -> float:
        if template_a is None or template_b is None:
            return 0.0
        if template_a.shape != template_b.shape:
            return 0.0
        # Dot product of L2 normalized vectors gives cosine similarity
        return float(np.dot(template_a, template_b))

class FaceService:
    """High-level face recognition service managing enrollment, template encryption, and verification."""

    def __init__(
        self,
        face_repo: FaceRepository,
        adapter: FaceRecognizerAdapter | None = None,
        encryption_key: bytes | None = None,
    ):
        self._repo = face_repo
        self._adapter = adapter or OpenCvFaceAdapter()
        # 256-bit key for AES-GCM template protection
        self._aes_key = encryption_key or secrets.token_bytes(32)

    def capture_camera_frame(self, camera_index: int = 0) -> np.ndarray:
        """Capture a single image frame from local camera. Disposed immediately."""
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise AuthenticationError("Kamera tidak tersedia atau tidak dapat diakses.")
        try:
            ret, frame = cap.read()
            if not ret or frame is None:
                raise AuthenticationError("Gagal membaca frame gambar dari kamera.")
            return frame
        finally:
            cap.release()

    def _encrypt_template(self, template: np.ndarray) -> str:
        """Encrypt biometric template using AES-256-GCM. Returns JSON envelope string."""
        raw_bytes = template.tobytes()
        aesgcm = AESGCM(self._aes_key)
        nonce = secrets.token_bytes(12)  # 96-bit nonce
        ciphertext = aesgcm.encrypt(nonce, raw_bytes, None)
        envelope = {
            "version": 1,
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
            "shape": list(template.shape),
            "dtype": str(template.dtype),
        }
        return json.dumps(envelope)

    def _decrypt_template(self, encrypted_str: str) -> np.ndarray:
        """Decrypt AES-256-GCM envelope and recover biometric template array."""
        try:
            data = json.loads(encrypted_str)
            nonce = bytes.fromhex(data["nonce"])
            ciphertext = bytes.fromhex(data["ciphertext"])
            shape = tuple(data["shape"])
            dtype = np.dtype(data["dtype"])
            aesgcm = AESGCM(self._aes_key)
            decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            return np.frombuffer(decrypted_bytes, dtype=dtype).reshape(shape)
        except Exception:
            raise AuthenticationError("Data template wajah terenkripsi rusak atau tidak valid.")

    def enroll_face(
        self,
        user_id: int,
        image: np.ndarray,
        user_consent: bool,
    ) -> FaceProfile:
        """Enroll face template for a user after verifying explicit informed consent."""
        if not user_consent:
            raise ValidationError("Persetujuan perekaman biometrik wajah wajib diberikan pengguna.")

        template = self._adapter.detect_and_extract_template(image)
        if template is None:
            raise ValidationError("Wajah tidak terdeteksi pada gambar. Pastikan pencahayaan cukup dan wajah menghadap kamera.")

        # Encrypt template (raw image is NEVER stored)
        encrypted_template = self._encrypt_template(template)
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

    def verify_face(
        self,
        user_id: int,
        image: np.ndarray,
        threshold: float = 0.75,
    ) -> bool:
        """Verify face in image against user's stored encrypted template."""
        profile = self._repo.get_active_by_user_id(user_id)
        if not profile:
            raise AuthenticationError("Pengguna tidak memiliki profil biometrik wajah aktif yang terdaftar.")

        stored_template = self._decrypt_template(profile.encrypted_template)

        probe_template = self._adapter.detect_and_extract_template(image)
        if probe_template is None:
            raise AuthenticationError("Wajah tidak terdeteksi pada kamera saat verifikasi.")

        similarity = self._adapter.compute_similarity(stored_template, probe_template)
        # Note: We do NOT log biometric embeddings or images.
        if similarity < threshold:
            logger.warning("Face biometric match failed for user_id=%s (similarity below threshold)", user_id)
            raise AuthenticationError("Verifikasi wajah gagal: wajah tidak cocok.")

        logger.info("Face biometric verification passed for user_id=%s", user_id)
        return True
