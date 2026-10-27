"""OpenLDAC Application Controller.

Orchestrates WASAPI loopback capture, Sony LDAC encoding,
Bluetooth AVDTP packetization, and the HFP Telephony Guard.
"""

from __future__ import annotations
import threading
import time
from typing import Callable, Optional
import numpy as np

from .audio.wasapi_capture import WasapiLoopbackCapture
from .bluetooth.avdtp_streamer import AvdtpStreamer
from .bluetooth.device_manager import BluetoothDevice, BluetoothDeviceManager
from .bluetooth.hfp_guard import HfpTelephonyGuard
from .codec.ldac_encoder import (
    EQMID_ABR,
    EQMID_HQ,
    EQMID_MQ,
    EQMID_SQ,
    LdacEncoder,
)
from .utils.config import AppConfig, load_config, save_config
from .utils.logger import get_logger

logger = get_logger("OpenLDAC-Core")

class OpenLDACController:
    """Core audio streaming and device management controller."""

    def __init__(self) -> None:
        self.config: AppConfig = load_config()
        self.device_manager = BluetoothDeviceManager()
        self.hfp_guard = HfpTelephonyGuard(on_state_changed=self._on_hfp_state_changed)
        
        self.encoder: Optional[LdacEncoder] = None
        self.capture: Optional[WasapiLoopbackCapture] = None
        self.streamer: Optional[AvdtpStreamer] = None
        
        self.is_streaming = False
        self.active_device: Optional[BluetoothDevice] = None
        
        # Audio accumulator for frame chunking
        self._audio_queue: list[np.ndarray] = []
        self._lock = threading.Lock()
        
        # Callbacks for UI updates
        self.on_telemetry_updated: Optional[Callable[[dict], None]] = None
        self.on_levels_updated: Optional[Callable[[float, float], None]] = None
        self.on_status_changed: Optional[Callable[[str], None]] = None

    def initialize(self) -> None:
        logger.info("Initializing OpenLDAC Core...")
        devices = self.device_manager.scan_devices()
        self.active_device = self.device_manager.get_selected_or_default(self.config.device_name)
        if self.active_device:
            logger.info(f"Selected target device: {self.active_device.name}")
            
        if self.config.hfp_guard_enabled and self.active_device:
            self.hfp_guard.enable_guard(self.active_device.name)

    def start_streaming(self, device: Optional[BluetoothDevice] = None) -> bool:
        if self.is_streaming:
            return True
            
        if device:
            self.active_device = device
            self.config.device_name = device.name
            self.config.device_mac = device.mac_address
            save_config(self.config)

        if not self.active_device:
            logger.error("No Bluetooth audio device selected for LDAC streaming.")
            return False

        logger.info(f"Starting LDAC streaming on: {self.active_device.name} @ {self.config.sample_rate} Hz")
        
        # 1. Initialize LDAC Encoder
        self.encoder = LdacEncoder(
            sample_rate=self.config.sample_rate,
            channels=2,
            eqmid=self.config.eqmid,
        )

        # 2. Initialize AVDTP Streamer
        self.streamer = AvdtpStreamer(sample_rate=self.config.sample_rate)

        # 3. Enforce HFP Guard if configured
        if self.config.hfp_guard_enabled:
            self.hfp_guard.enable_guard(self.active_device.name)

        # 4. Start WASAPI Loopback Audio Capture
        self.capture = WasapiLoopbackCapture(
            target_sample_rate=self.config.sample_rate,
            channels=2,
            on_audio_data=self._on_pcm_data_received,
            on_levels_update=self._on_levels_update,
        )
        self.capture.start()

        self.is_streaming = True
        if self.on_status_changed:
            self.on_status_changed(f"Streaming LDAC ({self.encoder.get_bitrate_kbps()} kbps)")
        return True

    def stop_streaming(self) -> None:
        if not self.is_streaming:
            return
            
        logger.info("Stopping LDAC stream...")
        self.is_streaming = False
        
        if self.capture:
            self.capture.stop()
            self.capture = None
            
        if self.on_status_changed:
            self.on_status_changed("Stream Stopped")

    def set_quality_mode(self, eqmid: int) -> None:
        self.config.eqmid = eqmid
        save_config(self.config)
        if self.encoder:
            self.encoder.set_eqmid(eqmid)
            bitrate = self.encoder.get_bitrate_kbps()
            logger.info(f"Switched LDAC Quality Mode: EQMID={eqmid} ({bitrate} kbps)")

    def toggle_hfp_guard(self, enabled: bool) -> None:
        self.config.hfp_guard_enabled = enabled
        save_config(self.config)
        if enabled:
            dev_name = self.active_device.name if self.active_device else ""
            self.hfp_guard.enable_guard(dev_name)
        else:
            self.hfp_guard.disable_guard()

    def _on_pcm_data_received(self, pcm_chunk: np.ndarray) -> None:
        if not self.is_streaming or not self.encoder or not self.streamer:
            return

        with self._lock:
            self._audio_queue.append(pcm_chunk)
            
            # Check if we have accumulated enough samples for a full LDAC frame
            samples_needed = self.encoder.samples_per_frame
            total_samples = sum(len(c) for c in self._audio_queue)
            
            while total_samples >= samples_needed:
                accum = np.vstack(self._audio_queue)
                frame_data = accum[:samples_needed]
                rem = accum[samples_needed:]
                
                self._audio_queue.clear()
                if len(rem) > 0:
                    self._audio_queue.append(rem)
                total_samples = len(rem)

                # Encode to Sony LDAC frame
                encoded_frame = self.encoder.encode_frame(frame_data)
                
                # Packetize into RTP/AVDTP Media Packet
                self.streamer.packetize_frames([encoded_frame], samples_per_frame=samples_needed)

    def _on_levels_update(self, lvl_l: float, lvl_r: float) -> None:
        if self.on_levels_updated:
            self.on_levels_updated(lvl_l, lvl_r)

    def _on_hfp_state_changed(self, active: bool, msg: str) -> None:
        logger.info(f"HFP Guard State: active={active} ({msg})")

    def get_telemetry(self) -> dict:
        """Returns real-time telemetry snapshot for the GUI."""
        bitrate = self.encoder.get_bitrate_kbps() if self.encoder else 0
        eqmid = self.encoder.active_eqmid if self.encoder else self.config.eqmid
        pkts = self.streamer.stats.packets_sent if self.streamer else 0
        frames = self.encoder.stats["frames_encoded"] if self.encoder else 0
        
        return {
            "is_streaming": self.is_streaming,
            "device_name": self.active_device.name if self.active_device else "None",
            "bitrate_kbps": bitrate,
            "eqmid": eqmid,
            "sample_rate": self.config.sample_rate,
            "packets_sent": pkts,
            "frames_encoded": frames,
            "hfp_guard_active": self.hfp_guard.is_active,
            "level_l": self.capture.level_l if self.capture else 0.0,
            "level_r": self.capture.level_r if self.capture else 0.0,
        }

    def shutdown(self) -> None:
        logger.info("Shutting down OpenLDAC...")
        self.stop_streaming()
        self.hfp_guard.disable_guard()
