# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [
    ('flexdown/i18n/*.json', 'flexdown/i18n'),
    ('flexdown/themes/*.qss', 'flexdown/themes'),
    ('bin', 'bin'),
    ('resources', 'resources'),
    ('browser_extension', 'browser_extension'),
]
binaries = []
hiddenimports = []

curl_datas, curl_binaries, curl_hidden = collect_all('curl_cffi')
datas += curl_datas
binaries += curl_binaries
hiddenimports += curl_hidden

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='FlexDown',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/app.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FlexDown',
)
