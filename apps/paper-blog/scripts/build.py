#!/usr/bin/env python3
"""Build and sign the native Paper Blog app, with its bundled title catalog."""
import plistlib
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def main():
    run('coil', 'build')
    app = ROOT / 'build/Paper Blog.app'
    contents = app / 'Contents'
    macos = contents / 'MacOS'
    resources = contents / 'Resources'
    macos.mkdir(parents=True, exist_ok=True)
    resources.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'build/release/paper-blog', macos / 'paper-blog')
    shutil.copy2(ROOT / 'resources/titles.json', resources / 'titles.json')
    run('coil', 'run', 'src/icon.coil', '--', '--snapshot', 'build/icon.png')
    iconset = ROOT / 'build/PaperBlog.iconset'
    iconset.mkdir(exist_ok=True)
    for points in [16, 32, 128, 256, 512]:
        for scale in [1, 2]:
            size = points * scale
            name = f'icon_{points}x{points}' + ('@2x' if scale == 2 else '') + '.png'
            run('sips', '-z', str(size), str(size), str(ROOT / 'build/icon.png'),
                '--out', str(iconset / name), stdout=subprocess.DEVNULL)
    run('iconutil', '-c', 'icns', str(iconset), '-o', str(resources / 'PaperBlog.icns'))
    with (contents / 'Info.plist').open('wb') as stream:
        plistlib.dump({
            'CFBundleIdentifier': 'dev.coil.paper-blog',
            'CFBundleName': 'Paper Blog',
            'CFBundleDisplayName': 'Paper Blog',
            'CFBundleExecutable': 'paper-blog',
            'CFBundlePackageType': 'APPL',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1',
            'CFBundleIconFile': 'PaperBlog',
            'LSMinimumSystemVersion': '14.0',
            'NSHighResolutionCapable': True,
            'NSPrincipalClass': 'NSApplication',
        }, stream)
    run('codesign', '--force', '--deep', '--sign', '-', str(app))
    run('codesign', '--verify', '--deep', '--strict', str(app))
    print(app)


if __name__ == '__main__':
    main()
