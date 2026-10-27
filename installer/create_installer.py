"""Generates a self-contained Windows Installer for OpenLDAC."""

import os
import shutil
import zipfile
from pathlib import Path

def create_installer():
    root = Path(__file__).resolve().parent.parent
    dist_dir = root / "dist" / "OpenLDAC"
    output_dir = root / "dist" / "installer"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not dist_dir.exists():
        print(f"[ERROR] Dist directory not found: {dist_dir}")
        return False

    # 1. Create a zip distribution package
    zip_path = output_dir / "OpenLDAC-v1.0.0-win-x64.zip"
    print(f"Creating portable zip release at: {zip_path}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in dist_dir.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(dist_dir.parent)
                zipf.write(file, arcname)

    # 2. Create Setup.ps1 / Setup.bat installer scripts
    setup_script = output_dir / "Install_OpenLDAC.ps1"
    setup_script.write_text(r"""# OpenLDAC Windows Setup Script
$ErrorActionPreference = "Stop"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    OpenLDAC Windows Installer v1.0.0   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$InstallDir = "$env:LOCALAPPDATA\Programs\OpenLDAC"
Write-Host "Installing to: $InstallDir" -ForegroundColor Yellow

if (Test-Path $InstallDir) {
    Remove-Item -Recurse -Force $InstallDir
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

$SourceDir = Join-Path $PSScriptRoot "..\OpenLDAC"
if (-not (Test-Path $SourceDir)) {
    $SourceDir = "$PSScriptRoot\OpenLDAC"
}

Copy-Item -Path "$SourceDir\*" -Destination $InstallDir -Recurse -Force

# Create Desktop Shortcut
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\OpenLDAC.lnk")
$Shortcut.TargetPath = "$InstallDir\OpenLDAC.exe"
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Description = "OpenLDAC High-Resolution Bluetooth Audio"
$Shortcut.Save()

# Create Uninstaller Script
$UninstallScript = "$InstallDir\Uninstall.bat"
@"
@echo off
echo Uninstalling OpenLDAC...
rmdir /s /q "%LOCALAPPDATA%\Programs\OpenLDAC"
del "%USERPROFILE%\Desktop\OpenLDAC.lnk"
echo OpenLDAC uninstalled successfully.
pause
"@ | Out-File -FilePath $UninstallScript -Encoding ASCII

Write-Host "`n[SUCCESS] OpenLDAC installed successfully!" -ForegroundColor Green
Write-Host "A shortcut has been created on your Desktop." -ForegroundColor Green
Write-Host "You can launch OpenLDAC from: $InstallDir\OpenLDAC.exe" -ForegroundColor Green
Start-Sleep -Seconds 2
""", encoding="utf-8")

    # 3. Create Windows Batch Launcher for one-click setup
    batch_setup = output_dir / "Install_OpenLDAC.bat"
    batch_setup.write_text(r"""@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install_OpenLDAC.ps1"
pause
""", encoding="utf-8")

    print(f"[SUCCESS] Installer created at: {output_dir}")
    print(f"Files generated:")
    print(f"  - {zip_path}")
    print(f"  - {setup_script}")
    print(f"  - {batch_setup}")
    return True

if __name__ == "__main__":
    create_installer()
