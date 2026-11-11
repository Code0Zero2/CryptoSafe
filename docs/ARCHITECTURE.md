# Architecture — CRYPTOSAFE

## 1. Architectural style

Gunakan layered modular monolith untuk versi desktop awal:

- Presentation: PySide6 windows/pages/widgets.
- Application services: use cases dan orchestration.
- Domain/core: aturan autentikasi, format pesan, block model.
- Infrastructure: SQLite, filesystem, camera adapter, USB adapter, crypto library.

GUI tidak boleh mengimplementasikan algoritma kriptografi langsung. GUI memanggil service dan menampilkan hasil.

## 2. Project structure

```text
CRYPTOSAFE/
├── main.py
├── requirements.txt
├── .gitignore
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   ├── DEVELOPMENT_GUIDE.md
│   ├── PLAN.md
│   ├── PROJECT_STATUS.md
│   ├── REQUIREMENTS.md
│   ├── SECURITY.md
│   └── TESTING.md
├── src/
│   └── cryptosafe/
│       ├── __init__.py
│       ├── app.py
│       ├── config.py
│       ├── auth/
│       │   ├── auth_service.py
│       │   ├── face_service.py
│       │   ├── password_service.py
│       │   ├── rate_limiter.py
│       │   ├── session_manager.py
│       │   └── usb_token_service.py
│       ├── common/
│       │   ├── errors.py
│       │   └── logging_config.py
│       ├── crypto/
│       │   ├── aes_gcm.py
│       │   ├── blockchain_service.py
│       │   ├── chacha20.py
│       │   ├── file_crypto_service.py
│       │   ├── file_envelope.py
│       │   ├── key_manager.py
│       │   ├── steganography_service.py
│       │   ├── text_crypto_service.py
│       │   ├── text_envelope.py
│       │   └── vigenere.py
│       ├── database/
│       │   ├── blockchain_repository.py
│       │   ├── connection.py
│       │   ├── contract_file_repository.py
│       │   ├── contract_file_service.py
│       │   ├── contract_repository.py
│       │   ├── contract_service.py
│       │   ├── encrypted_message_repository.py
│       │   ├── encrypted_message_service.py
│       │   ├── face_repository.py
│       │   ├── schema.py
│       │   ├── usb_repository.py
│       │   └── user_repository.py
│       └── gui/
│           ├── audit_dialog.py
│           ├── contract_page.py
│           ├── dashboard_page.py
│           ├── face_capture_dialog.py
│           ├── file_page.py
│           ├── login_page.py
│           ├── main_window.py
│           ├── register_page.py
│           ├── stego_page.py
│           ├── styles.py
│           ├── text_page.py
│           └── usb_dialog.py
└── tests/
    ├── unit/
    └── integration/
```

Pemisahan tanggung jawab antar layer (Presentation, Application Services, Data Access/Repositories, dan Infrastructure) dijaga secara ketat untuk menjamin modularitas dan kemudahan pengujian independen.

## 3. Login sequence

1. User enters username and password.
2. Auth service retrieves account record by normalized username.
3. Verify password using Argon2id.
4. Resolve the token enrollment associated with the same user.
5. Perform USB token challenge-response.
6. Perform local face verification against the same user enrollment.
7. Create authenticated session.
8. Open dashboard.

Do not reveal whether a username exists through different public error messages. Apply throttling to repeated failures.

## 4. Data flow — text

Plaintext → Vigenere transform → AES-256-GCM encryption → versioned envelope → storage/transmission.

Decryption reverses the order: AES-GCM authentication/decryption → Vigenere inverse → plaintext.

AES key is not the Vigenere key. Use a separate, explicit key policy. Do not derive AES key directly from a short Vigenere keyword.

## 5. Data flow — file

File bytes → ChaCha20-Poly1305 authenticated encryption → versioned file envelope → output file.

For large files, define a reviewed chunked format with unique nonce per chunk, authenticated chunk index/metadata, and final completeness verification. Do not improvise chunk nonce construction.

## 6. Data flow — image

Secret message → AES-GCM envelope → binary payload with length/version → LSB embedding into PNG.

Extraction → payload validation → AES-GCM authentication/decryption → plaintext.

## 7. Data flow — database

Sensitive plaintext → AES-GCM service → nonce + ciphertext + version → SQLite.

Key material must be outside the database. Use an explicit key-management design, not a hardcoded constant.

## 8. Data flow — blockchain

Asset bytes / canonical metadata snapshot → SHA-256 digest → block record containing previous block hash → deterministic canonical serialization → block hash.

Integrated audit events:
- Contracts: `CONTRACT_CREATED`, `CONTRACT_STATUS_UPDATED`, `CONTRACT_DELETED`.
- Notes: `NOTE_CREATED`, `NOTE_UPDATED`, `NOTE_DELETED`.
- Vault Files: `FILE_ATTACHED`, `FILE_DELETED`.

Verification recomputes asset digest, block hashes, and previous-hash links.

## 9. Key management principles

- Separate keys by purpose: text, file, database, image payload, USB token.
- Never reuse nonce with the same AEAD key.
- Use cryptographically secure random generation.
- Store key material separately from encrypted data.
- For a student prototype, document the selected key wrapping/KDF approach and its limitations.
- Never print or log keys.
