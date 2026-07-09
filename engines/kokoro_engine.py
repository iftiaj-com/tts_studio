"""
engines/kokoro_engine.py  –  Kokoro-82M / kokoro-onnx adapter
"""
import os
from engines.base import BaseTTSEngine
from core.constants import KOKORO_VOICES

try:
    from kokoro import KPipeline
    import soundfile as sf
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

# Always mark as available — we have the ONNX fallback bundled
_AVAILABLE = True


class KokoroEngine(BaseTTSEngine):
    name = "Kokoro-82M (Fast Local AI)"

    def __init__(self):
        self._pipelines = {}   # dict of lang_code -> KPipeline
        self._shared_model = None

    @staticmethod
    def is_available() -> bool:
        return _AVAILABLE

    def _get_pipeline(self, lang_code: str, device_str: str, status_cb=None):
        """Get or create a pipeline for the specific language."""
        if lang_code in self._pipelines:
            return self._pipelines[lang_code]

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        model_path = os.path.join(project_root, "kokoro-v1.0.onnx")
        voices_path = os.path.join(project_root, "voices.bin")

        # Prefer local ONNX pipeline if weights exist to avoid Hugging Face network freezes
        if os.path.exists(model_path):
            try:
                if status_cb:
                    status_cb("Loading local Kokoro ONNX pipeline...")
                from kokoro_onnx import Kokoro
                
                if not os.path.exists(voices_path):
                    import urllib.request
                    if status_cb:
                        status_cb("Downloading Kokoro ONNX voices...")
                    v_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
                    urllib.request.urlretrieve(v_url, voices_path)
                    
                pipeline = Kokoro(model_path, voices_path)
                self._pipelines[lang_code] = pipeline
                self._use_onnx = True
                return pipeline
            except Exception as onnx_err:
                print(f"Failed to load local ONNX pipeline: {onnx_err}. Falling back to PyTorch...")

        try:
            from kokoro import KPipeline, KModel
            if status_cb:
                status_cb(f"Loading Kokoro {lang_code} pipeline…")
            
            if self._shared_model is None:
                self._shared_model = KModel().to(device_str).eval()
            
            pipeline = KPipeline(lang_code=lang_code, model=self._shared_model)
            self._pipelines[lang_code] = pipeline
            self._use_onnx = False
            return pipeline
        except Exception as e:
            # Fall back to kokoro-onnx (v1.0)
            print(f"Kokoro PyTorch load failed, using ONNX fallback: {e}")
            from kokoro_onnx import Kokoro
            
            if not os.path.exists(model_path) or not os.path.exists(voices_path):
                import urllib.request
                if status_cb:
                    status_cb("Downloading Kokoro ONNX model…")
                m_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
                v_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
                if not os.path.exists(model_path):
                    urllib.request.urlretrieve(m_url, model_path)
                if not os.path.exists(voices_path):
                    urllib.request.urlretrieve(v_url, voices_path)

            pipeline = Kokoro(model_path, voices_path)
            self._pipelines[lang_code] = pipeline
            self._use_onnx = True
            return pipeline

    def synthesize(self, text: str, tmp_dir: str, **kwargs) -> dict:
        import numpy as np
        import soundfile as sf
        import time
        import re

        device_str = kwargs.get("device", "cpu")
        lang_code  = kwargs.get("kokoro_lang_code", "a")
        voice_key  = kwargs.get("voice_key", "af_heart")
        speed      = kwargs.get("kokoro_speed", 1.0)
        status_cb  = kwargs.get("status_cb", None)
        check_cancel = kwargs.get("check_cancel", lambda: False)
        use_subtitle = kwargs.get("kokoro_subtitle", False)

        voice_id = KOKORO_VOICES[lang_code][voice_key]
        
        # Filename convention: First_three_word_of_input_timestamp
        words = re.findall(r'\w+', text)
        prefix = "_".join(words[:3]) if words else "audio"
        ts = time.strftime("%Y%m%d_%H%M%S")
        base_name = f"{prefix}_{ts}"
        wav_path = os.path.join(tmp_dir, f"{base_name}.wav")
        srt_path = os.path.join(tmp_dir, f"{base_name}.srt") if use_subtitle else None

        if use_subtitle:
            if status_cb: status_cb("Generating speech and subtitles (Simpler-Kokoro)...")
            try:
                from Simpler_Kokoro import SimplerKokoro
                sk = SimplerKokoro(device=device_str)
                sk.generate(
                    text=text,
                    voice=voice_id,
                    speed=speed,
                    output_path=wav_path,
                    write_subtitles=True,
                    subtitles_path=srt_path,
                    subtitles_word_level=True
                )
                return {
                    "playback_file": wav_path, 
                    "save_file": wav_path, 
                    "save_ext": ".wav",
                    "srt_file": srt_path
                }
            except Exception as e:
                print(f"Simpler-Kokoro failed: {e}")
                if status_cb: status_cb(f"⚠ SRT failed: {e}. Falling back...")


        pipeline = self._get_pipeline(lang_code, device_str, status_cb)

        if status_cb:
            status_cb(f"Generating Kokoro speech ({lang_code})...")

        if getattr(self, '_use_onnx', False):
            onnx_lang_map = {'a': 'en-us', 'b': 'en-gb', 'e': 'es', 'f': 'fr-fr', 
                            'h': 'hi', 'i': 'it', 'p': 'pt-br', 'j': 'ja', 'z': 'zh'}
            samples, sr = pipeline.create(text, voice=voice_id, speed=speed, 
                                          lang=onnx_lang_map.get(lang_code, 'en-us'))
            final_audio = samples
        else:
            generator = pipeline(text, voice=voice_id, speed=speed, split_pattern=r'\n+')
            audio_chunks = []
            for _, _, audio in generator:
                if check_cancel():
                    return {"playback_file": None, "save_file": None, "save_ext": ".wav"}
                if audio is not None:
                    audio_chunks.append(audio)

            if not audio_chunks:
                raise RuntimeError("Kokoro generated empty audio.")
            final_audio = np.concatenate(audio_chunks)
            sr = 24000

        sf.write(wav_path, final_audio, sr)
        return {"playback_file": wav_path, "save_file": wav_path, "save_ext": ".wav"}
