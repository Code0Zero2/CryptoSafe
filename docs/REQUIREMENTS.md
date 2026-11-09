# Requirements — CRYPTOSAFE

## 1. Ruang lingkup

CRYPTOSAFE adalah aplikasi desktop Python untuk pembelajaran dan demonstrasi fitur keamanan. Aplikasi bukan produk messenger komersial dan tidak boleh dipasarkan sebagai sistem keamanan tersertifikasi.

## 2. Functional requirements

### FR-01 — Multi-user
- Sistem mendukung lebih dari satu akun.
- Setiap akun memiliki username unik.
- Setiap akun memiliki kredensial dan faktor autentikasi yang terikat pada akun tersebut.

### FR-02 — Registrasi
- Pengguna dapat mendaftarkan username dan password.
- Password dan konfirmasi password harus cocok.
- Username divalidasi dan tidak boleh duplikat.
- Password tidak boleh disimpan plaintext.

### FR-03 — Login
- Form login meminta username dan password.
- Setelah password benar, sistem memeriksa USB token yang terdaftar.
- Sistem kemudian melakukan verifikasi wajah lokal.
- Semua faktor harus terikat pada username yang sama.
- Login gagal jika salah satu faktor gagal.
- UI harus membedakan status DEMO dan status autentikasi nyata.

### FR-04 — USB token
- Pengguna dapat enroll, revoke, dan mengganti token.
- Token harus membuktikan kepemilikan secret dengan challenge-response.
- Challenge harus random, sekali pakai, dan memiliki expiry.
- Sistem harus mencegah replay sejauh desain memungkinkan.

### FR-05 — Face recognition
- Enrollment dan matching dilakukan lokal.
- Pengguna diberi tahu ketika kamera aktif dan data biometrik direkam.
- Sistem tidak mengunggah gambar/embedding ke layanan eksternal.
- Keterbatasan liveness detection dijelaskan.

### FR-06 — Enkripsi teks
- Teks dienkripsi dengan Vigenere lalu AES-256-GCM.
- Teks dapat didekripsi kembali dengan kunci yang benar.
- Modifikasi ciphertext harus terdeteksi oleh autentikasi GCM.
- Vigenere hanya lapisan edukatif.

### FR-07 — Enkripsi file
- File dienkripsi dengan ChaCha20-Poly1305.
- File hasil enkripsi berbeda dari file asli.
- Dekripsi hanya berhasil dengan key yang benar dan data autentik.
- Format file menyimpan versi dan nonce yang dibutuhkan.

### FR-08 — Database
- Pesan sensitif dienkripsi sebelum disimpan.
- SQLite tidak menyimpan pesan sensitif dalam plaintext.
- Key tidak disimpan bersama ciphertext dalam database.
- Query menggunakan parameterized statements.

### FR-09 — Steganografi
- Pesan dienkripsi sebelum disisipkan ke gambar.
- Format PNG didukung.
- Sistem dapat mengekstrak payload dan mendekripsinya.
- Gambar yang rusak atau kapasitas tidak cukup ditangani dengan aman.

### FR-10 — Blockchain/hash chain
- Sistem mencatat hash aset.
- Blok menyimpan hash blok sebelumnya.
- Sistem dapat memvalidasi seluruh rantai.
- Perubahan pada blok/aset terdeteksi jika dibandingkan dengan ledger yang dipercaya.

### FR-11 — Audit dan sesi
- Logout menghapus sesi dan material sensitif sementara.
- Log tidak menyimpan password, key, token, plaintext pesan, atau data biometrik.
- Kegagalan autentikasi dicatat tanpa membocorkan secret.

## 3. Non-functional requirements

- NFR-01: Python desktop GUI menggunakan PySide6.
- NFR-02: Modul GUI, authentication, cryptography, database, steganography, blockchain dipisahkan.
- NFR-03: Semua operasi file dan database menangani exception.
- NFR-04: Algoritma modern menggunakan library kriptografi yang terawat.
- NFR-05: Randomness kriptografis berasal dari CSPRNG/library kriptografi.
- NFR-06: Tidak ada kunci atau password hardcoded.
- NFR-07: Aplikasi mendokumentasikan OS/Python/dependency yang didukung.
- NFR-08: Tes otomatis tersedia untuk algoritma dan layanan inti.
- NFR-09: UI tidak boleh membeku saat operasi berat; gunakan worker/thread bila diperlukan.
- NFR-10: Data biometrik dan token diperlakukan sebagai data sensitif.

## 4. Batasan dan asumsi

- Target awal adalah aplikasi desktop single-machine.
- SQLite digunakan untuk versi awal.
- Face recognition bergantung pada kamera dan dukungan library/model pada OS.
- USB berbasis file secret dapat disalin; ini bukan setara hardware security key.
- Hash chain lokal tidak menyediakan konsensus atau desentralisasi.
- AES-GCM dan ChaCha20-Poly1305 memerlukan nonce unik untuk setiap key.
- Steganografi LSB bukan jaminan kerahasiaan atau ketakterdeteksian.
- Aplikasi perlu diuji pada OS target sebelum demo.

## 5. Kriteria penerimaan tingkat tinggi

- Akun dapat dibuat dan username duplikat ditolak.
- Password disimpan sebagai Argon2id hash.
- Faktor USB dan wajah hanya dapat dikaitkan dengan akun yang tepat.
- Pesan teks round-trip dan perubahan ciphertext terdeteksi.
- File round-trip dan perubahan data terdeteksi.
- Pesan sensitif tidak terlihat plaintext di SQLite.
- Pesan dapat disisipkan dan diekstrak dari PNG.
- Perubahan pada aset/blok dapat terdeteksi.
- Semua tes utama lulus dan keterbatasan didokumentasikan.
