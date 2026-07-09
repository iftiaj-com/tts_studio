import os
import subprocess
import sys
import shutil
from pathlib import Path

# VoiceCraft PyInstaller Builder
# This script automates the compilation of the TTS application into a portable EXE.

def build():
    print("=== TTS Studio Build System ===")
    
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
        "--collect-all", "soundfile",
        "--collect-all", "pygame",
        "--hidden-import", "pydub",
        "--workpath", str(build_dir),
        "--distpath", str(dist_dir),
        str(main_script)
    ]
    
    if os.path.exists("kokoro-v1.0.onnx"):
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
