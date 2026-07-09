"""
engines/pyttsx3_engine.py  –  pyttsx3 (System Voices) adapter
"""
import os
from engines.base import BaseTTSEngine

try:
    import pyttsx3
    _engine_test = pyttsx3.init()
    _engine_test.stop()
    del _engine_test
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False


class Pyttsx3Engine(BaseTTSEngine):
    name = "pyttsx3 (System Voices)"

    @staticmethod
    def is_available() -> bool:
        return _AVAILABLE

    @staticmethod
    def load_system_voices() -> list:
        """Return [(display_name, voice_id), ...] for all installed voices."""
        voices = []
        try:
            engine = pyttsx3.init()
            raw    = engine.getProperty("voices") or []
            for v in raw:
                name = v.name
                if "Microsoft" in name:
                    parts = name.split(" - ")
                    name  = parts[0].replace("Microsoft ", "") if parts else name
                voices.append((name, v.id))
            engine.stop()
        except Exception:
            voices = [("Default", "")]
        return voices or [("Default", "")]

    def synthesize(self, text: str, tmp_dir: str, **kwargs) -> dict:
        voice_id = kwargs.get("voice_id", "")
        rate     = kwargs.get("rate", 175)
        volume   = kwargs.get("volume", 0.9)
        status_cb = kwargs.get("status_cb", None)

        if status_cb:
            status_cb("Generating speech with system voice…")

        engine = pyttsx3.init()
        if voice_id:
            engine.setProperty("voice", voice_id)
        engine.setProperty("rate",   rate)
        engine.setProperty("volume", volume)

        wav_path = os.path.join(tmp_dir, "output.wav")
        engine.save_to_file(text, wav_path)
        engine.runAndWait()
        engine.stop()

        return {"playback_file": wav_path, "save_file": wav_path, "save_ext": ".wav"}
