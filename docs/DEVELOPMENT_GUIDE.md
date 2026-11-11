# Developer & Contribution Guide — CryptoSafe

**Official Theme:** *Sistem Manajemen Dokumen Kontrak Rahasia Berbasis Kriptografi*  
**Target Platform:** Windows 10/11 (dukungan Linux/macOS tersedia)  
**Runtime:** Python 3.10+ (Direkomendasikan Python 3.11 atau 3.12)

---

## 1. Setup Lingkungan Pengembangan dari Nol (Windows)

Panduan ini ditujukan bagi anggota tim baru untuk menyiapkan lingkungan kerja di komputer Windows yang baru/bersih.

### 1.1 Prasyarat Sistem
- **Git for Windows:** Terpasang dan dapat diakses dari terminal (`git --version`).
- **Python 3.10+:** Pastikan opsi *"Add Python to PATH"* dicentang saat instalasi (`python --version`).
- **Webcam (Opsional):** Kamera internal atau USB jika ingin menguji fitur Face Recognition.
- **Flash Drive USB (Opsional):** Format FAT32/NTFS untuk pengujian hardware token 2FA.

### 1.2 Langkah Kloning dan Pembuatan Lingkungan Virtual
Buka terminal **PowerShell** atau **Command Prompt (CMD)**:

```powershell
# 1. Kloning repositori
git clone <repository_url>
cd CRYPTOSAFE

# 2. Buat Python Virtual Environment (.venv)
python -m venv .venv

# 3. Aktifkan Virtual Environment
# Untuk PowerShell:
.venv\Scripts\Activate.ps1

# Jika muncul error ExecutionPolicy di PowerShell, jalankan:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Untuk Command Prompt (CMD):
.venv\Scripts\activate.bat
```

### 1.3 Instalasi Dependensi
Pastikan pip diperbarui ke versi mutakhir, lalu pasang paket dari `requirements.txt`:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Daftar dependensi utama yang dipasang:
- `PySide6`: Framework UI Qt6 untuk desktop.
- `cryptography`: Pustaka standar untuk cipher AES-256-GCM, ChaCha20-Poly1305, PBKDF2, dan HMAC.
- `argon2-cffi`: Hashing password berbasis Argon2id.
- `opencv-python`: Pengambilan frame webcam dan Haar Cascade detector untuk Face ID.
- `numpy`: Manipulasi matriks fitur citra wajah dan perhitungan Cosine Similarity.
- `Pillow`: Manipulasi citra PNG lossless untuk steganografi LSB.

---

## 2. Menjalankan Aplikasi

Aplikasi CryptoSafe memiliki titik masuk utama di berkas `main.py` pada root direktori repositori.

### 2.1 Perintah Utama (Direkomendasikan)
Jalankan langsung melalui virtual environment:
```powershell
python main.py
```
*Berkas `main.py` secara otomatis menambahkan direktori `src` ke dalam `sys.path` sebelum memanggil modul `cryptosafe.app`.*

### 2.2 Perintah Alternatif dengan `PYTHONPATH`
Jika menjalankan sebagai modul paket Python:
```powershell
# Di PowerShell:
$env:PYTHONPATH="src"
python -m cryptosafe.app

# Di Command Prompt (CMD):
set PYTHONPATH=src
python -m cryptosafe.app
```

---

## 3. Menjalankan Pengujian (Testing)

Proyek ini menggunakan modul bawaan `unittest` standar CPython. Semua pengujian terletak pada direktori `tests/`.

### 3.1 Menjalankan Seluruh Test Suite
Jalankan *test discovery* untuk mengeksekusi semua berkas `test_*.py`:
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

### 3.2 Menjalankan Berdasarkan Kategori
```powershell
# Menjalankan hanya pengujian unit
python -m unittest discover -s tests/unit -p "test_*.py"

# Menjalankan hanya pengujian integrasi (GUI, DB, Blockchain)
python -m unittest discover -s tests/integration -p "test_*.py"
```

### 3.3 Menjalankan Pengujian Modul Tertentu
Sebelum mengubah kode suatu modul, jalankan pengujian modul tersebut secara terisolasi:
```powershell
# Pengujian autentikasi password & lockout
python -m unittest tests/unit/test_auth_service.py

# Pengujian Face ID & biometrik
python -m unittest tests/unit/test_face_recognition.py

# Pengujian super-enkripsi teks Vigenere + AES-GCM
python -m unittest tests/unit/test_text_crypto_service.py

# Pengujian ChaCha20-Poly1305 file vault
python -m unittest tests/unit/test_file_crypto_service.py
python -m unittest tests/unit/test_contract_file_service.py

# Pengujian blockchain SHA-256 hash chain
python -m unittest tests/unit/test_blockchain_service.py
python -m unittest tests/integration/test_contract_blockchain_integration.py
```

---

## 4. Arsitektur dan Alur Kerja Antarmodul

CryptoSafe menerapkan arsitektur berlapis (*layered architecture*) yang memisahkan tanggung jawab antarmuka pengguna, koordinasi logika bisnis, dan akses data:

```
+--------------------------------------------------------------------------+
|                            PRESENTATION (GUI)                            |
|             src/cryptosafe/gui/ (MainWindow, ContractPage, etc.)         |
|  - Menangani input pengguna, validasi form, dan rendering tabel/dialog.  |
|  - TIDAK BOLEH memanggil query SQL atau kriptografi langsung.            |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                         APPLICATION SERVICES                             |
|          src/cryptosafe/database/*_service.py, src/cryptosafe/auth/      |
|  - ContractService, ContractFileService, EncryptedMessageService         |
|  - BlockchainService, AuthService, FaceService, USBTokenService          |
|  - Mengoordinasikan operasi bisnis, derivasi kunci, dan transaksi.      |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                          DATA ACCESS (REPOSITORIES)                      |
|                  src/cryptosafe/database/*_repository.py                 |
|  - ContractRepository, ContractFileRepository, UserRepository            |
|  - BlockchainRepository, EncryptedMessageRepository                      |
|  - Menjalankan parameterized SQL query murni.                            |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                         DATABASE & VAULT STORAGE                         |
|     connection.py (SQLite SAVEPOINT Context)  &  data/vault/ (*.enc)     |
+--------------------------------------------------------------------------+
```

### 4.1 Contoh Alur: Transaksi Bersama Kontrak & Blockchain
1. Pengguna mengisi form kontrak baru di `ContractPage` dan menekan tombol *Save*.
2. `ContractPage` memanggil `ContractService.create_contract(...)`.
3. `ContractService` membuka konteks transaksi bersama menggunakan `connection.transaction()`:
   - Baris kontrak disimpan melalui `ContractRepository.create_contract(...)`.
   - Snapshot metadata kanonis disusun dan di-hash menggunakan SHA-256.
   - Blok audit baru bertipe `CONTRACT_CREATED` ditambahkan ke `blockchain_blocks` melalui `BlockchainService.append_block(...)`.
4. Jika salah satu operasi mengalami galat (misal tabrakan indeks blockchain atau kegagalan disk), konteks transaksi mengeksekusi `ROLLBACK TO SAVEPOINT`, sehingga status basis data tetap konsisten.

---

## 5. Algoritma Kriptografi & Implementasi Riil

Saat mengembangkan modul baru atau berdiskusi teknis, gunakan terminologi yang akurat sesuai implementasi aktual:

1. **Master Password Hashing:** **Argon2id** (RFC 9106) dengan salt 16-byte unik per pengguna.
2. **2FA USB Token:** **HMAC-SHA256** *challenge-response*. Token rahasia 32-byte disimpan di drive USB; respon diverifikasi menggunakan perbandingan *constant-time* (`hmac.compare_digest`).
3. **Face ID Biometrics:**
   - Deteksi wajah: **OpenCV Haar Cascade** frontal face detector.
   - Ekstraksi fitur: Pemotongan ROI wajah, konversi skala abu-abu, *resize* standar $64 \times 64$, ekualisasi histogram, pemusatan rata-rata nol (*zero-mean centering*), dan normalisasi vektor L2.
   - Algoritma Kemiripan: **Cosine Similarity** dengan toleransi pergeseran koordinat (*translation tolerance* shift $\pm 2$ piksel) dan ambang batas minimum $\ge 0.70$.
   - Perlindungan Template: Serialisasi embedding disimpan terenkripsi **AES-256-GCM** dengan *Associated Authenticated Data* (AAD) terikat ke `user_id`.
4. **Enkripsi File Dokumen:** **ChaCha20-Poly1305** dengan nonce 12-byte acak per berkas. Berkas fisik disimpan di `data/vault/<uuid>.enc` tanpa membocorkan nama atau ekstensi asli.
5. **Super-Enkripsi Teks:** **Vigenère** (lapisan demonstrasi substitusi) dilanjutkan enkripsi amplop **AES-256-GCM** menggunakan kunci hasil derivasi **PBKDF2-HMAC-SHA256** (600.000 iterasi).
6. **Steganografi Gambar:** **1-bit LSB** pada kanal RGB citra PNG lossless. Pesan dienkripsi dengan AES-256-GCM dan diberi header panjang serta identitas `CSAF`.
7. **Buku Besar Audit:** **SHA-256 Hash Chain** lokal dengan trigger SQLite `BEFORE UPDATE` dan `BEFORE DELETE` untuk mencegah modifikasi blok lama.

---

## 6. Panduan Menambah Fitur dan Memperbaiki Bug

### 6.1 Prinsip Pengembangan
- **Surgical Changes:** Sentuh hanya kode yang relevan dengan tugas. Jangan melakukan refactoring besar tanpa persetujuan tim.
- **Preserve Documentation & Comments:** Pertahankan komentar dan docstring arsitektural yang sudah ada.
- **Never Implement Custom Cryptography:** Selalu gunakan pustaka teruji (`cryptography`, `argon2-cffi`, `secrets`). Jangan membuat algoritma cipher atau KDF buatan sendiri.
- **Zero-Knowledge Audit Trail:** Jangan pernah mencatat plaintext, password, kunci enkripsi, atau koordinat biometrik ke dalam payload blockchain atau file log.
- **Atomic Rollback:** Setiap mutasi domain yang memiliki event blockchain wajib dibungkus dalam blok transaksi bersama `connection.transaction()`.

### 6.2 Langkah Praktis Memperbaiki Bug (Bug Fixing)
1. **Buat Tes Reproduksi:** Tulis skenario pengujian di `tests/unit/` atau `tests/integration/` yang mendemonstrasikan kegagalan.
2. **Verifikasi Kegagalan:** Jalankan tes tersebut dan pastikan gagal pada baris yang diduga bermasalah.
3. **Lakukan Perbaikan Minimum:** Ubah kode aplikasi seminimal mungkin untuk membuat tes tersebut lulus.
4. **Cek Regresi:** Jalankan seluruh test suite untuk memastikan modul lain tidak terganggu.

---

## 7. Git Workflow & Kontribusi Tim

### 7.1 Aturan Percabangan (Branching)
- `main`: Branch utama yang selalu stabil dan siap rilis. Seluruh tes harus lulus sebelum merge ke branch ini.
- `feature/<nama-fitur>`: Branch untuk penambahan fitur baru (contoh: `feature/export-blockchain-csv`).
- `bugfix/<nama-bug>`: Branch untuk perbaikan kerusakan (contoh: `bugfix/camera-timeout`).

### 7.2 Standar Pesan Commit
Gunakan format imperatif yang jelas dan ringkas:
```
feat(vault): add chunked file encryption support
fix(face): adjust default cosine similarity threshold
test(blockchain): add concurrent append retry test case
docs: update development guide for clean Windows setup
```

### 7.3 Kebersihan Kode & Pengecekan Whitespace
Sebelum melakukan commit atau push, selalu periksa status diff dan pastikan tidak ada whitespace berlebih di akhir berkas:
```powershell
# Pastikan tidak ada berkas sensitif atau database yang masuk stage
git status

# Pastikan tidak ada whitespace berlebih
git diff --check
```

### 7.4 Checklist Pull Request (PR)
Sebelum PR di-merge ke branch `main`, pastikan:
- [ ] Pengujian otomatis lulus 100% (`python -m unittest discover -s tests -p "test_*.py"`).
- [ ] Tidak ada berkas `.db`, `.enc`, `.venv`, `.key`, atau `.log` yang ikut ter-commit.
- [ ] Tidak ada informasi sensitif (password, master key, token) di dalam kode atau dokumen.
- [ ] Dokumentasi `docs/PROJECT_STATUS.md` diperbarui jika ada perubahan status fitur.

