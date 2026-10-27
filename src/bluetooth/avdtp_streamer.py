"""OpenLDAC Bluetooth AVDTP / A2DP Streamer.

Implements RTP packetization for Sony LDAC according to the
Bluetooth SIG A2DP Specification and Sony LDAC RTP Payload Format.
"""

from __future__ import annotations
import struct
import time
from dataclasses import dataclass
from typing import Optional
from ..utils.logger import get_logger

logger = get_logger("AVDTP-Streamer")

# Sony LDAC Vendor Specific Codec Constants
SONY_VENDOR_ID = 0x0000012D
SONY_LDAC_CODEC_ID = 0x00AA
RTP_PAYLOAD_TYPE_LDAC = 96  # Dynamic payload type

@dataclass
class StreamStats:
    packets_sent: int = 0
    bytes_sent: int = 0
    bitrate_kbps: float = 0.0
    packet_rate: float = 0.0
    jitter_ms: float = 0.0
    underruns: int = 0
    connected_device: str = ""

class AvdtpStreamer:
    """A2DP AVDTP transport and RTP packetizer for LDAC bitstreams."""

    def __init__(self, sample_rate: int = 96000, mtu: int = 679) -> None:
        self.sample_rate = sample_rate
        self.mtu = mtu
        self.sequence_number = 0
        self.timestamp = 0
        self.ssrc = 0x534F4E59  # 'SONY'
        
        self.stats = StreamStats()
        self._last_stats_time = time.time()
        self._bytes_in_window = 0
        self._packets_in_window = 0

    @staticmethod
    def get_ldac_codec_capabilities() -> bytes:
        """Returns the 8-byte Sony LDAC Service Capabilities element for A2DP negotiation."""
        # Octet 0-3: Vendor ID (0x0000012D Little Endian)
        # Octet 4-5: Codec ID (0x00AA Little Endian)
        # Octet 6: Sample rates supported (96k:0x04 | 88.2k:0x08 | 48k:0x10 | 44.1k:0x20 = 0x3C)
        # Octet 7: Channel modes (Stereo:0x01 | Dual:0x02 | Mono:0x04 = 0x07)
        return struct.pack(
            "<IHBB",
            SONY_VENDOR_ID,
            SONY_LDAC_CODEC_ID,
            0x3C, # All 4 sample rates supported
            0x07  # Stereo + Dual + Mono
        )

    def packetize_frames(self, ldac_frames: list[bytes], samples_per_frame: int = 256) -> bytes:
        """Packs one or more LDAC frames into an RTP/AVDTP media packet.
        
        RTP Header (12 bytes):
          Byte 0: V=2, P=0, X=0, CC=0 (0x80)
          Byte 1: M=1, PT=96 (0xE0 or 0x60)
          Bytes 2-3: Sequence Number (16-bit big endian)
          Bytes 4-7: Timestamp (32-bit big endian)
          Bytes 8-11: SSRC (32-bit big endian)
        LDAC Payload Header (1 byte):
          Byte 12: Frame Count (number of encoded LDAC frames)
        Payload Data:
          Concatenated LDAC frames
        """
        if not ldac_frames:
            return b""

        frame_count = len(ldac_frames)
        payload_data = b"".join(ldac_frames)

        # RTP Header
        header = struct.pack(
            ">BBHII",
            0x80, # Version 2
            RTP_PAYLOAD_TYPE_LDAC & 0x7F,
            self.sequence_number & 0xFFFF,
            self.timestamp & 0xFFFFFFFF,
            self.ssrc
        )

        # LDAC Payload Header (1 byte frame count)
        ldac_hdr = struct.pack("B", frame_count)

        packet = header + ldac_hdr + payload_data

        # Increment RTP sequence and timestamp
        self.sequence_number = (self.sequence_number + 1) & 0xFFFF
        self.timestamp = (self.timestamp + (samples_per_frame * frame_count)) & 0xFFFFFFFF

        # Update telemetry
        pkt_len = len(packet)
        self.stats.packets_sent += 1
        self.stats.bytes_sent += pkt_len
        self._bytes_in_window += pkt_len
        self._packets_in_window += 1

        now = time.time()
        dt = now - self._last_stats_time
        if dt >= 1.0:
            self.stats.bitrate_kbps = (self._bytes_in_window * 8.0) / (dt * 1000.0)
            self.stats.packet_rate = self._packets_in_window / dt
            self._bytes_in_window = 0
            self._packets_in_window = 0
            self._last_stats_time = now

        return packet
