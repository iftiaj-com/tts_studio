"""
core/version.py
────────────────
Single source of truth for product identity. build_exe.py stamps these into
the EXE's version resource and passes them to the Inno Setup compiler, so a
release only needs the version bumped here.
"""

APP_NAME    = "VoiceCraft"
APP_TITLE   = "VoiceCraft TTS Studio"
__version__ = "1.0.0"
PUBLISHER   = "VoiceCraft"
SOURCE_URL  = "https://github.com/iftiaj-com/tts_studio"
LICENSE_ID  = "GPL-3.0-or-later"
