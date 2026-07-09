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

from core.temp_cleanup import sweep_orphan_temp_dirs
from ui.app import TTSStudioApp

if __name__ == "__main__":
    # Remove tts_studio_* temp dirs orphaned by a previous crash/force-quit.
    sweep_orphan_temp_dirs()
    app = TTSStudioApp()
    app.mainloop()
