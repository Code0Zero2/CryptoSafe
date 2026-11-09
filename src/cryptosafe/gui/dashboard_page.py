"""Dashboard page prototype with feature cards (M1)."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
)

class DashboardPage(QWidget):
    """Prototype Dashboard Page with feature cards and logout navigation."""

    logout_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = ""
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Header bar
        header_layout = QHBoxLayout()
        
        title_box = QVBoxLayout()
        self.title_label = QLabel("CRYPTOSAFE — Dashboard")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        title_box.addWidget(self.title_label)

        self.user_label = QLabel("Pengguna Aktif: Tamu (Sesi Simulasi)")
        self.user_label.setStyleSheet("color: #4B5563; font-size: 13px;")
        title_box.addWidget(self.user_label)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Demo Mode Badge
        demo_badge = QLabel("PROTOTYPE DEMO")
        demo_badge.setStyleSheet(
            "background-color: #FEF3C7; color: #92400E; border: 1px solid #F59E0B; "
            "padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 11px;"
        )
        header_layout.addWidget(demo_badge)

        # Logout button
        self.logout_button = QPushButton("Logout")
        self.logout_button.setStyleSheet(
            "background-color: #EF4444; color: white; padding: 6px 16px; "
            "font-weight: bold; border-radius: 4px; font-size: 12px;"
        )
        self.logout_button.clicked.connect(self._handle_logout)
        header_layout.addWidget(self.logout_button)

        main_layout.addLayout(header_layout)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # Features grid inside scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(16)

        features = [
            (
                "Super-Enkripsi Teks",
                "Kombinasi Vigenère cipher edukatif dan enkripsi modern AES-256-GCM.",
                "Milestone M6 — Direncanakan"
            ),
            (
                "Enkripsi Berkas",
                "Enkripsi berkas biner/teks dengan ChaCha20-Poly1305 dan envelope ber-versi.",
                "Milestone M7 — Direncanakan"
            ),
            (
                "Penyimpanan Database Terenkripsi",
                "Penyimpanan catatan sensitif ke SQLite terenkripsi AES-256-GCM.",
                "Milestone M8 — Direncanakan"
            ),
            (
                "Steganografi Gambar",
                "Penyisipan payload terenkripsi AES-GCM ke citra PNG via LSB.",
                "Milestone M9 — Direncanakan"
            ),
            (
                "Verifikasi Integritas Aset",
                "Ledger lokal hash chain berbasis SHA-256 untuk mendeteksi perubahan aset.",
                "Milestone M10 — Direncanakan"
            ),
            (
                "Manajemen Kredensial Multi-Faktor",
                "Pendaftaran token USB dan template verifikasi wajah lokal.",
                "Milestones M3 & M4 — Direncanakan"
            ),
        ]

        for idx, (title, desc, status) in enumerate(features):
            row = idx // 2
            col = idx % 2
            card = self._create_feature_card(title, desc, status)
            grid.addWidget(card, row, col)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_feature_card(self, title: str, description: str, status: str) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 12px; }"
        )
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #1E293B;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(desc_lbl)

        layout.addStretch()

        status_lbl = QLabel(f"Status: {status}")
        status_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569;")
        layout.addWidget(status_lbl)

        return card

    def set_user(self, username: str):
        """Update dashboard for the authenticated user session."""
        self.username = username
        self.user_label.setText(f"Pengguna Aktif: {username} (Sesi Simulasi DEMO)")

    def _handle_logout(self):
        self.username = ""
        self.user_label.setText("Pengguna Aktif: Tamu (Sesi Simulasi)")
        self.logout_requested.emit()

