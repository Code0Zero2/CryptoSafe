# Implementation Guide — CRYPTOSAFE

## Development baseline

- Python: choose and pin a currently supported version after checking dependency compatibility.
- GUI: PySide6.
- Database: Python sqlite3 initially.
- Password hashing: argon2-cffi.
- Modern cryptography: `cryptography`.
- Image operations: Pillow and NumPy.
- Face recognition: choose after a small compatibility proof-of-concept; keep behind an adapter interface.
- USB detection: choose a cross-platform library after defining supported OS; keep behind an adapter interface.

## Coding rules

1. Use type hints for service interfaces.
2. Keep GUI thin; call services.
3. Use pathlib for paths.
4. Use structured exceptions and user-friendly error messages.
5. Avoid broad `except Exception` unless logging/re-raising at an application boundary.
6. Never log secrets.
7. Add tests for normal, invalid, and tampered input.
8. Keep dependencies minimal and pinned after validation.
9. Do not add cloud APIs for face recognition; local processing is required.
10. Do not add networking or message delivery unless requested.

## First implementation milestone

Build only:
- package structure
- PySide6 main window
- login page with username/password
- visibly simulated USB and face status
- dashboard cards
- navigation and logout
- basic tests for navigation/input validation if practical

The first milestone must not pretend authentication is real. Label the button and status as prototype/demo.

## Later service interfaces (suggested)

- `PasswordService.hash_password(password) -> str`
- `PasswordService.verify_password(password, encoded_hash) -> bool`
- `UsbTokenService.enroll(user_id, usb_device) -> EnrollmentResult`
- `UsbTokenService.verify(user_id, usb_device) -> bool`
- `FaceService.enroll(user_id, camera_frame) -> EnrollmentResult`
- `FaceService.verify(user_id, camera_frame) -> FaceVerificationResult`
- `TextCryptoService.encrypt(plaintext, key_material) -> Envelope`
- `TextCryptoService.decrypt(envelope, key_material) -> plaintext`
- `FileCryptoService.encrypt_file(source, destination, key_material)`
- `FileCryptoService.decrypt_file(source, destination, key_material)`
- `MessageRepository.store_encrypted_message(envelope)`
- `SteganographyService.embed(image, encrypted_payload, output_path)`
- `SteganographyService.extract(image) -> encrypted_payload`
- `BlockchainService.register_asset(asset_id, digest)`
- `BlockchainService.verify_chain() -> VerificationResult`

These are conceptual interfaces. Agent should adapt types to the actual implementation and explain changes.
