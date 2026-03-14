"""
voice_translator.py
Transcribe Telegram voice messages and translate them.

Dependencies:
  - vosk (offline speech-to-text)
  - pydub (for audio conversion; requires ffmpeg installed)
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Optional, Tuple


def _convert_to_wav_mono_16k(input_path: str, output_path: str) -> bool:
    """Convert audio to 16kHz mono WAV suitable for Vosk (requires ffmpeg via pydub)."""
    try:
        from pydub import AudioSegment  # type: ignore

        ffmpeg_bin = os.getenv("FFMPEG_BINARY")
        ffprobe_bin = os.getenv("FFPROBE_BINARY")
        if ffmpeg_bin:
            AudioSegment.converter = ffmpeg_bin
        if ffprobe_bin:
            AudioSegment.ffprobe = ffprobe_bin

        audio = AudioSegment.from_file(input_path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(output_path, format="wav")
        return True
    except Exception:
        return False


def _load_vosk_model(model_dir: str):
    try:
        from vosk import Model  # type: ignore

        if not model_dir or not os.path.isdir(model_dir):
            return None
        return Model(model_dir)
    except Exception:
        return None


def _vosk_transcribe_wav(wav_path: str, model_dir: str) -> Optional[str]:
    """Transcribe a WAV file using Vosk model at model_dir."""
    try:
        import wave
        from vosk import KaldiRecognizer  # type: ignore

        model = _load_vosk_model(model_dir)
        if model is None:
            return None

        with wave.open(wav_path, "rb") as wf:
            if wf.getnchannels() != 1 or wf.getframerate() != 16000:
                return None
            rec = KaldiRecognizer(model, wf.getframerate())
            rec.SetWords(True)
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                rec.AcceptWaveform(data)
            final = json.loads(rec.FinalResult())
            text = (final.get("text") or "").strip()
            return text or None
    except Exception:
        return None


def _transcribe_auto_vosk(wav_path: str) -> Tuple[str, Optional[str], bool]:
    """Try Uzbek and English Vosk models and pick the best result."""
    uz_dir = os.getenv("VOSK_MODEL_UZ", "")
    en_dir = os.getenv("VOSK_MODEL_EN", "")

    uz_text = _vosk_transcribe_wav(wav_path, uz_dir) if uz_dir else None
    en_text = _vosk_transcribe_wav(wav_path, en_dir) if en_dir else None

    def _score(t: Optional[str]) -> int:
        if not t:
            return 0
        return len(t.strip())

    if _score(uz_text) >= _score(en_text) and uz_text:
        return uz_text, "uz", True
    if en_text:
        return en_text, "en", True

    return (
        "❌ Audio transkripsiya qilishda xatolik yuz berdi.\n"
        "Vosk modellari topilmadi yoki ishlamadi.\n\n"
        "Iltimos, muhit o'zgaruvchilarini o'rnating:\n"
        "- VOSK_MODEL_UZ: Uzbek model papkasi\n"
        "- VOSK_MODEL_EN: English model papkasi\n"
        "va `ffmpeg` o'rnatilganligini tekshiring.",
        None,
        False,
    )


def transcribe_audio(audio_bytes: bytes, original_ext: str = ".ogg") -> Tuple[str, bool]:
    """
    Transcribe audio bytes to text.

    Returns:
        (transcribed_text_or_error, success: bool)
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Save original audio
        orig_path = os.path.join(tmp_dir, f"voice{original_ext}")
        with open(orig_path, "wb") as f:
            f.write(audio_bytes)

        wav_path = os.path.join(tmp_dir, "voice.wav")
        converted = _convert_to_wav_mono_16k(orig_path, wav_path)
        if not converted:
            return (
                "❌ Audio WAV formatga o'tkazilmadi.\n"
                "Iltimos, `ffmpeg` o'rnatilganligini tekshiring.\n"
                "Agar o'rnatilgan bo'lsa ham topilmasa, muhit o'zgaruvchilarini bering:\n"
                "- FFMPEG_BINARY: ffmpeg.exe to'liq yo'li\n"
                "- FFPROBE_BINARY: ffprobe.exe to'liq yo'li",
                False,
            )

        text, _lang, ok = _transcribe_auto_vosk(wav_path)
        return text, ok


def transcribe_audio_with_language(audio_bytes: bytes, original_ext: str = ".ogg") -> Tuple[str, Optional[str], bool]:
    """Like transcribe_audio, but also returns detected language code when available."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        orig_path = os.path.join(tmp_dir, f"voice{original_ext}")
        with open(orig_path, "wb") as f:
            f.write(audio_bytes)

        wav_path = os.path.join(tmp_dir, "voice.wav")
        converted = _convert_to_wav_mono_16k(orig_path, wav_path)
        if not converted:
            return (
                "❌ Audio WAV formatga o'tkazilmadi.\n"
                "Iltimos, `ffmpeg` o'rnatilganligini tekshiring.\n"
                "Agar o'rnatilgan bo'lsa ham topilmasa, muhit o'zgaruvchilarini bering:\n"
                "- FFMPEG_BINARY: ffmpeg.exe to'liq yo'li\n"
                "- FFPROBE_BINARY: ffprobe.exe to'liq yo'li",
                None,
                False,
            )

        text, lang, ok = _transcribe_auto_vosk(wav_path)
        return text, lang, ok


def tts_mp3_bytes(text: str, lang: str) -> Tuple[bytes, bool]:
    """Generate MP3 bytes with gTTS. lang should be 'uz' or 'en'."""
    if not text or not text.strip():
        return b"", False
    try:
        from gtts import gTTS  # type: ignore
        import io

        buf = io.BytesIO()
        tts = gTTS(text=text.strip(), lang=lang)
        tts.write_to_fp(buf)
        return buf.getvalue(), True
    except Exception:
        return b"", False
