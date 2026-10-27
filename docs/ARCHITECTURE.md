# OpenLDAC Architecture Decision Record (ADR)

## 1. Context & Motivation
Windows 10 and 11 natively support Bluetooth A2DP with SBC and AAC, but lack native support for Sony LDAC (up to 990 kbps @ 96 kHz / 24-bit).
Third-party solutions like Alternative A2DP Driver (`AltA2DP.sys`) rely on custom KMDF PortCls kernel-mode drivers signed with commercial Extended Validation (EV) certificates, wrapped with closed-source paywalls, and suffer from kernel crash vulnerabilities during sleep/wake cycles.
Furthermore, standard Windows Bluetooth audio suffers from a critical flaw: when any application (e.g., games or Discord) accesses the Bluetooth device microphone, Windows demotes the connection from A2DP stereo to low-quality 8 kHz / 16 kHz mono telephony audio (Hands-Free Profile).

## 2. Selected Architecture: Option B (User-Mode WASAPI + LDAC Transport)
OpenLDAC implements a pure **User-Mode Architecture**:

```
[ Windows Applications (Games, Media Players, Browsers) ]
                       │
                       ▼
          [ Windows Audio Engine (WASAPI) ]
                       │ (Bit-Perfect Shared Loopback)
                       ▼
        [ OpenLDAC WASAPI Loopback Capture ] (48/96 kHz, 32-bit float)
                       │
                       ▼
            [ Sony LDAC Frame Encoder ]
         (Subband Quantization, Scale Factors, CRC)
         (Quality Presets: 990 / 660 / 330 kbps & ABR)
                       │
                       ▼
           [ AVDTP / RTP Media Packetizer ]
            (Payload Type 96, Timestamps, SSRC)
                       │
                       ▼
   [ Bluetooth A2DP Source / Transport Controller ]
                       │
                       ▼
      [ Bluetooth Headphones (Sony, ANC, etc.) ]
```

## 3. Key Design Choices
1. **Zero Kernel Exposure:** No kernel-mode drivers (`.sys`) are installed. System integrity, Secure Boot, and crash resilience are 100% preserved.
2. **HFP Telephony Guard:** Solves the microphone quality degradation bug by actively inhibiting Bluetooth hands-free recording endpoints during Hi-Fi playback, preventing Windows from dropping the audio link into telephone mode.
3. **Open Source & Permissive:** Licensed under Apache 2.0 with no expiration timers, trial paywalls, or closed binaries.
4. **Standalone Packaging:** Fully distributable as a standalone Windows executable (`OpenLDAC.exe`) and portable installer.
