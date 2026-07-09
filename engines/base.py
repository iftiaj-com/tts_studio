"""
engines/base.py
───────────────
Abstract base class every TTS engine adapter must implement.

To add a new engine:
  1. Create engines/my_engine.py and subclass BaseTTSEngine.
  2. Implement `is_available()` and `synthesize()`.
  3. Register it in engines/registry.py.
"""

from abc import ABC, abstractmethod


class BaseTTSEngine(ABC):
    """Interface all TTS engine adapters must satisfy."""

    # Human-readable name shown in the UI dropdown
    name: str = "Unknown Engine"

    @staticmethod
    @abstractmethod
    def is_available() -> bool:
        """Return True if the engine's dependencies are installed."""
        ...

    @abstractmethod
    def synthesize(self, text: str, tmp_dir: str, **kwargs) -> dict:
        """
        Generate speech for *text* and write the result into *tmp_dir*.

        Parameters
        ----------
        text    : The text to synthesise.
        tmp_dir : A temporary directory path where output files can be written.
        **kwargs: Engine-specific settings (voices, rate, device, etc.)

        Returns
        -------
        dict with keys:
          playback_file : str  – path to the file used for playback
          save_file     : str  – path to the file offered for download
          save_ext      : str  – default file extension, e.g. ".mp3" or ".wav"
        """
        ...
