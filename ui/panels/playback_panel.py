"""
ui/panels/playback_panel.py  –  Playback & Export card
"""
import customtkinter as ctk
from core.constants import COLORS, FONTS
from ui.theme import card


class PlaybackPanel:
    def __init__(self, parent, on_generate, on_cancel, on_play, on_stop, on_save, on_save_srt, on_open_folder, row=None):
        if row is not None:
            frame = card(parent, row, "🎧  Playback & Export")
            btn_height = 44
            play_width = 110
            stop_width = 110
            save_width = 130
            srt_width = 130
            folder_width = 130
            use_grid_layout = False
        else:
            frame = ctk.CTkFrame(
                parent, fg_color=COLORS["bg_card"],
                corner_radius=14, border_width=1, border_color=COLORS["border"]
            )
            frame.pack(fill="x", padx=16, pady=6)
            
            ctk.CTkLabel(
                frame, text="🎧  Playback & Export",
                font=FONTS["subtitle"],
                text_color=COLORS["text_primary"],
            ).pack(anchor="w", padx=16, pady=(14, 10))
            
            btn_height = 38
            play_width = 75
            stop_width = 75
            save_width = 100
            srt_width = 100
            folder_width = 85
            use_grid_layout = True

        self.progress = ctk.CTkProgressBar(frame, height=6,
                                           fg_color=COLORS["slider_track"],
                                           progress_color=COLORS["accent_primary"],
                                           corner_radius=3)
        self.progress.pack(fill="x", padx=16, pady=(0, 12))
        self.progress.set(0)

        if not use_grid_layout:
            btn_row = ctk.CTkFrame(frame, fg_color="transparent")
            btn_row.pack(fill="x", padx=16, pady=(0, 14))

            self.generate_btn = ctk.CTkButton(
                btn_row, text="⚡  Generate Speech", font=FONTS["button"],
                fg_color=COLORS["accent_primary"], hover_color=COLORS["accent_secondary"],
                corner_radius=10, height=btn_height, command=on_generate)
            self.generate_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

            self.cancel_btn = ctk.CTkButton(
                btn_row, text="✖  Cancel", font=FONTS["button"],
                fg_color="#CC0000", hover_color=COLORS["error"],
                corner_radius=10, height=btn_height, width=100, command=on_cancel, state="disabled")
            self.cancel_btn.pack(side="left", padx=6)

            self.play_btn = ctk.CTkButton(
                btn_row, text="▶  Play", font=FONTS["button"],
                fg_color=COLORS["bg_input"], hover_color=COLORS["accent_primary"],
                border_color=COLORS["accent_primary"], border_width=2,
                corner_radius=10, height=btn_height, width=play_width, command=on_play, state="disabled")
            self.play_btn.pack(side="left", padx=6)

            self.stop_btn = ctk.CTkButton(
                btn_row, text="⏹  Stop", font=FONTS["button"],
                fg_color=COLORS["bg_input"], hover_color=COLORS["error"],
                border_color=COLORS["error"], border_width=2,
                corner_radius=10, height=btn_height, width=stop_width, command=on_stop, state="disabled")
            self.stop_btn.pack(side="left", padx=6)

            self.save_btn = ctk.CTkButton(
                btn_row, text="💾  Save MP3", font=FONTS["button"],
                fg_color=COLORS["success"], hover_color="#00B87A",
                text_color=COLORS["bg_dark"],
                corner_radius=10, height=btn_height, width=save_width, command=on_save, state="disabled")
            self.save_btn.pack(side="left", padx=6)

            self.save_srt_btn = ctk.CTkButton(
                btn_row, text="📄  Save SRT", font=FONTS["button"],
                fg_color="#3498DB", hover_color="#2980B9",
                text_color="#FFFFFF",
                corner_radius=10, height=btn_height, width=srt_width, command=on_save_srt, state="disabled")
            self.save_srt_btn.pack(side="left", padx=6)

            self.open_folder_btn = ctk.CTkButton(
                btn_row, text="📂  Open Folder", font=FONTS["button"],
                fg_color=COLORS["bg_card"], hover_color=COLORS["accent_secondary"],
                border_color=COLORS["border"], border_width=1,
                text_color=COLORS["text_primary"],
                corner_radius=10, height=btn_height, width=folder_width,
                command=on_open_folder, state="disabled")
            self.open_folder_btn.pack(side="left", padx=(6, 0))
        else:
            row1 = ctk.CTkFrame(frame, fg_color="transparent")
            row1.pack(fill="x", padx=16, pady=(0, 6))

            self.generate_btn = ctk.CTkButton(
                row1, text="⚡  Generate Speech", font=FONTS["button"],
                fg_color=COLORS["accent_primary"], hover_color=COLORS["accent_secondary"],
                corner_radius=10, height=btn_height, command=on_generate)
            self.generate_btn.pack(side="left", expand=True, fill="x")

            row2 = ctk.CTkFrame(frame, fg_color="transparent")
            row2.pack(fill="x", padx=16, pady=(0, 14))
            # "uniform" keeps the 3:3:4:4:3:3 column ratio fixed so a button
            # text change (e.g. "Play" -> "Playing…") can't resize siblings.
            row2.columnconfigure((0, 1, 4, 5), weight=3, uniform="btn")
            row2.columnconfigure((2, 3), weight=4, uniform="btn")

            self.play_btn = ctk.CTkButton(
                row2, text="▶  Play", font=FONTS["button"],
                fg_color=COLORS["bg_input"], hover_color=COLORS["accent_primary"],
                border_color=COLORS["accent_primary"], border_width=2,
                corner_radius=10, height=btn_height, width=0, command=on_play, state="disabled")
            self.play_btn.grid(row=0, column=0, padx=2, sticky="ew")

            self.stop_btn = ctk.CTkButton(
                row2, text="⏹  Stop", font=FONTS["button"],
                fg_color=COLORS["bg_input"], hover_color=COLORS["error"],
                border_color=COLORS["error"], border_width=2,
                corner_radius=10, height=btn_height, width=0, command=on_stop, state="disabled")
            self.stop_btn.grid(row=0, column=1, padx=2, sticky="ew")

            self.save_btn = ctk.CTkButton(
                row2, text="💾  Save MP3", font=FONTS["button"],
                fg_color=COLORS["success"], hover_color="#00B87A",
                text_color=COLORS["bg_dark"],
                corner_radius=10, height=btn_height, width=0, command=on_save, state="disabled")
            self.save_btn.grid(row=0, column=2, padx=2, sticky="ew")

            self.save_srt_btn = ctk.CTkButton(
                row2, text="📄  Save SRT", font=FONTS["button"],
                fg_color="#3498DB", hover_color="#2980B9",
                text_color="#FFFFFF",
                corner_radius=10, height=btn_height, width=0, command=on_save_srt, state="disabled")
            self.save_srt_btn.grid(row=0, column=3, padx=2, sticky="ew")

            self.open_folder_btn = ctk.CTkButton(
                row2, text="📂  Folder", font=FONTS["button"],
                fg_color=COLORS["bg_card"], hover_color=COLORS["accent_secondary"],
                border_color=COLORS["border"], border_width=1,
                text_color=COLORS["text_primary"],
                corner_radius=10, height=btn_height, width=0,
                command=on_open_folder, state="disabled")
            self.open_folder_btn.grid(row=0, column=4, padx=2, sticky="ew")

            self.cancel_btn = ctk.CTkButton(
                row2, text="✖  Cancel", font=FONTS["button"],
                fg_color="#CC0000", hover_color=COLORS["error"],
                corner_radius=10, height=btn_height, width=0, command=on_cancel, state="disabled")
            self.cancel_btn.grid(row=0, column=5, padx=2, sticky="ew")

    def set_generating(self, is_generating: bool):
        """Toggle Cancel button state during generation."""
        if is_generating:
            self.cancel_btn.configure(state="normal", text="✖  Cancel")
        else:
            self.cancel_btn.configure(state="disabled", text="✖  Cancel")
