# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件 - 完整版
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# 收集所有需要的数据文件
datas = [
    ('web', 'web'),  # 前端文件
]

# 自动收集第三方包数据文件（二维码/PIL等）
datas += collect_data_files('qrcode')
datas += collect_data_files('PIL')

# 收集所有隐藏导入
hiddenimports = [
    # 核心依赖
    'requests',
    'urllib3',
    'charset_normalizer',
    'idna',
    'certifi',

    # WebSocket
    'websocket',
    'websocket_client',

    # GUI
    'webview',

    # Rich
    'rich',

    # HTML解析
    'lxml',
    'cssselect',

    # 异步
    'gevent',
    'greenlet',

    # Web框架
    'bottle',
    'eel',

    # Excel导出
    'openpyxl',

    # 二维码
    'qrcode',
    'PIL',
    'PIL.Image',

    # 其他
    'json',
    'threading',
    'queue',
    'logging',
]

# 尽量覆盖 pywebview/qrcode 的动态导入
hiddenimports += collect_submodules('webview')
hiddenimports += collect_submodules('qrcode')
hiddenimports += collect_submodules('PIL')

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RaincourseAIHelper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
