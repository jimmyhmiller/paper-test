#!/usr/bin/env python3
"""Build a self-contained, ad-hoc signed macOS Paper Calculator bundle."""
from pathlib import Path
import plistlib
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
subprocess.run(['coil', 'build'], cwd=ROOT, check=True)
app = ROOT / 'build/Paper Calculator.app'
contents = app / 'Contents'
macos = contents / 'MacOS'
macos.mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT / 'build/release/paper-calculator', macos / 'paper-calculator')
resources = contents / 'Resources'
resources.mkdir(exist_ok=True)
subprocess.run(['coil', 'run', 'src/icon.coil'], cwd=ROOT, check=True)
iconset = ROOT / 'build/PaperCalculator.iconset'
iconset.mkdir(exist_ok=True)
for points in [16, 32, 128, 256, 512]:
    for scale in [1, 2]:
        size = points * scale
        name = f'icon_{points}x{points}' + ('@2x' if scale == 2 else '') + '.png'
        subprocess.run(['sips', '-z', str(size), str(size), str(ROOT / 'build/icon.png'),
                        '--out', str(iconset / name)], check=True, stdout=subprocess.DEVNULL)
subprocess.run(['iconutil', '-c', 'icns', str(iconset), '-o', str(resources / 'PaperCalculator.icns')], check=True)
with (contents / 'Info.plist').open('wb') as stream:
    plistlib.dump({
        'CFBundleIdentifier': 'dev.coil.paper-calculator',
        'CFBundleName': 'Paper Calculator',
        'CFBundleDisplayName': 'Paper Calculator',
        'CFBundleExecutable': 'paper-calculator',
        'CFBundlePackageType': 'APPL',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1',
        'CFBundleIconFile': 'PaperCalculator',
        'LSMinimumSystemVersion': '14.0',
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
    }, stream)
subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(app)], check=True)
print(app)
