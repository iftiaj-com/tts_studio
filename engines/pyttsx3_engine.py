"""
engines/pyttsx3_engine.py  –  pyttsx3 (System Voices) adapter

pyttsx3 wraps SAPI5 (Windows) / NSSpeechSynthesizer (macOS), which are
apartment-threaded COM/ObjC APIs: initializing or driving them from an
arbitrary worker thread causes access violations and silent crashes.
All pyttsx3 calls are therefore marshalled onto ONE dedicated, long-lived
worker thread via a job queue.
"""
import os
import queue
import threading

from engines.base import BaseTTSEngine

try:
    import pyttsx3
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False


class _Pyttsx3Worker:
    """Runs every pyttsx3 job on a single dedicated thread.

    A fresh engine is created per job *inside* that thread: this keeps the
    COM apartment consistent (fixing the sub-thread crash) while avoiding
    the well-known pyttsx3 bug where a reused engine hangs on the second
    runAndWait() call.
    """

    def __init__(self):
        self._jobs = queue.Queue()
        self._thread = None
        self._lock = threading.Lock()

    def _ensure_thread(self):
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(
                    target=self._run, daemon=True, name="pyttsx3-worker")
                self._thread.start()

    def _run(self):
        while True:
            fn, result = self._jobs.get()
            try:
                result["value"] = fn()
            except Exception as e:  # propagate to the submitting thread
                result["error"] = e
            finally:
                result["done"].set()

    def submit(self, fn, timeout=300):
        """Run *fn* on the pyttsx3 thread and return its result."""
        self._ensure_thread()
        result = {"done": threading.Event(), "value": None, "error": None}
        self._jobs.put((fn, result))
        if not result["done"].wait(timeout):
            raise TimeoutError("pyttsx3 synthesis timed out")
        if result["error"] is not None:
            raise result["error"]
        return result["value"]


_WORKER = _Pyttsx3Worker()


class Pyttsx3Engine(BaseTTSEngine):
    name = "pyttsx3 (System Voices)"

    @staticmethod
    def is_available() -> bool:
        return _AVAILABLE

    @staticmethod
    def load_system_voices() -> list:
        """Return [(display_name, voice_id), ...] for all installed voices."""
        def _job():
            voices = []
            engine = pyttsx3.init()
            raw    = engine.getProperty("voices") or []
            for v in raw:
                name = v.name
                if "Microsoft" in name:
                    parts = name.split(" - ")
                    name  = parts[0].replace("Microsoft ", "") if parts else name
                voices.append((name, v.id))
            engine.stop()
            return voices

        try:
            voices = _WORKER.submit(_job, timeout=30)
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

        wav_path = os.path.join(tmp_dir, "output.wav")

        def _job():
            engine = pyttsx3.init()
            if voice_id:
                engine.setProperty("voice", voice_id)
            engine.setProperty("rate",   rate)
            engine.setProperty("volume", volume)
            engine.save_to_file(text, wav_path)
            engine.runAndWait()
            engine.stop()

        _WORKER.submit(_job)

        return {"playback_file": wav_path, "save_file": wav_path, "save_ext": ".wav"}
