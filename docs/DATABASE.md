# Database Design — CRYPTOSAFE

SQLite is the embedded relational database engine. Schema versioning is managed via migrations (current version: 5) with parameterized SQL queries, foreign key enforcement, and immutability triggers.

## Database Tables

### schema_version
- `version`: INTEGER PRIMARY KEY
- `applied_at`: TEXT NOT NULL (ISO 8601 UTC)

### users
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `username`: TEXT UNIQUE NOT NULL (indexed)
- `password_hash`: TEXT NOT NULL (Argon2id encoded hash)
- `is_active`: INTEGER NOT NULL DEFAULT 1
- `created_at`: TEXT NOT NULL (ISO 8601 UTC)
- `updated_at`: TEXT NOT NULL (ISO 8601 UTC)

### usb_credentials
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id`: INTEGER NOT NULL REFERENCES users(id) (indexed)
- `token_id`: TEXT NOT NULL UNIQUE (indexed)
- `verifier`: TEXT NOT NULL (HMAC verification material; raw secret is never stored)
- `created_at`: TEXT NOT NULL (ISO 8601 UTC)
- `revoked_at`: TEXT (nullable, ISO 8601 UTC)

### face_profiles
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id`: INTEGER NOT NULL REFERENCES users(id) (indexed)
- `encrypted_template`: TEXT NOT NULL (AES-256-GCM encrypted embedding with user-bound AAD)
- `model_name`: TEXT NOT NULL (e.g. `OpenCV-Haar-L2Norm`)
- `model_version`: TEXT NOT NULL (e.g. `1.0.0`)
- `created_at`: TEXT NOT NULL (ISO 8601 UTC)
- `consent_recorded_at`: TEXT NOT NULL (ISO 8601 UTC)
- `revoked_at`: TEXT (nullable, ISO 8601 UTC)

### contracts
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `contract_number`: TEXT NOT NULL UNIQUE
- `title`: TEXT NOT NULL
- `parties`: TEXT NOT NULL
- `start_date`: TEXT
- `end_date`: TEXT
- `status`: TEXT NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft', 'Review', 'Approved', 'Signed', 'Archived')) (indexed)
- `created_by`: INTEGER NOT NULL REFERENCES users(id) (indexed)
- `created_at`: TEXT NOT NULL (ISO 8601 UTC)
- `updated_at`: TEXT NOT NULL (ISO 8601 UTC)

### encrypted_messages
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `contract_id`: INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE (indexed)
- `user_id`: INTEGER NOT NULL REFERENCES users(id) (indexed)
- `content_type`: TEXT NOT NULL CHECK (content_type IN ('note', 'clause', 'draft'))
- `label`: TEXT NOT NULL
- `ciphertext`: TEXT NOT NULL (Vigenère + AES-256-GCM envelope)
- `algorithm`: TEXT NOT NULL DEFAULT 'AES-256-GCM+Vigenere'
- `envelope_version`: INTEGER NOT NULL DEFAULT 1
- `created_at`: TEXT NOT NULL (ISO 8601 UTC)
- `updated_at`: TEXT NOT NULL (ISO 8601 UTC)

### contract_files
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `contract_id`: INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE (indexed)
- `user_id`: INTEGER NOT NULL REFERENCES users(id) (indexed)
- `original_filename`: TEXT NOT NULL
- `encrypted_path`: TEXT NOT NULL UNIQUE (relative path to `data/vault/<uuid>.enc`)
- `mime_type`: TEXT
- `size_bytes`: INTEGER NOT NULL
- `algorithm`: TEXT NOT NULL DEFAULT 'ChaCha20-Poly1305'
- `envelope_version`: INTEGER NOT NULL DEFAULT 1
- `created_at`: TEXT NOT NULL (ISO 8601 UTC)

### blockchain_blocks
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `block_index`: INTEGER NOT NULL UNIQUE (indexed)
- `timestamp`: TEXT NOT NULL (ISO 8601 UTC)
- `event_type`: TEXT NOT NULL (e.g. `CONTRACT_CREATED`, `CONTRACT_STATUS_UPDATED`, `NOTE_CREATED`, `FILE_ATTACHED`)
- `asset_id`: TEXT NOT NULL (indexed, format: `contract:<id>`, `note:<id>`, `file:<id>`)
- `asset_hash`: TEXT NOT NULL (indexed, SHA-256 hex digest)
- `payload_json`: TEXT NOT NULL (canonical JSON metadata without plaintext secrets)
- `previous_hash`: TEXT NOT NULL (SHA-256 hex digest of previous block; genesis uses `0`*64)
- `block_hash`: TEXT NOT NULL (SHA-256 hex digest of block contents)
- `created_by`: INTEGER REFERENCES users(id)

## Database Triggers

To enforce append-only ledger integrity, two triggers prevent modification or deletion of blocks:

```sql
CREATE TRIGGER IF NOT EXISTS prevent_blockchain_update
BEFORE UPDATE ON blockchain_blocks
BEGIN
    SELECT RAISE(ABORT, 'Blockchain blocks are immutable and cannot be updated.');
END;

CREATE TRIGGER IF NOT EXISTS prevent_blockchain_delete
BEFORE DELETE ON blockchain_blocks
BEGIN
    SELECT RAISE(ABORT, 'Blockchain blocks are immutable and cannot be deleted.');
END;
```

## Important Security Notes

- Do not store plaintext sensitive messages in `encrypted_messages`.
- Do not store AES or ChaCha encryption keys in any database table.
- Biometric templates are sensitive: they are encrypted using AES-256-GCM with user-bound AAD before database insertion.
- The USB token verifier stores verification material, never the raw token secret key.
- Enable foreign key enforcement (`PRAGMA foreign_keys = ON;`) on every connection.
- Use atomic transactions (`connection.transaction()` context manager with `SAVEPOINT`) for multi-step mutations to maintain synchronization between domain tables and the blockchain audit trail.
