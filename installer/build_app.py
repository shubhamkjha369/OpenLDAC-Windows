"""Build script to create standalone OpenLDAC executables with embedded application icon."""

import os
import shutil
import sys
import subprocess
from pathlib import Path

def build():
    root = Path(__file__).resolve().parent.parent
    dist_dir = root / "dist"
    build_dir = root / "build_temp"
    run_file = root / "run.py"
    icon_file = root / "assets" / "icon.ico"

    icon_args = [f"--icon={icon_file}"] if icon_file.exists() else []

    # 1. Build Directory Distribution
    print("=== Building Directory Distribution (dist/OpenLDAC/) ===")
    cmd_dir = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "OpenLDAC",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--paths={root}",
        *icon_args,
        "--collect-all", "customtkinter",
        "--collect-all", "sounddevice",
        "--collect-all", "comtypes",
        str(run_file)
    ]
    res1 = subprocess.run(cmd_dir, cwd=str(root))

    # 2. Build Single-File Portable Executable
    print("\n=== Building Single-File Portable (dist/OpenLDAC_Portable.exe) ===")
    cmd_onefile = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "OpenLDAC_Portable",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--paths={root}",
        *icon_args,
        "--collect-all", "customtkinter",
        "--collect-all", "sounddevice",
        "--collect-all", "comtypes",
        str(run_file)
    ]
    res2 = subprocess.run(cmd_onefile, cwd=str(root))

    # Clean up temporary build directory so users don't encounter stub confusion
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)

    if res1.returncode == 0 and res2.returncode == 0:
        print(f"\n[SUCCESS] All executables built successfully with custom icon!")
        print(f"  - Directory format: {dist_dir / 'OpenLDAC' / 'OpenLDAC.exe'}")
        print(f"  - Portable single-file: {dist_dir / 'OpenLDAC_Portable.exe'}")
        return True
    return False

if __name__ == "__main__":
    build()
