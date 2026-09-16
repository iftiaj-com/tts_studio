import os
import subprocess
import sys
import shutil
from pathlib import Path

# VoiceCraft PyInstaller Builder
# This script automates the compilation of the TTS application into a portable EXE.

# Every library PyInstaller must be able to see for the build to be complete.
# Keyed by import name; the value is what the engine needs it for.
_REQUIRED = {
    "gtts":           "gTTS engine",
    "edge_tts":       "Edge TTS engine",
    "kokoro":         "Kokoro PyTorch path",
    "kokoro_onnx":    "Kokoro ONNX path",
    "piper":          "Piper TTS engine",
    "melo":           "MeloTTS engine",
    "pyttsx3":        "pyttsx3 engine",
    "faster_whisper": "word-level subtitles",
    "customtkinter":  "GUI",
    "soundfile":      "audio I/O",
}


def _check_interpreter():
    """Refuse to build from an interpreter that cannot see the engine libraries.

    PyInstaller bundles whatever *this* interpreter can import. Building with a
    bare `python` picks up whichever one is first on PATH, which silently drops
    engines from the EXE while the build still reports success.
    """
    import importlib.util
    missing = [(m, why) for m, why in _REQUIRED.items()
               if importlib.util.find_spec(m) is None]
    if not missing:
        return True

    print(f"[!] This interpreter is missing {len(missing)} required package(s):")
    for mod, why in missing:
        print(f"      {mod:16} ({why})")
    print(f"[!] Building here would produce an EXE without them.")
    print(f"[!] Interpreter in use: {sys.executable}")
    print(f"[!] Build with the project venv instead:")
    print(r"        .\venv_311\Scripts\python.exe build_exe.py")
    return False


def build():
    print("=== TTS Studio Build System ===")

    if not _check_interpreter():
        return
    
    # 1. Setup paths
    base_dir = Path(__file__).parent.absolute()
    main_script = base_dir / "tts_app.py"
    dist_dir = base_dir / "dist"
    build_dir = base_dir / "build"
    
    print(f"[*] Base directory: {base_dir}")
    
    # 2. Check for dependencies
    try:
        import PyInstaller
    except ImportError:
        print("[!] PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 3. Construct PyInstaller command
    # We use --noconsole for a clean GUI app
    # We use --collect-all to ensure heavy libraries are fully included
    command = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconsole",
        "--name=TTS_Studio",
        "--clean",
        "--noconfirm",

        "--add-data", "models;models",
        "--collect-all", "torch",
        "--collect-all", "transformers",
        "--collect-all", "customtkinter",
        "--collect-all", "kokoro",
        "--collect-all", "language_tags",
        "--collect-all", "espeakng_loader",
        "--collect-all", "faster_whisper",
        "--collect-all", "kokoro_onnx",
        "--collect-all", "melo",
        "--collect-all", "piper",
        "--collect-all", "soundfile",
        "--collect-all", "pygame",
        "--hidden-import", "pydub",
        "--workpath", str(build_dir),
        "--distpath", str(dist_dir),
        str(main_script)
    ]
    
    # Presence is not enough: a truncated model bundles cleanly and only fails
    # at runtime with "INVALID_PROTOBUF", which is how a 78 MB stub once shipped.
    if os.path.exists("kokoro-v1.0.onnx"):
        from engines.kokoro_engine import _onnx_is_complete
        if not _onnx_is_complete("kokoro-v1.0.onnx"):
            print("[!] kokoro-v1.0.onnx is truncated. Delete it and let the app "
                  "re-download, or fetch it again before building.")
            return
        command.extend(["--add-data", "kokoro-v1.0.onnx;."])
    if os.path.exists("voices.bin"):
        command.extend(["--add-data", "voices.bin;."])
    
    print(f"[*] Running command: {' '.join(command)}")
    
    try:
        subprocess.check_call(command)
        print("\n[+] Build successful!")
        print(f"[+] Application located in: {dist_dir / 'TTS_Studio'}")
        
        # 4. Final instructions
        print("\n=== FINAL STEPS ===")
        print("1. Locate the 'dist/TTS_Studio' folder.")
        print("2. You can now distribute this folder as a portable package.")
        print("3. On first launch, the app will download required models to the user's cache.")
        print("4. Launch 'TTS_Studio.exe' inside that folder.")
        
    except subprocess.CalledProcessError as e:
        print(f"[!] Build failed with exit code: {e.returncode}")

if __name__ == "__main__":
    build()
