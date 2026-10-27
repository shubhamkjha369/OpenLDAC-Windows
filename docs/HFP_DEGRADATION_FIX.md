# Windows Bluetooth Microphone Audio Degradation: Root Cause & Fix

## The Problem
When connecting Bluetooth headphones (such as Sony WH-1000XM4/XM5, WF-1000XM4/XM5, boat Nirvana Ion ANC, Airdopes, or Bose) to Windows, starting any game (Call of Duty, Valorant, CS2, Fortnite) or launching Discord causes the game audio to immediately sound muffled, hollow, tinny, and compressed like an old telephone call.

The audio quality only recovers after manually going into Sound Settings and disabling the headset microphone.

## Technical Root Cause
Bluetooth Classic operates over a shared 2.4 GHz radio with bandwidth limits.
A Bluetooth headset exposes two profiles to Windows:
1. **A2DP (Advanced Audio Distribution Profile):** High-bitrate unidirectional stereo streaming (up to 990 kbps in LDAC, 256 kbps AAC, 328 kbps SBC). Ideal for gaming, music, and movies.
2. **HFP / HSP (Hands-Free Profile):** Bidirectional low-bitrate voice communication. Due to radio limitations, HFP output is restricted to **8 kHz CVSD (AM telephone quality)** or **16 kHz mSBC (low quality voice)** in mono.

When Windows detects that an application (a game with in-game voice chat enabled, Discord, Zoom, or Windows voice recorder) has opened an audio recording stream on the headset's microphone endpoint:
- Windows immediately suspends A2DP stereo playback.
- Windows forces all system and game audio output through the headset's **Hands-Free AG Audio** endpoint at 8,000 Hz or 16,000 Hz mono.
- The commercial Alternative A2DP Driver simply logs `Suspended by HFP` and allows the degradation to occur.

## How OpenLDAC Fixes It: HFP Telephony Guard
OpenLDAC introduces an integrated **HFP Telephony Guard**:
1. It automatically enumerates and identifies all Hands-Free recording endpoints tied to the active Bluetooth audio device.
2. When **Game / Hi-Fi Audio Lock** is active, OpenLDAC inhibits the Bluetooth headset's hands-free microphone endpoint.
3. Because no application can request an audio capture handle from the Bluetooth radio, Windows never receives the signal to switch from A2DP to HFP.
4. Games and voice apps seamlessly fall back to using your laptop's internal microphone, external USB microphone, or webcam mic.
5. Game audio remains locked in bit-perfect, pristine **High-Resolution Stereo LDAC (up to 990 kbps)** throughout the gaming session!
6. When the user toggles the lock off or closes OpenLDAC, normal telephony endpoints are automatically restored.
