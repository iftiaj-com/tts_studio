"""
ui/app.py
──────────
TTSStudioApp — the main application window.
Assembles all panels and owns the generation / playback pipeline.
"""

import os
import sys
import io
import time
import wave
import shutil
import tempfile
import threading
import subprocess
import re

# Pyinstaller windowed-mode fix
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

import customtkinter as ctk
from tkinter import filedialog, messagebox
import numpy as np
import pygame
import torch
from pydub import AudioSegment
from pydub import silence as pydub_silence

from core.constants import COLORS, FONTS
from ui.theme import card
from ui.panels.text_panel          import TextPanel
from ui.panels.engine_panel        import EnginePanel
from ui.panels.effects_panel       import EffectsPanel
from ui.panels.customization_panel import CustomizationPanel
from ui.panels.playback_panel      import PlaybackPanel

from engines.registry   import get_available_engines
from engines.pyttsx3_engine import Pyttsx3Engine
from effects.audio_effects  import AudioEffects
from effects.registry       import EFFECTS_REGISTRY

try:
    import librosa
    _LIBROSA = True
except ImportError:
    _LIBROSA = False


class TTSStudioApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("TTS Studio")
        self.geometry("1180x680")
        self.minsize(1100, 600)
        self.configure(fg_color=COLORS["bg_dark"])
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # State
        self._temp_playback_file = None
        self._temp_save_file     = None
        self._temp_save_ext      = ".wav"
        self._temp_mp3           = None
        self._temp_srt           = None
        self._final_saved_file   = None
        self._is_playing         = False
        self._is_generating      = False
        self._playback_thread    = None
        self._stop_event         = threading.Event()

        # Engines
        self._available_engines = get_available_engines()
        self._engine_map        = {e.name: e for e in self._available_engines}

        # System voices for pyttsx3
        self._system_voices = []
        if Pyttsx3Engine.is_available():
            self._system_voices = Pyttsx3Engine.load_system_voices()

        pygame.mixer.init()
        self._build_ui()

    # ──────────────────────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Main container filling the window
        main_container = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"])
        main_container.pack(fill="both", expand=True)

        # Header (Top, full width)
        header = ctk.CTkFrame(main_container, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(18, 4))
        header.columnconfigure(1, weight=1)
        bar = ctk.CTkFrame(header, width=5, height=50,
                           fg_color=COLORS["accent_primary"], corner_radius=3)
        bar.grid(row=0, column=0, rowspan=2, padx=(0, 14), sticky="ns")
        ctk.CTkLabel(header, text="🎙  TTS Studio", font=FONTS["title"],
                     text_color=COLORS["text_primary"]).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(header,
                     text="Text-to-Speech Studio  •  gTTS + Edge + Kokoro + Melo + Piper + Audio Effects",
                     font=FONTS["body_small"],
                     text_color=COLORS["text_muted"]).grid(row=1, column=1, sticky="w")

        # Split content frame (Middle)
        content_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=24, pady=(10, 10))
        # "uniform" locks both columns to a fixed 50/50 split so button
        # text/state changes during generation can't re-balance the layout.
        content_frame.columnconfigure(0, weight=1, minsize=500, uniform="content")
        content_frame.columnconfigure(1, weight=1, minsize=500, uniform="content")
        content_frame.rowconfigure(0, weight=1)

        # Left Column (Text Input + Playback)
        left_col = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Right Column (Scrollable list of panels: TTS Engine, Customization, Voice Effects)
        right_scroll = ctk.CTkScrollableFrame(
            content_frame, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent_primary"]
        )
        right_scroll.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # add="+" preserves CTkScrollableFrame's own <Configure> handler
        # (_fit_frame_dimensions_to_canvas), which stretches the inner frame
        # to the full canvas width. Binding without it replaced that handler
        # and left the right-side cards at their narrow natural width.
        def _reset_xview(event):
            right_scroll._parent_canvas.xview_moveto(0)
        right_scroll._parent_canvas.bind("<FocusIn>", _reset_xview, add="+")
        right_scroll._parent_canvas.bind("<Configure>", _reset_xview, add="+")

        # Panels in Left Column
        self._text_panel = TextPanel(left_col, row=None)
        self._play_panel = PlaybackPanel(
            left_col,
            on_generate=self._on_generate,
            on_cancel=self._on_cancel,
            on_play=self._on_play,
            on_stop=self._on_stop,
            on_save=self._on_save,
            on_save_srt=self._on_save_srt,
            on_open_folder=self._on_open_folder,
            row=None
        )

        # Panels in Right Scrollable Column
        self._engine_panel = EnginePanel(right_scroll, self._available_engines, self._system_voices, row=None)
        self._cust_panel = CustomizationPanel(right_scroll, row=None)
        self._effects_panel = EffectsPanel(right_scroll, row=None)

        # Status Bar (Bottom)
        status_frame = ctk.CTkFrame(main_container, fg_color=COLORS["bg_card"],
                                    corner_radius=10, border_width=1,
                                    border_color=COLORS["border"])
        status_frame.pack(fill="x", padx=24, pady=(5, 15))

        si = ctk.CTkFrame(status_frame, fg_color="transparent")
        si.pack(fill="x", padx=14, pady=8)
        self._status_dot = ctk.CTkLabel(si, text="●", font=("Segoe UI", 10),
                                        text_color=COLORS["text_muted"])
        self._status_dot.pack(side="left", padx=(0, 8))
        self._status_label = ctk.CTkLabel(si,
                                          text="Ready — Enter text and click Generate",
                                          font=FONTS["status"],
                                          text_color=COLORS["text_secondary"])
        self._status_label.pack(side="left")
        engine_badge_text = self._available_engines[0].name.split("(")[0].strip() \
            if self._available_engines else "None"
        self._engine_badge = ctk.CTkLabel(si, text=engine_badge_text,
                                          font=FONTS["body_small"],
                                          text_color=COLORS["accent_primary"],
                                          fg_color=COLORS["bg_input"],
                                          corner_radius=6, width=60, height=22)
        self._engine_badge.pack(side="right", padx=(8, 0))

    # ──────────────────────────────────────────────────────────────
    #  STATUS
    # ──────────────────────────────────────────────────────────────

    def _set_status(self, text, color=None):
        self._status_label.configure(text=text)
        self._status_dot.configure(text_color=color or COLORS["text_muted"])

    # ──────────────────────────────────────────────────────────────
    #  GENERATION
    # ──────────────────────────────────────────────────────────────

    def _on_generate(self):
        if self._is_generating:
            return
        text = self._text_panel.get_text().strip()
        if not text:
            self._set_status("⚠  Please enter some text first", COLORS["warning"])
            return

        self._temp_playback_file = None
        self._temp_save_file     = None
        self._temp_save_ext      = ".wav"
        self._temp_mp3           = None
        self._temp_srt           = None

        self._is_generating = True
        self._stop_event.clear()

        pp = self._play_panel
        pp.generate_btn.configure(state="disabled", text="Generating…")
        pp.cancel_btn.configure(state="normal", text="✖  Cancel")
        pp.set_generating(True)
        for btn in (pp.play_btn, pp.stop_btn, pp.save_btn, pp.save_srt_btn, pp.open_folder_btn):
            btn.configure(state="disabled")
        pp.progress.set(0)
        self._set_status("Generating speech…", COLORS["warning"])

        threading.Thread(target=self._generate_worker, args=(text,), daemon=True).start()

    def _on_cancel(self):
        if self._is_generating:
            self._stop_event.set()
            self._set_status("⌛  Cancelling…", COLORS["warning"])
            self._play_panel.cancel_btn.configure(state="disabled", text="Cancelling…")

    def _on_generate_finish(self, playback_file):
        self._is_generating = False
        pp = self._play_panel
        pp.generate_btn.configure(state="normal", text="⚡  Generate Speech")
        pp.set_generating(False)
        if playback_file is None:
            self._set_status("⏹  Generation cancelled", COLORS["warning"])
            pp.progress.set(0)
            return
        self._temp_playback_file = playback_file
        pp.play_btn.configure(state="normal")
        pp.save_btn.configure(state="normal")
        if self._temp_srt and os.path.exists(self._temp_srt):
            pp.save_srt_btn.configure(state="normal")
        else:
            pp.save_srt_btn.configure(state="disabled")
        
        if self._temp_mp3:
            pp.open_folder_btn.configure(state="normal")
        self._set_status("✅  Speech generated successfully!", COLORS["success"])

    def _on_generate_error(self, error_msg):
        self._is_generating = False
        pp = self._play_panel
        pp.generate_btn.configure(state="normal", text="⚡  Generate Speech")
        pp.set_generating(False)
        pp.progress.set(0)
        self._set_status(f"❌  Error: {error_msg}", COLORS["error"])
        messagebox.showerror("Generation Error", error_msg)

    def _generate_worker(self, text):
        def check_cancel():
            if self._stop_event.is_set():
                self.after(0, self._on_generate_finish, None)
                return True
            return False

        try:
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            if check_cancel():
                return

            tmp_dir = tempfile.mkdtemp(prefix="tts_studio_")
            self.after(0, lambda: self._play_panel.progress.set(0.10))

            eng_settings  = self._engine_panel.get_settings()
            cust_settings = self._cust_panel.get_settings()
            fx_active     = self._effects_panel.get_active_effects()

            engine_name = eng_settings["engine_name"]
            use_gpu     = eng_settings["use_gpu"] and torch.cuda.is_available()
            device_str  = "cuda" if use_gpu else "cpu"

            # Locate the engine instance
            engine = self._engine_map.get(engine_name)
            if engine is None:
                raise RuntimeError(f"Engine '{engine_name}' not found.")

            # Build per-engine kwargs
            kwargs = dict(
                device=device_str,
                status_cb=lambda msg: self.after(0, lambda m=msg: self._set_status(
                    m, COLORS["accent_primary"])),
                check_cancel=check_cancel,
                lang_key=eng_settings["gtts_lang_key"],
                voice_key=(
                    eng_settings["edge_voice_key"]   if "Edge"    in engine_name else
                    eng_settings["kokoro_voice_key"] if "Kokoro"  in engine_name else
                    eng_settings["piper_voice_key"]  if "Piper"   in engine_name else
                    eng_settings["kokoro_voice_key"]  # fallback
                ),
                melo_voice_cfg=eng_settings["melo_voice_cfg"],
                melo_speed=eng_settings["melo_speed"],
                rate=eng_settings["edge_rate"],
                kokoro_speed=eng_settings["kokoro_speed"],
                kokoro_lang_code=eng_settings.get("kokoro_lang_code", "a"),
                kokoro_subtitle=eng_settings.get("kokoro_subtitle", False),
                voice_id=eng_settings["pyttsx3_voice_id"],
                volume=eng_settings["pyttsx3_volume"],
            )
            if "pyttsx3" in engine_name:
                kwargs["rate"] = eng_settings["pyttsx3_rate"]

            result = engine.synthesize(text, tmp_dir, **kwargs)
            print(f"DEBUG: result={result}")
            if check_cancel():
                return

            playback_file = result["playback_file"]
            save_file     = result["save_file"]
            save_ext      = result["save_ext"]
            self._temp_srt = result.get("srt_file")
            print(f"DEBUG: self._temp_srt={self._temp_srt}")

            self.after(0, lambda: self._play_panel.progress.set(0.40))

            # ── Skip silences ──────────────────────────────────────
            if cust_settings["skip_silences"] and playback_file:
                if check_cancel():
                    return
                self.after(0, lambda: self._set_status(
                    "Removing silences…", COLORS["accent_primary"]))
                try:
                    seg    = AudioSegment.from_file(playback_file)
                    chunks = pydub_silence.split_on_silence(
                        seg, min_silence_len=200, silence_thresh=-40)
                    if chunks:
                        joined = chunks[0]
                        for c in chunks[1:]:
                            joined += c
                        out = os.path.join(tmp_dir, "silence_skipped.wav")
                        joined.export(out, format="wav")
                        playback_file = save_file = out
                        save_ext = ".wav"
                except Exception as e:
                    self.after(0, lambda err=str(e): self._set_status(
                        f"⚠ Skip silences failed: {err}", COLORS["warning"]))

            # ── Speed adjustment ───────────────────────────────────
            speed = cust_settings["speed"]
            if abs(speed - 1.0) > 0.01 and playback_file:
                if check_cancel():
                    return
                self.after(0, lambda: self._set_status(
                    f"Adjusting speed to {speed:.2f}x…", COLORS["accent_primary"]))
                try:
                    src = playback_file
                    if src.endswith(".mp3"):
                        converted = os.path.join(tmp_dir, "speed_converted.wav")
                        AudioSegment.from_mp3(src).export(converted, format="wav")
                        src = converted
                    samples, sr = AudioEffects.load_wav_as_float(src)
                    samples = AudioEffects.change_speed(samples, speed)
                    out = os.path.join(tmp_dir, "speed_adjusted.wav")
                    AudioEffects.save_float_as_wav(samples, sr, out)
                    playback_file = save_file = out
                    save_ext = ".wav"
                except Exception as e:
                    self.after(0, lambda err=str(e): self._set_status(
                        f"⚠ Speed adjustment failed: {err}", COLORS["warning"]))

            # ── Effects pipeline ───────────────────────────────────
            normalize_key = "normalize"
            heavy_fx = any(
                fx_active.get(e["key"], False)
                for e in EFFECTS_REGISTRY
                if e["key"] != normalize_key
            )
            any_fx = heavy_fx or fx_active.get(normalize_key, False)
            env_choice = cust_settings["env_choice"]

            if (any_fx or env_choice != "None") and playback_file:
                if check_cancel():
                    return
                status_msg = "Applying voice effects…" if any_fx else "Adding ambiance noise…"
                self.after(0, lambda: self._set_status(status_msg, COLORS["accent_primary"]))
                try:
                    src = playback_file
                    if src.endswith(".mp3"):
                        conv = os.path.join(tmp_dir, "converted.wav")
                        AudioSegment.from_mp3(src).export(conv, format="wav")
                        src = conv
                    samples, sr = AudioEffects.load_wav_as_float(src)
                    self.after(0, lambda: self._play_panel.progress.set(0.50))

                    for effect in EFFECTS_REGISTRY:
                        if check_cancel():
                            return
                        if effect["key"] == "normalize":
                            continue  # Run normalize at the end of the pipeline instead
                        if not fx_active.get(effect["key"], False):
                            continue
                        fn     = effect["fn"]
                        kwargs_fx = effect.get("kwargs", {})
                        try:
                            samples = fn(samples, sr, **kwargs_fx)
                        except TypeError:
                            samples = fn(samples, **kwargs_fx)

                    # ── Equalizer ─────────────────────────────────────────
                    if cust_settings.get("eq_enabled", False):
                        if check_cancel():
                            return
                        self.after(0, lambda: self._set_status("Applying equalizer…", COLORS["accent_primary"]))
                        try:
                            low_factor = 10 ** (cust_settings["eq_bass"] / 20.0)
                            mid_factor = 10 ** (cust_settings["eq_mids"] / 20.0)
                            high_factor = 10 ** (cust_settings["eq_treble"] / 20.0)
                            samples = AudioEffects.three_band_eq(samples, sr, low_factor, mid_factor, high_factor)
                        except Exception as eq_err:
                            self.after(0, lambda err=str(eq_err): self._set_status(
                                f"⚠ EQ failed: {err}", COLORS["warning"]))

                    # Ambiance mix
                    env_choice = cust_settings["env_choice"]
                    if env_choice != "None":
                        amb_path = (cust_settings["custom_amb_path"]
                                    if env_choice == "Custom File..."
                                    else env_choice)
                        if amb_path:
                            samples = AudioEffects.add_environment_sound(
                                samples, sr, amb_path,
                                volume=cust_settings["env_volume"])

                    # Post-mix normalization (always last)
                    if fx_active.get("normalize", False):
                        samples = AudioEffects.normalize(samples)

                    self.after(0, lambda: self._play_panel.progress.set(0.65))
                    out = os.path.join(tmp_dir, "processed.wav")
                    AudioEffects.save_float_as_wav(samples, sr, out)
                    playback_file = save_file = out
                    save_ext = ".wav"

                except Exception as fx_err:
                    self.after(0, lambda err=str(fx_err): self._set_status(
                        f"⚠ Effects failed: {err}", COLORS["warning"]))

            self.after(0, lambda: self._play_panel.progress.set(0.90))

            # ── Subtitles generation ───────────────────────────────
            if cust_settings.get("auto_subtitle", False) and playback_file:
                if check_cancel():
                    return
                try:
                    from core.subtitles import generate_subtitles
                    srt_out = os.path.join(tmp_dir, "final.srt")
                    
                    def _sub_cb(msg):
                        self.after(0, lambda m=msg: self._set_status(m, COLORS["accent_primary"]))
                        
                    seg_mode = cust_settings.get("sub_segmentation", "word")
                    generate_subtitles(playback_file, srt_out, status_cb=_sub_cb, segmentation=seg_mode)
                    self._temp_srt = srt_out
                except Exception as e:
                    print(f"Subtitle generation failed: {e}")
                    self.after(0, lambda err=str(e): self._set_status(f"⚠ Subtitles failed: {err}", COLORS["warning"]))

            # ── MP3 export for save ────────────────────────────────
            self._temp_mp3 = None
            if save_file and not save_file.endswith(".mp3"):
                try:
                    mp3_out = os.path.join(tmp_dir, "final.mp3")
                    AudioSegment.from_wav(save_file).export(mp3_out,
                                                            format="mp3", bitrate="192k")
                    self._temp_mp3 = mp3_out
                except Exception:
                    pass
            elif save_file and save_file.endswith(".mp3"):
                self._temp_mp3 = save_file

            # Clean old temp dir
            old_dir = None
            if self._temp_playback_file:
                old_dir = os.path.dirname(self._temp_playback_file)
            if old_dir and old_dir != tmp_dir:
                shutil.rmtree(old_dir, ignore_errors=True)

            self._temp_save_file = save_file
            self._temp_save_ext  = save_ext
            self.after(0, lambda: self._on_generate_finish(playback_file))

        except Exception as e:
            self.after(0, lambda err=str(e): self._on_generate_error(err))

    # ──────────────────────────────────────────────────────────────
    #  PLAYBACK
    # ──────────────────────────────────────────────────────────────

    def _on_play(self):
        pf = self._temp_playback_file
        if not pf or not os.path.exists(pf):
            self._set_status("⚠  No audio to play — generate first", COLORS["warning"])
            return
        if self._is_playing:
            pygame.mixer.music.stop()
        amb = self._cust_panel._ambiance_channel
        if amb and amb.get_busy():
            amb.pause()
        pygame.mixer.music.load(pf)
        pygame.mixer.music.play()
        self._is_playing = True
        self._play_panel.play_btn.configure(text="▶  Playing…", state="disabled")
        self._play_panel.stop_btn.configure(state="normal")
        self._set_status("🎵  Playing audio…", COLORS["accent_primary"])
        threading.Thread(target=self._monitor_playback, daemon=True).start()

    def _monitor_playback(self):
        try:
            pf = self._temp_playback_file
            try:
                if pf.endswith(".wav"):
                    with wave.open(pf, 'r') as wf:
                        duration_ms = (wf.getnframes() / wf.getframerate()) * 1000
                else:
                    duration_ms = (os.path.getsize(pf) / 4000) * 1000
            except Exception:
                duration_ms = 10000
            start = time.time()
            while pygame.mixer.music.get_busy() and self._is_playing:
                elapsed  = (time.time() - start) * 1000
                progress = min(elapsed / max(duration_ms, 1), 1.0)
                self.after(0, lambda p=progress: self._play_panel.progress.set(p))
                time.sleep(0.05)
            self.after(0, self._on_playback_done)
        except Exception:
            self.after(0, self._on_playback_done)

    def _on_playback_done(self):
        self._is_playing = False
        self._play_panel.play_btn.configure(text="▶  Play", state="normal")
        self._play_panel.stop_btn.configure(state="disabled")
        self._play_panel.progress.set(0)
        self._set_status("✅  Playback complete", COLORS["success"])
        amb = self._cust_panel._ambiance_channel
        if amb:
            amb.unpause()

    def _on_stop(self):
        if self._is_playing:
            self._is_playing = False
            pygame.mixer.music.stop()
            self._play_panel.play_btn.configure(text="▶  Play", state="normal")
            self._play_panel.stop_btn.configure(state="disabled")
            self._play_panel.progress.set(0)
            self._set_status("⏹  Playback stopped", COLORS["text_muted"])
            amb = self._cust_panel._ambiance_channel
            if amb:
                amb.unpause()

    # ──────────────────────────────────────────────────────────────
    #  SAVE / EXPORT
    # ──────────────────────────────────────────────────────────────

    def _on_save(self):
        sf = self._temp_save_file
        if not sf or not os.path.exists(sf):
            self._set_status("⚠  No audio to save — generate first", COLORS["warning"])
            return
        has_mp3 = bool(self._temp_mp3 and os.path.exists(self._temp_mp3))
        if has_mp3:
            default_ext = ".mp3"
            ftypes = [("MP3 Audio", "*.mp3"), ("WAV Audio", "*.wav"), ("All Files", "*.*")]
        else:
            default_ext = ".wav"
            ftypes = [("WAV Audio", "*.wav"), ("All Files", "*.*")]

        # New filename convention: First_three_word_of_input_timestamp
        text = self._text_panel.get_text().strip()
        words = re.findall(r'\w+', text)
        prefix = "_".join(words[:3]) if words else "tts_studio"
        ts = time.strftime('%Y%m%d_%H%M%S')
        initial_name = f"{prefix}_{ts}{default_ext}"

        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        os.makedirs(output_dir, exist_ok=True)
        filepath = filedialog.asksaveasfilename(
            title="Save Speech Audio",
            defaultextension=default_ext,
            filetypes=ftypes,
            initialdir=output_dir,
            initialfile=initial_name,
        )
        if not filepath:
            return
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            src = self._temp_mp3 if (filepath.lower().endswith(".mp3") and has_mp3) else sf
            shutil.copy2(src, filepath)
            
            # Save SRT if it exists
            if self._temp_srt and os.path.exists(self._temp_srt):
                srt_path = os.path.splitext(filepath)[0] + ".srt"
                shutil.copy2(self._temp_srt, srt_path)
                self._set_status(f"💾  Saved audio & subtitles to {os.path.basename(filepath)}", COLORS["success"])
            else:
                self._set_status(f"💾  Saved to {os.path.basename(filepath)}", COLORS["success"])

            self._final_saved_file = filepath
            self._play_panel.open_folder_btn.configure(state="normal")
        except Exception as e:
            self._set_status(f"❌  Save error: {e}", COLORS["error"])

    def _on_save_srt(self):
        sf = self._temp_srt
        if not sf or not os.path.exists(sf):
            self._set_status("⚠  No subtitle to save", COLORS["warning"])
            return

        text = self._text_panel.get_text().strip()
        words = re.findall(r'\w+', text)
        prefix = "_".join(words[:3]) if words else "subtitles"
        ts = time.strftime('%Y%m%d_%H%M%S')
        initial_name = f"{prefix}_{ts}.srt"

        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        os.makedirs(output_dir, exist_ok=True)
        filepath = filedialog.asksaveasfilename(
            title="Save Subtitles (SRT)",
            defaultextension=".srt",
            filetypes=[("SRT Subtitles", "*.srt"), ("All Files", "*.*")],
            initialdir=output_dir,
            initialfile=initial_name,
        )
        if not filepath:
            return
        try:
            shutil.copy2(sf, filepath)
            self._final_saved_file = filepath
            self._play_panel.open_folder_btn.configure(state="normal")
            self._set_status(f"💾  Saved SRT to {os.path.basename(filepath)}", COLORS["success"])
        except Exception as e:
            self._set_status(f"❌  Save error: {e}", COLORS["error"])

    def _on_open_folder(self):
        target = (self._final_saved_file or self._temp_mp3 or self._temp_save_file)
        if target and os.path.exists(target):
            try:
                subprocess.run(['explorer', '/select,', os.path.normpath(target)])
            except Exception as e:
                self._set_status(f"❌  Could not open folder: {e}", COLORS["error"])

    # ──────────────────────────────────────────────────────────────
    #  CLEANUP
    # ──────────────────────────────────────────────────────────────

    def destroy(self):
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        pf = self._temp_playback_file
        if pf:
            shutil.rmtree(os.path.dirname(pf), ignore_errors=True)
        if hasattr(self, '_cust_panel') and hasattr(self._cust_panel, 'cleanup'):
            self._cust_panel.cleanup()
        super().destroy()
