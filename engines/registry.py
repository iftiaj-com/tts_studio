"""
engines/registry.py
────────────────────
Master engine registry — single place to enable / add TTS engines.

To add a new engine:
  1. Create engines/my_engine.py with a class that subclasses BaseTTSEngine.
  2. Import it here and add it to ENGINE_CLASSES.
  3. Done — the UI will detect it automatically via is_available().
"""

from engines.gtts_engine import GTTSEngine
from engines.edge_engine import EdgeEngine
from engines.kokoro_engine import KokoroEngine
from engines.piper_engine import PiperEngine
from engines.melo_engine import MeloEngine
from engines.pyttsx3_engine import Pyttsx3Engine

# Ordered list — the UI displays engines in this order.
ENGINE_CLASSES = [
    GTTSEngine,
    EdgeEngine,
    KokoroEngine,
    PiperEngine,
    MeloEngine,
    Pyttsx3Engine,
]


def get_available_engines() -> list:
    """Return instantiated engine objects for every available engine."""
    return [cls() for cls in ENGINE_CLASSES if cls.is_available()]
