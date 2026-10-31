#!/usr/bin/env python3
"""Exercise the shipped executable's fixture and offline-cache paths."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / 'build/release/paper-blog'


def run(*args, env=None, success=True):
    result = subprocess.run([str(EXE), '--fetch-once', *args], cwd=ROOT,
                            env=env, text=True, capture_output=True, timeout=55)
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    return result.stdout


def main():
    assert '15 views / 2 posts / 4 UTC buckets' in run('--fixture', 'tests/fixtures/sparse.json')
    assert '0 views / 0 posts / 4 UTC buckets' in run('--fixture', 'tests/fixtures/empty.json')
    assert '15 views / 2 posts / 4 UTC buckets' in run('--fixture', 'tests/fixtures/hourly.json')
    assert '0 views / 0 posts / 4 UTC buckets' in run('--fixture', 'tests/fixtures/hourly-empty.json')
    assert 'Could not load' in run('--fixture', 'tests/fixtures/does-not-exist.json', success=False)
    with tempfile.TemporaryDirectory(prefix='paper-blog-check-') as temporary:
        cache = Path(temporary) / 'cache'
        cache.mkdir()
        env = dict(os.environ, PAPER_BLOG_CACHE_DIR=str(cache),
                   PAPER_BLOG_AUTH_CONFIG=str(Path(temporary) / 'missing-credentials'))
        assert 'Credentials missing' in run(env=env, success=False)
        snapshot = (ROOT / 'tests/fixtures/sparse.json').read_bytes()
        (cache / 'timeline.json').write_bytes(snapshot)
        result = run(env=env, success=False)
        assert '15 views / 2 posts' in result
        assert 'Credentials missing' in result
        assert (cache / 'timeline.json').read_bytes() == snapshot
        (cache / 'timeline.json').write_text('{broken')
        assert '0 views / 0 posts' in run(env=env, success=False)
    print('PASS: fixtures, valid empty data, missing fixture, missing credentials, '
          'last-good cache preservation, corrupt cache recovery')


if __name__ == '__main__':
    main()
