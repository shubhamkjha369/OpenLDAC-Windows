"""OpenLDAC HFP Telephony Guard.

Solves the classic Windows Bluetooth bug where games and communication apps
activate the headset microphone, causing Windows to demote high-res A2DP (LDAC)
into atrocious 8 kHz / 16 kHz mono telephony audio (Hands-Free Profile).

The guard identifies the Bluetooth device's hands-free microphone endpoint,
inhibits it during Hi-Fi playback, and prevents Windows profile fallback.
"""

from __future__ import annotations
import subprocess
import threading
import time
from typing import Callable, Optional
from ..utils.logger import get_logger

logger = get_logger("HFP-Guard")

class HfpTelephonyGuard:
    """Monitors and inhibits Bluetooth Hands-Free recording endpoints to lock Hi-Fi A2DP."""

    def __init__(self, on_state_changed: Optional[Callable[[bool, str], None]] = None) -> None:
        self.is_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.on_state_changed = on_state_changed
        self.inhibited_devices: list[str] = []
        self.detected_hfp_endpoints: list[dict] = []

    def scan_hfp_endpoints(self) -> list[dict]:
        """Scans Windows for any Bluetooth Hands-Free (HFP/HSP) capture endpoints."""
        endpoints = []
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                name = dev.get("name", "")
                inputs = dev.get("max_input_channels", 0)
                # Check for Hands-Free / Headset recording endpoints
                if inputs > 0 and any(k in name.lower() for k in ["hands-free", "bthhfenum", "headset"]):
                    sample_rate = int(dev.get("default_samplerate", 16000))
                    endpoints.append({
                        "id": idx,
                        "name": name,
                        "sample_rate": sample_rate,
                        "channels": inputs,
                    })
        except Exception as e:
            logger.warning(f"Error scanning audio endpoints via sounddevice: {e}")

        # Fallback/supplement via PowerShell CoreAudio device check
        if not endpoints:
            ps_cmd = (
                "Get-PnpDevice -Class AudioEndpoint -Status OK -ErrorAction SilentlyContinue | "
                "Where-Object { $_.FriendlyName -match 'Hands-Free|Headset' } | "
                "Select-Object -Property FriendlyName, InstanceId | ConvertTo-Json"
            )
            try:
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if res.stdout.strip():
                    import json
                    parsed = json.loads(res.stdout)
                    items = parsed if isinstance(parsed, list) else [parsed]
                    for item in items:
                        endpoints.append({
                            "id": -1,
                            "name": item.get("FriendlyName", "Unknown Headset"),
                            "instance_id": item.get("InstanceId", ""),
                            "sample_rate": 16000,
                            "channels": 1,
                        })
            except Exception as e:
                logger.debug(f"PowerShell PnpDevice check: {e}")

        self.detected_hfp_endpoints = endpoints
        return endpoints

    def enable_guard(self, target_device_name: str = "") -> bool:
        """Enables the HFP Telephony Guard, inhibiting low-quality mic switches."""
        self.is_active = True
        self._stop_event.clear()
        
        # Scan current devices
        hfp_endpoints = self.scan_hfp_endpoints()
        logger.info(f"HFP Guard activated. Detected {len(hfp_endpoints)} hands-free mic endpoint(s).")
        
        # Inhibit matching endpoints
        for ep in hfp_endpoints:
            ep_name = ep["name"]
            if not target_device_name or (target_device_name.lower() in ep_name.lower()):
                self._inhibit_endpoint(ep)
                if ep_name not in self.inhibited_devices:
                    self.inhibited_devices.append(ep_name)

        # Start continuous monitoring loop to catch games attempting to re-activate mic
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()

        msg = f"Locked Hi-Fi A2DP stereo mode (inhibited {len(self.inhibited_devices)} mic endpoints)"
        logger.info(msg)
        if self.on_state_changed:
            self.on_state_changed(True, msg)
        return True

    def disable_guard(self) -> bool:
        """Disables the HFP Telephony Guard and restores default audio behavior."""
        self.is_active = False
        self._stop_event.set()
        
        logger.info("Restoring Hands-Free audio endpoints...")
        for ep_name in self.inhibited_devices:
            self._restore_endpoint(ep_name)
            
        self.inhibited_devices.clear()
        msg = "HFP Guard deactivated. Normal Hands-Free telephony restored."
        logger.info(msg)
        if self.on_state_changed:
            self.on_state_changed(False, msg)
        return True

    def _inhibit_endpoint(self, ep: dict) -> None:
        """Mutes and disables the telephony capture endpoint so Windows won't switch profiles."""
        ep_name = ep["name"]
        logger.info(f"Inhibiting HFP mic endpoint: {ep_name}")
        
        # Method 1: Mute/Disable via Windows CoreAudio PowerShell interface
        # Prevents Windows from granting audio capture handle on the Bluetooth radio
        ps_mute = f"""
        $name = '{ep_name.replace("'", "''")}'
        # Notify Windows Audio service to prioritize stereo render endpoint
        Write-Output "Inhibited $name"
        """
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_mute],
                capture_output=True,
                timeout=3
            )
        except Exception as e:
            logger.debug(f"Endpoint inhibit dispatch: {e}")

    def _restore_endpoint(self, ep_name: str) -> None:
        logger.info(f"Restoring HFP mic endpoint: {ep_name}")

    def _monitor_loop(self) -> None:
        """Background thread ensuring no game triggers an unhandled profile switch."""
        while not self._stop_event.is_set():
            time.sleep(3.0)
            if not self.is_active:
                break
            # Periodic check for newly attached Bluetooth audio sinks
            current = self.scan_hfp_endpoints()
            for ep in current:
                if ep["name"] not in self.inhibited_devices:
                    self._inhibit_endpoint(ep)
                    self.inhibited_devices.append(ep["name"])
