"""
effects/audio_effects.py
────────────────────────
All numpy-based audio DSP effects for VoiceCraft.

To add a new effect:
  1. Add a @staticmethod method below.
  2. Register it in effects/registry.py.
  3. The UI panel will pick it up automatically.
"""

import wave
import math
import random

import numpy as np
from pydub import AudioSegment

try:
    import librosa
    _LIBROSA_AVAILABLE = True
except ImportError:
    _LIBROSA_AVAILABLE = False


class AudioEffects:
    """Pure numpy audio effects — no external DSP libraries required."""

    # ──────────────────────────────────────────────────────────────
    #  I/O HELPERS
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def load_wav_as_float(wav_path):
        """Load a WAV file as a float32 numpy array + sample rate."""
        audio = AudioSegment.from_file(wav_path)
        audio = audio.set_channels(1)
        sr = audio.frame_rate
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        samples = samples / (2 ** 15)
        return samples, sr

    @staticmethod
    def save_float_as_wav(samples, sr, wav_path):
        """Save a float32 numpy array back to WAV."""
        samples = np.clip(samples, -1.0, 1.0)
        int_samples = (samples * (2 ** 15 - 1)).astype(np.int16)
        with wave.open(wav_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(int_samples.tobytes())

    # ──────────────────────────────────────────────────────────────
    #  UTILITY / SHARED PRIMITIVES
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def change_speed(samples, speed_factor):
        """
        Change playback speed WITHOUT affecting pitch (time-stretching).
        Uses librosa's phase-vocoder when available so the voice character
        (timbre, formants, pitch) is fully preserved at any speed.
        Falls back to naive resampling (which DOES shift pitch) if librosa
        is not installed.
        """
        if speed_factor == 1.0:
            return samples

        if _LIBROSA_AVAILABLE:
            # rate > 1 → faster, rate < 1 → slower  (matches speed_factor)
            stretched = librosa.effects.time_stretch(y=samples, rate=speed_factor)
            return stretched.astype(np.float32)

        # ── numpy fallback (changes pitch as a side-effect) ──────────
        old_indices = np.arange(len(samples))
        new_length  = int(len(samples) / speed_factor)
        new_indices = np.linspace(0, len(samples) - 1, new_length)
        return np.interp(new_indices, old_indices, samples).astype(np.float32)

    @staticmethod
    def _time_stretch_ola(samples, rate, frame_size=512, hop_size=128):
        """Time-stretch audio using OLA (Overlap-Add) in pure NumPy."""
        if rate == 1.0 or len(samples) < frame_size:
            return samples

        # Analysis hop size
        ana_hop = int(hop_size * rate)
        if ana_hop <= 0:
            return samples

        num_samples = len(samples)
        # Hann window
        window = np.hanning(frame_size).astype(np.float32)

        # Output length
        out_len = int(num_samples / rate) + frame_size
        output = np.zeros(out_len, dtype=np.float32)
        weights = np.zeros(out_len, dtype=np.float32)

        ana_idx = 0.0
        syn_idx = 0

        while int(ana_idx) + frame_size < num_samples:
            frame = samples[int(ana_idx):int(ana_idx) + frame_size]
            output[syn_idx:syn_idx + frame_size] += frame * window
            weights[syn_idx:syn_idx + frame_size] += window

            ana_idx += ana_hop
            syn_idx += hop_size

        # Avoid division by zero
        mask = weights > 1e-5
        output[mask] /= weights[mask]
        
        return output[:syn_idx]

    @staticmethod
    def soft_clip(x, threshold=0.90):
        """Apply a soft-knee clipping function in pure NumPy to prevent clipping."""
        abs_x = np.abs(x)
        out = np.copy(x)
        mask = abs_x > threshold
        if np.any(mask):
            scale = threshold + (1.0 - threshold) * np.tanh((abs_x[mask] - threshold) / (1.0 - threshold))
            out[mask] = np.sign(x[mask]) * scale
        return out

    @staticmethod
    def pitch_shift(samples, sr, semitones=0):
        """
        Shift pitch independently of playback speed.
        Uses librosa's phase-vocoder when available for high quality.
        Falls back to a simple resampling trick otherwise.
        """
        if semitones == 0:
            return samples

        if _LIBROSA_AVAILABLE:
            shifted = librosa.effects.pitch_shift(
                y=samples, sr=sr, n_steps=semitones)
            return shifted.astype(np.float32)

        # ── numpy fallback (OLA pitch shift) ─────────────────────────
        factor  = 2.0 ** (semitones / 12.0)
        try:
            stretched = AudioEffects._time_stretch_ola(samples, 1.0 / factor)
            old_indices = np.arange(len(stretched))
            new_length = len(samples)
            new_indices = np.linspace(0, len(stretched) - 1, new_length)
            return np.interp(new_indices, old_indices, stretched).astype(np.float32)
        except Exception as e:
            # Basic fallback
            indices = np.arange(0, len(samples), factor)
            indices = indices[indices < len(samples)].astype(int)
            return samples[indices]

    @staticmethod
    def estimate_pitch(samples, sr):
        """Estimate the average fundamental frequency (F0) of speech samples using autocorrelation."""
        n = len(samples)
        if n < sr:
            return 120.0  # Fallback if too short
        
        # Analyze a 1-second segment in the middle
        start = n // 2 - sr // 2
        chunk = samples[start:start + sr]
        chunk = chunk - np.mean(chunk)
        
        # Autocorrelation
        corr = np.correlate(chunk, chunk, mode='full')
        corr = corr[len(corr)//2:]
        
        # Human pitch range: 50 Hz to 400 Hz
        min_lag = int(sr / 400)
        max_lag = int(sr / 50)
        
        if max_lag >= len(corr):
            return 120.0
            
        search_area = corr[min_lag:max_lag]
        if len(search_area) == 0:
            return 120.0
            
        peak_lag = np.argmax(search_area) + min_lag
        
        if corr[peak_lag] < 0.05 * corr[0]:
            return 120.0  # Weak peak fallback
            
        return float(sr) / peak_lag

    @staticmethod
    def normalize(samples, target_db=-3.0):
        """Normalize audio to a target dB level and remove DC offset."""
        samples = samples - np.mean(samples)
        mx = np.max(np.abs(samples))
        if mx > 0:
            target_amp = 10 ** (target_db / 20.0)
            samples = samples * (target_amp / mx)
        return samples

    @staticmethod
    def reverb(samples, sr, decay=0.3, delay_ms=40):
        """Simple comb-filter reverb."""
        delay_samples = int(sr * delay_ms / 1000)
        output = samples.copy()
        for i in range(delay_samples, len(output)):
            output[i] += decay * output[i - delay_samples]
        mx = np.max(np.abs(output))
        if mx > 0:
            output = output / mx * 0.9
        return output

    # ──────────────────────────────────────────────────────────────
    #  BACKGROUND AMBIANCE MIXER
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def add_environment_sound(samples, sr, environment="Airplane Cabin", volume=0.5):
        """Mix synthesized or file-based background ambiance into the audio."""
        import os
        n = len(samples)
        t = np.arange(n, dtype=np.float32) / sr
        bg_track = np.zeros(n, dtype=np.float32)

        # ── Noise Helper: Pink Noise with Optional Low-pass Filter ──
        def generate_pink_noise(length, cutoff_hz=None):
            white = np.random.normal(0, 1, length).astype(np.float32)
            fft   = np.fft.rfft(white)
            freqs = np.fft.rfftfreq(length, 1.0 / sr)
            freqs[0] = 1.0  # avoid div by zero
            # Pink noise power drops 3dB per octave (1/f power, 1/sqrt(f) amplitude)
            fft /= np.sqrt(freqs)
            if cutoff_hz is not None:
                # 2nd-order Butterworth-like low-pass filter in frequency-domain
                response = 1.0 / np.sqrt(1.0 + (freqs / cutoff_hz) ** 4)
                fft *= response
            pink = np.fft.irfft(fft, length)
            return pink / (np.max(np.abs(pink)) + 1e-8)

        if environment == "Airplane Cabin":
            # Deep cabin air hum (low-passed pink noise at 200 Hz for muffled cabin air flow)
            air_flow = generate_pink_noise(n, cutoff_hz=200.0)
            
            # Deep engine rumble (low-passed pink noise at 70 Hz for heavy cabin vibration)
            engine_rumble = generate_pink_noise(n, cutoff_hz=70.0)
            
            # Subdued turbine engine hum (low frequency harmonics around 75 Hz, 150 Hz, 225 Hz)
            engine_hum = (np.sin(2 * np.pi * 75 * t) * 0.4 + 
                          np.sin(2 * np.pi * 150 * t) * 0.2 + 
                          np.sin(2 * np.pi * 225 * t) * 0.1)
            
            # Combine components to build a realistic airplane cabin atmosphere
            bg_track = engine_rumble * 0.55 + air_flow * 0.35 + engine_hum * 0.10

        elif environment == "Nature/Forest":
            # Pink noise wind + intermittent crickets
            pink = generate_pink_noise(n)
            # Higher freq crickets (resonant chirps)
            chirp_carrier = np.sin(2 * np.pi * 4200 * t)
            # 3Hz amplitude modulation with a bias to make it 'chirpy'
            chirp_mod = np.clip(np.sin(2 * np.pi * 3 * t) - 0.7, 0, 1) * 10
            crickets = chirp_carrier * chirp_mod
            bg_track = pink * 0.3 + crickets * 0.15

        elif os.path.exists(environment):
            try:
                bg_audio = AudioSegment.from_file(environment).set_channels(1).set_frame_rate(sr)
                bg_samples = np.array(bg_audio.get_array_of_samples(), dtype=np.float32) / (2 ** 15)
                if len(bg_samples) < n:
                    repeats = int(np.ceil(n / len(bg_samples)))
                    bg_samples = np.tile(bg_samples, repeats)
                bg_track = bg_samples[:n]
            except Exception as e:
                print(f"Error loading custom ambiance: {e}")
                return samples
        else:
            return samples

        # ── Final Mixing ──────────────────────────────────────────
        # Normalize bg_track first
        mx_bg = np.max(np.abs(bg_track))
        if mx_bg > 0:
            bg_track = bg_track / mx_bg
        
        # Scale by volume (allow it to be louder — up to 0.8 at max volume)
        scale = volume * 0.8
        bg_track *= scale

        # Apply auto-ducking to the ambiance track based on speech envelope
        window_size = int(sr * 0.15)  # 150ms window
        if window_size > 0 and len(samples) > window_size:
            try:
                speech_abs = np.abs(samples)
                kernel = np.ones(window_size, dtype=np.float32) / window_size
                speech_env = np.convolve(speech_abs, kernel, mode='same')
                mx_env = np.max(speech_env)
                if mx_env > 0:
                    speech_env /= mx_env
                duck_depth = 0.50
                ducking_gain = 1.0 - (duck_depth * speech_env)
                bg_track *= ducking_gain
            except Exception as e:
                print(f"Ducking failed: {e}")

        # Mix with samples
        mix = samples + bg_track
        
        # Soft-clip instead of hard division to maintain speech presence and prevent distortion
        return AudioEffects.soft_clip(mix, threshold=0.90)

    @staticmethod
    def three_band_eq(samples, sr, low_gain=1.0, mid_gain=1.0, high_gain=1.0):
        """
        3-Band Graphic Equalizer using frequency-domain partitioning.
        low_gain, mid_gain, high_gain are linear factors (e.g. 1.0 = 0dB).
        """
        n = len(samples)
        if n == 0:
            return samples
            
        # Compute real FFT
        fft_signal = np.fft.rfft(samples)
        freqs = np.fft.rfftfreq(n, 1.0 / sr)
        
        # Define band limits
        # Bass: 0 - 250 Hz
        # Mids: 250 - 4000 Hz
        # Treble: 4000 Hz+
        low_mask = freqs < 250.0
        mid_mask = (freqs >= 250.0) & (freqs < 4000.0)
        high_mask = freqs >= 4000.0
        
        # Apply scaling factors
        fft_signal[low_mask]  *= low_gain
        fft_signal[mid_mask]  *= mid_gain
        fft_signal[high_mask] *= high_gain
        
        # Inverse FFT
        equalized = np.fft.irfft(fft_signal, n)
        
        # Normalize/clip output safely
        mx = np.max(np.abs(equalized))
        if mx > 1.0:
            equalized = equalized / mx * 0.95
            
        return equalized.astype(np.float32)

    # ──────────────────────────────────────────────────────────────
    #  EFFECTS
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def vocoder(samples, sr, num_bands=20, carrier_base_freq=100):
        """Channel vocoder — robotic monotone voice."""
        n = len(samples)
        t = np.arange(n, dtype=np.float32) / sr
        carrier = np.zeros(n, dtype=np.float32)
        for harmonic in range(1, 15):
            freq = carrier_base_freq * harmonic
            carrier += (1.0 / harmonic) * np.sin(2 * np.pi * freq * t)
        carrier = carrier / np.max(np.abs(carrier) + 1e-8)

        output = np.zeros(n, dtype=np.float32)
        fft_signal = np.fft.rfft(samples)
        fft_carrier = np.fft.rfft(carrier)
        freqs = np.fft.rfftfreq(n, 1.0 / sr)
        band_edges = np.logspace(np.log10(80), np.log10(min(sr / 2 - 1, 8000)), num_bands + 1)

        for i in range(num_bands):
            lo, hi = band_edges[i], band_edges[i + 1]
            mask = (freqs >= lo) & (freqs < hi)
            band_signal = np.zeros_like(fft_signal)
            band_signal[mask] = fft_signal[mask]
            env_signal = np.abs(np.fft.irfft(band_signal, n))
            window_size = max(int(sr * 0.01), 1)
            kernel = np.ones(window_size) / window_size
            env_smooth = np.convolve(env_signal, kernel, mode='same')
            band_carrier = np.zeros_like(fft_carrier)
            band_carrier[mask] = fft_carrier[mask]
            carrier_band = np.fft.irfft(band_carrier, n)
            output += env_smooth * carrier_band

        mx = np.max(np.abs(output))
        if mx > 0:
            output = output / mx * 0.9
        return output

    @staticmethod
    def glitch(samples, sr, chunk_ms=30, repeat_prob=0.15, max_repeats=4):
        """Glitch — randomly repeats small audio chunks."""
        chunk_size = int(sr * chunk_ms / 1000)
        output = []
        i = 0
        while i < len(samples):
            chunk = samples[i:i + chunk_size]
            output.append(chunk)
            if random.random() < repeat_prob:
                repeats = random.randint(1, max_repeats)
                for _ in range(repeats):
                    output.append(chunk)
            i += chunk_size
        return np.concatenate(output).astype(np.float32)

    @staticmethod
    def ring_modulator(samples, sr, freq=30.0, mix=0.7):
        """Ring modulation — Dalek-like choppy effect."""
        t = np.arange(len(samples), dtype=np.float32) / sr
        modulator = np.sin(2 * np.pi * freq * t)
        modulated = samples * modulator
        return ((1 - mix) * samples + mix * modulated).astype(np.float32)

    @staticmethod
    def pilot_radio(samples, sr):
        """Airline pilot intercom — bandpass 300–3000 Hz + soft clip."""
        n = len(samples)
        fft_signal = np.fft.rfft(samples)
        freqs = np.fft.rfftfreq(n, 1.0 / sr)
        mask = (freqs >= 300) & (freqs <= 3000)
        filtered = np.fft.irfft(fft_signal * mask, n)
        clipped = np.clip(filtered, -0.5, 0.5)
        mx = np.max(np.abs(clipped))
        if mx > 0:
            clipped = clipped / mx * 0.95
        return clipped.astype(np.float32)

    @staticmethod
    def telephone(samples, sr):
        """Vintage telephone — 300–3400 Hz + carbon mic saturation + line hum."""
        n = len(samples)
        t = np.arange(n, dtype=np.float32) / sr
        samples = np.tanh(samples * 2.5)
        fft_signal = np.fft.rfft(samples)
        freqs = np.fft.rfftfreq(n, 1.0 / sr)
        mask = (freqs >= 300) & (freqs <= 3400)
        fft_signal = fft_signal * mask
        nasal_mask = (freqs >= 1000) & (freqs <= 2500)
        fft_signal[nasal_mask] *= 1.5
        samples = np.fft.irfft(fft_signal, n)
        samples += np.sin(2 * np.pi * 60 * t) * 0.003
        samples += np.random.normal(0, 0.005, n).astype(np.float32)
        samples = np.clip(samples, -0.6, 0.6)
        mx = np.max(np.abs(samples))
        if mx > 0:
            samples = samples / mx * 0.85
        return samples.astype(np.float32)

    @staticmethod
    def hyperpop(samples, sr):
        """Fast, high-pitched, glitchy pop sound."""
        fast = AudioEffects.change_speed(samples, 1.4)
        return np.clip(fast * 1.5, -1.0, 1.0)

    @staticmethod
    def melancholic(samples, sr):
        """Slow, intimate, slightly muffled sound."""
        slow = AudioEffects.change_speed(samples, 0.85)
        window = np.ones(5) / 5
        muffled = np.convolve(slow, window, mode='same')
        return (muffled * 0.85).astype(np.float32)

    @staticmethod
    def natgeo_narrator(samples, sr):
        """Deep, resonant, broadcast-quality compression."""
        samples = AudioEffects.change_speed(samples, 0.95)
        n = len(samples)
        fft_signal = np.fft.rfft(samples)
        freqs = np.fft.rfftfreq(n, 1.0 / sr)
        
        # Broadcast style EQ
        # High pass below 50 Hz to cut sub-bass mud
        fft_signal[freqs < 50] *= 0.0
        # Boost low-mid chest voice (80-160 Hz) for deep narration warmth
        fft_signal[(freqs >= 80) & (freqs <= 160)] *= 1.75
        # Boost presence (3.5k-7k Hz) for speech clarity and articulation
        fft_signal[(freqs >= 3500) & (freqs <= 7000)] *= 1.35
        samples = np.fft.irfft(fft_signal, n)
        
        # Smooth radio compression
        threshold, ratio = 0.35, 0.45
        abs_s = np.abs(samples)
        compressed = np.where(abs_s > threshold,
                              threshold + (abs_s - threshold) * ratio, abs_s)
        samples = np.sign(samples) * compressed
        
        return np.clip(samples * 1.25, -1.0, 1.0).astype(np.float32)

    @staticmethod
    def seductive(samples, sr, gender="male"):
        """Sensual, subdued tone with downward inflection and breathiness."""
        samples = AudioEffects.change_speed(samples, 0.88)
        n = len(samples)
        t = np.arange(n, dtype=np.float32) / sr
        
        # Dynamic pitch shifting to target exactly 96 Hz (male) or 280 Hz (female)
        try:
            f0 = AudioEffects.estimate_pitch(samples, sr)
            target_hz = 96.0 if gender == "male" else 280.0
            semitones = 12.0 * math.log2(target_hz / f0)
            # Limit shift to avoid sounding too artificial
            semitones = max(-7.0, min(7.0, semitones))
        except Exception:
            semitones = -2.0 if gender == "male" else 5.0
            
        samples = AudioEffects.pitch_shift(samples, sr, semitones=semitones)
        
        # Downward pitch inflection (seductive speech trailing off)
        warp = np.ones(n, dtype=np.float32)
        end_start = int(n * 0.8)
        if n > end_start:
            warp[end_start:] = np.linspace(1.0, 1.15, n - end_start)
            indices = np.cumsum(1.0 / warp)
            indices = (indices / indices[-1] * (n - 1)).astype(np.float32)
            samples = np.interp(indices, np.arange(n), samples).astype(np.float32)
            
        # Add intimate high-frequency breath noise
        noise = np.random.normal(0, 0.02, n).astype(np.float32)
        breathe = noise - np.roll(noise, 1)  # simple LPF high-pass filter
        samples += breathe * 0.12
        
        # Add vocal fry sub-harmonic pulses
        fry_pulses = (np.sin(2 * np.pi * 40 * t) > 0.98).astype(np.float32)
        samples += fry_pulses * 0.025 * np.abs(samples)
        
        # Smooth low-pass filter to muffle sharp high sounds
        window = np.ones(5) / 5
        return np.convolve(samples, window, mode='same').astype(np.float32)

    @staticmethod
    def saas_flash(samples, sr):
        """SaaS Flash — punchy, ultra-crisp marketing voice for social shorts."""
        samples = AudioEffects.change_speed(samples, 1.18)
        samples = AudioEffects.pitch_shift(samples, sr, semitones=-0.5)
        n = len(samples)
        fft_signal = np.fft.rfft(samples)
        freqs = np.fft.rfftfreq(n, 1.0 / sr)
        
        # High pass below 110 Hz to fit small mobile phone speakers
        fft_signal[freqs < 110] *= 0.0
        # Boost presence (2000 - 5000 Hz) for maximum text articulation
        fft_signal[(freqs >= 2000) & (freqs <= 5000)] *= 1.6
        # Scoop low mids (300 - 600 Hz) to clear boxy frequencies
        fft_signal[(freqs >= 300) & (freqs <= 600)] *= 0.8
        # Add sizzle (8k Hz+)
        fft_signal[freqs > 8000] *= 1.3
        samples = np.fft.irfft(fft_signal, n)
        
        # Tight, heavy compression
        threshold, ratio = 0.15, 0.25
        abs_s = np.abs(samples)
        compressed = np.where(abs_s > threshold,
                              threshold + (abs_s - threshold) * ratio, abs_s)
        samples = np.sign(samples) * compressed * 1.55
        return np.tanh(samples * 1.15).astype(np.float32)

    @staticmethod
    def cinematic(samples, sr):
        """Cinematic — intimate, breathy, ASMR-style trailer voice."""
        samples = AudioEffects.change_speed(samples, 0.88)
        samples = AudioEffects.pitch_shift(samples, sr, semitones=-2.0)
        n = len(samples)
        fft_signal = np.fft.rfft(samples)
        freqs = np.fft.rfftfreq(n, 1.0 / sr)
        
        # Massive low end (50 - 120 Hz)
        fft_signal[(freqs >= 50) & (freqs <= 120)] *= 2.1
        # Scoop out boxy mids (350 - 750 Hz)
        fft_signal[(freqs >= 350) & (freqs <= 750)] *= 0.72
        # Airy highs boost (6.5k - 13k Hz) for breathy ASMR trailer whisper
        fft_signal[(freqs >= 6500) & (freqs <= 13000)] *= 1.95
        samples = np.fft.irfft(fft_signal, n)
        
        # Compression
        threshold, ratio = 0.12, 0.22
        abs_s = np.abs(samples)
        compressed = np.where(abs_s > threshold,
                              threshold + (abs_s - threshold) * ratio, abs_s)
        samples = np.sign(samples) * compressed * 1.75
        samples = np.tanh(samples * 0.95)
        
        # Deeper reverb decay for space
        return AudioEffects.reverb(samples, sr, decay=0.32, delay_ms=50).astype(np.float32)

    @staticmethod
    def arjun(samples, sr):
        """Arjun (Tech Reviewer) — energetic, crisp, YouTube-style voice."""
        samples = AudioEffects.change_speed(samples, 1.12)
        samples = AudioEffects.pitch_shift(samples, sr, semitones=1.0)
        n = len(samples)
        fft_signal = np.fft.rfft(samples)
        freqs = np.fft.rfftfreq(n, 1.0 / sr)
        
        # High pass at 85 Hz to remove desk hum/room tone
        fft_signal[freqs < 85] *= 0.0
        # Boost key vocal presence range (2.5k - 5.5k Hz) for YouTuber style punch
        fft_signal[(freqs >= 2500) & (freqs <= 5500)] *= 1.55
        # Muffled mids cut (300 - 500 Hz)
        fft_signal[(freqs >= 300) & (freqs <= 500)] *= 0.85
        samples = np.fft.irfft(fft_signal, n)
        
        # YouTuber limiting/compression
        threshold, ratio = 0.22, 0.38
        abs_s = np.abs(samples)
        compressed = np.where(abs_s > threshold,
                              threshold + (abs_s - threshold) * ratio, abs_s)
        samples = np.sign(samples) * compressed * 1.35
        return np.clip(samples, -1.0, 1.0).astype(np.float32)

    @staticmethod
    def dramatic_ads(samples, sr):
        """Dramatic Ads — deep, authoritative movie-trailer / commercial voice."""
        samples = AudioEffects.change_speed(samples, 0.92)
        samples = AudioEffects.pitch_shift(samples, sr, semitones=-2.5)
        n = len(samples)
        fft_signal = np.fft.rfft(samples)
        freqs = np.fft.rfftfreq(n, 1.0 / sr)
        
        # High pass at 60 Hz
        fft_signal[freqs < 60] *= 0.0
        # Boost chest resonance low-mids (90 - 160 Hz)
        fft_signal[(freqs >= 90) & (freqs <= 160)] *= 1.95
        # Scoop boxy mids
        fft_signal[(freqs >= 400) & (freqs <= 800)] *= 0.8
        # Boost commercial sizzle (4.5k - 9k Hz)
        fft_signal[(freqs >= 4500) & (freqs <= 9000)] *= 1.65
        samples = np.fft.irfft(fft_signal, n)
        
        # Heavy brickwall compression
        threshold, ratio = 0.12, 0.32
        abs_s = np.abs(samples)
        compressed = np.where(abs_s > threshold,
                              threshold + (abs_s - threshold) * ratio, abs_s)
        samples = np.sign(samples) * compressed * 1.65
        return np.tanh(samples * 0.95).astype(np.float32)

    @staticmethod
    def techy(samples, sr):
        """Techy — articulate, proximity-warm voice for code/tech explanations."""
        samples = AudioEffects.change_speed(samples, 1.08)
        samples = AudioEffects.pitch_shift(samples, sr, semitones=-1.0)
        n = len(samples)
        fft_signal = np.fft.rfft(samples)
        freqs = np.fft.rfftfreq(n, 1.0 / sr)
        
        # Clean desk rumble
        fft_signal[freqs < 90] *= 0.0
        # Proximity warm mic effect (140 - 240 Hz)
        fft_signal[(freqs >= 140) & (freqs <= 240)] *= 1.45
        # Scoop low mids
        fft_signal[(freqs >= 350) & (freqs <= 650)] *= 0.82
        # Articulation boost (3k - 6k Hz)
        fft_signal[(freqs >= 3000) & (freqs <= 6000)] *= 1.5
        samples = np.fft.irfft(fft_signal, n)
        
        # Soft compressor
        threshold, ratio = 0.2, 0.42
        abs_s = np.abs(samples)
        compressed = np.where(abs_s > threshold,
                              threshold + (abs_s - threshold) * ratio, abs_s)
        samples = np.sign(samples) * compressed * 1.45
        return np.tanh(samples).astype(np.float32)
