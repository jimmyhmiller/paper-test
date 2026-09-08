#!/usr/bin/env python3
"""Build pinned Ghostty with the tracked Paper glyph-layer extension. No Jim service or terminal multiplexer."""
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
patch = ROOT / 'vendor/patches/paper-glyph-layer.patch'
# Accept precisely the pristine or already-patched state. Reject drift;
# never silently edit a differently modified upstream checkout.
args = ['patch', '-p1', '--batch', '--forward', '-i', str(patch)]
check = subprocess.run(args + ['--dry-run'], cwd=SOURCE, capture_output=True)
if check.returncode == 0:
    subprocess.run(args, cwd=SOURCE, check=True)
else:
    check = subprocess.run(['patch', '-p1', '--batch', '--reverse', '--dry-run', '-i', str(patch)],
                           cwd=SOURCE, capture_output=True)
    if check.returncode:
        raise SystemExit('Ghostty source differs from the tracked Paper patch: ' + check.stderr.decode())
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
(DEST / 'revision').write_text(REV + '\n' + hashlib.sha256(patch.read_bytes()).hexdigest() + '\n')
print('Paper-enabled Ghostty ready:', DEST)
