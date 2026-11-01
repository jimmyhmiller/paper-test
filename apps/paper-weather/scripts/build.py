#!/usr/bin/env python3
"""Build the native Paper Weather executable and a local macOS app bundle."""
from pathlib import Path
import plistlib
import shutil
import subprocess

APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_ROOT.parents[1]
BINARY = PROJECT_ROOT / "build/paper-weather"
BUNDLE = PROJECT_ROOT / "build/Paper Weather.app"


def main():
    subprocess.run(["coil", "build", "-o", str(BINARY)], cwd=APP_ROOT, check=True)
    contents = BUNDLE / "Contents"
    macos = contents / "MacOS"
    macos.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BINARY, macos / "paper-weather")
    licenses = contents / "Resources/Licenses"
    licenses.mkdir(parents=True, exist_ok=True)
    shutil.copy2(APP_ROOT / "third-party/SunCalc-LICENSE.txt", licenses / "SunCalc.txt")
    with (contents / "Info.plist").open("wb") as stream:
        plistlib.dump({
            "CFBundleIdentifier": "dev.coil.paper-weather",
            "CFBundleName": "Paper Weather",
            "CFBundleDisplayName": "Paper Weather",
            "CFBundleExecutable": "paper-weather",
            "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "1",
            "LSMinimumSystemVersion": "14.0",
            "NSHighResolutionCapable": True,
            "NSPrincipalClass": "NSApplication",
        }, stream)
    subprocess.run(["codesign", "--force", "--sign", "-", str(BUNDLE)], check=True)
    print(BUNDLE)


if __name__ == "__main__":
    main()
