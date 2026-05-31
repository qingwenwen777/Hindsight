# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：桌面版后端（单目录 onedir）。

难点处理：
- alembic 迁移脚本/ini 在运行时按文件加载 -> 作为 data 一并打包
- akshare / scipy / pandas / yfinance 含数据文件与隐式导入 -> collect_all
- uvicorn / anthropic / openai 的动态导入 -> 收集子模块
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# 运行时按文件加载的 alembic 资源
datas += [
    ("alembic", "alembic"),
    ("alembic.ini", "."),
]

# 数据密集 / 隐式导入的第三方库，全量收集
# py_mini_racer 含原生 mini_racer.dll，akshare 部分数据源（sina 等）依赖它
for pkg in ("akshare", "scipy", "pandas", "yfinance", "anthropic", "openai", "apscheduler", "py_mini_racer"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# uvicorn 用动态导入加载实现，需显式收集子模块
hiddenimports += collect_submodules("uvicorn")
hiddenimports += [
    "app.main",
    "app.models",
    # SQLite 方言（SQLAlchemy 延迟导入）
    "sqlalchemy.dialects.sqlite",
]


a = Analysis(
    ["desktop_main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="tradeai-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
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
    upx=False,
    upx_exclude=[],
    name="tradeai-backend",
)
