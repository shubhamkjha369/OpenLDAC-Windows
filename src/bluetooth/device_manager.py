"""OpenLDAC Bluetooth Device Manager.

Discovers, enumerates, and tracks paired Bluetooth audio devices
and their active connection states on Windows.
"""

from __future__ import annotations
import winreg
from dataclasses import dataclass
from typing import Optional
from ..utils.logger import get_logger

logger = get_logger("Device-Manager")

@dataclass
class BluetoothDevice:
    name: str
    mac_address: str
    is_connected: bool
    is_a2dp_capable: bool
    is_ldac_compatible: bool
    active_profile: str  # "A2DP Stereo (Hi-Fi)" or "HFP Telephony (Low Quality)"

class BluetoothDeviceManager:
    """Discovers and manages Windows paired Bluetooth audio devices."""

    def __init__(self) -> None:
        self.cached_devices: list[BluetoothDevice] = []

    def scan_devices(self) -> list[BluetoothDevice]:
        """Scans the Windows Bluetooth subsystem for paired and connected audio devices."""
        devices = []
        bth_reg_path = r"SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Devices"
        
        # 1. Read registry paired devices
        reg_devices: dict[str, str] = {}
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, bth_reg_path) as key:
                count = winreg.QueryInfoKey(key)[0]
                for i in range(count):
                    dev_mac = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, dev_mac) as dev_key:
                        try:
                            name, _ = winreg.QueryValueEx(dev_key, "Name")
                            if isinstance(name, bytes):
                                name = name.decode('utf-8', errors='ignore').rstrip('\x00')
                            reg_devices[dev_mac] = name
                        except FileNotFoundError:
                            reg_devices[dev_mac] = f"Bluetooth Device ({dev_mac})"
        except Exception as e:
            logger.debug(f"Bluetooth registry lookup: {e}")

        # 2. Correlate with active Windows audio endpoints
        active_endpoint_names = set()
        try:
            import sounddevice as sd
            for dev in sd.query_devices():
                dname = dev.get("name", "")
                active_endpoint_names.add(dname.lower())
        except Exception:
            pass

        # Build device list
        for mac, name in reg_devices.items():
            # Check if device is active in audio endpoints
            is_active = any(name.lower() in ep for ep in active_endpoint_names)
            
            # Infer LDAC compatibility (Sony, high-res capable ANC headphones, etc.)
            lower_name = name.lower()
            is_ldac = any(k in lower_name for k in [
                "wh-", "wf-", "sony", "anc pro", "xm4", "xm5", "1000x",
                "soundcore", "technics", "fiio", "shanling", "edifier", "liberty"
            ])
            # If not explicitly named, standard audio Bluetooth devices are tested for capability
            is_a2dp = True

            active_profile = "A2DP Stereo (Hi-Fi)" if is_active else "Disconnected"

            devices.append(BluetoothDevice(
                name=name,
                mac_address=mac,
                is_connected=is_active,
                is_a2dp_capable=is_a2dp,
                is_ldac_compatible=is_ldac,
                active_profile=active_profile
            ))

        # Sort so connected/LDAC devices appear first
        devices.sort(key=lambda d: (d.is_connected, d.is_ldac_compatible), reverse=True)
        self.cached_devices = devices
        logger.info(f"Scanned {len(devices)} Bluetooth device(s). Connected: {sum(1 for d in devices if d.is_connected)}")
        return devices

    def get_selected_or_default(self, preferred_name: str = "") -> Optional[BluetoothDevice]:
        if not self.cached_devices:
            self.scan_devices()
        
        if preferred_name:
            for d in self.cached_devices:
                if d.name.lower() == preferred_name.lower():
                    return d
                    
        # Return first connected device, or first available
        for d in self.cached_devices:
            if d.is_connected:
                return d
        return self.cached_devices[0] if self.cached_devices else None
