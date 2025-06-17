# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files

# Ruta base
base_path = os.path.abspath('.')

# Incluir base de datos y JSON
datas = [
    (os.path.join('diccionarios', 'base_dat.db'), 'diccionarios'),
    (os.path.join('diccionarios', 'black_list.json'), 'diccionarios'),
    (os.path.join('icono.ico'), '.'),
]

# Incluir todos los íconos de botones de la carpeta img
img_path = os.path.join(base_path, 'img')
if os.path.isdir(img_path):
    for archivo in os.listdir(img_path):
        full_path = os.path.join(img_path, archivo)
        if os.path.isfile(full_path):
            datas.append((full_path, os.path.join('img')))

a = Analysis(
    ['main_app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'tkcalendar',
        'pandas'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main_app',
    icon='icono.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Cambialo a True si querés que se abra la consola al ejecutar
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main_app',
)
