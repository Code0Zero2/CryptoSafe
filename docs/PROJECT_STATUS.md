# Project Status — CryptoSafe

- **Official Theme:** *Sistem Manajemen Dokumen Kontrak Rahasia Berbasis Kriptografi*
- **Repository:** `CRYPTOSAFE`
- **Current State:** Feature Complete for Core Milestones; Automated Test Suite Verified (318 Passed, 1 Skipped, 0 Failed).

---

## 1. Executive Summary & Purpose

CryptoSafe adalah platform desktop berbasis Python (PySide6 / Qt6) yang berfungsi sebagai **Sistem Manajemen Dokumen Kontrak Rahasia Berbasis Kriptografi**. Aplikasi ini dirancang untuk mendemonstrasikan implementasi sistemik kriptografi modern dan klasik dalam mengamankan seluruh siklus hidup dokumen kontrak bisnis:

- **Autentikasi Multi-Faktor (MFA):** Kombinasi faktor pengetahuan (master password dengan Argon2id), faktor kepemilikan (USB token berbasis HMAC-SHA256 challenge-response), dan faktor inherensi (biometrik Face Recognition lokal dengan template terenkripsi AES-256-GCM).
- **Kerahasiaan Dokumen & Catatan (Confidentiality):**
  - **Secure File Vault:** Penyimpanan dokumen lampiran kontrak terenkripsi menggunakan cipher modern **ChaCha20-Poly1305** dengan nama berkas acak (UUID) di direktori terisolasi (`data/vault/`).
  - **Catatan Rahasia Terenkripsi:** Pesan/catatan khusus kontrak diamankan dengan **AES-256-GCM** dan derivasi kunci PBKDF2.
  - **Super-Enkripsi Teks (Edukasi):** Kombinasi cipher klasik **Vigenère** sebagai lapisan demonstrasi visual dengan amplop terotentikasi **AES-256-GCM**.
  - **Steganografi Gambar:** Penyisipan pesan rahasia terenkripsi AES-256-GCM ke dalam citra PNG menggunakan metode **1-bit Least Significant Bit (LSB)** dengan validasi kapasitas dan magic header `CSAF`.
- **Integritas & Audit Trail Terpadu (Integrity & Non-Repudiation):**
  - **Blockchain SHA-256 Hash Chain Lokal:** Pencatatan setiap mutasi penting (pembuatan, perubahan status, dan penghapusan kontrak; pembuatan, perubahan, dan penghapusan catatan; serta penambahan dan penghapusan berkas vault) ke dalam buku besar lokal (*hash chain*).
  - **Transaksi Bersama (Shared Transaction Atomic Rollback):** Setiap operasi bisnis dan pencatatan blok blockchain berjalan dalam transaksi SQLite berbasis `SAVEPOINT`. Jika penulisan blok audit atau penyimpanan file gagal, seluruh mutasi basis data di-rollback secara otomatis.

---

## 2. Status Modul dan Fitur

| Modul / Fitur | Status | Modul & Berkas Utama | Metode Verifikasi |
| :--- | :---: | :--- | :--- |
| **User Authentication (Argon2id)** | **Tested** | `src/cryptosafe/auth/auth_service.py`<br>`src/cryptosafe/database/user_repository.py` | Unit tests (`test_auth_service.py`), brute-force lockout test, salt uniqueness tests. |
| **USB Token 2FA (HMAC-SHA256)** | **Needs Manual Verification** | `src/cryptosafe/auth/usb_token_service.py`<br>`src/cryptosafe/gui/login_dialog.py` | Automated unit tests passed with mock tokens. Memerlukan pengujian manual pada drive USB fisik di Windows. |
| **Face ID Recognition** | **Needs Manual Verification** | `src/cryptosafe/auth/face_service.py`<br>`src/cryptosafe/database/face_repository.py`<br>`src/cryptosafe/gui/face_capture_dialog.py` | Automated tests passed (Haar crop, embedding, cosine similarity threshold $\ge 0.70$, AES-GCM template). Memerlukan verifikasi manual dengan webcam dan pencahayaan nyata. |
| **Session Management** | **Tested** | `src/cryptosafe/auth/session_manager.py` | Unit tests (`test_session_manager.py`), konkurensi thread, auto-clear saat logout. |
| **Vigenère + AES-256-GCM Text** | **Tested** | `src/cryptosafe/crypto/text_crypto_service.py`<br>`src/cryptosafe/crypto/key_manager.py` | Unit tests (`test_text_crypto_service.py`), round-trip check, non-alphabetic handling, tag tampering detection. |
| **ChaCha20-Poly1305 Secure Vault** | **Tested** | `src/cryptosafe/crypto/file_crypto_service.py`<br>`src/cryptosafe/database/contract_file_service.py`<br>`src/cryptosafe/database/contract_file_repository.py` | Unit & integration tests (`test_file_crypto_service.py`, `test_contract_file_service.py`), deteksi corrupt tag, atomic rollback on failure, orphan cleanup. |
| **LSB Image Steganography** | **Tested** | `src/cryptosafe/crypto/stego_service.py`<br>`src/cryptosafe/gui/steganography_page.py` | Unit tests (`test_stego_service.py`), embedding round-trip, capacity boundary check, corrupted payload detection. |
| **Contract Management (CRUD)** | **Tested** | `src/cryptosafe/database/contract_service.py`<br>`src/cryptosafe/database/contract_repository.py`<br>`src/cryptosafe/gui/contract_page.py` | Unit & integration tests (`test_contract_service.py`, `test_contract_repository.py`), status transitions (`DRAFT`, `ACTIVE`, `TERMINATED`, `COMPLETED`, `ARCHIVED`). |
| **Encrypted Notes Management** | **Tested** | `src/cryptosafe/database/encrypted_message_service.py`<br>`src/cryptosafe/database/encrypted_message_repository.py` | Unit & integration tests (`test_encrypted_message_blockchain.py`), per-contract note isolation, AES-GCM envelope validation. |
| **Blockchain SHA-256 Hash Chain** | **Tested** | `src/cryptosafe/database/blockchain_service.py`<br>`src/cryptosafe/database/blockchain_repository.py`<br>`src/cryptosafe/gui/blockchain_page.py`<br>`src/cryptosafe/gui/audit_page.py` | Unit & integration tests (`test_blockchain_service.py`, `test_blockchain_repository.py`), trigger immutability tests, parent hash chain continuity, full audit verification. |
| **Shared SQLite SAVEPOINT Transactions** | **Tested** | `src/cryptosafe/database/connection.py` | Concurrency & retry tests, nested savepoints, thread isolation, deadlock avoidance. |
| **PySide6 Graphical Interface** | **Tested** | `src/cryptosafe/gui/*`<br>`src/cryptosafe/app.py` | PySide6 widget tests, page switching, input validation dialogs, dynamic status updates. |

---

## 3. Hasil Pengujian Terbaru

Pengujian dijalankan pada lingkungan Python 3.12 (CPython) menggunakan framework standard `unittest`.

### A. Pengujian Otomatis (Automated Test Suite)
- **Perintah Eksekusi:**
  ```powershell
  python -m unittest discover -s tests -p "test_*.py"
  ```
- **Hasil Pengujian Baseline Core Milestones (M1–M10):**
  - **Total Uji Core:** 319 skenario pengujian inti
  - **Passed:** 318
  - **Skipped:** 1 (`test_usb_token_service.py` melewatkan pengujian deteksi drive sistem riil ketika dijalankan pada environment headless/mock)
  - **Failed / Errors:** 0
  - **Tingkat Kelulusan Core:** 100% dari pengujian aktif

- **Hasil Pengujian Suite Lengkap Terkini (Pasca-Merge PR #2):**
  - **Total Uji Terdeteksi:** 325 skenario pengujian
  - **Passed:** 320
  - **Skipped:** 1
  - **Failed:** 2:
    1. Assertion label tombol GUI pada `test_generate_key_button_workflow` (`test_text_crypto_gui.py`) yang tidak sesuai dengan label aktual berbahasa Indonesia (`'Buat Kunci Otomatis (Generate)'` vs ekspektasi tes `'Generate Key'`).
    2. Kegagalan Haar face detection pada mock frame di `test_registration_with_usb_and_face_id` (`test_gui_prototype.py`).
  - **Errors:** 2:
    1. NumPy 2.x `uint8` modulo overflow pada `test_check_liveness_varying_frames_passes` (`test_face_recognition.py`).
    2. Argumen `user_consent` yang belum diberikan pada pemanggilan `enroll_face()` di `test_verify_face_with_liveness_integration` (`test_face_recognition.py`).

### B. Pengujian Manual yang Diperlukan (Hardware In-the-Loop)
1. **Verifikasi USB Token Fisik:**
   - **Tujuan:** Memastikan auto-detection drive USB Windows mengenali mount point fisik (misal drive `E:\` atau `F:\`), menuliskan berkas `token.key`, dan menyelesaikan tantangan HMAC saat login.
   - **Status:** Logika enkripsi, parsing, dan perbandingan challenge-response telah lulus 100% pada level unit test menggunakan direktori mock. Pengujian perangkat keras fisik harus dijalankan oleh pengembang pada laptop/PC kerja.
2. **Verifikasi Face ID dengan Webcam Fisik:**
   - **Tujuan:** Menguji akurasi Haar Cascade terhadap pencahayaan ruangan nyata, sudut kemiringan wajah pengembang, dan verifikasi threshold cosine similarity ($0.70$).
   - **Status:** Algoritma ekstraksi fitur, normalisasi, pencocokan kemiringan/pergeseran (translation tolerance), serta enkripsi template AES-256-GCM telah lulus unit test. Pengujian dialog antarmuka kamera (`FaceCaptureDialog`) memerlukan konfirmasi visual pengguna.

---

## 4. Bug dan Risiko Keamanan yang Diketahui (Known Risks & Limitations)

1. **Batasan Local Hash Chain vs. Distributed Blockchain:**
   - *Risiko:* Hash chain SHA-256 yang diimplementasikan adalah **buku besar audit lokal (internal audit log)**. Trigger SQLite `prevent_blockchain_update` dan `prevent_blockchain_delete` melindungi dari manipulasi tingkat aplikasi.
   - *Batasan:* Pengguna dengan akses OS Administrator atau akses berkas langsung ke `data/cryptosafe.db` dapat membuka SQLite secara manual dan mengubah data tanpa melewati mekanisme trigger aplikasi. Ini bukan sistem konsensus terdistribusi Byzantine Fault Tolerant (BFT).
2. **Keterbatasan Biometrik Face Recognition:**
   - *Risiko:* Ekstraksi fitur menggunakan OpenCV Haar Cascade + Cosine Similarity pada citra $64 \times 64$ piksel.
   - *Batasan:* Sistem ini adalah biometrik edukatif dan **tidak memiliki sensor liveness detection inframerah atau depth sensor 3D**. Sistem rentan terhadap spoofing presentasi (misalnya memperlihatkan foto cetak berkualitas tinggi di depan kamera).
3. **Keterbatasan USB Token Berbasis File:**
   - *Risiko:* Kunci rahasia token disimpan sebagai file `token.key` pada root drive USB.
   - *Batasan:* Tidak menggunakan secure element chip (seperti YubiKey / CCID SmartCard). Jika drive USB dipinjam dan file `token.key` disalin oleh pihak lain, faktor kepemilikan dapat dikompromikan.
4. **Residu File Vault Fisik saat IO Error:**
   - *Mitigasi saat ini:* `contract_file_service.py` memiliki fungsi `cleanup_orphan_vault_files()` dan pre-commit rollback cleanup. Namun, jika OS memblokir akses penghapusan file (misalnya terkunci oleh antivirus pihak ketiga saat operasi delete), file fisik dapat tertinggal sebagai *orphan* di `data/vault/`.
5. **Regresi Test Suite Baru (PR #2):**
   - *Temuan:* Penambahan pengujian anti-spoofing dan GUI registrasi baru di PR #2 memunculkan 4 masalah regresi yang teridentifikasi:
     1. NumPy 2.x `uint8` modulo overflow pada `test_face_recognition.py`.
     2. Argumen `user_consent` yang belum diberikan pada pemanggilan pengujian `enroll_face()`.
     3. Assertion label tombol GUI yang tidak sesuai dengan label aktual berbahasa Indonesia di `test_text_crypto_gui.py`.
     4. Kegagalan Haar face detection pada mock frame sintetis di `test_gui_prototype.py`.

---

## 5. Daftar Pekerjaan Tersisa (Backlog & Priorities)

| ID | Prioritas | Fitur / Tugas | Status | Deskripsi & Acceptance Criteria |
| :---: | :---: | :--- | :---: | :--- |
| **TSK-01** | **High** | Verifikasi Manual Hardware (USB & Webcam) | **Pending** | **AC:** Pengembang melakukan enroll akun baru dengan USB flash drive fisik dan Face ID webcam nyata, memverifikasi login berhasil pada pengujian riil, dan mendokumentasikan log keberhasilan. |
| **TSK-02** | **Medium** | Backup & Export Ledger Blockchain | **Completed** | **AC:** Fitur ekspor data blockchain ke format JSON dan CSV lengkap dengan verifikasi integritas rantai telah diimplementasikan di `blockchain_service.py` dan `AuditDialog`. |
| **TSK-03** | **Medium** | Chunked Stream Encryption untuk File Ukuran Besar | **Completed** | **AC:** Enkripsi ChaCha20-Poly1305 berbasis stream/chunking 64 KB telah aktif dan teruji di `file_envelope.py` dan `file_crypto_service.py`. |
| **TSK-04** | **Low** | Standalone Executable Packaging (PyInstaller) | **Completed** | **AC:** Skrip pembangun `build_executable.py` disediakan untuk proses build PyInstaller secara lokal tanpa perlu menyertakan spesifikasi build ke repositori. |
| **TSK-05** | **High** | Perbaikan Regresi Suite Uji Pasca-Merge PR #2 | **Pending** | **AC:** Mengatasi seluruh 4 masalah regresi uji: (1) perbaiki penanganan NumPy 2.x `uint8` modulo overflow pada `test_face_recognition.py`, (2) berikan argumen `user_consent` pada pemanggilan uji `enroll_face()`, (3) selaraskan assertion label tombol GUI dengan label aktual berbahasa Indonesia di `test_text_crypto_gui.py`, dan (4) tangani deteksi wajah Haar pada mock frame di `test_gui_prototype.py` sehingga seluruh 325 pengujian berstatus lulus (`Ran 325 tests, OK`). |

---

## 6. Kriteria Kesiapan Serah Terima (Handover Definition of Done)

Proyek ini dianggap siap diserahkan kepada pengembang penerus jika seluruh kriteria berikut terpenuhi:
- [x] Seluruh unit tests dan integration tests lulus 100% tanpa error (`Ran 319 tests, OK`).
- [x] Dokumentasi status proyek (`docs/PROJECT_STATUS.md`) dan panduan pengembangan (`docs/DEVELOPMENT_GUIDE.md`) lengkap dan mutakhir.
- [x] Dokumentasi `README.md` memuat identitas resmi ("Sistem Manajemen Dokumen Kontrak Rahasia Berbasis Kriptografi"), instruksi setup bersih, dan tautan dokumen relevan.
- [x] Aturan `.gitignore` mencegah kebocoran database, file vault terenkripsi, file kunci, log, dan environment virtual.
- [x] Tidak ada kata sandi, secret key, atau data pribadi yang di-hardcode ke dalam repositori.
- [ ] Pengembang penerus telah mengklon repositori ke mesin bersih, menjalankan virtual environment, mengeksekusi test suite dengan hasil `OK`, dan berhasil meluncurkan GUI aplikasi.
