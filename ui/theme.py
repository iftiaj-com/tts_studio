"""
ui/theme.py
───────────
Shared UI helpers and the _card() factory used across all panels.
Import COLORS and FONTS from here in all UI code.
"""

import customtkinter as ctk
from core.constants import COLORS, FONTS


def card(parent, row: int, title: str) -> ctk.CTkFrame:
    """Create a styled card frame with a section title and return it."""
    frame = ctk.CTkFrame(
        parent,
        fg_color=COLORS["bg_card"],
        corner_radius=14,
        border_width=1,
        border_color=COLORS["border"],
    )
    frame.grid(row=row, column=0, sticky="ew", padx=24, pady=6)
    ctk.CTkLabel(
        frame, text=title,
        font=FONTS["subtitle"],
        text_color=COLORS["text_primary"],
    ).pack(anchor="w", padx=16, pady=(14, 10))
    return frame


def styled_option_menu(parent, variable, values, width=280, **kw):
    """Return a pre-styled CTkOptionMenu."""
    return ctk.CTkOptionMenu(
        parent,
        variable=variable,
        values=values,
        font=FONTS["body"],
        fg_color=COLORS["bg_card"],
        button_color=COLORS["accent_primary"],
        button_hover_color=COLORS["accent_secondary"],
        dropdown_fg_color=COLORS["bg_card"],
        dropdown_hover_color=COLORS["accent_primary"],
        corner_radius=8,
        width=width,
        **kw,
    )


def styled_slider(parent, variable, from_, to, width=200, command=None):
    """Return a pre-styled CTkSlider."""
    return ctk.CTkSlider(
        parent,
        from_=from_,
        to=to,
        variable=variable,
        width=width,
        button_color=COLORS["accent_primary"],
        button_hover_color=COLORS["accent_secondary"],
        progress_color=COLORS["accent_primary"],
        fg_color=COLORS["slider_track"],
        command=command,
    )


def styled_switch(parent, text, variable, **kw):
    """Return a pre-styled CTkSwitch."""
    return ctk.CTkSwitch(
        parent,
        text=text,
        variable=variable,
        onvalue=True,
        offvalue=False,
        button_color=COLORS["accent_primary"],
        button_hover_color=COLORS["accent_secondary"],
        progress_color=COLORS["switch_on"],
        fg_color=COLORS["switch_off"],
        **kw,
    )
