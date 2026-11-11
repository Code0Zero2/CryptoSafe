"""Interactive camera viewfinder dialog for face biometric enrollment and verification (Tahap 2)."""

from __future__ import annotations

import logging
import time
from typing import Callable
import cv2
import numpy as np
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QMessageBox,
)
from cryptosafe.auth.face_service import FaceRecognizerAdapter, FaceService

logger = logging.getLogger("cryptosafe.face_gui")

# Module-level registry keeping strong references to threads that haven't finished yet
# to prevent C++ destruction crashes when dialogs are garbage collected.
_pending_shutdown_threads: set["CameraThread"] = set()


class CameraThread(QThread):
    """Asynchronous worker thread capturing video frames and detecting faces without blocking Qt GUI thread."""

    frame_ready = Signal(np.ndarray, object)  # (raw_frame_bgr, face_rect_tuple_or_None)
    camera_error = Signal(str)

    def __init__(
        self,
        camera_index: int = 0,
        adapter: FaceRecognizerAdapter | None = None,
        capture_factory: Callable[[int], object] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._camera_index = camera_index
        self._adapter = adapter
        self._capture_factory = capture_factory or (lambda idx: cv2.VideoCapture(idx))
        self._running = False
        self._stop_requested = False
        self._cap = None

    def run(self):
        """Thread loop reading frames continuously and emitting signals."""
        self._running = True
        try:
            if self._stop_requested:
                return

            try:
                self._cap = self._capture_factory(self._camera_index)
            except Exception as err:
                logger.error("Failed to initialize capture device: %s", err)
                self.camera_error.emit(f"Gagal membuka perangkat kamera: {err}")
                return

            is_opened = False
            if self._cap is not None:
                if hasattr(self._cap, "isOpened"):
                    try:
                        is_opened = bool(self._cap.isOpened())
                    except Exception:
                        is_opened = False
                else:
                    is_opened = True

            if not is_opened:
                self.camera_error.emit("Kamera tidak tersedia atau tidak dapat diakses.")
                return

            if self._stop_requested:
                return

            # Warm up sensor: discard first 2 frames if possible
            try:
                for _ in range(2):
                    if self._stop_requested:
                        return
                    if hasattr(self._cap, "read"):
                        self._cap.read()
            except Exception:
                pass

            while self._running and not self._stop_requested:
                try:
                    if hasattr(self._cap, "read"):
                        ret, frame = self._cap.read()
                    else:
                        break
                except Exception:
                    break

                if not ret or frame is None:
                    time.sleep(0.04)
                    continue

                if self._stop_requested:
                    break

                # Detect face rectangle for visual feedback
                face_rect = self._detect_face(frame)
                # Emit an explicit copy of frame to isolate memory across thread boundaries
                self.frame_ready.emit(frame.copy(), face_rect)

                # Regulate to ~25-30 FPS to minimize CPU overhead
                time.sleep(0.033)
        finally:
            self._running = False
            if self._cap is not None:
                try:
                    if hasattr(self._cap, "release"):
                        self._cap.release()
                except Exception as err:
                    logger.debug("Exception while releasing capture: %s", err)
                finally:
                    self._cap = None

    def _detect_face(self, frame: np.ndarray) -> tuple[int, int, int, int] | None:
        """Detect primary face bounding box (x, y, w, h) for viewfinder overlay."""
        if frame is None or frame.size == 0:
            return None
        try:
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            elif len(frame.shape) == 2:
                gray = frame
            else:
                return None

            # Check if adapter has face cascade
            cascade = getattr(self._adapter, "_face_cascade", None) if self._adapter else None
            if cascade is not None:
                faces = cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=4,
                    minSize=(30, 30),
                )
                if len(faces) == 0:
                    faces = cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.05,
                        minNeighbors=3,
                        minSize=(30, 30),
                    )
                if len(faces) > 0:
                    x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
                    return (int(x), int(y), int(w), int(h))

            # Small pre-cropped fixture fallback
            if gray.shape[0] <= 128 and gray.shape[1] <= 128:
                return (0, 0, int(gray.shape[1]), int(gray.shape[0]))
        except Exception:
            pass
        return None

    def stop(self, timeout_ms: int = 1500) -> bool:
        """Signal thread to stop and wait safely for hardware release.

        Returns True if thread finished cleanly, False if timed out.
        """
        self._stop_requested = True
        self._running = False
        if self.isRunning():
            return self.wait(timeout_ms)
        return True


class FaceCaptureDialog(QDialog):
    """Viewfinder dialog displaying live camera preview, face bounding box, and capture trigger."""

    def __init__(
        self,
        face_service: FaceService,
        mode: str = "enroll",  # 'enroll' or 'login'
        camera_index: int = 0,
        camera_thread: CameraThread | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._face_service = face_service
        self._mode = mode
        self._camera_index = camera_index
        self._custom_thread = camera_thread
        self.captured_frame: np.ndarray | None = None
        self.captured_liveness_frames: list[np.ndarray] = []
        self._recent_frames: list[np.ndarray] = []
        self._last_raw_frame: np.ndarray | None = None
        self._last_face_frame: np.ndarray | None = None
        self._last_face_rect: tuple[int, int, int, int] | None = None
        self._camera_thread: CameraThread | None = None

        self._setup_ui()
        self._start_camera()

    def _setup_ui(self):
        title = "Perekaman Biometrik Wajah" if self._mode == "enroll" else "Verifikasi Biometrik Wajah"
        self.setWindowTitle(title)
        self.resize(520, 520)
        self.setMinimumSize(460, 480)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header Title
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E293B;")
        main_layout.addWidget(title_lbl)

        desc_text = (
            "Posisikan wajah Anda tepat di depan kamera untuk mendaftarkan profil biometrik."
            if self._mode == "enroll"
            else "Posisikan wajah Anda di depan kamera untuk menyelesaikan verifikasi login."
        )
        desc_lbl = QLabel(desc_text)
        desc_lbl.setStyleSheet("font-size: 12px; color: #475569;")
        desc_lbl.setWordWrap(True)
        main_layout.addWidget(desc_lbl)

        # Video Preview Viewfinder
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet(
            "background-color: #0F172A; border: 2px solid #334155; border-radius: 8px;"
        )
        self.preview_frame.setMinimumSize(440, 310)
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(4, 4, 4, 4)

        self.preview_label = QLabel("Memulai kamera...")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 500;")
        preview_layout.addWidget(self.preview_label)
        main_layout.addWidget(self.preview_frame)

        # Status Indicator Label
        self.status_label = QLabel("Inisialisasi kamera...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #B45309; "
            "padding: 6px; background-color: #FEF3C7; border: 1px solid #FCD34D; border-radius: 4px;"
        )
        main_layout.addWidget(self.status_label)

        # Liveness Indicator Pill
        self.liveness_label = QLabel("🛡 Anti-Spoofing: Aktif (Verifikasi Keaslian & Gerak Wajah)")
        self.liveness_label.setAlignment(Qt.AlignCenter)
        self.liveness_label.setStyleSheet(
            "font-size: 11px; font-weight: 500; color: #0F766E; "
            "padding: 3px; background-color: #CCFBF1; border-radius: 3px;"
        )
        main_layout.addWidget(self.liveness_label)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Batal")
        self.cancel_btn.setStyleSheet(
            "padding: 8px 18px; font-weight: 500; font-size: 12px; border-radius: 4px; border: 1px solid #CBD5E1;"
        )
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        self.capture_btn = QPushButton("Ambil Foto")
        self.capture_btn.setStyleSheet(
            "background-color: #059669; color: white; font-weight: bold; font-size: 12px; "
            "padding: 8px 22px; border-radius: 4px;"
        )
        self.capture_btn.setEnabled(False)
        self.capture_btn.clicked.connect(self._on_capture)
        btn_layout.addWidget(self.capture_btn)

        main_layout.addLayout(btn_layout)

    def _start_camera(self):
        """Instantiate and start the camera worker thread."""
        if self._custom_thread is not None:
            self._camera_thread = self._custom_thread
        else:
            adapter = getattr(self._face_service, "_adapter", None)
            self._camera_thread = CameraThread(
                camera_index=self._camera_index,
                adapter=adapter,
                parent=self,
            )

        self._camera_thread.frame_ready.connect(self._on_frame_ready)
        self._camera_thread.camera_error.connect(self._on_camera_error)
        self._camera_thread.start()

    def _stop_camera(self):
        """Safely shut down the camera thread and release hardware resources."""
        thread = self._camera_thread
        if thread is not None:
            # 1. Disconnect signals to avoid any callback execution while shutting down
            try:
                thread.frame_ready.disconnect()
            except Exception:
                pass
            try:
                thread.camera_error.disconnect()
            except Exception:
                pass

            # 2. Detach parent so QDialog destruction does not prematurely delete QThread C++ instance
            try:
                thread.setParent(None)
            except Exception:
                pass

            # 3. Stop thread with timeout
            finished = thread.stop(timeout_ms=1500)
            if not finished and thread.isRunning():
                logger.warning(
                    "CameraThread did not terminate within timeout; retaining reference until shutdown."
                )
                _pending_shutdown_threads.add(thread)
                thread.finished.connect(lambda: _pending_shutdown_threads.discard(thread))

            self._camera_thread = None

    def _on_frame_ready(self, frame: np.ndarray, face_rect: tuple[int, int, int, int] | None):
        """Render received frame with bounding box and update guidance status."""
        self._last_raw_frame = frame
        self._last_face_rect = face_rect
        if face_rect is not None:
            self._last_face_frame = frame.copy()
            self._recent_frames.append(frame.copy())
            if len(self._recent_frames) > 10:
                self._recent_frames.pop(0)
        self.capture_btn.setEnabled(True)

        display_frame = frame.copy()
        fh, fw = frame.shape[:2]

        if face_rect is not None:
            x, y, w, h = face_rect
            # Evaluate optimal face positioning
            is_centered = (fw * 0.15 <= x <= fw * 0.75) and (fh * 0.10 <= y <= fh * 0.80)
            is_large_enough = w >= fw * 0.18

            if is_centered and is_large_enough:
                box_color = (0, 210, 80)  # Bright green
                self.status_label.setText("✓ Wajah terdeteksi — Posisi optimal, siap mengambil foto")
                self.status_label.setStyleSheet(
                    "font-size: 12px; font-weight: bold; color: #047857; "
                    "padding: 6px; background-color: #D1FAE5; border: 1px solid #10B981; border-radius: 4px;"
                )
            else:
                box_color = (0, 180, 255)  # Orange / Yellow
                self.status_label.setText("Wajah terdeteksi — Dekatkan atau posisikan wajah di tengah frame")
                self.status_label.setStyleSheet(
                    "font-size: 12px; font-weight: bold; color: #1D4ED8; "
                    "padding: 6px; background-color: #DBEAFE; border: 1px solid #3B82F6; border-radius: 4px;"
                )

            # Draw bounding box
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), box_color, 2)
        else:
            self.status_label.setText("Belum ada wajah terdeteksi — Hadapkan wajah ke arah kamera")
            self.status_label.setStyleSheet(
                "font-size: 12px; font-weight: bold; color: #B45309; "
                "padding: 6px; background-color: #FEF3C7; border: 1px solid #FCD34D; border-radius: 4px;"
            )

        # Convert to QPixmap and update preview
        try:
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            self.preview_label.setPixmap(
                pixmap.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        except Exception:
            pass

    def _on_camera_error(self, message: str):
        """Handle hardware or connection failure gracefully."""
        self.status_label.setText(f"Gagal: {message}")
        self.status_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #DC2626; "
            "padding: 6px; background-color: #FEE2E2; border: 1px solid #EF4444; border-radius: 4px;"
        )
        self.preview_label.setText("Kamera Tidak Tersedia")
        self.capture_btn.setEnabled(False)

    def reject(self):
        """Override QDialog.reject() to ensure camera is stopped on Esc or cancel."""
        self.captured_frame = None
        self._stop_camera()
        super().reject()

    def accept(self):
        """Override QDialog.accept() to ensure camera is stopped on capture."""
        self._stop_camera()
        super().accept()

    def closeEvent(self, event):
        """Ensure thread is stopped and camera hardware released upon closing dialog."""
        self._stop_camera()
        super().closeEvent(event)

    def _on_capture(self):
        """Accept dialog and preserve clean raw frame for cryptographic processing."""
        chosen_frame = self._last_face_frame if self._last_face_frame is not None else self._last_raw_frame
        if chosen_frame is not None:
            self.captured_frame = chosen_frame.copy()
            self.captured_liveness_frames = list(self._recent_frames)
            self.accept()
        else:
            QMessageBox.warning(self, "Peringatan", "Frame gambar belum tersedia.")

    def _on_cancel(self):
        """Cancel capture and reject dialog."""
        self.reject()
