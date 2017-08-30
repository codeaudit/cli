# -*- mode: python -*-

import sys
import os.path
import platform
import config_parser


cfg_parser_loc = os.path.dirname(sys.modules['config_parser'].__file__)

a = Analysis(['riseml/__main__.py'],
             pathex=[],
             binaries=[('/usr/bin/rsync', 'bin')],
             datas=[(os.path.join(cfg_parser_loc, 'schemas/*'), 'config_parser/schemas')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['win32com'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=None)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=None)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='riseml_%s' % platform.system().lower(),
          debug=False,
          strip=False,
          upx=True,
          console=True )
