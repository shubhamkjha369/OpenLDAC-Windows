"""Build script to create standalone OpenLDAC.exe executable."""

import os
import sys
import subprocess
from pathlib import Path

def build():
    root = Path(__file__).resolve().parent.parent
    dist_dir = root / "dist"
    build_dir = root / "build"
    run_file = root / "run.py"

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "OpenLDAC",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--paths={root}",
        "--collect-all", "customtkinter",
        "--collect-all", "sounddevice",
        "--collect-all", "comtypes",
        str(run_file)
    ]

    print("Running PyInstaller:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(root))
    if res.returncode == 0:
        exe_path = dist_dir / "OpenLDAC" / "OpenLDAC.exe"
        print(f"\n[SUCCESS] Standalone executable created at: {exe_path}")
        return exe_path
    else:
        print(f"\n[ERROR] Build failed with code: {res.returncode}")
        return None

if __name__ == "__main__":
    build()
