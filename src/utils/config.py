"""OpenLDAC Configuration Subsystem.

Saves and loads user preferences from JSON config file in APPDATA.
"""

from __future__ import annotations
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

@dataclass
class AppConfig:
    device_name: str = ""
    device_mac: str = ""
    eqmid: int = 0  # 0: 990 kbps (Quality), 1: 660 kbps (Balanced), 2: 330 kbps (Stability), 3: ABR
    sample_rate: int = 96000  # 44100, 48000, 88200, 96000
    bit_depth: int = 24       # 16, 24, 32
    buffer_frames: int = 1024
    hfp_guard_enabled: bool = True
    auto_reconnect: bool = True
    dark_theme: bool = True

def get_config_dir() -> Path:
    app_data = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
    path = Path(app_data) / "OpenLDAC"
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_config_path() -> Path:
    return get_config_dir() / "config.json"

def load_config() -> AppConfig:
    cfg_file = get_config_path()
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return AppConfig(**{k: v for k, v in data.items() if k in AppConfig.__annotations__})
        except Exception:
            pass
    return AppConfig()

def save_config(config: AppConfig) -> bool:
    cfg_file = get_config_path()
    try:
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(asdict(config), f, indent=2)
        return True
    except Exception:
        return False
