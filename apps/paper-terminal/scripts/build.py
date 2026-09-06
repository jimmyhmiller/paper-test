#!/usr/bin/env python3
"""Build and bundle Paper Terminal, including runtime resources."""
from pathlib import Path
import plistlib
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / 'build/ghostty/lib/libghostty-internal.a').is_file():
    raise SystemExit('Run python3 scripts/prepare-ghostty.py first.')
subprocess.run(['coil', 'build'], cwd=ROOT, check=True)
app = ROOT / 'build/Paper Terminal.app'
contents = app / 'Contents'
macos = contents / 'MacOS'
resources = contents / 'Resources'
macos.mkdir(parents=True, exist_ok=True)
resources.mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT / 'build/release/folio', macos / 'paper-terminal')
shutil.copytree(ROOT / 'config', resources / 'config', dirs_exist_ok=True)
shutil.copytree(ROOT / 'build/ghostty/share/ghostty', resources / 'ghostty', dirs_exist_ok=True)
# Terminfo lives adjacent to Ghostty's resources; bundle it for standalone launch.
shutil.copytree(ROOT / 'build/ghostty/share/terminfo', resources / 'terminfo', dirs_exist_ok=True)
shutil.copy2(ROOT / 'vendor/GHOSTTY-LICENSE', resources / 'GHOSTTY-LICENSE')
subprocess.run(['coil', 'run', 'src/icon.coil'], cwd=ROOT, check=True)
iconset = ROOT / 'build/PaperTerminal.iconset'
iconset.mkdir(exist_ok=True)
for points in [16, 32, 128, 256, 512]:
    for scale in [1, 2]:
        size = points * scale
        name = f'icon_{points}x{points}' + ('@2x' if scale == 2 else '') + '.png'
        subprocess.run(['sips', '-z', str(size), str(size), str(ROOT / 'build/icon.png'), '--out', str(iconset / name)], check=True, stdout=subprocess.DEVNULL)
subprocess.run(['iconutil', '-c', 'icns', str(iconset), '-o', str(resources / 'PaperTerminal.icns')], check=True)
with (contents / 'Info.plist').open('wb') as f:
    plistlib.dump({
        'CFBundleIdentifier': 'dev.coil.paper-terminal',
        'CFBundleName': 'Paper Terminal',
        'CFBundleDisplayName': 'Paper Terminal',
        'CFBundleExecutable': 'paper-terminal',
        'CFBundlePackageType': 'APPL',
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleVersion': '1',
        'CFBundleIconFile': 'PaperTerminal',
        'LSMinimumSystemVersion': '14.0',
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
        'NSHumanReadableCopyright': 'Paper Terminal. Includes Ghostty (MIT).',
    }, f)
subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(app)], check=True)
print(app)
