"""
effects/registry.py
────────────────────
Master registry of every voice effect available in VoiceCraft.

To add a new effect:
  1. Add the DSP method to effects/audio_effects.py.
  2. Add an entry to EFFECTS_REGISTRY below.
  3. Done — the UI panel reads this list automatically.

Registry entry keys:
  key       – unique internal identifier (must match the BooleanVar attribute
               name suffix used in the app: self._fx_<key>)
  label     – display label shown in the UI toggle card
  desc      – short description shown below the toggle
  fn        – the callable (AudioEffects static method)
  kwargs    – extra keyword arguments passed to fn (optional)
"""

from effects.audio_effects import AudioEffects

EFFECTS_REGISTRY = [
    # Shown first in the UI. Processing order is unaffected: the pipeline
    # (ui/app.py) skips "normalize" in the effects loop and always applies
    # it as the final pass after ambiance mixing.
    {
        "key":    "normalize",
        "label":  "🔊  Normalize",
        "desc":   "Consistent volume levels",
        "fn":     AudioEffects.normalize,
        "default": True,      # pre-checked in the UI
    },
    {
        "key":    "vocoder",
        "label":  "🤖  Vocoder",
        "desc":   "Robotic monotone voice",
        "fn":     AudioEffects.vocoder,
    },
    {
        "key":    "glitch",
        "label":  "🔀  Glitch",
        "desc":   "Random audio chunk repeats",
        "fn":     AudioEffects.glitch,
    },
    {
        "key":    "ringmod",
        "label":  "📡  Ring Mod",
        "desc":   "Dalek-like choppy effect",
        "fn":     AudioEffects.ring_modulator,
    },
    {
        "key":    "reverb",
        "label":  "🌊  Reverb",
        "desc":   "Echoing spacious sound",
        "fn":     AudioEffects.reverb,
    },
    {
        "key":    "pitch",
        "label":  "🎵  Pitch Shift",
        "desc":   "Shift pitch up (+3 semitones)",
        "fn":     AudioEffects.pitch_shift,
        "kwargs": {"semitones": 3},
    },
    {
        "key":    "pilot",
        "label":  "✈️  Pilot",
        "desc":   "Airplane intercom voice",
        "fn":     AudioEffects.pilot_radio,
    },
    {
        "key":    "hyperpop",
        "label":  "🎶  Hyperpop",
        "desc":   "Fast glitchy pop sound",
        "fn":     AudioEffects.hyperpop,
    },
    {
        "key":    "melancholic",
        "label":  "🌧️  Melancholic",
        "desc":   "Slow intimate muffled",
        "fn":     AudioEffects.melancholic,
    },
    {
        "key":    "natgeo",
        "label":  "🎥  NatGeo",
        "desc":   "Deep, prestigious documentary narrator voice (MKH 416 warmth)",
        "fn":     AudioEffects.natgeo_narrator,
    },
    {
        "key":    "seductive_m",
        "label":  "🍷  Seductive (M)",
        "desc":   "Intimate, deep velvety masculine voice (close-mic warmth & zero phase distortion)",
        "fn":     AudioEffects.seductive_male,
    },
    {
        "key":    "seductive_f",
        "label":  "💋  Seductive (F)",
        "desc":   "Intimate, warm sensual female voice (close-mic breathiness & zero phase distortion)",
        "fn":     AudioEffects.seductive_female,
    },
    {
        "key":    "saas_flash",
        "label":  "⚡  SaaS Flash",
        "desc":   "Snappy 195 WPM breathless marketing voice",
        "fn":     AudioEffects.saas_flash,
    },
    {
        "key":    "cinematic",
        "label":  "🎬  Cinematic",
        "desc":   "Soft, soothing & warm intimate voiceover (TLM 103 condenser)",
        "fn":     AudioEffects.cinematic,
    },
    {
        "key":    "arjun",
        "label":  "🏹  Arjun",
        "desc":   "Warm & crisp YouTube reviewer (SM7B broadcast tone)",
        "fn":     AudioEffects.arjun,
    },
    {
        "key":    "dramatic_ads",
        "label":  "📢  Dramatic Ads",
        "desc":   "Authoritative & punchy commercial broadcast voice (SM7B exciter)",
        "fn":     AudioEffects.dramatic_ads,
    },
    {
        "key":    "techy",
        "label":  "💻  Techy",
        "desc":   "Deep, calm & articulate developer tutorial voice (clean SM7B)",
        "fn":     AudioEffects.techy,
    },
    {
        "key":    "telephone",
        "label":  "☎️  Telephone",
        "desc":   "Vintage 3.4kHz limited line voice",
        "fn":     AudioEffects.telephone,
    },
]
