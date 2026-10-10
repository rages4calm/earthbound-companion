# Build from the project root using the repaired CoilSnake Python environment.
# Only code, schema, audit metadata and tool libraries are bundled. The pinned
# upstream Redux project is downloaded and checked on the player's computer.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import coilsnake

script_root=Path(SPECPATH)
root=script_root.parent
native=root/'native-source'
data=[(str(native/'earthbound.yml'),'native-source'),
      (str(native/'commondefs.yml'),'native-source'),
      (str(root/'research/maternalbound-native-bridge.json'),'research')]
for relative in ('src/data/event_script_data.h','src/data/text_refs.h','src/data/runtime_generated/asset_ids.h','src/include/constants.h'):
    path=native/relative
    data.append((str(path),str(Path('native-source')/Path(relative).parent)))
for folder in ('src/game','src/entity','src/intro'):
    for path in (native/folder).glob('*.c'):
        data.append((str(path),str(Path('native-source')/folder)))
data += collect_data_files('coilsnake',excludes=['assets/bin/**','assets/images/**'])
data += collect_data_files('certifi')
hidden=collect_submodules('coilsnake',filter=lambda name:'.ui.gui' not in name)
hidden+=collect_submodules('certifi')
hidden+=collect_submodules('ebtools.config')+collect_submodules('ebtools.text_dsl')
# Editable PEP 660 import finders are invisible to PyInstaller's static
# module graph. Supply the actual source parent as well as hidden imports.
a=Analysis([str(script_root/'redux_setup_entry.py')],pathex=[str(script_root),str(native),str(Path(coilsnake.__file__).parent.parent)],
           binaries=[],datas=data,hiddenimports=hidden,hookspath=[],hooksconfig={},
           runtime_hooks=[],excludes=['wx','pytest','tests'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='redux-setup',debug=False,
        bootloader_ignore_signals=False,strip=False,upx=False,console=True)
