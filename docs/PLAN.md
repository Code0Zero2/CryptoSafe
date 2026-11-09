# Project Plan — CRYPTOSAFE

## 1. Tujuan

Membangun aplikasi desktop Python multi-user untuk demonstrasi penggunaan autentikasi berlapis, enkripsi pesan, enkripsi file, database terenkripsi, steganografi, dan verifikasi integritas aset menggunakan hash chain.

## 2. Prinsip pelaksanaan

1. Implementasi bertahap; jangan membangun semua fitur sekaligus.
2. Setiap milestone harus memiliki tes otomatis/manual.
3. Pertahankan pemisahan GUI, layanan, penyimpanan, dan algoritma.
4. Lakukan code review dan threat review pada fitur keamanan.
5. Jangan menghapus atau mengubah data pengguna tanpa konfirmasi.
6. Jangan menimpa file konfigurasi atau kode yang sudah ada tanpa memeriksa isinya.
7. Gunakan mock/stub hanya untuk pengembangan GUI dan tandai jelas sebagai simulasi.

## 3. Roadmap

### M0 — Inspeksi dan fondasi proyek
- Periksa repository, Python version, OS, dan file yang sudah ada.
- Buat struktur package, virtual environment instructions, dependency file, konfigurasi logging.
- Tambahkan README dan cara menjalankan aplikasi.
- Tetapkan versi dependency yang kompatibel.
- Hasil: aplikasi minimal dapat dijalankan dan tes dasar berjalan.

### M1 — GUI prototype
- PySide6 main window.
- Login page: username dan password.
- Status USB dan kamera ditampilkan sebagai status belum diverifikasi.
- Dashboard dengan kartu fitur.
- Navigasi login/dashboard/logout.
- Semua autentikasi masih mock dan harus diberi label DEMO.
- Hasil: GUI dapat dijalankan; tidak ada klaim autentikasi sungguhan.

### M2 — Database dan manajemen pengguna
- SQLite schema dan migration/versioning sederhana.
- Registrasi multi-user.
- Username unik, validasi input, konfirmasi password.
- Password hashing Argon2id melalui library terawat.
- Verifikasi password saat login.
- Penanganan akun nonaktif dan kegagalan login.
- Jangan simpan password plaintext.
- Hasil: registrasi dan login username/password berfungsi.

### M3 — USB token authentication
- Rancang token per pengguna.
- Pilihan yang disarankan: challenge-response menggunakan kunci rahasia yang dibuat acak dan disimpan pada media USB, dengan verifier/server-side yang tidak menyimpan secret plaintext.
- Gunakan HMAC-SHA-256 untuk respons challenge atau skema setara yang ditinjau.
- Challenge harus acak, sekali pakai, memiliki masa berlaku, dan dicegah dari replay.
- Jangan mengandalkan volume label, serial number, nama file, atau file token statis sebagai satu-satunya bukti.
- Sediakan proses enroll, revoke, dan re-enroll token.
- Jelaskan keterbatasan: file secret pada USB dapat disalin; untuk ketahanan lebih tinggi gunakan perangkat hardware token dengan secure element.
- Hasil: akun hanya lolos tahap USB dengan token terdaftar.

### M4 — Face recognition lokal
- Pilih library/model yang kompatibel dengan OS dan Python.
- Pendaftaran wajah dengan persetujuan pengguna.
- Simpan template/embedding biometrik dengan perlindungan yang sesuai; minimalkan retensi foto mentah.
- Face matching dengan threshold yang dapat dikonfigurasi dan diuji.
- Liveness detection harus dinyatakan sebagai kebutuhan terpisah; jangan mengklaim anti-spoofing jika belum diterapkan.
- Sediakan fallback pemulihan akun yang aman.
- Hasil: verifikasi wajah lokal berjalan dan memiliki dokumentasi keterbatasan.

### M5 — Integrasi autentikasi
- Urutan login: username → password → USB token → face verification → session/dashboard.
- Ikat semua faktor ke akun username yang sama.
- Terapkan rate limiting/penundaan login dan pesan error yang tidak membocorkan apakah username terdaftar.
- Logout menghapus state sesi dan data sementara.
- Hasil: login multi-factor terintegrasi.

### M6 — Super-enkripsi teks
- Implementasikan Vigenere sebagai lapisan klasik edukatif.
- Tentukan alfabet, normalisasi, dan penanganan karakter non-alfabet secara eksplisit.
- Enkripsi hasil Vigenere menggunakan AES-256-GCM dari library `cryptography`.
- Gunakan nonce unik 96-bit untuk setiap enkripsi dengan key yang sama.
- Simpan metadata versi, algoritma, nonce, salt/KDF bila relevan, dan ciphertext dalam format terstruktur.
- Jangan memakai Vigenere sebagai sumber keamanan utama.
- Uji round-trip, karakter, pesan kosong, pesan panjang, kunci salah, dan ciphertext termodifikasi.
- Hasil: encrypt/decrypt teks.

### M7 — Enkripsi file
- Gunakan ChaCha20-Poly1305 dari library `cryptography`.
- Buat format file envelope dengan magic bytes, versi, nonce, metadata minimal, dan ciphertext/tag.
- Tangani file besar dengan batas ukuran yang jelas. Jangan memuat file tak terbatas ke RAM.
- Catat bahwa ChaCha20-Poly1305 API standar memproses satu pesan; untuk file besar gunakan format chunked yang dirancang benar dengan nonce unik per chunk dan autentikasi metadata.
- Jangan mengubah file asli; hasilkan file terenkripsi baru.
- Hasil: encrypt/decrypt file dan deteksi modifikasi.

### M8 — Database message encryption
- Enkripsi field pesan sensitif menggunakan AES-256-GCM sebelum disimpan.
- Simpan nonce dan versi format bersama ciphertext.
- Pisahkan key management dari SQLite.
- Gunakan parameterized queries.
- Uji bahwa plaintext tidak muncul pada database/log.
- Hasil: pesan sensitif tersimpan sebagai ciphertext dan dapat dibaca setelah dekripsi terotorisasi.

### M9 — Steganografi gambar
- Gunakan PNG untuk menghindari kehilangan bit akibat kompresi lossy.
- Enkripsi pesan terlebih dahulu dengan AES-GCM.
- Sisipkan ciphertext, panjang payload, dan format/version melalui LSB.
- Tambahkan batas kapasitas gambar dan validasi payload.
- Ekstraksi harus memverifikasi integritas AES-GCM.
- Jangan klaim steganografi membuat pesan tidak terdeteksi secara forensik.
- Hasil: embed/extract payload pada PNG.

### M10 — Blockchain/hash chain aset
- Definisikan aset yang dicatat (misalnya hash file konfigurasi atau metadata aset).
- Setiap blok: index, timestamp, asset identifier, asset hash, previous hash, block hash, version.
- Hash menggunakan serialisasi JSON kanonis yang deterministik dan SHA-256.
- Implementasikan validasi seluruh rantai dan deteksi perubahan.
- Simpan ledger dan backup.
- Jelaskan bahwa hash chain lokal bukan blockchain terdistribusi dan tidak tahan penggantian seluruh ledger tanpa anchor eksternal.
- Hasil: registrasi dan verifikasi integritas aset.

### M11 — Integrasi, packaging, dan dokumentasi
- Hubungkan semua halaman dengan service layer.
- Uji skenario end-to-end.
- Audit log agar tidak memuat password, key, plaintext, embedding, atau token.
- Buat instruksi instalasi, backup, recovery, dan keterbatasan.
- Pertimbangkan packaging desktop setelah stabil.
- Hasil: release kandidat untuk demonstrasi.

## 4. Definition of Done setiap milestone

Milestone hanya dianggap selesai jika:
- Kode berjalan pada environment yang didokumentasikan.
- Tes terkait lulus.
- Tidak ada secret hardcoded.
- Error ditangani dan pesan pengguna jelas.
- README/dokumentasi diperbarui.
- Perubahan diringkas dan file yang berubah dicatat.
- Keterbatasan yang belum diselesaikan ditulis secara eksplisit.

## 5. Urutan prioritas

M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 → M9 → M10 → M11.

Jangan melompati milestone keamanan yang menjadi dependensi fitur berikutnya tanpa persetujuan pengguna.
