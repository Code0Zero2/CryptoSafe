# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for building standalone CryptoSafe desktop application."""

import sys
import os
from pathlib import Path
import cv2

block_cipher = None

# Locate OpenCV Haar cascade models
opencv_cascade_dir = cv2.data.haarcascades
datas = [
    (opencv_cascade_dir, 'cv2/data'),
    ('README.md', '.'),
]

# Hidden imports required by dynamic PySide6 plugins and cryptographic engines
hidden_imports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'cryptography',
    'cryptography.hazmat.primitives.ciphers.aead',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
    'argon2',
    'argon2.low_level',
    'PIL',
    'PIL.Image',
    'numpy',
    'cv2',
    'sqlite3',
    'cryptosafe',
    'cryptosafe.config',
    'cryptosafe.app',
    'cryptosafe.auth',
    'cryptosafe.crypto',
    'cryptosafe.database',
    'cryptosafe.gui',
    'cryptosafe.gui.audit_dialog',
]

a = Analysis(
    ['main.py'],
    pathex=['src', '.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CryptoSafe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Desktop GUI mode without background terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CryptoSafe',
)
