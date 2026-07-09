"""
tts_app.py  –  VoiceCraft entry point
──────────────────────────────────────
This file is intentionally tiny. All logic lives in the packages below:

  core/       – constants, design tokens, voice maps
  engines/    – TTS engine adapters + registry
  effects/    – audio DSP effects + registry
  ui/         – panels, theme helpers, and the main app window

Run with:
    python tts_app.py
"""

from ui.app import TTSStudioApp

if __name__ == "__main__":
    app = TTSStudioApp()
    app.mainloop()
