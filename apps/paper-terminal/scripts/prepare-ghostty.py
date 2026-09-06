#!/usr/bin/env python3
"""Build pristine, pinned Ghostty. No Jim service or terminal multiplexer."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REV = '7aa9591746ffa4d2eee458960c76554352832595'
DEST = ROOT / 'build/ghostty'
SOURCE = ROOT / 'build/deps' / ('ghostty-' + REV)
if not SOURCE.exists():
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    archive = SOURCE.parent / (REV + '.tar.gz')
    urllib.request.urlretrieve('https://codeload.github.com/ghostty-org/ghostty/tar.gz/' + REV, archive)
    with tarfile.open(archive) as tar:
        tar.extractall(SOURCE.parent, filter='data')
    archive.unlink()
if hashlib.sha256((ROOT / 'vendor/ghostty.h').read_bytes()).digest() != hashlib.sha256((SOURCE / 'include/ghostty.h').read_bytes()).digest():
    raise SystemExit('Pinned Ghostty header mismatch')
if subprocess.check_output(['zig', 'version'], text=True).strip() != '0.16.0':
    raise SystemExit('Ghostty requires Zig 0.16.0')
subprocess.run(['zig', 'build', '-Dapp-runtime=none', '-Demit-xcframework=true',
    '-Dxcframework-target=native', '-Doptimize=ReleaseFast', '-Demit-docs=false',
    '-Demit-webdata=false', '-Demit-macos-app=false', '--prefix', str(DEST)], cwd=SOURCE, check=True)
artifacts = list((SOURCE / 'macos/GhosttyKit.xcframework').glob('macos-*/libghostty-internal.a'))
if len(artifacts) != 1:
    raise SystemExit('Expected one native GhosttyKit library')
(DEST / 'lib').mkdir(parents=True, exist_ok=True)
shutil.copy2(artifacts[0], DEST / 'lib/libghostty-internal.a')
shutil.copy2(SOURCE / 'LICENSE', ROOT / 'vendor/GHOSTTY-LICENSE')
(DEST / 'revision').write_text(REV + '\n')
print('Pristine Ghostty ready:', DEST)
