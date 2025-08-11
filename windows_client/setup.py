"""
Setup script for CopyArena Windows Client
Creates a standalone executable for easy distribution
"""

import sys
from cx_Freeze import setup, Executable
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(__file__))

# Dependencies are automatically detected, but it's good to specify them
build_options = {
    'packages': [
        'tkinter', 
        'requests', 
        'MetaTrader5', 
        'threading', 
        'json', 
        'hashlib',
        'datetime',
        'logging',
        'dataclasses'
    ],
    'excludes': [
        'test',
        'unittest',
        'pydoc',
        'tkinter.test'
    ],
    'include_files': [
        # Add any additional files that need to be included
    ],
    'optimize': 2
}

# Base for GUI applications on Windows
base = None
if sys.platform == "win32":
    base = "Win32GUI"

# Executable configuration
executables = [
    Executable(
        script="copyarena_client.py",
        base=base,
        target_name="CopyArenaClient.exe",
        icon=None,  # Add icon file path if you have one
        shortcut_name="CopyArena Client",
        shortcut_dir="DesktopFolder"
    )
]

setup(
    name="CopyArena Client",
    version="1.0.0",
    description="CopyArena MT5 Integration Client",
    author="CopyArena LLC",
    url="https://copyarena.com",
    options={'build_exe': build_options},
    executables=executables
)
