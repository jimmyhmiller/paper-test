#!/usr/bin/env python3
"""Install the signed build as a standalone macOS application."""
import argparse
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--applications', type=Path, default=Path('/Applications'))
    args = parser.parse_args()
    source = ROOT / 'build/Paper Blog.app'
    if not source.is_dir():
        parser.error('Build the app first with python3 scripts/build.py')
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(source)], check=True)
    args.applications.mkdir(parents=True, exist_ok=True)
    destination = args.applications / source.name
    with tempfile.TemporaryDirectory(prefix='.paper-blog-install-', dir=args.applications) as staging:
        staged = Path(staging) / source.name
        backup = Path(staging) / 'previous.app'
        subprocess.run(['ditto', str(source), str(staged)], check=True)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(staged)], check=True)
        if destination.exists():
            destination.rename(backup)
        try:
            staged.rename(destination)
        except BaseException:
            if backup.exists():
                backup.rename(destination)
            raise
    print(destination)


if __name__ == '__main__':
    main()
