#!/usr/bin/env python3
"""Exercise the app against real PTYs, including launch from a standalone bundle."""
from pathlib import Path
import os
import plistlib
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build'
BUILD.mkdir(exist_ok=True)

def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)

run('coil', 'verify')
run('cc', '-std=c11', '-fsyntax-only', '-Ivendor', 'tests/abi.c')
run('coil', 'build', 'tests/integration.coil', '-o', str(BUILD / 'integration'))
run('python3', 'scripts/build.py')
# A separate bundle exercises NSBundle resolution without changing the production app.
app = BUILD / 'Integration.app'
if app.exists():
    shutil.rmtree(app)
shutil.copytree(BUILD / 'Paper Terminal.app', app)
contents = app / 'Contents'
shutil.copy2(BUILD / 'integration', contents / 'MacOS/paper-terminal')
plist_path = contents / 'Info.plist'
with plist_path.open('rb') as f:
    plist = plistlib.load(f)
plist['CFBundleIdentifier'] = 'dev.coil.paper-terminal.integration'
with plist_path.open('wb') as f:
    plistlib.dump(plist, f)
run('codesign', '--force', '--deep', '--sign', '-', str(app))
log = BUILD / 'integration-bundle.log'
with log.open('w') as f:
    result = subprocess.run([str(contents / 'MacOS/paper-terminal')], cwd='/tmp',
                            env={**os.environ, 'GHOSTTY_LOG': 'stderr'},
                            stdout=f, stderr=subprocess.STDOUT, timeout=90)
output = log.read_text()
if result.returncode or 'PASS: real PTYs' not in output:
    raise SystemExit(output)
if re.search(r'(^|\n)(error\(|assertion failed)', output):
    raise SystemExit(output)
if re.search(r'spirv error|error initializing postprocess shaders|failed to compile.*shader', output):
    raise SystemExit(output)
if 'shell integration automatically injected' not in output:
    raise SystemExit('Login shell integration did not load; see ' + str(log))
if '/Integration.app/Contents/Resources/config/cursor.glsl' not in output:
    raise SystemExit('Bundled shader did not load; see ' + str(log))
# Ghostty must reap every direct shell process owned by the test.
pids = [int(x) for x in re.findall(r'started subcommand .* pid=(\d+)', output)]
assert len(pids) == 4, pids
for pid in pids:
    deadline = time.monotonic() + 3
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        if time.monotonic() > deadline:
            raise SystemExit(f'Terminal child {pid} survived app shutdown')
        time.sleep(0.05)
run('codesign', '--verify', '--deep', '--strict', str(BUILD / 'Paper Terminal.app'))
print('PASS: ABI, model, real PTYs, bundled resources from /tmp, shell integration, shader, and child reaping')
