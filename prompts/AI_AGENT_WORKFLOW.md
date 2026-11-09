# AI Agent Workflow — Cara Penggunaan

## 1. Persiapan

1. Buat folder kerja `CRYPTOSAFE`.
2. Masukkan seluruh dokumen kit ke folder `docs/` atau ke root project sesuai kebutuhan.
3. Jika source code sudah ada, salin/attach repository tersebut juga.
4. Buka project menggunakan AI Agent yang dapat membaca file proyek.
5. Tempel `AI_AGENT_PROMPT.md` sebagai system/project instruction jika platform mendukung. Jika tidak, kirim sebagai pesan pertama.

## 2. Prompt pertama — inspeksi

```text
Baca seluruh dokumentasi CRYPTOSAFE, terutama AI_AGENT_PROMPT.md.
Periksa repository dan file yang sudah ada tanpa mengubah apa pun.
Laporkan:
1. struktur proyek saat ini,
2. fitur yang sudah ada dan statusnya,
3. perbedaan kode dengan dokumentasi,
4. milestone yang paling tepat dikerjakan berikutnya,
5. risiko atau dependensi yang perlu diperhatikan.
Jangan mengedit file dahulu.
```

## 3. Prompt memulai M0/M1

```text
Mulai milestone M0 dan M1 sesuai PLAN.md.
Buat atau rapikan fondasi project dan GUI prototype PySide6.
Login harus memiliki input username dan password.
USB dan face recognition hanya status simulasi dan harus diberi label DEMO.
Buat dashboard dan navigasi logout.
Jangan implementasikan autentikasi nyata atau algoritma kriptografi pada milestone ini.
Jalankan tes yang relevan dan jelaskan cara menjalankan aplikasi.
```

## 4. Prompt untuk milestone berikutnya

Gunakan satu prompt pada satu waktu. Jangan meminta seluruh roadmap sekaligus.

### M2 — User management

```text
Implementasikan hanya M2 pada PLAN.md: SQLite user repository, registrasi multi-user, username unik, validasi password dan hashing Argon2id. Buat migration/schema dan tes. Jangan implementasikan USB atau face recognition dahulu. Laporkan file berubah, hasil tes, dan cara verifikasi manual.
```

### M3 — USB token

```text
Implementasikan hanya M3. Sebelum coding, jelaskan desain challenge-response, lifecycle enroll/revoke, dan keterbatasan secret berbasis file USB. Gunakan CSPRNG dan HMAC dari library teruji; challenge sekali pakai dan expiry. Jangan menganggap serial/label USB sebagai autentikasi kuat. Buat tes replay, wrong token, missing token, revoked token, dan cross-account.
```

### M4 — Face recognition lokal

```text
Implementasikan hanya M4. Lakukan proof-of-concept kompatibilitas OS/Python/library terlebih dahulu. Buat adapter agar GUI tidak bergantung pada library tertentu. Proses harus lokal, ada consent, perlindungan template, dan dokumentasi threshold serta keterbatasan liveness. Jangan klaim anti-spoofing tanpa implementasi dan tes.
```

### M5 — Integrasi login

```text
Integrasikan login berurutan: username, password, USB token, lalu face verification. Pastikan semua faktor terikat pada user_id yang sama. Terapkan session/logout, throttling, dan error handling. Buat integration tests untuk setiap faktor gagal dan akun silang.
```

### M6 — Super-enkripsi teks

```text
Implementasikan M6 saja. Buat Vigenere edukatif dengan aturan alfabet/Unicode terdokumentasi, lalu AES-256-GCM dari library cryptography. Definisikan envelope versioned, nonce unik, dan key management. Uji round-trip, wrong key, tampering, empty/long/Unicode input. Jelaskan bahwa Vigenere bukan keamanan utama.
```

### M7 — Enkripsi file

```text
Implementasikan M7 saja dengan ChaCha20-Poly1305 dari library cryptography. Rancang format file versioned dan autentik. Jelaskan batas ukuran; bila chunked, desain nonce dan autentikasi metadata harus ditinjau sebelum coding. Jangan mengubah file asli. Uji round-trip, wrong key, truncation, tampering, dan empty file.
```

### M8 — Database encryption

```text
Implementasikan M8 saja. Enkripsi pesan sensitif dengan AES-256-GCM sebelum disimpan di SQLite. Kunci harus terpisah dari database. Gunakan parameterized SQL. Buat tes yang membuktikan plaintext tidak muncul dalam database/log dan tampering gagal.
```

### M9 — Steganografi

```text
Implementasikan M9 saja: enkripsi payload AES-GCM lalu sisipkan melalui LSB pada PNG. Definisikan format payload, panjang, versi, kapasitas, dan validasi. Buat tes embed/extract, kapasitas tidak cukup, gambar rusak, dan wrong key. Jangan klaim LSB tidak terdeteksi.
```

### M10 — Blockchain

```text
Implementasikan M10 saja. Buat hash chain lokal dengan SHA-256, canonical serialization, previous_hash, asset digest, dan verifikasi rantai. Buat tes tampering, reorder, missing block, dan asset change. Dokumentasikan bahwa ledger lokal bukan blockchain terdistribusi.
```

### M11 — Integrasi final

```text
Kerjakan M11 berdasarkan PLAN.md dan TESTING.md. Integrasikan modul, jalankan seluruh test suite, periksa logging dan secret leakage, perbarui dokumentasi, serta buat instruksi instalasi/demo/backup/recovery. Jangan menyatakan release siap jika ada tes kritis gagal.
```

## 5. Cara melanjutkan di chat baru

Kirim:
- dokumentasi kit,
- repository/source code terbaru,
- ringkasan milestone terakhir,
- output tes terakhir.

Lalu gunakan:

```text
Lanjutkan proyek CRYPTOSAFE dari kondisi repository saat ini.
Baca AI_AGENT_PROMPT.md dan seluruh dokumentasi.
Periksa perubahan terakhir dan tes yang sudah dijalankan.
Jangan mengasumsikan progres dari percakapan sebelumnya jika tidak terlihat pada repository.
Tentukan satu langkah berikutnya sesuai PLAN.md dan tunggu persetujuan saya sebelum perubahan besar.
```

## 6. Aturan kerja harian

- Satu milestone atau subtask kecil per sesi.
- Minta agent menjelaskan rencana sebelum perubahan besar.
- Tinjau diff sebelum menerima perubahan.
- Jalankan tes setelah perubahan.
- Commit perubahan yang lulus tes.
- Jangan masukkan `.env`, database pribadi, token USB, atau biometrik ke repository.
- Simpan backup sebelum migration atau perubahan storage.
