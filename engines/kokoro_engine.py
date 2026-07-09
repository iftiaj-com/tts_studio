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

_ONNX_MODEL_URL  = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
_ONNX_VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"


class DownloadCancelled(Exception):
    """Raised when the user cancels while model weights are downloading."""


def _download_with_progress(url, dest_path, label="file",
                            status_cb=None, check_cancel=None):
    """Stream *url* to *dest_path* in chunks with progress + cancellation.

    Downloads into a .part file and atomically renames on success, so a
    cancelled/failed download never leaves a corrupt weights file behind.
    """
    import urllib.request
    tmp_path = dest_path + ".part"
    request = urllib.request.Request(url, headers={"User-Agent": "TTS-Studio"})
    try:
        with urllib.request.urlopen(request, timeout=30) as resp, \
                open(tmp_path, "wb") as out:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            while True:
                if check_cancel and check_cancel():
                    raise DownloadCancelled(f"Download of {label} cancelled")
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if status_cb:
                    if total:
                        status_cb(f"Downloading {label}… "
                                  f"{done * 100 // total}% "
                                  f"({done // (1024 * 1024)} / {total // (1024 * 1024)} MB)")
                    else:
                        status_cb(f"Downloading {label}… {done // (1024 * 1024)} MB")
        os.replace(tmp_path, dest_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _create_onnx_pipeline(model_path, voices_path, device_str, status_cb=None):
    """Build a kokoro-onnx pipeline with explicit execution providers.

    kokoro-onnx's default constructor lets onnxruntime silently pick the CPU
    provider even on CUDA machines; here we probe onnxruntime for CUDA and
    hand it an explicitly-ordered provider list.
    """
    from kokoro_onnx import Kokoro

    providers = ["CPUExecutionProvider"]
    if device_str == "cuda":
        try:
            import onnxruntime as ort
            if "CUDAExecutionProvider" in ort.get_available_providers():
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            elif status_cb:
                status_cb("⚠ CUDA requested but onnxruntime-gpu not installed — using CPU.")
        except ImportError:
            pass

    try:
        import onnxruntime as ort
        if hasattr(Kokoro, "from_session"):
            session = ort.InferenceSession(model_path, providers=providers)
            if status_cb:
                status_cb(f"Kokoro ONNX running on {session.get_providers()[0]}")
            return Kokoro.from_session(session, voices_path)
    except Exception as e:
        print(f"Explicit ONNX session failed ({e}); using default constructor.")

    # Older kokoro-onnx versions honour the ONNX_PROVIDER env var instead.
    if providers[0] == "CUDAExecutionProvider":
        os.environ.setdefault("ONNX_PROVIDER", "CUDAExecutionProvider")
    return Kokoro(model_path, voices_path)


class KokoroEngine(BaseTTSEngine):
    name = "Kokoro-82M (Fast Local AI)"

    def __init__(self):
        self._pipelines = {}   # (kind, lang_or_device) -> pipeline
        self._shared_model = None

    @staticmethod
    def is_available() -> bool:
        return _AVAILABLE

    def _get_pipeline(self, lang_code: str, device_str: str,
                      status_cb=None, check_cancel=None):
        """Get or create a pipeline for the specific language/device."""
        # The ONNX pipeline is language-agnostic (lang is passed per call),
        # so one instance per device serves every language.
        onnx_key  = ("onnx", device_str)
        torch_key = ("torch", lang_code)
        if onnx_key in self._pipelines:
            self._use_onnx = True
            return self._pipelines[onnx_key]
        if torch_key in self._pipelines:
            self._use_onnx = False
            return self._pipelines[torch_key]

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        model_path = os.path.join(project_root, "kokoro-v1.0.onnx")
        voices_path = os.path.join(project_root, "voices.bin")

        # Prefer local ONNX pipeline if weights exist to avoid Hugging Face network freezes
        if os.path.exists(model_path):
            try:
                if status_cb:
                    status_cb("Loading local Kokoro ONNX pipeline...")
                if not os.path.exists(voices_path):
                    _download_with_progress(
                        _ONNX_VOICES_URL, voices_path, label="Kokoro voices",
                        status_cb=status_cb, check_cancel=check_cancel)

                pipeline = _create_onnx_pipeline(
                    model_path, voices_path, device_str, status_cb)
                self._pipelines[onnx_key] = pipeline
                self._use_onnx = True
                return pipeline
            except DownloadCancelled:
                raise
            except Exception as onnx_err:
                print(f"Failed to load local ONNX pipeline: {onnx_err}. Falling back to PyTorch...")

        try:
            from kokoro import KPipeline, KModel
            if status_cb:
                status_cb(f"Loading Kokoro {lang_code} pipeline…")

            if self._shared_model is None:
                self._shared_model = KModel().to(device_str).eval()

            pipeline = KPipeline(lang_code=lang_code, model=self._shared_model)
            self._pipelines[torch_key] = pipeline
            self._use_onnx = False
            return pipeline
        except Exception as e:
            # Fall back to kokoro-onnx (v1.0)
            print(f"Kokoro PyTorch load failed, using ONNX fallback: {e}")

            if not os.path.exists(model_path):
                _download_with_progress(
                    _ONNX_MODEL_URL, model_path, label="Kokoro ONNX model",
                    status_cb=status_cb, check_cancel=check_cancel)
            if not os.path.exists(voices_path):
                _download_with_progress(
                    _ONNX_VOICES_URL, voices_path, label="Kokoro voices",
                    status_cb=status_cb, check_cancel=check_cancel)

            pipeline = _create_onnx_pipeline(
                model_path, voices_path, device_str, status_cb)
            self._pipelines[onnx_key] = pipeline
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


        pipeline = self._get_pipeline(lang_code, device_str, status_cb, check_cancel)

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
