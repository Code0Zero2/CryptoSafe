# Test Plan — CRYPTOSAFE

## General
- Use temporary directories and disposable SQLite databases.
- Use dummy test accounts and synthetic data.
- Never use real passwords, real biometric data, or production USB secrets in automated tests.

## GUI / M1
- App opens to login page.
- Username and password inputs exist.
- Empty username/password is rejected.
- Demo navigation opens dashboard.
- Logout returns to login.
- Demo labels clearly indicate authentication is not active.

## Account / M2
- Registration succeeds for valid input.
- Duplicate username is rejected.
- Password confirmation mismatch is rejected.
- Password hash differs from plaintext and verifies correctly.
- Wrong password fails.
- Database does not contain plaintext password.

## USB / M3
- Correct enrolled token passes.
- Missing token fails.
- Wrong token fails.
- Expired challenge fails.
- Reused challenge fails.
- Revoked token fails.
- Token for account A cannot authenticate account B.

## Face / M4
- Matching fixture passes according to configured threshold.
- Nonmatching fixture fails.
- Camera unavailable is handled.
- Enrollment consent is recorded.
- No biometric data appears in logs.
- Liveness claims are tested separately.

## Text / M6
- Encrypt then decrypt returns original supported text.
- Wrong key fails authentication.
- Modified ciphertext fails authentication.
- Modified nonce fails authentication.
- Empty and long messages work.
- Unicode and non-alphabet characters follow documented Vigenere policy.

## File / M7
- Encrypt/decrypt round-trip preserves bytes.
- Wrong key fails.
- Modified/truncated file fails.
- Empty file is handled.
- Large-file limits/chunk behavior are tested.
- Source file remains unchanged.

## Database / M8
- Stored sensitive message is not plaintext.
- Authorized decrypt returns original message.
- Tampered ciphertext fails.
- SQL injection-like input is treated as data.
- Keys are absent from database.

## Steganography / M9
- Embed/extract round-trip succeeds on supported PNG.
- Insufficient capacity fails safely.
- Wrong key fails authentication.
- Corrupted image/payload is rejected.
- Output image is created separately.

## Blockchain / M10
- New block links to previous hash.
- Untampered chain validates.
- Modified block data fails validation.
- Modified asset fails digest comparison.
- Missing/reordered block fails validation.
- Document local-ledger trust limitation.

## Integration / M11
- User A cannot use User B's USB enrollment.
- User A cannot use User B's face profile.
- Full login sequence succeeds only when all factors pass.
- Logout clears session.
- Logs contain no secrets.
