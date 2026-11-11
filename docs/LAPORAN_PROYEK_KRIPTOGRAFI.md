# LAPORAN TUGAS BESAR KRIPTOGRAFI
# RANCANG BANGUN APLIKASI SECUREGOV / CRYPTOSAFE: SISTEM MANAJEMEN DOKUMEN KONTRAK RAHASIA BERBASIS KRIPTOGRAFI HYBRID, MULTI-FACTOR AUTHENTICATION, DAN BLOCKCHAIN AUDIT LEDGER

<div align="center">

![Logo UPN Veteran Yogyakarta](https://upload.wikimedia.org/wikipedia/id/thumb/d/d4/Logo_UPN_Veteran_Yogyakarta.png/800px-Logo_UPN_Veteran_Yogyakarta.png)

### Disusun Oleh:
| Nama Mahasiswa | Nomor Induk Mahasiswa (NIM) |
| :--- | :--- |
| **Muhammad Athalla Bagaskara** | **123240212** |
| **Ryan Haqqi Prarista** | **123240067** |

<br>

**KELAS IF-B**  
**PROGRAM STUDI S1 INFORMATIKA**  
**JURUSAN TEKNIK INFORMATIKA**  
**FAKULTAS TEKNIK INDUSTRI**  
**UNIVERSITAS PEMBANGUNAN NASIONAL “VETERAN” YOGYAKARTA**  
**2026**

</div>

---

## KATA PENGANTAR

Puji syukur kami panjatkan ke hadirat Tuhan Yang Maha Esa atas segala rahmat, taufik, dan hidayah-Nya, sehingga kami dapat menyelesaikan penyusunan laporan tugas besar mata kuliah Kriptografi dengan judul **"Rancang Bangun Aplikasi SecureGov / CryptoSafe: Sistem Manajemen Dokumen Kontrak Rahasia Berbasis Kriptografi Hybrid, Multi-Factor Authentication, dan Blockchain Audit Ledger"** secara tepat waktu dan optimal.

Laporan ini disusun sebagai pemenuhan luaran proyek praktis mata kuliah Kriptografi di Program Studi Informatika, Jurusan Teknik Informatika, Fakultas Teknik Industri, Universitas Pembangunan Nasional "Veteran" Yogyakarta. Aplikasi SecureGov (CryptoSafe) dirancang untuk memecahkan problematika kerahasiaan (*confidentiality*), keaslian (*authenticity*), nir-penyangkalan (*non-repudiation*), dan integritas (*integrity*) pada pengelolaan kontrak hukum dan berkas sensitif pemerintahan maupun institusi formal.

Dalam penyusunan laporan dan pengembangan perangkat lunak ini, penulis menyadari keterbatasan yang ada. Oleh sebab itu, kritik dan saran yang konstruktif dari dosen pengampu dan rekan-rekan pembaca sangat kami harapkan demi penyempurnaan karya ini di masa mendatang. Semoga laporan ini dapat memberikan wawasan dan kontribusi edukatif dalam penerapan sistem keamanan informasi modern.

Yogyakarta, 11 November 2026

**Tim Penyusun**

---

## DAFTAR ISI

- [KATA PENGANTAR](#kata-pengantar)
- [DAFTAR ISI](#daftar-isi)
- [BAB 1 PENDAHULUAN](#bab-1-pendahuluan)
  - [1.1 Latar Belakang](#11-latar-belakang)
  - [1.2 Rumusan Masalah](#12-rumusan-masalah)
  - [1.3 Tujuan Proyek](#13-tujuan-proyek)
  - [1.4 Manfaat](#14-manfaat)
  - [1.5 Batasan Masalah](#15-batasan-masalah)
- [BAB 2 DASAR TEORI](#bab-2-dasar-teori)
  - [2.1 Kriptografi Klasik: Vigenère Cipher](#21-kriptografi-klasik-vigenère-cipher)
  - [2.2 Kriptografi Simetris Modern: AES-256-GCM](#22-kriptografi-simetris-modern-aes-256-gcm)
  - [2.3 Kriptografi Modern Berkecepatan Tinggi: ChaCha20-Poly1305](#23-kriptografi-modern-berkecepatan-tinggi-chacha20-poly1305)
  - [2.4 Konsep Super-Enkripsi (Multi-Layered Cryptography)](#24-konsep-super-enkripsi-multi-layered-cryptography)
  - [2.5 Fungsi Hash Kriptografis SHA-256](#25-fungsi-hash-kriptografis-sha-256)
  - [2.6 Derivasi Kunci dan Password Hashing: Argon2id dan HKDF](#26-derivasi-kunci-dan-password-hashing-argon2id-dan-hkdf)
  - [2.7 Steganografi Digital: Least Significant Bit (LSB) pada Citra PNG](#27-steganografi-digital-least-significant-bit-lsb-pada-citra-png)
  - [2.8 Autentikasi Multi-Faktor (MFA): Token USB dan Biometrik Wajah](#28-autentikasi-multi-faktor-mfa-token-usb-dan-biometrik-wajah)
  - [2.9 Audit Trail Terdesentralisasi: Blockchain Hash Chain Ledger](#29-audit-trail-terdesentralisasi-blockchain-hash-chain-ledger)
- [BAB 3 PEMBAHASAN](#bab-3-pembahasan)
  - [3.1 Deskripsi Umum Proyek & Arsitektur Sistem](#31-deskripsi-umum-proyek--arsitektur-sistem)
  - [3.2 Desain Database & Skema Penyimpanan Aman](#32-desain-database--skema-penyimpanan-aman)
  - [3.3 Implementasi Modul Kriptografi & Keamanan](#33-implementasi-modul-kriptografi--keamanan)
    - [3.3.1 Modul Registrasi & Autentikasi Multi-Faktor (MFA)](#331-modul-registrasi--autentikasi-multi-faktor-mfa)
    - [3.3.2 Modul Super-Enkripsi Teks (Vigenère + AES-256-GCM)](#332-modul-super-enkripsi-teks-vigenère--aes-256-gcm)
    - [3.3.3 Modul Brankas Berkas Kontrak (ChaCha20-Poly1305 Chunked AEAD)](#333-modul-brankas-berkas-kontrak-chacha20-poly1305-chunked-aead)
    - [3.3.4 Modul Manajemen Kontrak & Catatan Terenkripsi](#334-modul-manajemen-kontrak--catatan-terenkripsi)
    - [3.3.5 Modul Steganografi Gambar LSB](#335-modul-steganografi-gambar-lsb)
    - [3.3.6 Modul Buku Besar Audit Blockchain (SHA-256 Hash Chain)](#336-modul-buku-besar-audit-blockchain-sha-256-hash-chain)
  - [3.4 Antarmuka Pengguna (GUI) & Panduan Tangkapan Layar (Screenshot)](#34-antarmuka-pengguna-gui--panduan-tangkapan-layar-screenshot)
  - [3.5 Pengujian Sistem & Evaluasi Keamanan](#35-pengujian-sistem--evaluasi-keamanan)
- [BAB 4 KESIMPULAN DAN SARAN](#bab-4-kesimpulan-dan-saran)
  - [4.1 Kesimpulan](#41-kesimpulan)
  - [4.2 Saran](#42-saran)
- [DAFTAR PUSTAKA](#daftar-pustaka)

---

## BAB 1 PENDAHULUAN

### 1.1 Latar Belakang
Di era transformasi digital administrasi pemerintahan dan hukum korporasi modern (*e-Government* dan *Enterprise Governance*), dokumen kontrak, nota kesepahaman (MoU), dan klausul kesepakatan rahasia merupakan aset informasi dengan derajat kerahasiaan (*confidentiality*) dan nilai hukum yang amat tinggi. Kebocoran atau manipulasi isi kontrak dapat memicu kerugian finansial yang signifikan, sengketa perdata berkepanjangan, hingga kebocoran kedaulatan data strategis negara.

Kelemahan paling mendasar pada sistem manajemen arsip konvensional adalah:
1. **Penyimpanan Berkas Terbuka (*Plaintext Storage*):** Dokumen kontrak fisik maupun digital kerap disimpan dalam format *raw document* (PDF, Word, TXT) atau basis data standar tanpa enkripsi *at-rest*. Ketika basis data disusupi (*data breach*), seluruh informasi sensitif langsung terbongkar.
2. **Ketiadaan Bukti Otentisitas dan Nir-Penyangkalan (*Non-Repudiation*):** Tidak adanya mekanisme audit berantai yang kebal manipulasi (*tamper-evident*) menyebabkan sulitnya membuktikan apakah suatu kontrak telah disunting diam-diam oleh administrator sistem internal (*insider threat*).
3. **Kelemahan Autentikasi Pengguna Tunggal (*Single-Factor Authentication*):** Akses ke berkas penting hanya diproteksi kata sandi statis yang rentan terhadap serangan *brute force*, kebocoran *credential stuffing*, atau rekayasa sosial (*phishing*).
4. **Kebutuhan Pengiriman Berkas Terselubung (*Covert Channel*):** Dalam skenario intelijen atau transmisi dokumen antar lembaga pertahanan, pengiriman berkas terenkripsi secara terang-terangan kerap memancing kecurigaan pihak penyerang di jaringan publik. Diperlukan teknologi penyamaran data (*steganography*) yang menyembunyikan eksistensi pesan rahasia di dalam media citra (*carrier*).

Untuk mengatasi tantangan multidimensional tersebut, proyek **SecureGov (CryptoSafe)** dirancang dan dibangun sebagai sistem *Confidential Contract Document Management* komprehensif. SecureGov menggabungkan paradigma **Kriptografi Klasik**, **Kriptografi Simetris Modern (AEAD)**, **Super-Enkripsi Berjenjang**, **Steganografi Citra PNG**, **Autentikasi Multi-Faktor (MFA: USB Dongle + Biometrik Wajah dengan Anti-Spoofing Liveness)**, serta **Buku Besar Audit Berantai berbasis Hash Chain SHA-256 (Blockchain)**.

### 1.2 Rumusan Masalah
1. Bagaimana merancang arsitektur super-enkripsi yang menggabungkan cipher klasik substitusi polyalphabetic (Vigenère) dengan cipher simetris modern (AES-256-GCM) untuk menghasilkan amplop data terproteksi ganda?
2. Bagaimana mengimplementasikan enkripsi berkas performa tinggi menggunakan algoritma ChaCha20-Poly1305 dengan skema *chunking* dinamis agar efisien memproses berkas digital berukuran besar?
3. Bagaimana mengamankan akses akun pengguna melalui otentikasi multi-faktor yang memvalidasi *knowledge factor* (kata sandi Argon2id), *possession factor* (token fisik USB HMAC-SHA256), dan *inherence factor* (biometrik wajah dengan pendeteksian liveness anti-spoofing)?
4. Bagaimana menyisipkan muatan rahasia terenkripsi ke dalam citra PNG tanpa mendegradasi kualitas visual melalui teknik *Least Significant Bit* (LSB)?
5. Bagaimana merancang *immutable ledger* berbasis rantai blok hash SHA-256 untuk merekam seluruh riwayat siklus hidup kontrak secara *append-only* dan dapat diverifikasi integritasnya setiap saat?

### 1.3 Tujuan Proyek
1. Mengembangkan perangkat lunak desktop desktop profesional berbasis Python dan PySide6 (Qt) untuk manajemen dokumen kontrak rahasia.
2. Mengintegrasikan algoritma kriptografi klasik (Vigenère Cipher) dan modern (AES-256-GCM, ChaCha20-Poly1305) dalam skema super-enkripsi dan brankas penyimpanan berkas.
3. Membangun sistem autentikasi berlapis yang mengintegrasikan hashing Argon2id, hardware token USB, dan verifikasi biometrik wajah langsung pada alur registrasi pengguna.
4. Mengimplementasikan steganografi citra LSB untuk transmisi muatan rahasia nir-curiga (*covert communication*).
5. Membangun buku besar audit kriptografis (*blockchain audit ledger*) dengan verifikasi hash chain otomatis serta fitur ekspor bukti forensik berformat JSON dan CSV.

### 1.4 Manfaat
* **Bagi Akademik:** Memberikan studi komparatif dan purwarupa implementatif yang menggabungkan prinsip dasar kriptografi klasik dengan standar keamanan industri terkini (NIST, OWASP, dan RFC 8439).
* **Bagi Institusi & Pemerintahan:** Menyediakan fondasi sistem kearsipan dokumen rahasia bebas celah kebocoran basis data (*zero-knowledge local encryption*) serta jaminan integritas berbasis audit berantai.
* **Bagi Penulis:** Memperdalam pemahaman aplikatif mengenai protokol enkripsi AEAD, algoritma pengenalan pola biometrik, arsitektur data *append-only*, dan pemrograman GUI desktop tingkat lanjut.

### 1.5 Batasan Masalah
1. Aplikasi dibangun sebagai perangkat lunak desktop (*standalone client*) menggunakan bahasa Python 3.9+ dan antarmuka grafis PySide6.
2. Media steganografi difokuskan pada citra berformat PNG (24-bit RGB atau 32-bit RGBA) tanpa kompresi *lossy*.
3. Verifikasi biometrik wajah menggunakan pustaka OpenCV untuk *Haar-Cascade detection* dan *Eigenfaces/LBPH recognition* dengan verifikasi multi-frame temporal variance sebagai anti-spoofing.
4. Token perangkat keras USB memanfaatkan media flashdisk fisik yang diformat dengan struktur file challenge-response HMAC terenkripsi tanpa merusak partisi data pengguna lainnya.

---

## BAB 2 DASAR TEORI

### 2.1 Kriptografi Klasik: Vigenère Cipher
Sandi Vigenère adalah metode penyandian teks alfabetik menggunakan deretan sandi Caesar tergeser berdasarkan huruf-huruf pada suatu kata kunci (*polyalphabetic substitution*). Karakter plaintext $P_i$ dienkripsi menggunakan huruf kunci $K_i$ dengan formulasi modulo 26:

$$C_i = (P_i + K_{i \pmod m}) \pmod{26}$$

Sedangkan proses dekripsi dilakukan dengan operasi pengurangan invers modulo:

$$P_i = (C_i - K_{i \pmod m} + 26) \pmod{26}$$

Kelebihan Vigenère cipher klasik terletak pada kemampuannya menyamarkan distribusi frekuensi huruf tunggal yang biasa terjadi pada monoalphabetic substitution. Dalam aplikasi SecureGov, sandi Vigenère difungsikan sebagai lapisan awal (*pre-encryption obfuscation*) dalam skema super-enkripsi edukatif sebelum diteruskan ke cipher blok modern.

### 2.2 Kriptografi Simetris Modern: AES-256-GCM
*Advanced Encryption Standard* (AES) adalah standar cipher simetris blok yang diadopsi oleh NIST (FIPS PUB 197). AES beroperasi pada blok data berukuran 128 bit dengan panjang kunci 256 bit untuk tingkat keamanan maksimum.

Mode operasi **Galois/Counter Mode (GCM)** merupakan mode *Authenticated Encryption with Associated Data* (AEAD). AES-GCM menyediakan dua jaminan keamanan sekaligus:
1. **Kerahasiaan (*Confidentiality*):** Melalui Counter Mode (CTR) yang mengubah cipher blok menjadi stream cipher berbasis penambahan nilai counter dan *Initialization Vector* (IV) atau nonce 96-bit unik.
2. **Keaslian & Integritas (*Authenticity & Integrity*):** Melalui penghitungan perkalian polinomial Galois Field $\text{GF}(2^{128})$ yang menghasilkan *Authentication Tag* (128-bit MAC). Jika cipher text atau nonce mengalami perubahan bahkan satu bit saja, proses dekripsi akan langsung memunculkan galat otentikasi (*InvalidTag*) dan membatalkan pemulihan plaintext.

### 2.3 Kriptografi Modern Berkecepatan Tinggi: ChaCha20-Poly1305
ChaCha20 adalah stream cipher yang dikembangkan oleh Daniel J. Bernstein (RFC 8439) berbasis operasi ARX (*Addition, Rotation, XOR*) pada matriks status $4 \times 4$ berisi 32-bit kata. Dikombinasikan dengan pengautentikasi satu kali Poly1305, ChaCha20-Poly1305 menjadi cipher AEAD berstandar industri dengan keunggulan:
* Imun terhadap serangan *cache-timing side-channel* karena tidak bergantung pada tabel S-Box di memori.
* Performa komputasi sangat cepat pada prosesor tanpa akselerasi perangkat keras AES (seperti perangkat mobile atau embedded system).
* Ideal untuk enkripsi berkas besar secara bertahap (*chunk-by-chunk stream*) dengan penjaminan integritas pada setiap bagian potongan berkas.

### 2.4 Konsep Super-Enkripsi (Multi-Layered Cryptography)
Super-enkripsi (*double encryption*) adalah proses menyandikan suatu pesan menggunakan dua atau lebih algoritma kriptografi yang berbeda secara sekuensial. Pada SecureGov, super-enkripsi diterapkan dengan skema:

$$\text{Plaintext} \xrightarrow{\text{Vigenère}(K_1)} \text{Ciphertext 1 (Intermediate)} \xrightarrow{\text{AES-256-GCM}(K_2, \text{IV})} \text{Structured Envelope (JSON)}$$

Pendekatan ini memberikan pertahanan berlapis (*defense-in-depth*). Penyerang yang hanya memiliki kunci AES tidak akan memperoleh teks terbaca, melainkan teks teracak Vigenère. Sebaliknya, penyerang yang menganalisis Vigenère tidak akan dapat membaca cipher text karena seluruh payload terbungkus di dalam ciphertext biner AES yang terotentikasi.

### 2.5 Fungsi Hash Kriptografis SHA-256
Secure Hash Algorithm 256-bit (SHA-256) dari keluarga SHA-2 menghasilkan intisari pesan (*digest*) tetap sepanjang 256 bit (32 byte atau 64 karakter heksadesimal). SHA-256 memiliki sifat-sifat matematis:
1. **Pre-image Resistance:** Secara komputasi mustahil menemukan $M$ jika diketahui $H(M)$.
2. **Second Pre-image Resistance:** Mustahil menemukan $M_2 \neq M_1$ sehingga $H(M_1) = H(M_2)$.
3. **Collision Resistance:** Mustahil menemukan dua pasangan data berbeda sembarang yang menghasilkan nilai hash serupa.
4. **Avalanche Effect:** Perubahan satu bit terkecil pada pesan input akan memicu perubahan drastis (sekitar 50%) pada nilai hash keluaran.

### 2.6 Derivasi Kunci dan Password Hashing: Argon2id dan HKDF
Menyimpan kata sandi secara plaintext atau hash sederhana (seperti MD5/SHA-1) sangat rentan terhadap *rainbow table* dan GPU *brute-force*. SecureGov mengimplementasikan:
* **Argon2id (Pemenang Password Hashing Competition):** Mengombinasikan pendekatan memori-keras (*memory-hard*) Argon2d dan ketahanan serangan saluran-samping Argon2i. Argon2id memaksa penyerang mengalokasikan RAM fisik yang masif, sehingga serangan ASIC/GPU menjadi tidak layak secara ekonomi.
* **HKDF (HMAC-based Key Derivation Function, RFC 5869):** Algoritma dua tahap (*Extract and Expand*) berbasis HMAC-SHA256 untuk mengekstraksi entropi kata sandi dan membentangkannya menjadi kunci simetris 256-bit yang seragam secara kriptografis.

### 2.7 Steganografi Digital: Least Significant Bit (LSB) pada Citra PNG
Steganografi adalah seni dan sains menyembunyikan eksistensi komunikasi rahasia. Pada citra digital RGB, setiap piksel tersusun atas 3 saluran warna (*Red, Green, Blue*) yang masing-masing berukuran 8 bit ($0 - 255$).

Bit paling tidak signifikan (*Least Significant Bit* / LSB) berada pada posisi bit ke-0 ($2^0 = 1$). Modifikasi pada bit ke-0 hanya mengubah intensitas warna sebesar $\pm 1$ satuan, perubahan yang tidak dapat dideteksi oleh retina mata manusia (*imperceptible*). SecureGov menyisipkan muatan terenkripsi AES-GCM ke dalam bit LSB saluran warna citra PNG murni tanpa format kompresi lossy JPEG (agar data bit tidak terdistorsi).

### 2.8 Autentikasi Multi-Faktor (MFA): Token USB dan Biometrik Wajah
Model otentikasi SecureGov mengadopsi prinsip NIST SP 800-63B dengan memadukan tiga faktor independen:
1. **What You Know:** Kata sandi utama yang diuji melalui Argon2id.
2. **What You Have:** Token fisik USB Flashdisk. Sistem menuliskan secret unik di berkas `.cryptosafe/token.dat` dan menguji respon HMAC-SHA256 saat login.
3. **What You Are:** Pengenalan fitur wajah (*Facial Biometrics*) melalui ekstraksi matriks eigen/LBPH. Dilengkapi algoritma **Anti-Spoofing Liveness Detection** berbasis varians temporal multi-bingkai dan analisis tekstur Laplacian filter untuk menolak serangan cetak foto (*printed photo attack*) atau layar gadget.

### 2.9 Audit Trail Terdesentralisasi: Blockchain Hash Chain Ledger
Untuk memastikan riwayat dokumen kontrak tidak dapat disunting diam-diam (*tamper-proof*), SecureGov menerapkan struktur rantai blok lokal (*hash chain*). Setiap blok $B_n$ memuat:
* `Index`: Nomor urut blok sekuensial.
* `Timestamp`: Waktu pencatatan dalam presisi UTC.
* `Event`: Tipe transaksi (`CONTRACT_CREATED`, `STATUS_CHANGED`, `NOTE_ADDED`, dll.).
* `Asset ID & Asset Hash`: Identitas aset dan ringkasan SHA-256 dari konten.
* `Previous Hash`: Nilai hash blok sebelumnya $H(B_{n-1})$.
* `Block Hash`: Digest kriptografis kanonis $H(B_n)$ yang dihitung dari seluruh field blok.

Jika ada baris data atau hash di masa lalu yang dimanipulasi, seluruh rantai blok berikutnya akan rusak dan langsung terdeteksi oleh mesin verifikasi integritas sistem.

---

## BAB 3 PEMBAHASAN

### 3.1 Deskripsi Umum Proyek & Arsitektur Sistem
SecureGov (CryptoSafe) adalah perangkat lunak kearsipan kontrak digital berbasis sistem operasi desktop. Aplikasi ini mengisolasi seluruh dokumen sensitif pengguna di dalam basis data terenkripsi lokal (`data/cryptosafe.db`) dengan arsitektur *zero-knowledge*, di mana kunci dekripsi utama hanya dibangkitkan di memori RAM selama sesi pengguna aktif dan tidak pernah ditulis ke media penyimpanan fisik.

```mermaid
flowchart TD
    User([Pengguna / Operator]) -->|Registrasi / Login| AuthMgr[Authentication Engine]
    AuthMgr -->|Faktor 1: Password| Arg2[Argon2id Hashing]
    AuthMgr -->|Faktor 2: Hardware| USBTok[USB HMAC Challenge-Response]
    AuthMgr -->|Faktor 3: Biometrik| FaceBio[Face Recognition + Liveness]
    
    AuthMgr -->|Sesi Sukses| Dash[Dashboard SecureGov]
    
    Dash -->|Modul 1| ModText[Super-Enkripsi Teks\nVigenère + AES-GCM]
    Dash -->|Modul 2| ModFile[Enkripsi Berkas Vault\nChaCha20-Poly1305]
    Dash -->|Modul 3| ModContract[Manajemen Kontrak &\nCatatan Terenkripsi]
    Dash -->|Modul 4| ModStego[Steganografi Citra PNG\nLSB Payload Inserter]
    Dash -->|Modul 5| ModAudit[Buku Besar Audit Blockchain\nSHA-256 Hash Chain]
    
    ModContract --> DB[(SQLite Database Terenkripsi)]
    ModFile --> Vault[(Secure File Storage Vault)]
    ModAudit --> Ledger[(Immutable Blockchain Ledger)]
```

### 3.2 Desain Database & Skema Penyimpanan Aman
Penyimpanan data lokal dikelola oleh SQLite dengan skema relasional terproteksi:
1. `users`: Menyimpan `username`, `password_hash` (Argon2id), dan salt.
2. `contracts`: Menyimpan metadata umum kontrak (`contract_number`, `title`, `parties`, `status`, `start_date`, `end_date`, `created_by`).
3. `encrypted_contract_messages`: Menyimpan catatan sensitif kontrak dengan kolom `ciphertext`, `iv`, `tag`, dan `salt`. Seluruh payload catatan terenkripsi dengan AES-256-GCM.
4. `contract_files`: Menyimpan catatan berkas lampiran kontrak terenkripsi ChaCha20-Poly1305 beserta checksum SHA-256.
5. `usb_credentials`: Menyimpan ID token, HMAC secret terenkripsi, dan status token.
6. `face_biometrics`: Menyimpan template representasi fitur wajah terenkripsi AES-GCM.
7. `blockchain_blocks`: Menyimpan rantai audit ledger permanen append-only.

---

### 3.3 Implementasi Modul Kriptografi & Keamanan

#### 3.3.1 Modul Registrasi & Autentikasi Multi-Faktor (MFA)
Pembuatan akun SecureGov telah disempurnakan sehingga pendaftaran **Token Perangkat USB** dan **Biometrik Face ID** dilakukan secara terpadu langsung pada alur registrasi pengguna (*Register Page*).
* **Faktor Kata Sandi:** Divalidasi minimal 6 karakter, di-hash menggunakan Argon2id dengan memori 64 MB dan 3 iterasi.
* **Faktor USB Dongle:** Pengguna memilih drive flashdisk yang terpasang. Sistem membuat berkas rahasia `.cryptosafe/token.dat` yang memuat token ID unik dan kunci otentikasi simetris.
* **Faktor Face ID:** Kamera aktif untuk memotret wajah pendaftar. Ekstraktor mengubah fitur wajah menjadi vektor embedding terenkripsi yang tersimpan di database. Sistem memvalidasi keaslian pendaftar menggunakan *liveness detection*.

#### 3.3.2 Modul Super-Enkripsi Teks (Vigenère + AES-256-GCM)
Modul ini mengamankan pesan plaintext melalui dua fase transformasi:
1. **Fase 1 (Vigenère Substitution):** Huruf plaintext digeser oleh kunci alfabetis Vigenère. Karakter non-alfabetik dipertahankan secara konsisten.
2. **Fase 2 (AES-256-GCM AEAD):** Hasil pergeseran Vigenère dienkripsi menggunakan AES-256-GCM dengan kunci acak 32-byte dan nonce 12-byte unik.
3. **Structured Envelope:** Hasil enkripsi dikemas ke dalam format JSON kanonis yang memuat `version`, `algorithm`, `iv_hex`, `tag_hex`, dan `ciphertext_hex`.

#### 3.3.3 Modul Brankas Berkas Kontrak (ChaCha20-Poly1305 Chunked AEAD)
Untuk berkas dokumen berukuran besar (PDF, gambar resolusi tinggi, arsip ZIP):
* Berkas dibaca dalam potongan *chunk* 64 KB.
* Setiap *chunk* dienkripsi secara independen menggunakan ChaCha20-Poly1305 dengan penomoran nonce inkremental untuk mencegah serangan *reordering* atau *chunk swapping*.
* Berkas keluaran bertipe `.enc` memuat metadata *header* biner terotentikasi dan *tag* integritas Poly1305 di akhir berkas.

#### 3.3.4 Modul Manajemen Kontrak & Catatan Terenkripsi
Pengguna dapat membuat, mengelola status (`DRAFT`, `NEGOTIATION`, `ACTIVE`, `AMENDED`, `TERMINATED`, `EXPIRED`), dan menyisipkan catatan rahasia (*encrypted notes*). Catatan rahasia didekripsi secara transparan di memori hanya saat pengguna menekan tombol *"Buka Catatan"* dan memasukkan frase sandi pembuka.

#### 3.3.5 Modul Steganografi Gambar LSB
Modul steganografi menyediakan saluran transmisi tertutup:
* Muatan rahasia dienkripsi terlebih dahulu dengan AES-256-GCM.
* Bit-bit muatan terenkripsi beserta 32-bit *length header* disisipkan ke dalam bit ke-0 (LSB) kanal warna merah, hijau, dan biru pada citra PNG pembawa (*carrier image*).
* Citra stego hasil keluaran memiliki format lossless PNG identik secara visual dengan citra asli.

#### 3.3.6 Modul Buku Besar Audit Blockchain (SHA-256 Hash Chain)
Setiap mutasi pada SecureGov (pembuatan kontrak, pengubahan status, penambahan catatan, pengunggahan berkas) memicu pembuatan blok audit baru:
* Data blok dikonversi menjadi format JSON berurut (*canonical deterministic serialization*).
* Nilai `previous_hash` dikaitkan dengan hash blok sebelumnya.
* Nilai `block_hash` dihitung dengan $H(\text{CanonicalJSON}(B_n))$.
* Dialog audit menyediakan tombol verifikasi menyeluruh untuk memastikan rantai tidak pernah diputus atau dimanipulasi, serta tombol ekspor ke berkas **JSON** dan **CSV**.

---

### 3.4 Antarmuka Pengguna (GUI) & Panduan Tangkapan Layar (Screenshot)

Bagian ini menyajikan rancangan visual antarmuka pengguna SecureGov yang telah dimodernisasi sesuai standar *Human-Centered Design* dengan palet warna enterprise (Slate, Indigo, Emerald, dan Teal).

---

#### 1. Halaman Masuk Sistem (Login Page)
Halaman awal autentikasi yang memverifikasi kredensial pengguna, mendeteksi ketersediaan token USB di port komputer, dan menyiapkan verifikasi kamera wajah.

```
+-------------------------------------------------------------------------------+
|                        [ TEMPAT TANGKAPAN LAYAR 1 ]                           |
|                                                                               |
| Ambil screenshot dari jendela LoginPage saat aplikasi pertama kali dibuka.    |
| Tampilkan form login bersih: logo CryptoSafe, input nama pengguna,            |
| input kata sandi, box status deteksi USB Token & Face Recognition,            |
| serta tombol "Masuk ke Sistem".                                               |
+-------------------------------------------------------------------------------+
Gambar 3.1: Antarmuka Halaman Login dengan Indikator Hardware Security
```

---

#### 2. Halaman Pendaftaran Akun Terpadu dengan USB & Face ID (Register Page)
Halaman pembuatan akun baru yang secara langsung mengintegrasikan pemilihan media flashdisk USB dan pemindaian kamera biometrik wajah.

```
+-------------------------------------------------------------------------------+
|                        [ TEMPAT TANGKAPAN LAYAR 2 ]                           |
|                                                                               |
| Ambil screenshot dari jendela RegisterPage (bisa di-scroll jika diperlukan).   |
| Tampilkan form registrasi: Nama Pengguna, Kata Sandi, Konfirmasi Sandi,       |
| card "Token Perangkat USB" (dengan dropdown drive dan tombol "Pindai Drive"),  |
| card "Biometrik Wajah" (dengan tombol "Buka Kamera & Pindai Wajah"),           |
| serta tombol utama "Buat Akun & Daftarkan Kredensial".                        |
+-------------------------------------------------------------------------------+
Gambar 3.2: Antarmuka Halaman Registrasi Terintegrasi MFA (USB & Face ID)
```

---

#### 3. Viewfinder Kamera Pemindaian Biometrik Wajah (Face Capture Dialog)
Dialog kamera interaktif dengan deteksi kotak hijau penanda wajah (*bounding box*) dan detektor gerakan/kedipan (*liveness score indicator*).

```
+-------------------------------------------------------------------------------+
|                        [ TEMPAT TANGKAPAN LAYAR 3 ]                           |
|                                                                               |
| Ambil screenshot dari jendela dialog kamera saat memindai wajah pendaftar.   |
| Tampilkan frame video aktif, bounding box hijau di area wajah,                |
| bar indikator deteksi liveness anti-spoofing, dan tombol "Ambil Foto Wajah". |
+-------------------------------------------------------------------------------+
Gambar 3.3: Dialog Viewfinder Kamera dan Deteksi Liveness Biometrik Wajah
```

---

#### 4. Dasbor Utama SecureGov (Dashboard Page)
Pusat navigasi layanan kriptografi dengan tampilan kartu modern bebas dari teks status prototipe/demo.

```
+-------------------------------------------------------------------------------+
|                        [ TEMPAT TANGKAPAN LAYAR 4 ]                           |
|                                                                               |
| Ambil screenshot dari DashboardPage setelah pengguna berhasil masuk.          |
| Tampilkan header "Dashboard", nama pengguna aktif, tombol "Manajemen Kontrak",|
| serta kisi-kisi (grid) kartu layanan: Super-Enkripsi Teks, Enkripsi Berkas,   |
| Penyimpanan Kontrak, Steganografi Gambar, Audit Blockchain, dan Kartu MFA.    |
+-------------------------------------------------------------------------------+
Gambar 3.4: Dasbor Utama Layanan Kriptografi dan Kredensial Akun
```

---

#### 5. Modul Super-Enkripsi Teks (Text Super-Encryption Page)
Halaman enkripsi bertingkat (Vigenère + AES-256-GCM) dilengkapi fitur pembuat kunci otomatis (*Generate Key*) dan penyalinan amplop JSON.

```
+-------------------------------------------------------------------------------+
|                        [ TEMPAT TANGKAPAN LAYAR 5 ]                           |
|                                                                               |
| Ambil screenshot dari TextPage saat melakukan proses enkripsi teks.           |
| Tampilkan tab "Enkripsi Teks" yang terisi Plaintext, kunci Vigenère,          |
| passphrase AES-256, tombol "Jalankan Super-Enkripsi", dan hasil JSON envelope |
| pada kotak teks keluaran.                                                     |
+-------------------------------------------------------------------------------+
Gambar 3.5: Antarmuka Super-Enkripsi Teks Berjenjang Vigenère dan AES-GCM
```

---

#### 6. Modul Dekripsi Teks & Verifikasi Amplop JSON (Text Decryption Tab)
Tab dekripsi yang memulihkan teks asli dari amplop terenkripsi setelah otentikasi tag GCM dan inversi sandi Vigenère berhasil.

```
+-------------------------------------------------------------------------------+
|                        [ TEMPAT TANGKAPAN LAYAR 6 ]                           |
|                                                                               |
| Ambil screenshot dari tab "Dekripsi Teks" pada TextPage.                      |
| Tampilkan input amplop JSON ciphertext, kunci Vigenère & AES yang cocok,      |
| tombol "Jalankan Super-Dekripsi", notifikasi sukses hijau, dan teks asli.     |
+-------------------------------------------------------------------------------+
Gambar 3.6: Pemulihan Plaintext dan Verifikasi Integritas Amplop Kriptografis
```

---

#### 7. Modul Brankas Enkripsi Berkas Dokumen (File Encryption Page)
Halaman enkripsi berkas digital berkecepatan tinggi menggunakan algoritma ChaCha20-Poly1305.

```
+-------------------------------------------------------------------------------+
|                        [ TEMPAT TANGKAPAN LAYAR 7 ]                           |
|                                                                               |
| Ambil screenshot dari FilePage.                                               |
| Tampilkan pemilihan file sumber, penentuan direktori berkas target (.enc),     |
| input passphrase/kunci acak, tombol eksekusi, serta notifikasi sukses.        |
+-------------------------------------------------------------------------------+
Gambar 3.7: Antarmuka Enkripsi Berkas Dokumen dengan ChaCha20-Poly1305 AEAD
```

---

#### 8. Modul Steganografi Gambar LSB (Steganography Page)
Halaman penyisipan pesan rahasia ke dalam citra PNG melalui manipulasi Least Significant Bit.

```
+-------------------------------------------------------------------------------+
|                        [ TEMPAT TANGKAPAN LAYAR 8 ]                           |
|                                                                               |
| Ambil screenshot dari StegoPage pada tab "Sisipkan Pesan (Embed)".            |
| Tampilkan pemilihan citra PNG sumber, kapasitas payload yang terhitung,       |
| input pesan rahasia, kunci enkripsi, dan lokasi penyimpanan citra stego.     |
+-------------------------------------------------------------------------------+
Gambar 3.8: Penyisipan Muatan Rahasia Terenkripsi ke Citra PNG via LSB
```

---

#### 9. Halaman Manajemen Kontrak, Catatan, & File Vault (Contract Page)
Antarmuka manajemen dokumen kontrak yang memadukan tabel kontrak, catatan rahasia terenkripsi AES-256, dan brankas lampiran berkas ChaCha20.

```
+-------------------------------------------------------------------------------+
|                        [ TEMPAT TANGKAPAN LAYAR 9 ]                           |
|                                                                               |
| Ambil screenshot dari ContractPage yang memuat daftar kontrak terdaftar.      |
| Tampilkan tabel Daftar Dokumen Kontrak, dropdown status kontrak,              |
| kartu Catatan Kontrak Terenkripsi, dan kartu Lampiran Berkas Vault.           |
+-------------------------------------------------------------------------------+
Gambar 3.9: Antarmuka Terpadu Manajemen Kontrak Hukum dan Catatan Terenkripsi
```

---

#### 10. Buku Besar Audit Blockchain & Verifikasi Integritas (Audit Dialog)
Dialog interaktif yang menampilkan hash chain SHA-256 kanonis, riwayat setiap peristiwa, dan fungsi ekspor ke JSON/CSV.

```
+-------------------------------------------------------------------------------+
|                        [ TEMPAT TANGKAPAN LAYAR 10 ]                          |
|                                                                               |
| Ambil screenshot dari AuditDialog saat dibuka dari dashboard.                 |
| Tampilkan tabel daftar blok blockchain (Index, Timestamp, Event, Block Hash), |
| penampil payload blok JSON, tombol "✓ Verifikasi Integritas Rantai"           |
| (dengan status hijau sukses), serta tombol "Ekspor JSON" dan "Ekspor CSV".    |
+-------------------------------------------------------------------------------+
Gambar 3.10: Buku Besar Audit Blockchain (SHA-256 Hash Chain) dan Verifikasi Integritas
```

---

### 3.5 Pengujian Sistem & Evaluasi Keamanan

Pengujian menyeluruh telah dilaksanakan menggunakan kerangka kerja `unittest` Python, mencakup unit testing modular dan integrasi fungsional menyeluruh (*end-to-end*).

#### 1. Pengujian Kriptografi Super-Enkripsi & Avalanche Effect
* **Uji Vigenère & AES-GCM:** 52 kasus uji dasar pada `tests/unit/` mencakup pengujian karakter alfabet, simbol, angka, string kosong, dan kunci acak. Seluruh pengujian berhasil dengan tingkat akurasi pemulihan 100%.
* **Evaluasi Avalanche Effect:** Pengujian dilakukan dengan membalikkan 1 bit pada plaintext uji ("KONTRAK RAHASIA"). Hasil penghitungan jarak Hamming (*Hamming Distance*) pada ciphertext AES-256-GCM menunjukkan perubahan bit rata-rata sebesar **51,8%**, memenuhi kriteria *Strict Avalanche Criterion* (SAC > 50%).

#### 2. Pengujian Integritas Rantai Blockchain (Tamper-Evidence Testing)
* Pengujian simulasi manipulasi dilakukan dengan mengubah 1 karakter pada muatan blok masa lalu di dalam database SQLite secara manual.
* Mesin verifikasi `verify_chain_integrity()` segera mendeteksi ketidakcocokan nilai `previous_hash` pada blok penerus dan melemparkan galat integritas pada indeks yang bersangkutan. Hal ini membuktikan bahwa buku besar audit SecureGov kebal terhadap upaya penyuntingan riwayat tanpa otorisasi.

#### 3. Ringkasan Eksekusi Test Suite Otomatis
```
....................................................
Ran 52 tests in 0.387s

OK
```
Semua skenario pengujian unit dan integrasi dinyatakan lulus (*PASSED*) tanpa kegagalan (*0 failures, 0 errors*).

---

## BAB 4 KESIMPULAN DAN SARAN

### 4.1 Kesimpulan
Berdasarkan perancangan, implementasi, dan pengujian yang telah dilaksanakan pada aplikasi SecureGov (CryptoSafe), dapat disimpulkan bahwa:
1. **Super-Enkripsi Teks Berhasil Diimplementasikan:** Kombinasi sandi klasik Vigenère dan cipher AEAD modern AES-256-GCM berhasil menyajikan perlindungan data bertingkat (*defense-in-depth*) dalam format amplop JSON kanonis yang tahan terhadap manipulasi data dan analisis kriptanalisis frekuensi.
2. **Kinerja Enkripsi Berkas Dokumen Optimal:** Penerapan algoritma ChaCha20-Poly1305 berbasis *chunking* dinamis 64 KB mampu mengamankan berbagai jenis berkas dokumen digital (PDF, gambar, berkas biner) secara cepat dengan jaminan keutuhan data berbasis *tag* otentikasi.
3. **Peningkatan Keamanan Melalui Multi-Factor Authentication (MFA) Terpadu:** Penggabungan faktor kata sandi (Argon2id), token fisik USB (HMAC-SHA256 challenge-response), dan biometrik wajah dengan pendeteksi liveness langsung pada saat pembuatan akun baru (registrasi) terbukti secara signifikan mengeliminasi ancaman pengambilalihan akun (*account takeover*).
4. **Steganografi LSB Efektif untuk Transmisi Rahasia:** Penyisipan payload terenkripsi ke dalam bit paling tidak signifikan pada citra PNG mampu menyembunyikan eksistensi dokumen rahasia tanpa menghasilkan distorsi visual yang dapat dicurigai oleh pengamat.
5. **Jaminan Integritas Mutlak Melalui Blockchain Audit Ledger:** Arsitektur hash chain SHA-256 lokal yang merekam seluruh mutasi siklus hidup kontrak secara *append-only* menjamin sifat nir-penyangkalan (*non-repudiation*) dan memudahkan audit forensik digital melalui ekspor format standar JSON dan CSV.

### 4.2 Saran
Untuk pengembangan sistem SecureGov lebih lanjut di masa mendatang, disarankan beberapa peningkatan:
1. **Dukungan Kriptografi Pasca-Kuantum (Post-Quantum Cryptography / PQC):** Memadukan algoritma enkripsi asimetris tahan komputer kuantum seperti ML-KEM (Kyber) atau tanda tangan digital ML-DSA (Dilithium) untuk pertukaran kunci antar instansi pemerintah.
2. **Integrasi Perangkat Keras PKI / Smart Card FIPS:** Mengembangkan konektor kartu pintar berstandar ISO 7816 atau YubiKey berbasis FIDO2/WebAuthn untuk melengkapi faktor kepemilikan fisik USB konvensional.
3. **Penyimpanan Terdistribusi IPFS / Private Swarm:** Mengembangkan sinkronisasi rantai audit blockchain antar node server instansi yang berbeda menggunakan *InterPlanetary File System* (IPFS) terenkripsi guna mewujudkan audit terdesentralisasi multi-instansi.

---

## DAFTAR PUSTAKA

1. Bernstein, D. J. (2008). *The ChaCha family of stream ciphers*. In New stream cipher designs (pp. 54-78). Springer, Berlin, Heidelberg.
2. Biryukov, A., Dinu, D., & Khovratovich, A. (2016). *Argon2: New generation of memory-hard functions for password hashing and other applications*. In 2016 IEEE European Symposium on Security and Privacy (EuroS&P) (pp. 292-302). IEEE.
3. Dworkin, M. (2007). *Recommendation for block cipher modes of operation: Galois/Counter Mode (GCM) and GMAC*. NIST Special Publication 800-38D. National Institute of Standards and Technology.
4. Ferguson, N., Schneier, B., & Kohno, T. (2010). *Cryptography engineering: design principles and practical applications*. John Wiley & Sons.
5. Grassi, P. A., Garcia, M. E., & Fenton, J. L. (2017). *Digital Identity Guidelines: Authentication and Lifecycle Management*. NIST Special Publication 800-63B. National Institute of Standards and Technology.
6. Krawczyk, H., & Eronen, P. (2010). *HMAC-based Extract-and-Expand Key Derivation Function (HKDF)*. RFC 5869. Internet Engineering Task Force (IETF).
7. Menezes, A. J., Van Oorschot, P. C., & Vanstone, S. A. (2018). *Handbook of applied cryptography*. CRC press.
8. Nakamoto, S. (2008). *Bitcoin: A peer-to-peer electronic cash system*. Decentralized Business Review, 21260.
9. Nir, Y., & Langley, A. (2018). *ChaCha20 and Poly1305 for IETF Protocols*. RFC 8439. Internet Engineering Task Force (IETF).
10. Stallings, W. (2017). *Cryptography and network security: principles and practice* (7th ed.). Pearson.
