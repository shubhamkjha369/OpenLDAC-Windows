# OpenLDAC for Windows

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20x64-0078D6.svg)]()
[![Codecs](https://img.shields.io/badge/Codec-Sony%20LDAC%20(990%20kbps)-orange.svg)]()
[![Tests](https://img.shields.io/badge/Tests-10%2F10%20Passed-brightgreen.svg)]()

> **Standalone Open-Source Sony LDAC Audio Solution for Windows**  
> Pure user-mode architecture, bit-perfect WASAPI loopback, no kernel driver crashes, no commercial paywalls, and built-in **HFP Telephony Guard** to fix Bluetooth game audio degradation.

---

## 🌟 Key Features

* **High-Resolution Sony LDAC Encoding:**
  * **Quality Priority:** 990 kbps (at 96 kHz / 48 kHz) or 909 kbps (at 88.2 kHz / 44.1 kHz).
  * **Balanced Mode:** 660 kbps (at 96 kHz / 48 kHz) or 606 kbps (at 88.2 kHz / 44.1 kHz).
  * **Stability Priority:** 330 kbps (at 96 kHz / 48 kHz) or 303 kbps (at 88.2 kHz / 44.1 kHz).
  * **Adaptive Bitrate (ABR):** Dynamic bitrate scaling responding to RF buffer health.
* **🛡️ HFP Telephony Guard (Game Audio Fix):**
  * Eliminates the infamous Windows bug where launching a game or voice chat demotes Bluetooth headphones to 8 kHz / 16 kHz telephone-quality audio.
  * Locks connection into high-resolution stereo A2DP and keeps game sound pristine.
* **Pure User-Mode Architecture:**
  * Zero risk of Blue Screens of Death (BSODs).
  * Does not install unverified kernel `.sys` drivers.
  * Compatible with Windows Secure Boot and requires no Test Signing mode.
* **Modern Windows Native UI:**
  * Dark-mode interface powered by CustomTkinter.
  * Real-time stereo L/R VU level meters.
  * Live Bitrate, Sample Rate, and Packet Transmission counters.
  * Diagnostic console with live event logs.
* **100% Free & Open Source:**
  * Licensed under Apache 2.0.
  * No 14-day trial expirations, no license keys, no paywalls.

---

## 📁 Repository Structure

```
OpenLDAC/
├── src/
│   ├── app.py                 # Core streaming controller
│   ├── audio/
│   │   └── wasapi_capture.py  # Zero-latency WASAPI loopback capture
│   ├── codec/
│   │   └── ldac_encoder.py    # Sony LDAC protocol & frame encoder
│   ├── bluetooth/
│   │   ├── avdtp_streamer.py  # A2DP AVDTP/RTP packetizer
│   │   ├── device_manager.py  # Bluetooth device discovery & profiles
│   │   └── hfp_guard.py       # Game audio HFP inhibitor engine
│   ├── gui/
│   │   └── main_window.py     # CustomTkinter dark-mode application UI
│   └── utils/
│       ├── config.py          # User settings persistence
│       └── logger.py          # Thread-safe logging subsystem
├── tests/                     # 100% automated test suite (pytest)
│   ├── test_ldac_codec.py
│   ├── test_avdtp_packet.py
│   ├── test_hfp_guard.py
│   └── test_integration.py
├── installer/
│   ├── build_app.py           # PyInstaller standalone executable builder
│   └── create_installer.py    # Portable zip & installer script generator
├── dist/
│   ├── OpenLDAC/OpenLDAC.exe  # Standalone Windows executable
│   └── installer/             # Distribution installer packages
├── docs/
│   ├── ARCHITECTURE.md        # Architecture Decision Record (ADR)
│   └── HFP_DEGRADATION_FIX.md # Deep dive into the Bluetooth mic fix
└── run.py                     # Source launcher
```

---

## 🚀 Quick Start

### Option 1: Standalone Binary (No Python Required)
Run the compiled standalone executable directly:
```powershell
.\dist\OpenLDAC\OpenLDAC.exe
```

Or run the installer to set up desktop shortcuts:
```powershell
powershell -ExecutionPolicy Bypass -File .\dist\installer\Install_OpenLDAC.ps1
```

### Option 2: Run from Source
```powershell
pip install -r requirements.txt
python run.py
```

---

## 🧪 Running Automated Tests

Run the automated test suite with pytest:
```powershell
python -m pytest OpenLDAC/tests -v
```

All 10 tests verify codec frame sizes, sync words, CRC calculations, RTP packet headers, AVDTP capabilities, and the HFP Telephony Guard state machine.

---

## 📄 License
This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
Sony and LDAC are trademarks of Sony Corporation.
