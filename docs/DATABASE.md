# Database Design — CRYPTOSAFE

SQLite is the initial database. Use schema versioning/migrations and parameterized queries.

## Proposed tables

### users
- id: primary key
- username: unique, normalized
- password_hash: Argon2id encoded hash
- is_active: boolean
- created_at
- updated_at

### usb_credentials
- id: primary key
- user_id: foreign key to users
- token_id: random public identifier
- verifier: verifier material appropriate to the selected challenge-response design; never store raw token secret
- created_at
- revoked_at

### face_profiles
- id: primary key
- user_id: foreign key to users
- encrypted_template: protected biometric template/embedding
- model_name
- model_version
- created_at
- consent_recorded_at

### encrypted_messages
- id: primary key
- sender_user_id
- recipient_user_id (nullable if local notes)
- envelope_version
- algorithm
- nonce
- ciphertext
- created_at

### asset_registry
- id: primary key
- asset_identifier
- asset_path_or_logical_name
- sha256_digest
- created_at
- updated_at

### blockchain_blocks
- id: primary key
- block_index
- timestamp
- payload_json
- previous_hash
- block_hash

## Important notes

- Do not store plaintext sensitive message in `encrypted_messages`.
- Do not store AES/ChaCha key in these tables.
- Biometric templates are sensitive; encrypt them with a separately managed key and restrict access.
- Token verifier design must be reviewed before implementation; avoid storing a reusable response.
- Add indexes for username and relevant foreign keys.
- Enable foreign key enforcement.
- Use transactions for multi-step account enrollment.
- Add schema migration tests.
