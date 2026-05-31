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
for pkg in ("akshare", "scipy", "pandas", "yfinance", "anthropic", "openai", "apscheduler"):
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


# ---- 体积裁剪 ----
# 1) 剔除测试目录与测试夹具（scipy/pandas/numpy 带了大量 tests/ 与 *.npz/*.dat）
# 2) 剔除运行时不需要的源/头文件（.pyi/.pyx/.pxd/.c/.h/.f）
# 注意：只删 datas（资源文件），不动 binaries，避免破坏运行时依赖。
import os

_DROP_DIR_PARTS = (
    os.sep + "tests" + os.sep,
    os.sep + "test" + os.sep,
)
_DROP_SUFFIXES = (
    ".pyi", ".pyx", ".pxd", ".pyc",
    ".c", ".h", ".cpp", ".hpp", ".f", ".f90",
)
_TEST_DATA_SUFFIXES = (".npz", ".dat", ".npy")


def _keep(dest: str) -> bool:
    low = dest.lower()
    norm = os.sep + dest.replace("/", os.sep)
    if any(p in norm for p in _DROP_DIR_PARTS):
        return False
    if low.endswith(_DROP_SUFFIXES):
        return False
    if low.endswith(_TEST_DATA_SUFFIXES) and ("test" in low or "sample" in low):
        return False
    return True


_before = len(datas)
datas = [entry for entry in datas if _keep(entry[0])]
print(f"[desktop.spec] datas pruned: {_before} -> {len(datas)}")

# 3) 剔除未使用的大体积二进制：
#    - pyarrow 的可选组件（flight/substrait/dataset/gandiva/acero）——价格缓存只用核心 parquet 读写
#    - py_mini_racer（仅 akshare sina 源用，有 tencent/yfinance 回退；含 ~38MB 原生库）
_DROP_BINARY_PARTS = (
    "arrow_flight",
    "arrow_substrait",
    "arrow_dataset",
    "arrow_acero",
    "gandiva",
    "py_mini_racer",
    "mini_racer",
    "icudtl.dat",
)


def _keep_bin(dest: str) -> bool:
    low = dest.lower().replace("\\", "/")
    return not any(p in low for p in _DROP_BINARY_PARTS)


_bb = len(binaries)
binaries = [entry for entry in binaries if _keep_bin(entry[0])]
print(f"[desktop.spec] binaries pruned: {_bb} -> {len(binaries)}")
# 同样从 datas 里清掉 py_mini_racer 的数据（icudtl.dat 等）
datas = [entry for entry in datas if _keep_bin(entry[0])]


a = Analysis(
    ["desktop_main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "pytest",
        "IPython", "notebook", "jupyter", "PIL", "PyQt5", "PySide2",
        "scipy.io.matlab", "numpy.distutils", "setuptools._distutils",
    ],
    noarchive=False,
)

# Analysis 之后再次过滤：PyInstaller 的库 hook（如 pyarrow）会把 DLL 直接塞进
# a.binaries / a.datas，需在此处统一裁掉未使用的大体积二进制。
_ab = len(a.binaries)
a.binaries = [entry for entry in a.binaries if _keep_bin(entry[0])]
a.datas = [entry for entry in a.datas if _keep_bin(entry[0])]
print(f"[desktop.spec] a.binaries pruned: {_ab} -> {len(a.binaries)}")

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
