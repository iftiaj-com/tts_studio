"""
engines/melo_engine.py  –  MeloTTS adapter
"""
import os
from engines.base import BaseTTSEngine

try:
    from melo.api import TTS as MeloTTS
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False


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

        # Ensure required NLTK resources are downloaded
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

        voice_cfg  = kwargs.get("melo_voice_cfg", {"language": "EN", "speaker": "EN-US"})
        language   = voice_cfg.get("language", "EN")
        speaker    = voice_cfg.get("speaker", "EN-US")

        if status_cb:
            status_cb(f"Initializing MeloTTS ({language}). May download model checkpoint on first run...")

        model       = MeloTTS(language=language, device=device_str)
        speaker_ids = dict(model.hps.data.spk2id)

        # Fallback to first available speaker if the requested one isn't in the model
        spk_id = speaker_ids.get(speaker, list(speaker_ids.values())[0])

        speed = kwargs.get("melo_speed", 1.0)
        wav_path = os.path.join(tmp_dir, "output.wav")
        model.tts_to_file(text, spk_id, wav_path, speed=speed)

        return {"playback_file": wav_path, "save_file": wav_path, "save_ext": ".wav"}
