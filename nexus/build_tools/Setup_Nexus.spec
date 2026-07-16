# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['nexus_setup.py'],
    pathex=[],
    binaries=[],
    datas=[('Nexus_AI_Pro.exe', '.'), ('nexus_app.py', '.'), ('nexus_core.py', '.'), ('nexus_video_engine.py', '.'), ('vpk_manager.py', '.'), ('client', 'client'), ('requirements_RTX.txt', '.'), ('requirements_CPU.txt', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='Setup_Nexus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
