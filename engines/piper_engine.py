"""
engines/piper_engine.py  –  Piper TTS adapter
"""
import os
import wave
from engines.base import BaseTTSEngine

try:
    import piper  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


class PiperEngine(BaseTTSEngine):
    name = "Piper TTS (Local Fast)"

    @staticmethod
    def is_available() -> bool:
        return _AVAILABLE

    def synthesize(self, text: str, tmp_dir: str, **kwargs) -> dict:
        from piper import PiperVoice
        status_cb  = kwargs.get("status_cb", None)

        if status_cb:
            status_cb("Loading Piper voice…")

        # Get the absolute path to the project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        voice_id = kwargs.get("voice_key", "en_US-lessac-low")
        model_name = f"{voice_id}.onnx"
        
        default_model = os.path.join(project_root, "models", "piper", model_name)
        model_path = kwargs.get("model_path", default_model)
        
        if not os.path.exists(model_path):
            raise RuntimeError(
                f"Piper model missing at {model_path}! Download an ONNX model file first."
            )

        voice    = PiperVoice.load(model_path)
        wav_path = os.path.join(tmp_dir, "output.wav")
        with wave.open(wav_path, "wb") as w:
            voice.synthesize_wav(text, w)

        return {"playback_file": wav_path, "save_file": wav_path, "save_ext": ".wav"}
