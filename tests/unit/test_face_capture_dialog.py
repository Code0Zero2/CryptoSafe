"""Unit tests for FaceCaptureDialog and CameraThread."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock
import numpy as np

os.environ["QT_QPA_PLATFORM"] = "offscreen"

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog
from cryptosafe.gui.face_capture_dialog import (
    FaceCaptureDialog,
    CameraThread,
    _pending_shutdown_threads,
)

class DummyCapture:
    """Mock cv2.VideoCapture for unit testing."""
    def __init__(self, opened=True, frame=None, raise_on_read=False):
        self._opened = opened
        self._frame = frame if frame is not None else np.zeros((480, 640, 3), dtype=np.uint8)
        self._raise_on_read = raise_on_read
        self.released = False

    def isOpened(self):
        return self._opened

    def read(self):
        if self._raise_on_read:
            raise RuntimeError("Hardware disconnection error during read")
        if not self._opened or self.released:
            return False, None
        return True, self._frame

    def release(self):
        self.released = True

class TestFaceCaptureDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.mock_face_service = MagicMock()
        # Mock adapter with cascade classifier
        self.mock_cascade = MagicMock()
        self.mock_cascade.detectMultiScale.return_value = [(220, 140, 200, 200)]  # Centered face for 640x480
        self.mock_adapter = MagicMock()
        self.mock_adapter._face_cascade = self.mock_cascade

    def test_camera_thread_lifecycle_and_signals(self):
        """Verifies CameraThread emits frame_ready and releases hardware on stop."""
        test_frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        mock_cap = DummyCapture(opened=True, frame=test_frame)

        thread = CameraThread(
            camera_index=0,
            adapter=self.mock_adapter,
            capture_factory=lambda idx: mock_cap,
        )

        frames_received = []
        thread.frame_ready.connect(
            lambda f, rect: frames_received.append((f, rect)),
            Qt.ConnectionType.DirectConnection,
        )

        thread.start()
        thread.msleep(100)
        thread.stop()

        self.assertTrue(mock_cap.released)
        self.assertGreater(len(frames_received), 0)
        self.assertEqual(frames_received[0][0].shape, (480, 640, 3))
        self.assertEqual(frames_received[0][1], (220, 140, 200, 200))

    def test_camera_thread_error_when_unavailable_and_releases(self):
        """Verifies CameraThread emits camera_error and STILL releases hardware when isOpened() is False."""
        mock_cap = DummyCapture(opened=False)
        thread = CameraThread(
            camera_index=0,
            adapter=self.mock_adapter,
            capture_factory=lambda idx: mock_cap,
        )

        errors_received = []
        thread.camera_error.connect(
            lambda err: errors_received.append(err),
            Qt.ConnectionType.DirectConnection,
        )

        thread.start()
        thread.msleep(50)
        thread.stop()

        self.assertGreater(len(errors_received), 0)
        self.assertIn("tidak tersedia", errors_received[0])
        self.assertTrue(mock_cap.released, "VideoCapture.release() must be called even when isOpened() is False")

    def test_exception_during_capture_read_handled_safely(self):
        """Verifies hardware read exception exits loop gracefully and releases device."""
        mock_cap = DummyCapture(opened=True, raise_on_read=True)
        thread = CameraThread(
            camera_index=0,
            adapter=self.mock_adapter,
            capture_factory=lambda idx: mock_cap,
        )

        thread.start()
        thread.msleep(50)
        thread.stop()

        self.assertTrue(mock_cap.released)
        self.assertFalse(thread.isRunning())

    def test_frame_emitted_is_independent_copy(self):
        """Verifies that frame emitted across signal is an independent copy."""
        original_frame = np.full((480, 640, 3), 42, dtype=np.uint8)
        mock_cap = DummyCapture(opened=True, frame=original_frame)
        thread = CameraThread(
            camera_index=0,
            adapter=self.mock_adapter,
            capture_factory=lambda idx: mock_cap,
        )

        emitted_frames = []
        thread.frame_ready.connect(
            lambda f, rect: emitted_frames.append(f),
            Qt.ConnectionType.DirectConnection,
        )

        thread.start()
        thread.msleep(60)
        thread.stop()

        self.assertGreater(len(emitted_frames), 0)
        # Mutating original frame in mock must not affect previously emitted frame
        original_frame[0, 0, 0] = 99
        self.assertEqual(emitted_frames[0][0, 0, 0], 42)

    def test_dialog_init_modes(self):
        """Verifies FaceCaptureDialog sets up appropriate UI in enroll vs login modes."""
        mock_thread = CameraThread(
            camera_index=0,
            capture_factory=lambda idx: DummyCapture(opened=False),
        )
        dialog_enroll = FaceCaptureDialog(self.mock_face_service, mode="enroll", camera_thread=mock_thread)
        self.assertIn("Perekaman", dialog_enroll.windowTitle())
        self.assertFalse(dialog_enroll.capture_btn.isEnabled())
        dialog_enroll.close()

        mock_thread_login = CameraThread(
            camera_index=0,
            capture_factory=lambda idx: DummyCapture(opened=False),
        )
        dialog_login = FaceCaptureDialog(self.mock_face_service, mode="login", camera_thread=mock_thread_login)
        self.assertIn("Verifikasi", dialog_login.windowTitle())
        self.assertFalse(dialog_login.capture_btn.isEnabled())
        dialog_login.close()

    def test_dialog_camera_error_updates_ui(self):
        """Verifies camera error disables capture and shows error banner."""
        mock_thread = CameraThread(
            camera_index=0,
            capture_factory=lambda idx: DummyCapture(opened=False),
        )
        dialog = FaceCaptureDialog(self.mock_face_service, mode="enroll", camera_thread=mock_thread)

        dialog._on_camera_error("Kamera index 0 tidak ditemukan.")
        self.assertIn("Gagal: Kamera index 0 tidak ditemukan.", dialog.status_label.text())
        self.assertFalse(dialog.capture_btn.isEnabled())
        self.assertEqual("Kamera Tidak Tersedia", dialog.preview_label.text())
        dialog.close()

    def test_dialog_face_detection_badge_states(self):
        """Verifies status label reacts to no faces, off-center faces, and centered faces."""
        mock_thread = CameraThread(
            camera_index=0,
            capture_factory=lambda idx: DummyCapture(opened=False),
        )
        dialog = FaceCaptureDialog(self.mock_face_service, mode="enroll", camera_thread=mock_thread)
        sample_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Before frame arrives, capture button is disabled
        self.assertFalse(dialog.capture_btn.isEnabled())

        # 1. No faces detected
        dialog._on_frame_ready(sample_frame, None)
        self.assertIn("Belum ada wajah", dialog.status_label.text())
        self.assertTrue(dialog.capture_btn.isEnabled())

        # 2. Off-center face (far top-left: x=10, y=10, w=50, h=50)
        dialog._on_frame_ready(sample_frame, (10, 10, 50, 50))
        self.assertIn("tengah", dialog.status_label.text().lower())
        self.assertTrue(dialog.capture_btn.isEnabled())

        # 3. Well-centered face (centered near 320, 240)
        dialog._on_frame_ready(sample_frame, (220, 140, 200, 200))
        self.assertIn("optimal", dialog.status_label.text().lower())
        self.assertTrue(dialog.capture_btn.isEnabled())

        dialog.close()

    def test_capture_and_cancel_actions(self):
        """Verifies capture button saves raw frame copy, while cancel clears frame."""
        mock_thread = CameraThread(
            camera_index=0,
            capture_factory=lambda idx: DummyCapture(opened=False),
        )
        dialog = FaceCaptureDialog(self.mock_face_service, mode="enroll", camera_thread=mock_thread)
        raw_frame = np.full((480, 640, 3), 77, dtype=np.uint8)

        # Feed frame with centered face
        dialog._on_frame_ready(raw_frame, (220, 140, 200, 200))
        self.assertTrue(dialog.capture_btn.isEnabled())

        # Click Capture
        dialog.capture_btn.click()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertIsNotNone(dialog.captured_frame)
        self.assertEqual(dialog.captured_frame[0, 0, 0], 77)

        # Test Cancel action
        mock_thread2 = CameraThread(
            camera_index=0,
            capture_factory=lambda idx: DummyCapture(opened=False),
        )
        dialog2 = FaceCaptureDialog(self.mock_face_service, mode="enroll", camera_thread=mock_thread2)
        dialog2._on_frame_ready(raw_frame, (220, 140, 200, 200))
        dialog2.cancel_btn.click()
        self.assertEqual(dialog2.result(), QDialog.DialogCode.Rejected)
        self.assertIsNone(dialog2.captured_frame)

    def test_reject_and_esc_stops_camera(self):
        """Verifies that dialog.reject() (invoked by Esc key) stops the camera thread."""
        mock_cap = DummyCapture(opened=True)
        thread = CameraThread(
            camera_index=0,
            adapter=self.mock_adapter,
            capture_factory=lambda idx: mock_cap,
        )
        dialog = FaceCaptureDialog(self.mock_face_service, mode="enroll", camera_thread=thread)

        # Allow thread to initialize and acquire capture handle
        thread.msleep(50)

        # Call reject directly (simulating Esc key press)
        dialog.reject()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)
        self.assertIsNone(dialog.captured_frame)
        self.assertTrue(mock_cap.released)
        self.assertFalse(thread.isRunning())

if __name__ == "__main__":
    unittest.main()
