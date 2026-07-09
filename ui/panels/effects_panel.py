"""
ui/panels/effects_panel.py  –  Voice effects card
"""
import customtkinter as ctk
from core.constants import COLORS, FONTS
from ui.theme import card
from effects.registry import EFFECTS_REGISTRY


class EffectsPanel:
    def __init__(self, parent, row=None):
        if row is not None:
            frame = card(parent, row, "✨  Voice Effects")
            grid = ctk.CTkFrame(frame, fg_color="transparent")
            grid.pack(fill="x", padx=16, pady=(0, 14))
            num_cols = 4
        else:
            frame = ctk.CTkFrame(
                parent, fg_color=COLORS["bg_card"],
                corner_radius=14, border_width=1, border_color=COLORS["border"]
            )
            frame.pack(fill="x", padx=16, pady=6)
            
            ctk.CTkLabel(
                frame, text="✨  Voice Effects",
                font=FONTS["subtitle"],
                text_color=COLORS["text_primary"],
            ).pack(anchor="w", padx=16, pady=(14, 10))
            
            grid = ctk.CTkFrame(frame, fg_color="transparent")
            grid.pack(fill="x", padx=16, pady=(0, 14))
            num_cols = 2

        grid.columnconfigure(tuple(range(num_cols)), weight=1)
        self._vars: dict = {}
        for i, effect in enumerate(EFFECTS_REGISTRY):
            key, label, desc = effect["key"], effect["label"], effect["desc"]
            default = effect.get("default", False)
            var = ctk.BooleanVar(value=default)
            self._vars[key] = var
            r, c = divmod(i, num_cols)
            tile = ctk.CTkFrame(grid, fg_color=COLORS["bg_input"],
                                corner_radius=10, border_width=1,
                                border_color=COLORS["border"])
            tile.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            inner = ctk.CTkFrame(tile, fg_color="transparent")
            inner.pack(fill="x", padx=10, pady=6)
            ctk.CTkSwitch(inner, text=label, font=FONTS["body"],
                          text_color=COLORS["text_primary"], variable=var,
                          onvalue=True, offvalue=False,
                          button_color=COLORS["accent_primary"],
                          button_hover_color=COLORS["accent_secondary"],
                          progress_color=COLORS["switch_on"],
                          fg_color=COLORS["switch_off"],
                          switch_width=36, switch_height=18).pack(anchor="w")
            ctk.CTkLabel(inner, text=desc, font=("Segoe UI", 10),
                         text_color=COLORS["text_muted"]).pack(anchor="w", padx=(42, 0))

    def get_active_effects(self) -> dict:
        return {key: var.get() for key, var in self._vars.items()}
