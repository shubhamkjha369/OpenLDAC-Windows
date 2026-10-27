"""OpenLDAC Modern Native Windows User Interface.

Built with CustomTkinter for sleek dark-mode aesthetics, real-time VU meters,
dynamic bitrate monitoring, and one-click HFP Telephony Guard.
"""

from __future__ import annotations
import threading
import time
from typing import Optional
import customtkinter as ctk

from ..app import OpenLDACController
from ..codec.ldac_encoder import EQMID_ABR, EQMID_HQ, EQMID_MQ, EQMID_SQ
from ..utils.logger import register_log_observer, unregister_log_observer

# Theme styling configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MainWindow(ctk.CTk):
    """Main application window for OpenLDAC."""

    def __init__(self, controller: OpenLDACController) -> None:
        super().__init__()
        self.controller = controller
        
        self.title("OpenLDAC for Windows — High-Resolution Bluetooth Audio")
        self.geometry("900x720")
        self.minsize(820, 640)

        # Set window icon if available
        from pathlib import Path
        icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # UI state
        self._is_updating = True

        self._build_ui()
        self._populate_devices()
        
        # Subscribe to log events
        register_log_observer(self._on_log_message)

        # Start periodic telemetry update loop (30 FPS)
        self.after(33, self._poll_telemetry)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Header Banner
        self.header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("#1f2937", "#111827"))
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.header_frame,
            text="🎧 OpenLDAC",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#60a5fa"
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        self.title_desc = ctk.CTkLabel(
            self.header_frame,
            text="Standalone Open-Source Sony LDAC Audio Solution for Windows (990 kbps / 96kHz)",
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af"
        )
        self.title_desc.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 12), sticky="w")

        self.status_badge = ctk.CTkLabel(
            self.header_frame,
            text="● STANDBY",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#374151",
            text_color="#9ca3af",
            corner_radius=8,
            padx=14,
            pady=6
        )
        self.status_badge.grid(row=0, column=1, padx=20, pady=15, sticky="e")

        # 2. Main Controls Card
        self.controls_frame = ctk.CTkFrame(self, corner_radius=12)
        self.controls_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.controls_frame.grid_columnconfigure(1, weight=1)

        # Device Selection Row
        self.dev_label = ctk.CTkLabel(self.controls_frame, text="Target Bluetooth Device:", font=ctk.CTkFont(weight="bold"))
        self.dev_label.grid(row=0, column=0, padx=15, pady=12, sticky="w")

        self.device_combo = ctk.CTkComboBox(
            self.controls_frame,
            values=["Scanning..."],
            width=320,
            command=self._on_device_selected
        )
        self.device_combo.grid(row=0, column=1, padx=10, pady=12, sticky="ew")

        self.btn_refresh = ctk.CTkButton(
            self.controls_frame,
            text="🔄 Refresh",
            width=100,
            command=self._populate_devices
        )
        self.btn_refresh.grid(row=0, column=2, padx=10, pady=12)

        self.btn_stream = ctk.CTkButton(
            self.controls_frame,
            text="▶ Start LDAC Streaming",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            width=180,
            command=self._toggle_stream
        )
        self.btn_stream.grid(row=0, column=3, padx=15, pady=12)

        # Quality Preset Row (EQMID)
        self.quality_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.quality_frame.grid(row=1, column=0, columnspan=4, padx=15, pady=10, sticky="ew")
        self.quality_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.eqmid_var = ctk.IntVar(value=self.controller.config.eqmid)

        self.rb_hq = ctk.CTkRadioButton(
            self.quality_frame,
            text="🚀 Quality Priority\n990 kbps (Studio Master)",
            variable=self.eqmid_var,
            value=EQMID_HQ,
            command=self._on_quality_changed
        )
        self.rb_hq.grid(row=0, column=0, padx=10, pady=8, sticky="w")

        self.rb_mq = ctk.CTkRadioButton(
            self.quality_frame,
            text="⚖️ Balanced Mode\n660 kbps (Recommended)",
            variable=self.eqmid_var,
            value=EQMID_MQ,
            command=self._on_quality_changed
        )
        self.rb_mq.grid(row=0, column=1, padx=10, pady=8, sticky="w")

        self.rb_sq = ctk.CTkRadioButton(
            self.quality_frame,
            text="🛡️ Stability Priority\n330 kbps (Maximum Range)",
            variable=self.eqmid_var,
            value=EQMID_SQ,
            command=self._on_quality_changed
        )
        self.rb_sq.grid(row=0, column=2, padx=10, pady=8, sticky="w")

        self.rb_abr = ctk.CTkRadioButton(
            self.quality_frame,
            text="🔄 Adaptive Bitrate\nDynamic RF Auto-Tune",
            variable=self.eqmid_var,
            value=EQMID_ABR,
            command=self._on_quality_changed
        )
        self.rb_abr.grid(row=0, column=3, padx=10, pady=8, sticky="w")

        # HFP Telephony Guard Card (Game Audio Fix)
        self.guard_frame = ctk.CTkFrame(self.controls_frame, fg_color=("#1e293b", "#0f172a"), corner_radius=10)
        self.guard_frame.grid(row=2, column=0, columnspan=4, padx=15, pady=(5, 15), sticky="ew")
        self.guard_frame.grid_columnconfigure(1, weight=1)

        self.guard_icon = ctk.CTkLabel(self.guard_frame, text="🛡️", font=ctk.CTkFont(size=24))
        self.guard_icon.grid(row=0, column=0, rowspan=2, padx=(15, 5), pady=10)

        self.guard_title = ctk.CTkLabel(
            self.guard_frame,
            text="Game / Hi-Fi Audio Lock (HFP Telephony Guard)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8"
        )
        self.guard_title.grid(row=0, column=1, padx=10, pady=(10, 2), sticky="w")

        self.guard_desc = ctk.CTkLabel(
            self.guard_frame,
            text="Prevents Windows and games from degrading audio to 8/16kHz telephone sound when voice chat is opened.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.guard_desc.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="w")

        self.guard_switch_var = ctk.BooleanVar(value=self.controller.config.hfp_guard_enabled)
        self.guard_switch = ctk.CTkSwitch(
            self.guard_frame,
            text="Lock Active",
            variable=self.guard_switch_var,
            command=self._on_guard_toggled,
            onvalue=True,
            offvalue=False
        )
        self.guard_switch.grid(row=0, column=2, rowspan=2, padx=20, pady=10)

        # 3. Telemetry & Visualizer Dashboard
        self.dashboard_frame = ctk.CTkFrame(self, corner_radius=12)
        self.dashboard_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.dashboard_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Stat cards
        self.card_bitrate = self._create_stat_card(self.dashboard_frame, 0, "BITRATE", "0 kbps", "#3b82f6")
        self.card_sr = self._create_stat_card(self.dashboard_frame, 1, "SAMPLE RATE", "96,000 Hz", "#10b981")
        self.card_frames = self._create_stat_card(self.dashboard_frame, 2, "ENCODED FRAMES", "0", "#8b5cf6")
        self.card_hfp = self._create_stat_card(self.dashboard_frame, 3, "AUDIO PROFILE", "A2DP Hi-Fi", "#06b6d4")

        # VU Level Meters
        self.vu_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        self.vu_frame.grid(row=1, column=0, columnspan=4, padx=20, pady=15, sticky="ew")
        self.vu_frame.grid_columnconfigure(1, weight=1)

        self.lbl_vu_l = ctk.CTkLabel(self.vu_frame, text="L:", width=20, font=ctk.CTkFont(weight="bold"))
        self.lbl_vu_l.grid(row=0, column=0, padx=5, pady=2)
        self.bar_vu_l = ctk.CTkProgressBar(self.vu_frame, height=12)
        self.bar_vu_l.set(0.0)
        self.bar_vu_l.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        self.lbl_vu_r = ctk.CTkLabel(self.vu_frame, text="R:", width=20, font=ctk.CTkFont(weight="bold"))
        self.lbl_vu_r.grid(row=1, column=0, padx=5, pady=2)
        self.bar_vu_r = ctk.CTkProgressBar(self.vu_frame, height=12)
        self.bar_vu_r.set(0.0)
        self.bar_vu_r.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        # Diagnostic Log Window
        self.log_textbox = ctk.CTkTextbox(
            self.dashboard_frame,
            height=120,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word"
        )
        self.log_textbox.grid(row=2, column=0, columnspan=4, padx=20, pady=(5, 15), sticky="nsew")
        self.dashboard_frame.grid_rowconfigure(2, weight=1)

        # 4. Footer
        self.footer_label = ctk.CTkLabel(
            self,
            text="OpenLDAC v1.0.0 — Open Source (Apache-2.0) — No Paywalls, No Expiration, Pure User-Mode WASAPI Architecture",
            font=ctk.CTkFont(size=11),
            text_color="#6b7280"
        )
        self.footer_label.grid(row=3, column=0, padx=20, pady=(0, 10))

    def _create_stat_card(self, parent: ctk.CTkFrame, col: int, title: str, value: str, color: str) -> dict:
        frame = ctk.CTkFrame(parent, fg_color=("#1e293b", "#0f172a"), corner_radius=10)
        frame.grid(row=0, column=col, padx=8, pady=12, sticky="nsew")
        
        lbl_title = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="#94a3b8")
        lbl_title.pack(padx=10, pady=(8, 2))
        
        lbl_val = ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=16, weight="bold"), text_color=color)
        lbl_val.pack(padx=10, pady=(0, 8))
        
        return {"frame": frame, "title": lbl_title, "value": lbl_val}

    def _populate_devices(self) -> None:
        devices = self.controller.device_manager.scan_devices()
        dev_names = [d.name for d in devices] if devices else ["No Bluetooth Audio Devices Found"]
        self.device_combo.configure(values=dev_names)
        
        current_dev = self.controller.active_device
        if current_dev and current_dev.name in dev_names:
            self.device_combo.set(current_dev.name)
        elif dev_names:
            self.device_combo.set(dev_names[0])
            if devices:
                self.controller.active_device = devices[0]

    def _on_device_selected(self, dev_name: str) -> None:
        for d in self.controller.device_manager.cached_devices:
            if d.name == dev_name:
                self.controller.active_device = d
                break

    def _toggle_stream(self) -> None:
        if not self.controller.is_streaming:
            dev_name = self.device_combo.get()
            dev = self.controller.device_manager.get_selected_or_default(dev_name)
            if self.controller.start_streaming(dev):
                self.btn_stream.configure(text="⏹ Stop LDAC Streaming", fg_color="#dc2626", hover_color="#b91c1c")
                self.status_badge.configure(text="● LDAC STREAMING", fg_color="#065f46", text_color="#34d399")
        else:
            self.controller.stop_streaming()
            self.btn_stream.configure(text="▶ Start LDAC Streaming", fg_color="#2563eb", hover_color="#1d4ed8")
            self.status_badge.configure(text="● STANDBY", fg_color="#374151", text_color="#9ca3af")

    def _on_quality_changed(self) -> None:
        eqmid = self.eqmid_var.get()
        self.controller.set_quality_mode(eqmid)

    def _on_guard_toggled(self) -> None:
        enabled = self.guard_switch_var.get()
        self.controller.toggle_hfp_guard(enabled)

    def _on_log_message(self, msg: str) -> None:
        def append():
            try:
                self.log_textbox.insert("end", msg + "\n")
                self.log_textbox.see("end")
            except Exception:
                pass
        self.after(0, append)

    def _poll_telemetry(self) -> None:
        """Periodic GUI refresh for statistics and VU meters."""
        if self._is_updating:
            telem = self.controller.get_telemetry()
            
            # Update cards
            bitrate = telem["bitrate_kbps"]
            self.card_bitrate["value"].configure(text=f"{bitrate} kbps" if bitrate > 0 else "0 kbps")
            self.card_sr["value"].configure(text=f"{telem['sample_rate']:,} Hz")
            self.card_frames["value"].configure(text=f"{telem['frames_encoded']:,}")
            
            hfp_status = "Hi-Fi Protected" if telem["hfp_guard_active"] else "Standard"
            self.card_hfp["value"].configure(text=hfp_status)

            # Update VU bars with decay
            lvl_l = telem["level_l"]
            lvl_r = telem["level_r"]
            self.bar_vu_l.set(min(1.0, max(0.0, lvl_l * 1.5)))
            self.bar_vu_r.set(min(1.0, max(0.0, lvl_r * 1.5)))

            self.after(33, self._poll_telemetry)

    def destroy(self) -> None:
        self._is_updating = False
        unregister_log_observer(self._on_log_message)
        self.controller.shutdown()
        super().destroy()
