# CRYPTOSAFE — AI Agent Project Kit

Dokumentasi ini adalah sumber acuan utama untuk membangun CRYPTOSAFE, aplikasi desktop Python untuk pembelajaran dan demonstrasi kriptografi.

## Keputusan proyek

- Platform: desktop
- Bahasa: Python
- GUI: PySide6
- Pengguna: multi-user
- Identitas akun: username unik
- Autentikasi: password (Argon2id), USB hardware/software token, face recognition lokal
- Teks: Vigenere (lapisan demonstrasi) + AES-256-GCM
- File: ChaCha20-Poly1305
- Pesan sensitif di database: AES-256-GCM
- Gambar: AES + LSB steganography
- Integritas aset: blockchain/hash chain sederhana berbasis SHA-256
- Database: SQLite untuk versi awal

## Cara menggunakan dokumentasi

1. Berikan seluruh folder dokumentasi ini kepada AI Agent sebagai project context.
2. Minta agent membaca `AI_AGENT_PROMPT.md` dan semua dokumen yang dirujuk sebelum mengubah kode.
3. Ikuti urutan pada `AI_AGENT_WORKFLOW.md`.
4. Kerjakan satu milestone pada satu waktu.
5. Jalankan tes dan tinjau perubahan sebelum lanjut.
6. Jangan pernah memberikan password, private key, token USB asli, atau data biometrik pribadi kepada agent.

## Prinsip penting

- Jangan mengklaim fitur aman/selesai sebelum implementasi dan tes berhasil.
- Jangan membuat kriptografi sendiri untuk algoritma modern.
- Gunakan library kriptografi teruji.
- Vigenere dan blockchain lokal adalah komponen pembelajaran, bukan pengganti keamanan modern.
- Simpan kunci terpisah dari ciphertext dan database.
- Jangan menambahkan fitur di luar ruang lingkup tanpa persetujuan.

## Status awal

Dokumentasi ini mendefinisikan target proyek. Implementasi GUI tahap pertama yang pernah dibuat mungkin masih berupa prototype simulasi. Agent harus memeriksa kode aktual sebelum menganggap fitur telah tersedia.

## Panduan Instalasi dan Menjalankan Aplikasi (M0)

### 1. Persyaratan Sistem
- Python 3.10 atau yang lebih baru (Windows, Linux, macOS).
- Git (opsional untuk version control).

### 2. Menyiapkan Virtual Environment
Disarankan menggunakan virtual environment lokal agar tidak mencemari environment global:

```powershell
# Membuat virtual environment
python -m venv .venv

# Mengaktifkan virtual environment (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Mengaktifkan virtual environment (Windows Command Prompt)
.venv\Scripts\activate.bat
```

### 3. Memasang Dependensi
```powershell
pip install -r requirements.txt
```

### 4. Menjalankan Aplikasi
```powershell
python main.py
```

### 5. Menjalankan Pengujian
```powershell
python -m unittest discover -s tests
```
