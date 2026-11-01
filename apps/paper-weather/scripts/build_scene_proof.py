#!/usr/bin/env python3
"""Build the separate data-driven scene proof; do not replace Paper Weather."""
from pathlib import Path
import subprocess
APP = Path(__file__).resolve().parents[1]
ROOT = APP.parents[1]

def main():
    for tool, output in [('scene_player', 'paper-scene'), ('scene_validate', 'paper-scene-validate')]:
        subprocess.run(['coil', 'build', f'tools/{tool}.coil', '-o', str(ROOT/'build'/output)], cwd=APP, check=True)
    print(f'Player: {ROOT / "build/paper-scene"}')

if __name__ == '__main__':
    main()
