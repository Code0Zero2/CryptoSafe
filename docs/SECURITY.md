# Security Design and Rules — CRYPTOSAFE

## 1. Threat model (initial)

Protect against:
- Someone opening the app without the required account factors.
- Accidental or unauthorized reading of stored messages/files.
- Ciphertext or encrypted-file modification.
- Unauthorized modification of registered asset records.
- Basic replay of USB token responses.
- Accidental exposure of secrets in logs or repository.

Out of scope unless separately designed:
- Malware/keylogger on the host.
- A fully compromised operating system.
- Coercion or advanced biometric spoofing.
- Forensic-grade undetectability of steganography.
- Distributed consensus or public blockchain security.

## 2. Passwords

- Use Argon2id via a maintained implementation.
- Store encoded hash including salt and parameters.
- Never encrypt passwords for later recovery.
- Never store plaintext passwords.
- Avoid logging submitted passwords.
- Apply login throttling and generic failure messages.

## 3. USB token

- A static marker file, volume label, or USB serial alone is not sufficient authentication.
- Use challenge-response with a cryptographically random challenge.
- The response should be an HMAC or a reviewed equivalent.
- Challenges must expire and be one-time.
- Prevent replay and bind enrollment to the account.
- Provide revoke/re-enroll flow.
- Explain that a secret stored as an ordinary file can be copied. A hardware token is stronger.

## 4. Face recognition

- Process locally.
- Obtain user consent before enrollment.
- Protect templates/embeddings at rest.
- Minimize raw image retention.
- Set and test match thresholds; document false accept/false reject limitations.
- Do not claim liveness detection unless implemented and tested.
- Provide recovery path that does not silently bypass other factors.

## 5. AEAD cryptography

- Use AES-256-GCM and ChaCha20-Poly1305 from a maintained cryptography library.
- Generate a fresh nonce for each encryption under a given key.
- Never decrypt unauthenticated or modified data as valid.
- Handle authentication failure without exposing partial plaintext.
- Include format/version and required metadata in a well-defined envelope.
- Do not implement AES, ChaCha20, GCM, Poly1305, or Argon2 manually.

## 6. Vigenere

- Educational classical layer only.
- Do not claim it provides modern security.
- Document alphabet and normalization rules.
- Modern AEAD layer provides actual confidentiality and integrity.

## 7. Key storage

- Do not hardcode keys.
- Do not store keys beside ciphertext or in SQLite.
- Do not commit `.env`, token secrets, database files containing real user data, or biometric material.
- Define key backup, rotation, revocation, and recovery behavior.
- Do not invent a custom KDF or key-wrapping scheme.

## 8. Database and logging

- Parameterized SQL only.
- Encrypt sensitive fields before insertion.
- Avoid logging plaintext, passwords, keys, token responses, biometric images, or embeddings.
- Restrict local file permissions where supported.
- Document that SQLite file encryption is not automatically provided by encrypting selected message columns.

## 9. Steganography

- Use PNG.
- Encrypt before embedding.
- Validate capacity and payload length.
- Do not claim LSB is undetectable.
- Avoid modifying source image; write a new output.

## 10. Blockchain/hash chain

- Use deterministic canonical serialization.
- Recompute hashes during verification.
- Clearly state a local hash chain can be replaced wholesale by an attacker who controls all local files unless an external trusted anchor/backup exists.
- Do not describe this as a decentralized public blockchain.

## 11. Agent safety rules

- Never ask the user to paste real secrets.
- Use test credentials and dummy biometric fixtures.
- Never run destructive migrations without backup and approval.
- Never delete project data or overwrite user files without explicit approval.
- Explain security trade-offs before implementing a shortcut.
