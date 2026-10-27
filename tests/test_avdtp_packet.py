"""Unit tests for A2DP / AVDTP RTP Packetizer."""

import struct
import pytest
from src.bluetooth.avdtp_streamer import (
    AvdtpStreamer,
    SONY_VENDOR_ID,
    SONY_LDAC_CODEC_ID,
    RTP_PAYLOAD_TYPE_LDAC,
)

def test_ldac_codec_capabilities_format():
    caps = AvdtpStreamer.get_ldac_codec_capabilities()
    assert len(caps) == 8
    
    vendor_id, codec_id, srates, chmodes = struct.unpack("<IHBB", caps)
    assert vendor_id == SONY_VENDOR_ID      # 0x0000012D (Sony Corp)
    assert codec_id == SONY_LDAC_CODEC_ID   # 0x00AA (LDAC)
    assert (srates & 0x04) != 0             # 96 kHz flag set
    assert (chmodes & 0x01) != 0            # Stereo flag set

def test_rtp_packetization():
    streamer = AvdtpStreamer(sample_rate=96000)
    fake_frame = b"\x44" + b"\x00" * 329  # 330 bytes LDAC frame

    packet = streamer.packetize_frames([fake_frame], samples_per_frame=256)
    
    # 12 bytes RTP header + 1 byte LDAC frame count header + 330 bytes payload = 343 bytes
    assert len(packet) == 343
    
    # Verify RTP Header
    v_p_x_cc, m_pt, seq, ts, ssrc = struct.unpack(">BBHII", packet[:12])
    assert (v_p_x_cc >> 6) == 2            # Version 2
    assert (m_pt & 0x7F) == RTP_PAYLOAD_TYPE_LDAC
    assert seq == 0
    assert ts == 0
    assert ssrc == 0x534F4E59              # 'SONY'
    
    # Verify LDAC payload header
    frame_count = packet[12]
    assert frame_count == 1
    assert packet[13:13+330] == fake_frame

    # Test sequence number increment on next packet
    packet2 = streamer.packetize_frames([fake_frame], samples_per_frame=256)
    _, _, seq2, ts2, _ = struct.unpack(">BBHII", packet2[:12])
    assert seq2 == 1
    assert ts2 == 256  # Timestamp advanced by samples_per_frame
