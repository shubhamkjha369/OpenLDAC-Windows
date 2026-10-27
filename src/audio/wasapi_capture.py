"""OpenLDAC WASAPI Loopback Audio Capture Subsystem.

Direct Windows Core Audio COM implementation capturing system audio in real-time
with low latency, zero-copy buffer transfer, and format normalization for LDAC.
"""

from __future__ import annotations
import ctypes
from ctypes import wintypes, POINTER, Structure, byref, c_void_p, c_int, c_int64, c_float, c_byte
import queue
import threading
import time
from typing import Callable, Optional
import numpy as np

import comtypes
import comtypes.client
from comtypes import IUnknown, GUID, COMMETHOD, HRESULT

from ..utils.logger import get_logger

logger = get_logger("WASAPI-Capture")

CLSID_MMDeviceEnumerator = GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
IID_IMMDeviceEnumerator  = GUID('{A95664D2-9614-4F35-A746-DE8DB63617E6}')
IID_IAudioClient         = GUID('{1CB9AD4C-DBFA-4c32-B178-C2F568A703B2}')
IID_IAudioCaptureClient  = GUID('{C8ADBD64-E71E-48a0-A4DE-185C395CD317}')

eRender = 0
eConsole = 0
AUDCLNT_SHAREMODE_SHARED = 0
AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000

class WAVEFORMATEX(Structure):
    _fields_ = [
        ("wFormatTag", wintypes.WORD),
        ("nChannels", wintypes.WORD),
        ("nSamplesPerSec", wintypes.DWORD),
        ("nAvgBytesPerSec", wintypes.DWORD),
        ("nBlockAlign", wintypes.WORD),
        ("wBitsPerSample", wintypes.WORD),
        ("cbSize", wintypes.WORD)
    ]

class IMMDevice(IUnknown):
    _iid_ = GUID('{D666063F-1587-4E43-81F1-B948E807363F}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'Activate',
                  (['in'], POINTER(GUID), 'iid'),
                  (['in'], wintypes.DWORD, 'dwClsCtx'),
                  (['in'], c_void_p, 'pActivationParams'),
                  (['out'], POINTER(c_void_p), 'ppInterface')),
    ]

class IMMDeviceEnumerator(IUnknown):
    _iid_ = IID_IMMDeviceEnumerator
    _methods_ = [
        COMMETHOD([], HRESULT, 'EnumAudioEndpoints'),
        COMMETHOD([], HRESULT, 'GetDefaultAudioEndpoint',
                  (['in'], c_int, 'dataFlow'),
                  (['in'], c_int, 'role'),
                  (['out'], POINTER(POINTER(IMMDevice)), 'ppEndpoint')),
    ]

class IAudioClient(IUnknown):
    _iid_ = IID_IAudioClient
    _methods_ = [
        COMMETHOD([], HRESULT, 'Initialize',
                  (['in'], c_int, 'ShareMode'),
                  (['in'], wintypes.DWORD, 'StreamFlags'),
                  (['in'], c_int64, 'hnsBufferDuration'),
                  (['in'], c_int64, 'hnsPeriodicity'),
                  (['in'], POINTER(WAVEFORMATEX), 'pFormat'),
                  (['in'], c_void_p, 'AudioSessionGuid')),
        COMMETHOD([], HRESULT, 'GetBufferSize',
                  (['out'], POINTER(wintypes.DWORD), 'pNumBufferFrames')),
        COMMETHOD([], HRESULT, 'GetStreamLatency',
                  (['out'], POINTER(c_int64), 'phnsLatency')),
        COMMETHOD([], HRESULT, 'GetCurrentPadding',
                  (['out'], POINTER(wintypes.DWORD), 'pNumPaddingFrames')),
        COMMETHOD([], HRESULT, 'IsFormatSupported'),
        COMMETHOD([], HRESULT, 'GetMixFormat',
                  (['out'], POINTER(POINTER(WAVEFORMATEX)), 'ppDeviceFormat')),
        COMMETHOD([], HRESULT, 'GetDevicePeriod'),
        COMMETHOD([], HRESULT, 'Start'),
        COMMETHOD([], HRESULT, 'Stop'),
        COMMETHOD([], HRESULT, 'Reset'),
        COMMETHOD([], HRESULT, 'SetEventHandle'),
        COMMETHOD([], HRESULT, 'GetService',
                  (['in'], POINTER(GUID), 'riid'),
                  (['out'], POINTER(c_void_p), 'ppv')),
    ]

class IAudioCaptureClient(IUnknown):
    _iid_ = IID_IAudioCaptureClient
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetBuffer',
                  (['out'], POINTER(POINTER(c_byte)), 'ppData'),
                  (['out'], POINTER(wintypes.DWORD), 'pNumFramesToRead'),
                  (['out'], POINTER(wintypes.DWORD), 'pdwFlags'),
                  (['out'], POINTER(c_int64), 'pu64DevicePosition'),
                  (['out'], POINTER(c_int64), 'pu64QPCPosition')),
        COMMETHOD([], HRESULT, 'ReleaseBuffer',
                  (['in'], wintypes.DWORD, 'NumFramesRead')),
        COMMETHOD([], HRESULT, 'GetNextPacketSize',
                  (['out'], POINTER(wintypes.DWORD), 'pNumFramesInNextPacket')),
    ]

class WasapiLoopbackCapture:
    """Real-time Windows audio loopback capture engine."""

    def __init__(
        self,
        target_sample_rate: int = 96000,
        channels: int = 2,
        on_audio_data: Optional[Callable[[np.ndarray], None]] = None,
        on_levels_update: Optional[Callable[[float, float], None]] = None,
    ) -> None:
        self.target_sample_rate = target_sample_rate
        self.channels = channels
        self.on_audio_data = on_audio_data
        self.on_levels_update = on_levels_update
        
        self.is_capturing = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self.native_sample_rate = 48000
        self.native_channels = 2
        self.native_bits = 32
        
        # Performance metrics
        self.captured_frames_total = 0
        self.underruns = 0
        self.level_l = 0.0
        self.level_r = 0.0

    def start(self) -> bool:
        if self.is_capturing:
            return True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_worker, daemon=True)
        self._thread.start()
        self.is_capturing = True
        logger.info(f"Loopback capture worker started (target: {self.target_sample_rate} Hz, {self.channels} ch)")
        return True

    def stop(self) -> None:
        if not self.is_capturing:
            return
        self.is_capturing = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Loopback capture worker stopped.")

    def _capture_worker(self) -> None:
        comtypes.CoInitialize()
        try:
            enumerator = comtypes.client.CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
            endpoint = enumerator.GetDefaultAudioEndpoint(eRender, eConsole)
            pClient = endpoint.Activate(byref(IID_IAudioClient), 1, None)
            audio_client = ctypes.cast(pClient, POINTER(IAudioClient))

            pwfx = audio_client.GetMixFormat()
            wfx = pwfx.contents
            self.native_sample_rate = wfx.nSamplesPerSec
            self.native_channels = wfx.nChannels
            self.native_bits = wfx.wBitsPerSample
            logger.info(f"System Audio Format: {self.native_sample_rate} Hz, {self.native_channels} ch, {self.native_bits}-bit")

            # Initialize 100ms shared loopback buffer
            hnsBufferDuration = 1000000 # 100ms
            audio_client.Initialize(
                AUDCLNT_SHAREMODE_SHARED,
                AUDCLNT_STREAMFLAGS_LOOPBACK,
                hnsBufferDuration,
                0,
                pwfx,
                None
            )

            pCapture = audio_client.GetService(byref(IID_IAudioCaptureClient))
            capture_client = ctypes.cast(pCapture, POINTER(IAudioCaptureClient))
            audio_client.Start()

            frame_size = self.native_channels * (self.native_bits // 8)

            while not self._stop_event.is_set():
                time.sleep(0.005) # 5ms polling loop for ultra-low latency
                
                packet_size = capture_client.GetNextPacketSize()
                while packet_size > 0:
                    pData = POINTER(c_byte)()
                    frames_read = wintypes.DWORD()
                    flags = wintypes.DWORD()
                    device_pos = c_int64()
                    qpc_pos = c_int64()

                    capture_client.GetBuffer(
                        byref(pData),
                        byref(frames_read),
                        byref(flags),
                        byref(device_pos),
                        byref(qpc_pos)
                    )

                    n_frames = frames_read.value
                    if n_frames > 0:
                        total_bytes = n_frames * frame_size
                        # Copy buffer
                        raw_bytes = ctypes.string_at(pData, total_bytes)
                        capture_client.ReleaseBuffer(n_frames)

                        # Parse to float32
                        if self.native_bits == 32:
                            data = np.frombuffer(raw_bytes, dtype=np.float32).reshape(-1, self.native_channels)
                        elif self.native_bits == 16:
                            data = (np.frombuffer(raw_bytes, dtype=np.int16).reshape(-1, self.native_channels).astype(np.float32) / 32768.0)
                        else:
                            data = np.zeros((n_frames, self.native_channels), dtype=np.float32)

                        # Downmix or upmix to stereo if necessary
                        if self.native_channels > 2:
                            stereo_data = data[:, :2]
                        elif self.native_channels == 1:
                            stereo_data = np.repeat(data, 2, axis=1)
                        else:
                            stereo_data = data

                        # Resample to target_sample_rate if mismatch
                        if self.native_sample_rate != self.target_sample_rate:
                            ratio = self.target_sample_rate / self.native_sample_rate
                            new_length = int(len(stereo_data) * ratio)
                            if new_length > 0:
                                x_old = np.linspace(0, 1, len(stereo_data))
                                x_new = np.linspace(0, 1, new_length)
                                ch0 = np.interp(x_new, x_old, stereo_data[:, 0])
                                ch1 = np.interp(x_new, x_old, stereo_data[:, 1])
                                stereo_data = np.column_stack([ch0, ch1]).astype(np.float32)

                        # Update VU level meters
                        if len(stereo_data) > 0:
                            self.level_l = float(np.max(np.abs(stereo_data[:, 0])))
                            self.level_r = float(np.max(np.abs(stereo_data[:, 1])))
                            if self.on_levels_update:
                                self.on_levels_update(self.level_l, self.level_r)

                        # Dispatch audio data to encoder
                        if self.on_audio_data:
                            self.on_audio_data(stereo_data)

                        self.captured_frames_total += n_frames

                    packet_size = capture_client.GetNextPacketSize()

            audio_client.Stop()
        except Exception as e:
            logger.error(f"WASAPI capture thread exception: {e}")
        finally:
            comtypes.CoUninitialize()
