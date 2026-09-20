"""
engines/melo_engine.py  –  MeloTTS adapter
"""
import os
import sys
import logging
from engines.base import BaseTTSEngine
from core.model_cache import MODEL_CACHE

logger = logging.getLogger("VoiceCraft")

# In frozen PyInstaller app, ensure NLTK can locate bundled nltk_data inside _internal
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    try:
        import nltk
        bundle_nltk = os.path.join(sys._MEIPASS, "nltk_data")
        if os.path.exists(bundle_nltk) and bundle_nltk not in nltk.data.path:
            nltk.data.path.insert(0, bundle_nltk)
    except Exception as e:
        logger.debug("Could not configure bundled NLTK data path: %s", e)

try:
    from melo.api import TTS as MeloTTS
    _AVAILABLE = True
except Exception as e:
    try:
        log_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.dirname(__file__))
        err_file = os.path.join(log_dir, "melo_startup_error.log")
        import traceback
        with open(err_file, "w", encoding="utf-8") as f:
            f.write(f"MeloTTS failed to load:\n{e}\n\nTraceback:\n")
            traceback.print_exc(file=f)
    except Exception:
        pass
    logger.warning("MeloTTS is not available: %s", e, exc_info=True)
    _AVAILABLE = False

_NLTK_READY = False


def _ensure_nltk_resources(status_cb=None):
    """Check/download NLTK data once per process instead of on every synthesis."""
    global _NLTK_READY
    if _NLTK_READY:
        return
    import nltk
    try:
        nltk.data.find('taggers/averaged_perceptron_tagger_eng')
        nltk.data.find('corpora/cmudict')
    except LookupError:
        if status_cb:
            status_cb("Downloading NLTK resources...")
        nltk.download('averaged_perceptron_tagger_eng', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
        nltk.download('cmudict', quiet=True)
    _NLTK_READY = True


class MeloEngine(BaseTTSEngine):
    name = "MeloTTS (Multi-Lingual)"

    @staticmethod
    def is_available() -> bool:
        return _AVAILABLE

    def synthesize(self, text: str, tmp_dir: str, **kwargs) -> dict:
        device_str = kwargs.get("device", "cpu")
        status_cb  = kwargs.get("status_cb", None)

        if status_cb:
            status_cb(f"Generating MeloTTS speech on {device_str}…")

        _ensure_nltk_resources(status_cb)

        voice_cfg  = kwargs.get("melo_voice_cfg", {"language": "EN", "speaker": "EN-US"})
        language   = voice_cfg.get("language", "EN")
        speaker    = voice_cfg.get("speaker", "EN-US")

        def _load():
            if status_cb:
                status_cb(f"Initializing MeloTTS ({language}). May download model checkpoint on first run...")
            return MeloTTS(language=language, device=device_str)

        # Cached per (language, device); idle-evicted by MODEL_CACHE after 5 min.
        model       = MODEL_CACHE.get(("melo", language, device_str), _load)
        speaker_ids = dict(model.hps.data.spk2id)

        # Fallback to first available speaker if the requested one isn't in the model
        spk_id = speaker_ids.get(speaker, list(speaker_ids.values())[0])

        speed = kwargs.get("melo_speed", 1.0)
        wav_path = os.path.join(tmp_dir, "output.wav")
        model.tts_to_file(text, spk_id, wav_path, speed=speed)

        return {"playback_file": wav_path, "save_file": wav_path, "save_ext": ".wav"}
