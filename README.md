# CryptoSafe — Sistem Manajemen Dokumen Kontrak Rahasia Berbasis Kriptografi

CryptoSafe is a secure desktop application built with Python and PySide6 (Qt6), serving as a **Confidential Contract Document Management System Based on Cryptography** (*Sistem Manajemen Dokumen Kontrak Rahasia Berbasis Kriptografi*).

The platform demonstrates how modern cryptographic standards (memory-hard password hashing, authenticated symmetric encryption, multi-factor hardware and biometric authentication) can be unified with educational ciphers (Vigenère) and cryptographic integrity structures (append-only SHA-256 local hash chains) to secure the complete lifecycle of confidential contracts, private notes, and sensitive file attachments.

---

## Documentation Quick Links

- [Project Status & Roadmap (`docs/PROJECT_STATUS.md`)](docs/PROJECT_STATUS.md) — Comprehensive feature matrix, test results, known risks, and handover criteria.
- [Developer & Contribution Guide (`docs/DEVELOPMENT_GUIDE.md`)](docs/DEVELOPMENT_GUIDE.md) — Step-by-step setup, running guide, testing, architecture workflows, and Git practices.
- [Security Policy & Threat Model (`docs/SECURITY.md`)](docs/SECURITY.md) — Threat boundaries, cryptographic rationale, and policies.
- [Database Schema & Design (`docs/DATABASE.md`)](docs/DATABASE.md) — Table designs, triggers, indexes, and transactional boundaries.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Implemented Features](#implemented-features)
3. [Technology Stack & Cryptographic Algorithms](#technology-stack--cryptographic-algorithms)
4. [System Architecture & Module Workflow](#system-architecture--module-workflow)
5. [Repository Structure](#repository-structure)
6. [Prerequisites & Windows Setup](#prerequisites--windows-setup)
7. [Running the Application](#running-the-application)
8. [Running Automated Tests](#running-automated-tests)
9. [In-Depth Security Architecture](#in-depth-security-architecture)
10. [Security Limitations & Threat Model](#security-limitations--threat-model)
11. [Feature Status Matrix](#feature-status-matrix)
12. [Contribution Guidelines & Git Workflow](#contribution-guidelines--git-workflow)

---

## Project Overview

CryptoSafe is designed for organizations and students studying applied cryptography, providing an integrated desktop environment for managing sensitive business contracts:

- **Identity & Access Management:** Multi-factor authentication combining knowledge factors (Argon2id passwords), possession factors (USB token HMAC challenge-response), and inherence factors (local biometric facial recognition).
- **Confidentiality:** Dual-layer text encryption (Vigenère demonstration cipher inside AES-256-GCM), ChaCha20-Poly1305 file vault encryption, and LSB image steganography.
- **Integrity & Auditing:** An append-only local SHA-256 hash chain that logs lifecycle events for contracts, encrypted notes, and vault files with atomic rollback protection.
- **Contract & Asset Management:** A complete desktop workflow for drafting, activating, auditing, and archiving contracts with encrypted attachments.

---

## Implemented Features

### 1. Multi-Factor Authentication (MFA)
- **Master Password:** Hashed using **Argon2id** (RFC 9106 recommended parameters) with cryptographically secure random per-user salts.
- **Rate-Limiting & Lockout:** In-memory tracking of consecutive failed login attempts with progressive delays and temporary lockout to mitigate brute-force attacks.
- **USB Hardware/Software 2FA Token:**
  - Auto-detection of removable USB mass storage drives on Windows (or configurable fallback directory).
  - Challenge-response authentication based on **HMAC-SHA256**.
  - Secure token creation, pairing, and token file verification.
- **Biometric Face Recognition (Face ID):**
  - Camera capture dialog using OpenCV.
  - Haar Cascade frontal face detection.
  - Standardized preprocessing: grayscale conversion, 64x64 resolution, histogram equalization, zero-mean centering, and L2-normalized feature vector.
  - Translation-tolerant **Cosine Similarity** matching (threshold $\ge 0.70$).
  - AES-256-GCM encrypted biometric template storage with user-bound Associated Authenticated Data (AAD).

### 2. Classical & Modern Cryptography Suite
- **Vigenère Cipher (Educational Layer):** Full alphabet transposition cipher with configurable keyword, demonstrating historical polyalphabetic substitution.
- **Text Crypto (Vigenère + AES-256-GCM):** Dual-layer confidentiality: plaintext is transformed through Vigenère, then sealed in an authenticated AES-256-GCM envelope using PBKDF2-HMAC-SHA256 key derivation (600,000 iterations, 16-byte random salt).
- **Steganography Studio:** 1-bit Least Significant Bit (LSB) encoding in lossless PNG images. Secret messages are encrypted with AES-256-GCM before embedding, protected by a 4-byte length prefix and magic header `CSLSB\x01` to prevent noise extraction.

### 3. Secure File Vault
- **ChaCha20-Poly1305 Encryption:** Authenticated stream cipher encryption for arbitrary documents and attachments.
- **Random 12-byte Nonces:** Generated independently for each encryption operation.
- **Vault Isolation:** Encrypted files are stored in `data/vault/` under UUID-based storage filenames, stripping original filenames, directory trees, and metadata to prevent path traversal and metadata leakage.
- **Atomic Operations & Cleanup:** Pre-commit file cleanup ensures no orphaned files linger if database transactions fail; orphan detection utilities audit unlinked vault items.

### 4. Contract Lifecycle Management
- **Full Contract CRUD:** Create, update, view, transition status (`DRAFT`, `ACTIVE`, `TERMINATED`, `COMPLETED`, `ARCHIVED`), and delete contracts.
- **Encrypted Notes:** Contract-specific notes encrypted using AES-256-GCM.
- **Encrypted File Attachments:** Direct integration with the Secure File Vault.
- **Atomic Cascading Deletions:** Safe deletion of contracts, their encrypted notes, attachments, and corresponding audit blocks within a single transactional boundary.

### 5. Blockchain SHA-256 Hash Chain (Audit Ledger)
- **Cryptographic Hash Chain:** Each block contains `index`, `timestamp`, `event_type`, `asset_id`, `asset_hash`, `payload`, `previous_hash`, and current block `hash` (SHA-256).
- **SQLite Immutability Triggers:** Database triggers prevent `UPDATE` and `DELETE` operations on `blockchain_blocks`.
- **Integrated Audit Events:**
  - Contracts: `CONTRACT_CREATED`, `CONTRACT_STATUS_UPDATED`, `CONTRACT_DELETED`
  - Notes: `NOTE_CREATED`, `NOTE_UPDATED`, `NOTE_DELETED`
  - Vault Files: `FILE_ATTACHED`, `FILE_DELETED`
- **Zero-Knowledge Privacy:** Block payloads and asset hashes only compute over ciphertexts or encrypted vault binaries. Plaintexts, passwords, and cryptographic keys are never written to the ledger.
- **Full Ledger Integrity Verification:** One-click verification validating genesis block hash, parent hash continuity, SHA-256 block recalculation, and asset hash consistency.

---

## Technology Stack & Cryptographic Algorithms

| Layer / Role | Technology / Library | Specification / Standard |
| :--- | :--- | :--- |
| **Language & Runtime** | Python 3.10+ | Standard CPython |
| **GUI Framework** | PySide6 (Qt 6.12+) | Qt Widgets (Modern Dark Theme) |
| **Password Hashing** | `argon2-cffi` | **Argon2id**: Memory 64 MB, Time Cost 3, Parallelism 4, 16-byte random salt |
| **Authenticated Symmetric Encryption** | `cryptography` | **AES-256-GCM** (12-byte IV, 16-byte tag) & **ChaCha20-Poly1305** (12-byte nonce) |
| **Key Derivation Function** | `cryptography` | **PBKDF2-HMAC-SHA256**: 600,000 iterations, 16-byte random salt |
| **Hardware Token 2FA** | Python `hmac` / `hashlib` | **HMAC-SHA256**: 32-byte secret key, random 32-byte challenge |
| **Computer Vision & Face Detection** | `opencv-python` | OpenCV Haar Cascade (`haarcascade_frontalface_default.xml`), 64x64 ROI extraction |
| **Vector Math & Face Matching** | `numpy` | Zero-mean L2-normalized embeddings, **Cosine Similarity** matching (threshold $\ge 0.70$) |
| **Image Processing & Steganography** | `Pillow` (PIL) | Lossless PNG LSB 1-bit encoding + AES-256-GCM |
| **Integrity Ledger** | Python `hashlib` | Canonical JSON serialization + **SHA-256** hash chain |
| **Database Engine** | SQLite3 | WAL mode, Foreign Keys enabled, SAVEPOINT shared transactions |

---

## System Architecture & Module Workflow

CryptoSafe adopts a strictly separated layered architecture:

```
+-----------------------------------------------------------------------+
|                           Presentation Layer                          |
|  (PySide6 Windows: MainWindow, LoginDialog, ContractPage, VaultPage)   |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                         Coordination / Service Layer                  |
|  ContractService       EncryptedMessageService   ContractFileService  |
|  BlockchainService     AuthService               FaceService          |
|  TextCryptoService     FileCryptoService         StegoService         |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                           Data Access Layer                           |
|  UserRepository         ContractRepository       ContractFileRepository|
|  EncryptedMessageRepo   BlockchainRepository     DatabaseConnection   |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                          Storage & Persistence                        |
|  SQLite Database (data/cryptosafe.db)    File Vault (data/vault/)    |
+-----------------------------------------------------------------------+
```

### Module Workflows

1. **User Authentication Flow:**
   - User enters username and password in `LoginDialog`.
   - `AuthService` verifies credentials against `data/cryptosafe.db` using Argon2id.
   - If USB 2FA is enabled:
     - `USBTokenService` detects USB drive, issues a 32-byte random challenge, computes HMAC-SHA256 response with the paired token key, and compares it in constant time.
   - If Face ID is enabled:
     - `FaceCaptureDialog` activates camera, captures face frames, extracts 64x64 zero-mean L2-normalized features, decrypts the user's stored template using AES-256-GCM, and computes multi-crop Cosine Similarity against the threshold ($0.70$).
   - Upon success, `SessionManager` establishes an active session storing the authenticated user's ID and username (credentials and raw biometric vectors are immediately purged).

2. **Atomic Contract & Blockchain Append Flow:**
   - `ContractService.create_contract(...)` opens a shared SQLite transaction via `connection.transaction()`.
   - The contract row is inserted via `ContractRepository`.
   - Canonical JSON metadata is constructed and hashed using SHA-256.
   - `BlockchainService.append_block(...)` appends the `CONTRACT_CREATED` block to `blockchain_blocks` within the **same** SQLite transaction.
   - If either the database insert or the blockchain append encounters an error, the entire transaction is rolled back via `ROLLBACK TO SAVEPOINT`, preventing desynchronization between state and audit records.

3. **Secure Vault Attachment Flow:**
   - `ContractFileService.attach_file(...)` reads the source file from disk.
   - `FileCryptoService` encrypts file bytes with ChaCha20-Poly1305 using a freshly generated 12-byte nonce.
   - The encrypted ciphertext is written to `data/vault/<uuid>.enc`.
   - The SHA-256 hash of the encrypted `.enc` file is computed as the `asset_hash`.
   - In a shared SQLite transaction, file metadata is saved to `contract_files` and a `FILE_ATTACHED` block is appended to the blockchain.
   - If the database transaction fails, the physical `.enc` file is automatically deleted from disk to prevent orphaned files.

---

## Repository Structure

```
CRYPTOSAFE/
|-- .gitignore                  # Git ignore rules for virtualenv, DBs, vault, and secrets
|-- requirements.txt            # Python dependencies (PySide6, cryptography, opencv, etc.)
|-- main.py                     # Primary desktop entry point
|-- README.md                   # Project overview and introduction
|-- data/                       # Local runtime directory (ignored by git)
|   |-- cryptosafe.db           # SQLite application database
|   `-- vault/                  # ChaCha20-Poly1305 encrypted file storage (*.enc)
|-- docs/                       # Project specifications, security guides, and plans
|   |-- PROJECT_STATUS.md       # Current feature status, test metrics, and backlog
|   |-- DEVELOPMENT_GUIDE.md    # Developer setup, testing, and contribution manual
|   |-- DATABASE.md             # Schema design, tables, triggers, and indices
|   |-- IMPLEMENTATION_GUIDE.md # Technical implementation details
|   |-- PLAN.md                 # Project milestones and task breakdown
|   `-- SECURITY.md             # Threat model and security policies
|-- src/
|   `-- cryptosafe/
|       |-- app.py              # Application lifecycle and PySide6 bootstrap
|       |-- config.py           # Path configuration, constants, and cryptographic defaults
|       |-- auth/               # Authentication & identity services
|       |   |-- auth_service.py         # Argon2id password verification and rate limiting
|       |   |-- face_service.py         # Haar Cascade, feature extraction, Face ID
|       |   |-- session_manager.py      # Thread-safe user session management
|       |   `-- usb_token_service.py    # USB detection and HMAC challenge-response
|       |-- crypto/             # Core cryptographic transformation modules
|       |   |-- aes_gcm.py              # AES-256-GCM authenticated cipher
|       |   |-- chacha20.py             # ChaCha20-Poly1305 authenticated stream cipher
|       |   |-- file_crypto_service.py  # ChaCha20-Poly1305 chunked file vault encryption
|       |   |-- file_envelope.py        # 48-byte file envelope & chunk framing
|       |   |-- key_manager.py          # PBKDF2-HMAC-SHA256 key policies
|       |   |-- steganography_service.py# PNG LSB steganography + AES-256-GCM
|       |   |-- text_crypto_service.py  # Vigenere + PBKDF2 + AES-256-GCM
|       |   |-- text_envelope.py        # Versioned JSON text envelope
|       |   |-- vigenere.py             # Classical educational substitution cipher
|       |   `-- blockchain_service.py   # SHA-256 hash chain, verifier & exporter
|       |-- database/           # Persistence, services, and repositories
|       |   |-- connection.py               # SQLite connection pool and SAVEPOINT context
|       |   |-- blockchain_repository.py    # Blockchain block queries and appends
|       |   |-- contract_service.py         # Contract coordinator with blockchain integration
|       |   |-- contract_repository.py      # Contracts table SQL operations
|       |   |-- contract_file_service.py    # Vault attachment coordinator with blockchain
|       |   |-- contract_file_repository.py # File metadata repository
|       |   |-- encrypted_message_service.py# Encrypted notes coordinator with blockchain
|       |   |-- encrypted_message_repository.py # Notes repository
|       |   |-- user_repository.py          # User accounts repository
|       |   |-- usb_repository.py           # USB credential credentials repository
|       |   |-- face_repository.py          # Biometric face profile repository
|       |   `-- schema.py                   # Versioned SQLite migrations (v1-v5)
|       `-- gui/                # PySide6 graphical user interface
|           |-- main_window.py          # Main application shell with QStackedWidget
|           |-- login_page.py           # User authentication page
|           |-- register_page.py        # User registration page
|           |-- dashboard_page.py       # Central hub, feature cards & MFA controls
|           |-- contract_page.py        # Contract management, notes, and attachments UI
|           |-- file_page.py            # Standalone ChaCha20 file encryption UI
|           |-- text_page.py            # Super-encryption Vigenere + AES-GCM text UI
|           |-- stego_page.py           # PNG LSB image embedding and extraction UI
|           |-- audit_dialog.py         # Blockchain block explorer and integrity verifier
|           |-- face_capture_dialog.py  # Live camera feed, face capture & liveness check
|           `-- usb_dialog.py           # USB dongle enrollment dialog
`-- tests/
    |-- unit/                   # Unit test suite covering all modules and services
    `-- integration/            # End-to-end integration tests (GUI, Blockchain, MFA)
```

---

## Prerequisites & Windows Setup

### System Prerequisites
- **Operating System:** Windows 10 or Windows 11 (64-bit recommended). Linux and macOS are also supported.
- **Python:** Python 3.10, 3.11, or 3.12.
- **Hardware (Optional for MFA Testing):**
  - Standard USB flash drive (FAT32/NTFS) for USB Hardware Token 2FA.
  - Built-in webcam or USB camera for Face ID recognition.

---

### Step-by-Step Setup Guide

#### 1. Clone the Repository
Open PowerShell or Command Prompt:
```powershell
git clone <repository_url>
cd CRYPTOSAFE
```

#### 2. Create and Activate Virtual Environment
```powershell
# Create a local virtual environment
python -m venv .venv

# Activate in Windows PowerShell
.venv\Scripts\Activate.ps1

# (Alternative) Activate in Windows Command Prompt (CMD)
.venv\Scripts\activate.bat
```

> **PowerShell Execution Policy Note:** If PowerShell shows an execution policy error, enable local script execution for the current user:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

#### 3. Upgrade Pip and Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Verify installed packages:
```powershell
pip list
```

---

## Running the Application

CryptoSafe can be executed directly from the project root. The `main.py` entry point automatically configures `sys.path` to include the `src` directory.

### Launch Command
```powershell
# Make sure .venv is activated
python main.py
```

### Alternatively with explicit `PYTHONPATH`
```powershell
# In PowerShell:
$env:PYTHONPATH="src"
python -m cryptosafe.app

# In Windows Command Prompt (CMD):
set PYTHONPATH=src
python -m cryptosafe.app
```

---

## Running Automated Tests

The repository contains an automated test suite covering unit logic, cryptographic edge cases, and end-to-end GUI-database integrations. As of the latest handover run, 319 test scenarios were discovered and executed with 318 passed and 1 skipped (0 failures).

### Run Full Test Suite
```powershell
# Make sure .venv is activated
python -m unittest discover -s tests -p "test_*.py"
```

### Run Focused Test Suites
```powershell
# Run only unit tests
python -m unittest discover -s tests/unit -p "test_*.py"

# Run only integration tests
python -m unittest discover -s tests/integration -p "test_*.py"

# Run specific cryptographic test suite
python -m unittest tests/unit/test_text_crypto_service.py
python -m unittest tests/unit/test_file_crypto_service.py
python -m unittest tests/unit/test_face_recognition.py

# Run blockchain integration test suite
python -m unittest tests/integration/test_contract_blockchain_integration.py
python -m unittest tests/integration/test_note_blockchain_gui_integration.py
python -m unittest tests/integration/test_file_blockchain_gui_integration.py
```

---

## In-Depth Security Architecture

### 1. Password Storage: Argon2id
- **Algorithm:** Argon2id combines Argon2d (data-dependent memory access for side-channel resistance) and Argon2i (data-independent memory access for cache-timing resistance).
- **Parameters:**
  - Memory cost: $65,536\text{ KiB}$ ($64\text{ MB}$)
  - Time iterations: $3$
  - Parallelism: $4$ lanes
  - Salt: 16 bytes generated via `secrets.token_bytes(16)`
- **Storage Format:** Stored as standard encoded PHC string (`$argon2id$v=19$m=65536,t=3,p=4$...`).

### 2. Multi-Factor Token: HMAC-SHA256 Challenge-Response
- **Key Generation:** 32 cryptographically secure random bytes stored inside a protected `token.key` file on the removable drive.
- **Authentication Protocol:**
  1. The server/host generates a 32-byte non-repeating cryptographic challenge $C$.
  2. The service reads the secret key $K$ from the USB token.
  3. The response $R = \text{HMAC-SHA256}(K, C)$ is computed.
  4. The host computes the expected response using the stored key and compares with `hmac.compare_digest(R, R_{\text{expected}})` to prevent timing attacks.

### 3. Face ID: Computer Vision & Encrypted Biometrics
- **Preprocessing Pipeline:**
  1. Frame captured via OpenCV `cv2.VideoCapture`.
  2. Frontal face localized using Haar Feature-based Cascade Classifier.
  3. Bounding box cropped, converted to 8-bit single-channel grayscale, and resized to $64 \times 64$ pixels.
  4. Histogram equalization applied to normalize lighting variations.
  5. Zero-mean centering and L2 unit normalization producing a 4,096-dimensional float vector:
     $$\mathbf{v} = \frac{\mathbf{x} - \mu}{\|\mathbf{x} - \mu\|_2}$$
- **Matching Metric & Translation Tolerance:**
  - Evaluates **Cosine Similarity** ($\mathbf{u} \cdot \mathbf{v}$) across small coordinate shifts ($\pm 2$ pixels) to compensate for Haar Cascade jitter.
  - Verification succeeds if maximum Cosine Similarity $\ge 0.70$.
- **Template Security:**
  - Biometric templates are **never** stored in plaintext.
  - Serialized NumPy embeddings are encrypted with **AES-256-GCM**.
  - User ID and username are passed as **Associated Authenticated Data (AAD)** to prevent template substitution attacks across accounts.

### 4. Text Encryption: Vigenère + AES-256-GCM
- **Layer 1 (Vigenère):** Shifts alphabetical characters by a user-supplied keyword. Non-alphabetic characters remain untouched. Used as an educational visual transformation layer.
- **Layer 2 (AES-256-GCM):**
  - Key derived from passphrase using PBKDF2-HMAC-SHA256 ($600,000$ iterations, 16-byte random salt).
  - 12-byte random initialization vector (IV) generated per message.
  - Authenticated encryption output: `salt (16B) + IV (12B) + ciphertext + GCM auth tag (16B)`.

### 5. File Vault: ChaCha20-Poly1305
- **Algorithm:** Modern authenticated stream cipher standardized in RFC 8439.
- **Storage Architecture:**
  - Source files are encrypted in-memory and saved directly into `data/vault/<uuid>.enc`.
  - Nonces (12 bytes) are uniquely generated per file via `secrets.token_bytes(12)`.
  - The SQLite database records only metadata (file ID, contract ID, storage filename, original file size, encryption timestamp, and SHA-256 ciphertext hash).

### 6. Steganography: LSB + AES-256-GCM
- **Payload Construction:**
  - Secret text is encrypted with AES-256-GCM.
  - Payload layout: `MAGIC_HEADER (4B: "CSAF") + PAYLOAD_LENGTH (4B big-endian) + ENCRYPTED_BLOB`.
- **Embedding:**
  - Embedded into the least significant bit (bit 0) of the RGB channels of a PNG carrier image.
  - Carrier capacity is strictly validated prior to embedding ($8 \text{ bits/byte} \times \text{payload bytes} \le \text{width} \times \text{height} \times 3$).

### 7. Audit Trail: Append-Only SHA-256 Hash Chain
- **Hash Chaining Equation:**
  $$\text{Block Hash}_i = \text{SHA256}\left(\text{index}_i \,\|\, \text{timestamp}_i \,\|\, \text{event\_type}_i \,\|\, \text{asset\_id}_i \,\|\, \text{asset\_hash}_i \,\|\, \text{payload}_i \,\|\, \text{Block Hash}_{i-1}\right)$$
- **Genesis Block:** Block 0 has `previous_hash = "0" * 64`.
- **Database Triggers:** SQLite triggers `prevent_blockchain_update` and `prevent_blockchain_delete` abort any direct modification of existing blocks.
- **Privacy Principle:** No confidential data (passwords, encryption keys, decrypted plaintexts, biometric coordinates) are ever written to the blockchain table.

---

## Security Limitations & Threat Model

Developers extending or reviewing CryptoSafe must understand the following threat boundaries and limitations:

1. **Local Hash Chain is NOT a Distributed Blockchain:**
   - The SHA-256 hash chain is an **internal audit log**, not a Byzantine Fault Tolerant (BFT) distributed ledger.
   - It guarantees detection of accidental tampering or non-root manipulation through SQLite application interfaces.
   - **Boundary:** An attacker with root OS access or direct read/write permission to the SQLite database file on disk can disable triggers, rewrite hashes, and recalculate the chain. It does not replace a multi-party decentralized consensus network.

2. **Facial Recognition Threat Model:**
   - The Haar Cascade + Cosine Similarity matching pipeline is an **educational computer vision implementation**.
   - It does **not** include hardware 3D structured light sensors, infrared depth analysis, or neural liveness detection.
   - **Boundary:** It is vulnerable to presentation attacks (e.g. holding a printed photograph or tablet screen displaying the user's face in front of the webcam). Do not use this implementation for high-risk biometric defense without specialized anti-spoofing hardware.

3. **USB Token Threat Model:**
   - The USB token mechanism verifies the presence of an HMAC key stored in a `.key` file on a mounted volume.
   - **Boundary:** It relies on host filesystem permissions. An attacker who gains physical possession of the USB drive or copies the `.key` file can replicate the token.

4. **Local Host Security & Memory:**
   - Once a user is authenticated, cryptographic operations run in the local CPython process.
   - **Boundary:** Attackers with local administrative/debugging access (e.g. Memory Dumpers, Debuggers) can inspect memory buffers during active decryption operations.

---

## Feature Status Matrix

| Feature / Milestone | Implementation Status | Automated Tests | Notes & Developer Action |
| :--- | :---: | :---: | :--- |
| **User Authentication (Argon2id)** | Complete | 100% Passed | Multi-user with salts and lockout. |
| **USB Token 2FA (HMAC-SHA256)** | Complete | 100% Passed | Requires manual verification with physical USB drive. |
| **Biometric Face ID** | Complete | 100% Passed | Requires manual verification with webcam in physical lighting. |
| **Vigenère + AES-256-GCM Text** | Complete | 100% Passed | Production-grade authenticated envelope. |
| **ChaCha20-Poly1305 File Vault** | Complete | 100% Passed | Zero plaintext leaks, atomic savepoint rollbacks. |
| **LSB Image Steganography** | Complete | 100% Passed | Encrypted PNG payload with capacity checks. |
| **Contract Management (CRUD)** | Complete | 100% Passed | Full lifecycle with cascading integrity. |
| **SHA-256 Hash Chain Ledger** | Complete | 100% Passed | SQLite triggers + complete integrity verifier. |
| **Event Integration (Contracts)** | Complete | 100% Passed | `CONTRACT_CREATED`, `UPDATED`, `DELETED`. |
| **Event Integration (Notes)** | Complete | 100% Passed | `NOTE_CREATED`, `NOTE_UPDATED`, `NOTE_DELETED`. |
| **Event Integration (Vault Files)** | Complete | 100% Passed | `FILE_ATTACHED`, `FILE_DELETED`. |

For complete tracking details, refer to [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md).

---

## Contribution Guidelines & Git Workflow

Detailed developer onboarding instructions and contribution standards are available in [`docs/DEVELOPMENT_GUIDE.md`](docs/DEVELOPMENT_GUIDE.md).

### Core Development Principles
1. **Never Commit Secrets or Runtime Artifacts:**
   - Ensure `data/cryptosafe.db`, `data/vault/`, `token.key`, `.venv/`, and `*.log` are never staged.
   - Verify with `git status` before every commit.
2. **Never Implement Custom Cryptographic Primitives:**
   - Use established, audited implementations from `cryptography` or `argon2-cffi`.
   - Never implement custom symmetric block ciphers, key derivation routines, or hash functions.
3. **Preserve Atomic Transactions:**
   - Any service modifying domain data and appending audit records must use the shared SAVEPOINT transaction helper (`connection.transaction()`).
4. **Zero Trailing Whitespace:**
   - Ensure clean diffs before committing:
     ```powershell
     git diff --check
     ```
5. **Run the Full Test Suite Before Pushing:**
   - Always ensure all tests pass:
     ```powershell
     python -m unittest discover -s tests -p "test_*.py"
     ```

---

*CryptoSafe — Developed for Cryptography & Information Security Curriculum.*
