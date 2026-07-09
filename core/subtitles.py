import os
import gc
import torch
from faster_whisper import WhisperModel

# Global model instance to avoid reloading if not necessary, but we can clean it up
_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        # Load the base model, optimize for 4GB VRAM
        _whisper_model = WhisperModel(
            model_size_or_path="base", 
            device="cuda" if torch.cuda.is_available() else "cpu", 
            compute_type="float16" if torch.cuda.is_available() else "int8"
        )
    return _whisper_model

def unload_whisper_model():
    global _whisper_model
    if _whisper_model is not None:
        del _whisper_model
        _whisper_model = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{msecs:03d}"

def group_words_into_phrases(words, max_chars=40, max_duration=3.0, max_gap=0.5):
    """
    Groups a list of faster-whisper word objects into phrases/sentences.
    Each word object has: word (str), start (float), end (float).
    """
    if not words:
        return []
        
    phrases = []
    current_words = []
    current_start = None
    
    for word_obj in words:
        word_text = word_obj.word
        word_start = word_obj.start
        word_end = word_obj.end
        
        word_clean = word_text.strip()
        if not word_clean:
            continue
            
        if current_start is None:
            current_start = word_start
            
        should_split = False
        
        if current_words:
            last_word_obj = current_words[-1]
            last_word_clean = last_word_obj["word"]
            
            # 1. Punctuation split
            if last_word_clean and last_word_clean[-1] in ('.', '?', '!'):
                should_split = True
            # 2. Significant pause split
            elif word_start - last_word_obj["end"] > max_gap:
                should_split = True
            else:
                current_text = " ".join([w["word"] for w in current_words]) + " " + word_clean
                # 3. Character limit split
                if len(current_text) > max_chars:
                    should_split = True
                # 4. Duration split
                elif word_end - current_start > max_duration:
                    should_split = True
                    
        if should_split and current_words:
            phrases.append({
                "start": current_start,
                "end": current_words[-1]["end"],
                "text": " ".join([w["word"] for w in current_words])
            })
            current_words = []
            current_start = word_start
            
        current_words.append({
            "word": word_clean,
            "start": word_start,
            "end": word_end
        })
        
    if current_words:
        phrases.append({
            "start": current_start,
            "end": current_words[-1]["end"],
            "text": " ".join([w["word"] for w in current_words])
        })
        
    return phrases

def generate_subtitles(audio_path: str, output_srt_path: str, status_cb=None, segmentation="word"):
    """
    Generate subtitles using faster-whisper.
    segmentation: "word" for word-level, "sentence" for sentence/phrase-level.
    """
    if status_cb:
        status_cb("Loading transcription model...")
        
    model = get_whisper_model()
    
    if status_cb:
        status_cb("Generating subtitles...")
        
    segments, info = model.transcribe(audio_path, word_timestamps=True)
    
    # Collect all words from segments
    all_words = []
    for segment in segments:
        if segment.words:
            all_words.extend(segment.words)
            
    with open(output_srt_path, "w", encoding="utf-8") as f:
        if segmentation == "sentence" or segmentation == "phrase":
            phrases = group_words_into_phrases(all_words)
            for srt_index, phrase in enumerate(phrases, 1):
                start_str = format_timestamp(phrase["start"])
                end_str = format_timestamp(phrase["end"])
                f.write(f"{srt_index}\n")
                f.write(f"{start_str} --> {end_str}\n")
                f.write(f"{phrase['text']}\n\n")
        else:
            srt_index = 1
            for word in all_words:
                start_str = format_timestamp(word.start)
                end_str = format_timestamp(word.end)
                f.write(f"{srt_index}\n")
                f.write(f"{start_str} --> {end_str}\n")
                f.write(f"{word.word.strip()}\n\n")
                srt_index += 1

    unload_whisper_model()
    
    if status_cb:
        status_cb("Subtitles generated successfully.")
