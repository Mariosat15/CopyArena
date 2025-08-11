# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CopyArena Windows Client
This file provides better control over the build process and handles NumPy/MetaTrader5 dependencies properly
"""

import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules
import os

# Collect all MetaTrader5 and NumPy dependencies
mt5_datas, mt5_binaries, mt5_hiddenimports = collect_all('MetaTrader5')
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')

# Additional hidden imports to ensure compatibility
hiddenimports = [
    'MetaTrader5',
    'tkinter',
    'tkinter.ttk',
    'tkinter.scrolledtext',
    'requests',
    'numpy',
    'numpy.core',
    'numpy.core.multiarray',
    'numpy._core',
    'numpy._core.multiarray',
    'numpy.core._methods',
    'numpy.lib.format',
    'threading',
    'json',
    'hashlib',
    'datetime',
    'logging',
    'dataclasses',
    'typing',
    'pathlib',
    'urllib3',
    'certifi',
    'charset_normalizer',
] + mt5_hiddenimports + numpy_hiddenimports

# Data files to include
datas = [
    # Add config file if it exists
    ('copyarena_config.json', '.') if os.path.exists('copyarena_config.json') else None,
] + mt5_datas + numpy_datas

# Remove None entries
datas = [d for d in datas if d is not None]

# Binary files
binaries = mt5_binaries + numpy_binaries

# Analysis
a = Analysis(
    ['copyarena_client.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'PIL',
        'cv2',
        'sklearn',
        'tensorflow',
        'torch',
        'jupyter',
        'IPython',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate files
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create the executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CopyArenaClient',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging, False for release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon file path if you have one
)
