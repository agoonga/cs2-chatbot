# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['cs2chatbot.py'],  # Entry point of your application
    pathex=[],
    binaries=[
        ('dlls/vcruntime140.dll', '.'),  # Visual C++ Redistributable DLLs
        ('dlls/msvcp140.dll', '.'),
    ],
    datas=[
        ('util', 'util'),  # Include the util directory
        ('modules', 'modules'),  # Include the modules directory
        ('cmds', 'cmds'),  # Include the cmds directory
    ],
    hiddenimports=['sqlite3'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='cs2chatbot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/img/meef.ico',  # Path to your icon
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='cs2chatbot',
)