"""Integration tests for end-to-end OpenLDAC pipeline."""

import pytest
import numpy as np
from src.app import OpenLDACController
from src.codec.ldac_encoder import EQMID_HQ

def test_controller_initialization_and_telemetry():
    controller = OpenLDACController()
    controller.initialize()
    
    telem = controller.get_telemetry()
    assert isinstance(telem, dict)
    assert "is_streaming" in telem
    assert "bitrate_kbps" in telem
    assert "hfp_guard_active" in telem
    assert telem["is_streaming"] is False

def test_full_audio_pipeline_simulation():
    controller = OpenLDACController()
    controller.initialize()
    
    # Manually initialize encoder and streamer
    from src.codec.ldac_encoder import LdacEncoder
    from src.bluetooth.avdtp_streamer import AvdtpStreamer
    
    controller.encoder = LdacEncoder(sample_rate=96000, channels=2, eqmid=EQMID_HQ)
    controller.streamer = AvdtpStreamer(sample_rate=96000)
    controller.is_streaming = True

    # Feed 1024 samples of test audio (4 LDAC frames of 256 samples each)
    test_audio = np.random.uniform(-0.5, 0.5, (1024, 2)).astype(np.float32)
    controller._on_pcm_data_received(test_audio)

    assert controller.encoder.total_frames_encoded == 4
    assert controller.streamer.stats.packets_sent == 4
    assert controller.encoder.total_bytes_out == 4 * 330 # 1320 bytes

    telem = controller.get_telemetry()
    assert telem["frames_encoded"] == 4
    assert telem["packets_sent"] == 4
    assert telem["bitrate_kbps"] == 990
