# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para NEMO IDE - build one-folder

import os
import sys

# Diretório raiz do projeto (diretório de trabalho atual ao rodar pyinstaller)
ROOT = os.getcwd()

# --- Dados a incluir ---
datas = [
    (os.path.join(ROOT, "dashboard", "dist"), "dashboard/dist"),
    (os.path.join(ROOT, "agents"), "agents"),
    (os.path.join(ROOT, "squads"), "squads"),
    (os.path.join(ROOT, "skills"), "skills"),
    (os.path.join(ROOT, ".env.example"), "."),
    (os.path.join(ROOT, "models_config.py"), "."),
]

hiddenimports = [
    "uvicorn",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "starlette",
    "starlette.middleware",
    "starlette.routing",
    "starlette.staticfiles",
    "starlette.responses",
    "starlette.background",
    "fastapi",
    "fastapi.openapi",
    "fastapi.routing",
    "pydantic",
    "pydantic.v1",
    "pydantic_core",
    "openai",
    "dotenv",
    "yaml",
    "requests",
    "aiohttp",
    "rich",
    "annotated_doc",
]

excludes = [
    "tkinter",
    "matplotlib",
    "numpy",
    "pandas",
    "scipy",
    "PIL",
    "pytest",
    "notebook",
    "jupyter",
    "IPython",
]

a = Analysis(
    ["nemo_server.py"],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NEMO_IDE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NEMO_IDE',
)