"""Unit tests for HFP Telephony Guard."""

import pytest
from src.bluetooth.hfp_guard import HfpTelephonyGuard

def test_hfp_guard_state_transitions():
    guard = HfpTelephonyGuard()
    assert not guard.is_active

    # Enable guard
    res = guard.enable_guard()
    assert res is True
    assert guard.is_active

    # Disable guard
    res2 = guard.disable_guard()
    assert res2 is True
    assert not guard.is_active

def test_hfp_endpoint_detection():
    guard = HfpTelephonyGuard()
    endpoints = guard.scan_hfp_endpoints()
    assert isinstance(endpoints, list)
    # Check that any discovered endpoint has expected structure
    for ep in endpoints:
        assert "name" in ep
        assert "sample_rate" in ep
