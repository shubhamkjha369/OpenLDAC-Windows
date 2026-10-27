"""Unit tests for Sony LDAC Codec Encoder."""

import pytest
import numpy as np
from src.codec.ldac_encoder import (
    LdacEncoder,
    EQMID_HQ,
    EQMID_MQ,
    EQMID_SQ,
    EQMID_ABR,
    LDAC_SYNC_WORD_0,
    LDAC_SYNC_WORD_1,
)

def test_ldac_encoder_initialization():
    encoder = LdacEncoder(sample_rate=96000, channels=2, eqmid=EQMID_HQ)
    assert encoder.sample_rate == 96000
    assert encoder.channels == 2
    assert encoder.active_eqmid == EQMID_HQ
    assert encoder.samples_per_frame == 256
    assert encoder.get_bitrate_kbps() == 990

def test_ldac_frame_sizes_for_all_bitrates():
    # 96 kHz
    enc_hq = LdacEncoder(sample_rate=96000, channels=2, eqmid=EQMID_HQ)
    enc_mq = LdacEncoder(sample_rate=96000, channels=2, eqmid=EQMID_MQ)
    enc_sq = LdacEncoder(sample_rate=96000, channels=2, eqmid=EQMID_SQ)

    assert enc_hq.get_frame_byte_size(96000, EQMID_HQ) == 330
    assert enc_mq.get_frame_byte_size(96000, EQMID_MQ) == 220
    assert enc_sq.get_frame_byte_size(96000, EQMID_SQ) == 110

    # 44.1 kHz
    assert enc_hq.get_frame_byte_size(44100, EQMID_HQ) == 303
    assert enc_mq.get_frame_byte_size(44100, EQMID_MQ) == 202
    assert enc_sq.get_frame_byte_size(44100, EQMID_SQ) == 101

def test_ldac_frame_encoding():
    encoder = LdacEncoder(sample_rate=96000, channels=2, eqmid=EQMID_HQ)
    
    # Generate 1 frame of stereo sine wave (256 samples, 2 channels)
    t = np.linspace(0, 256 / 96000, 256, endpoint=False)
    sine_l = (0.8 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
    sine_r = (0.5 * np.cos(2 * np.pi * 1000 * t)).astype(np.float32)
    pcm_block = np.column_stack([sine_l, sine_r])

    frame1 = encoder.encode_frame(pcm_block)
    assert isinstance(frame1, bytes)
    assert len(frame1) == 330
    assert frame1[0] == LDAC_SYNC_WORD_0 # First frame has lead sync word

    frame2 = encoder.encode_frame(pcm_block)
    assert len(frame2) == 330
    assert frame2[0] == LDAC_SYNC_WORD_1 # Subsequent frame has follow sync word

    assert encoder.total_frames_encoded == 2
    assert encoder.total_bytes_out == 660

def test_ldac_adaptive_bitrate():
    encoder = LdacEncoder(sample_rate=96000, channels=2, eqmid=EQMID_ABR)
    assert encoder.active_eqmid == EQMID_MQ # Starts at Balanced

    # Under buffer pressure (0.2), should step down to Stability (SQ)
    encoder.adapt_bitrate(buffer_health_ratio=0.20)
    assert encoder.active_eqmid == EQMID_SQ

    # When buffer recovers (0.9), should step up towards High Quality (HQ)
    encoder.adapt_bitrate(buffer_health_ratio=0.90)
    assert encoder.active_eqmid == EQMID_MQ
    encoder.adapt_bitrate(buffer_health_ratio=0.90)
    assert encoder.active_eqmid == EQMID_HQ
