# -*- mode: python ; coding: utf-8 -*-
# CopyArena Professional Client v2.0 Build Configuration

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

# Add current directory to Python path for imports
sys.path.insert(0, str(Path.cwd()))

# Use PyInstaller's comprehensive collection for NumPy and MT5
print("Collecting NumPy and MetaTrader5 dependencies...")
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')
mt5_datas, mt5_binaries, mt5_hiddenimports = collect_all('MetaTrader5')
print(f"✅ Collected {len(numpy_datas)} NumPy data files")
print(f"✅ Collected {len(numpy_binaries)} NumPy binaries")
print(f"✅ Collected {len(mt5_datas)} MT5 data files")
print(f"✅ Collected {len(mt5_binaries)} MT5 binaries")

a = Analysis(
    ['copyarena_client.py'],
    pathex=[str(Path.cwd())],
    binaries=[
        # Include NumPy and MT5 binaries for full compatibility
        *numpy_binaries,
        *mt5_binaries,
    ],
    datas=[
        # Include NumPy and MT5 data files for full compatibility
        *numpy_datas,
        *mt5_datas,
    ],
    hiddenimports=[
        # Auto-collected hidden imports from PyInstaller
        *numpy_hiddenimports,
        *mt5_hiddenimports,
        'tkinter', 
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.simpledialog',
        'requests',
        'websocket',
        'json',
        'threading',
        'datetime',
        'hashlib',
        'base64',
        'io',
        
        # Security & Storage
        'keyring',
        'keyring.backends',
        'keyring.backends.Windows',
        'cryptography',
        'cryptography.fernet',
        
        # System Tray & GUI Enhancement
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw', 
        'PIL.ImageFont',
        
        # Notifications
        'plyer',
        'plyer.platforms.win.notification',
        
        # Additional tkinter modules
        'tkinter.font',
        'tkinter.filedialog',
        
        # HTTP/Network
        'urllib3',
        'ssl',
        'socket',
        
        # System modules
        'os',
        'sys',
        'time',
        'logging',
        'dataclasses',
        'typing',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size (but keep numpy for MT5)
        'matplotlib',
        'pandas',
        'scipy',
        'pytest',
        'black',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CopyArenaClient_Professional_v2.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for professional appearance
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='copyarena_icon.ico',  # Uncomment if you have an icon file
    version_info={
        'version': (2, 0, 0, 0),
        'description': 'CopyArena Professional Windows Client v2.0',
        'company': 'CopyArena',
        'product': 'CopyArena Professional Client',
        'copyright': 'Copyright (C) 2024 CopyArena'
    }
)
