"""
core/constants.py
─────────────────
App-wide design tokens, colour palette, fonts, and all voice/language maps.
Add new voices or language options here without touching any other file.
"""

# ═══════════════════════════════════════════════════════════════════
#  COLOUR PALETTE & DESIGN TOKENS
# ═══════════════════════════════════════════════════════════════════

COLORS = {
    "bg_dark":               "#0D0D0D",
    "bg_card":               "#1A1A2E",
    "bg_card_hover":         "#1F1F35",
    "bg_input":              "#16213E",
    "accent_primary":        "#6C63FF",
    "accent_secondary":      "#E94560",
    "accent_gradient_start": "#6C63FF",
    "accent_gradient_end":   "#E94560",
    "text_primary":          "#EAEAEA",
    "text_secondary":        "#A0A0B0",
    "text_muted":            "#656580",
    "success":               "#00D68F",
    "warning":               "#FFB800",
    "error":                 "#FF3D71",
    "border":                "#2A2A45",
    "slider_track":          "#2A2A45",
    "slider_fill":           "#6C63FF",
    "switch_on":             "#6C63FF",
    "switch_off":            "#2A2A45",
}

FONTS = {
    "title":      ("Segoe UI", 22, "bold"),
    "subtitle":   ("Segoe UI", 14, "bold"),
    "body":       ("Segoe UI", 13),
    "body_small": ("Segoe UI", 11),
    "mono":       ("Cascadia Code", 12),
    "button":     ("Segoe UI Semibold", 13),
    "status":     ("Segoe UI", 11),
}

# ═══════════════════════════════════════════════════════════════════
#  VOICE / LANGUAGE MAPS
#  Add new entries here to extend any engine's voice list.
# ═══════════════════════════════════════════════════════════════════

GTTS_LANGUAGES = {
    "English (US)":          {"lang": "en",    "tld": "us"},
    "English (UK)":          {"lang": "en",    "tld": "co.uk"},
    "English (Australia)":   {"lang": "en",    "tld": "com.au"},
    "English (India)":       {"lang": "en",    "tld": "co.in"},
    "English (Canada)":      {"lang": "en",    "tld": "ca"},
    "Spanish":               {"lang": "es",    "tld": "es"},
    "French":                {"lang": "fr",    "tld": "fr"},
    "German":                {"lang": "de",    "tld": "de"},
    "Italian":               {"lang": "it",    "tld": "it"},
    "Portuguese (Brazil)":   {"lang": "pt",    "tld": "com.br"},
    "Japanese":              {"lang": "ja",    "tld": "co.jp"},
    "Korean":                {"lang": "ko",    "tld": "co.kr"},
    "Chinese":               {"lang": "zh-CN", "tld": "com"},
    "Hindi":                 {"lang": "hi",    "tld": "co.in"},
    "Arabic":                {"lang": "ar",    "tld": "com"},
    "Russian":               {"lang": "ru",    "tld": "ru"},
    "Turkish":               {"lang": "tr",    "tld": "com.tr"},
}

EDGE_VOICES = {
    "US English - Guy (Male)":        "en-US-GuyNeural",
    "US English - Christopher (Male)":"en-US-ChristopherNeural",
    "US English - Eric (Male)":       "en-US-EricNeural",
    "US English - Aria (Female)":     "en-US-AriaNeural",
    "US English - Jenny (Female)":    "en-US-JennyNeural",
    "UK English - Ryan (Male)":       "en-GB-RyanNeural",
    "UK English - Sonia (Female)":    "en-GB-SoniaNeural",
    "Australian - William (Male)":    "en-AU-WilliamNeural",
    "Australian - Natasha (Female)":  "en-AU-NatashaNeural",
}

KOKORO_LANGS = {
    "American English": "a",
    "British English":  "b",
    "Spanish":          "e",
    "French":           "f",
    "Hindi":            "h",
    "Italian":          "i",
    "Japanese":         "j",
    "Portuguese":        "p",
    "Mandarin Chinese": "z",
}

# Full voice list from hexgrad/Kokoro-82M v1.0
KOKORO_VOICES = {
    "a": {
        "af_heart": "af_heart", "af_alloy": "af_alloy", "af_aoede": "af_aoede", 
        "af_bella": "af_bella", "af_jessica": "af_jessica", "af_kore": "af_kore",
        "af_nicole": "af_nicole", "af_nova": "af_nova", "af_river": "af_river",
        "af_sarah": "af_sarah", "af_sky": "af_sky",
        "am_adam": "am_adam", "am_echo": "am_echo", "am_eric": "am_eric",
        "am_fenrir": "am_fenrir", "am_liam": "am_liam", "am_michael": "am_michael",
        "am_onyx": "am_onyx", "am_puck": "am_puck", "am_santa": "am_santa"
    },
    "b": {
        "bf_alice": "bf_alice", "bf_emma": "bf_emma", "bf_isabella": "bf_isabella", "bf_lily": "bf_lily",
        "bm_daniel": "bm_daniel", "bm_fable": "bm_fable", "bm_george": "bm_george", "bm_lewis": "bm_lewis"
    },
    "e": {
        "ef_dora": "ef_dora", "em_alex": "em_alex", "em_santa": "em_santa"
    },
    "f": {
        "ff_siwis": "ff_siwis"
    },
    "h": {
        "hf_alpha": "hf_alpha", "hf_beta": "hf_beta", "hm_omega": "hm_omega", "hm_psi": "hm_psi"
    },
    "i": {
        "if_sara": "if_sara", "im_nicola": "im_nicola"
    },
    "j": {
        "jf_alpha": "jf_alpha", "jf_gongitsune": "jf_gongitsune", "jf_nezumi": "jf_nezumi", 
        "jf_tebukuro": "jf_tebukuro", "jm_kumo": "jm_kumo"
    },
    "p": {
        "pf_dora": "pf_dora", "pm_alex": "pm_alex", "pm_santa": "pm_santa"
    },
    "z": {
        "zf_xiaobei": "zf_xiaobei", "zf_xiaoni": "zf_xiaoni", "zf_xiaoxiao": "zf_xiaoxiao", 
        "zf_xiaoyi": "zf_xiaoyi", "zm_yunjian": "zm_yunjian", "zm_yunxi": "zm_yunxi", 
        "zm_yunxia": "zm_yunxia", "zm_yunyang": "zm_yunyang"
    }
}

PIPER_VOICES = {
    "US English (Lessac) - Low Quality": "en_US-lessac-low",
}

MELO_VOICES = {
    "English — US":         {"language": "EN", "speaker": "EN-US"},
    "English — UK (British)":  {"language": "EN", "speaker": "EN-BR"},
    "English — India":      {"language": "EN", "speaker": "EN-INDIA"},
    "English — Australia":  {"language": "EN", "speaker": "EN-AU"},
    "English — Default":    {"language": "EN", "speaker": "EN-Default"},
    "Spanish":              {"language": "ES", "speaker": "ES"},
    "French":               {"language": "FR", "speaker": "FR"},
    "Chinese (Mandarin)":   {"language": "ZH", "speaker": "ZH"},
    "Japanese":             {"language": "JP", "speaker": "JP"},
    "Korean":               {"language": "KR", "speaker": "KR"},
}

STYLETTS2_VOICES = {
    "Default (LJSpeech)": "default",
}
