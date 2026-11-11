#!/usr/bin/env python3
"""Build helper script for compiling CryptoSafe into a standalone desktop executable using PyInstaller."""

import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("=" * 70)
    print("CryptoSafe — Standalone Desktop Executable Builder")
    print("=" * 70)

    # 1. Check Python version
    major, minor = sys.version_info[:2]
    print(f"[1/4] Memeriksa versi Python: Python {major}.{minor} detected.")
    if major < 3 or (major == 3 and minor < 10):
        print("ERROR: CryptoSafe memerlukan Python 3.10 atau yang lebih baru.")
        sys.exit(1)

    # 2. Check PyInstaller availability
    print("[2/4] Memeriksa pustaka PyInstaller...")
    try:
        import PyInstaller
        print(f"      PyInstaller versi {PyInstaller.__version__} ditemukan.")
    except ImportError:
        print("      PyInstaller belum terpasang.")
        print("      Silakan pasang dengan menjalankan: pip install pyinstaller")
        sys.exit(1)

    # 3. Clean prior build artifacts
    print("[3/4] Membersihkan artefak build sebelumnya (build/, dist/)...")
    for folder in ("build", "dist"):
        p = Path(folder)
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            print(f"      Folder '{folder}' berhasil dibersihkan.")

    # 4. Execute PyInstaller using cryptosafe.spec
    spec_file = Path("cryptosafe.spec")
    if not spec_file.is_file():
        print("ERROR: File konfigurasi 'cryptosafe.spec' tidak ditemukan!")
        sys.exit(1)

    print("[4/4] Memulai kompilasi dengan PyInstaller (cryptosafe.spec)...")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "cryptosafe.spec"]
    try:
        res = subprocess.run(cmd, check=True)
        print("\n" + "=" * 70)
        print("BUILD SELESAI DENGAN SUKSES!")
        print("Aplikasi standalone dapat ditemukan di direktori:")
        print(f"-> {Path('dist/CryptoSafe').resolve()}")
        print("=" * 70)
        return res.returncode
    except subprocess.CalledProcessError as err:
        print(f"\nERROR: Kompilasi PyInstaller gagal dengan kode keluar {err.returncode}")
        return err.returncode

if __name__ == "__main__":
    sys.exit(main())
