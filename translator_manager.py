"""
translator_manager.py
Core translation engine using deep-translator + langdetect.
Supports EN↔UZ auto-detection and all other language pairs.
"""
from __future__ import annotations

from typing import Optional, TypedDict

try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

try:
    from deep_translator import GoogleTranslator
    DEEP_TRANSLATOR_AVAILABLE = True
except ImportError:
    DEEP_TRANSLATOR_AVAILABLE = False


# Supported language display names → deep-translator language codes
SUPPORTED_LANGUAGES: dict[str, str] = {
    "🇺🇿 O'zbekcha": "uz",
    "🇬🇧 Inglizcha": "en",
    "🇷🇺 Ruscha": "ru",
    "🇩🇪 Nemischa": "de",
    "🇫🇷 Fransuzcha": "fr",
    "🇸🇦 Arabcha": "ar",
    "🇹🇷 Turkcha": "tr",
    "🇨🇳 Xitoycha": "zh-CN",
    "🇯🇵 Yaponcha": "ja",
    "🇰🇷 Koreyscha": "ko",
    "🇪🇸 Ispancha": "es",
    "🇮🇳 Hindcha": "hi",
    "🇮🇹 Italyancha": "it",
    "🇵🇹 Portugalcha": "pt",
}

# Language codes that are primarily used in EN↔UZ auto mode
UZBEK_CODE = "uz"
ENGLISH_CODE = "en"


class TranslatorManager:
    """
    Provides language detection and translation services.
    Primary use case: auto-detect between English and Uzbek.
    Also supports any target language for 'Other Languages' mode.
    """

    def detect_language(self, text: str) -> Optional[str]:
        """Return ISO language code (e.g. 'en', 'uz', 'ru') or None on failure."""
        if not LANGDETECT_AVAILABLE:
            return None
        try:
            return detect(text)
        except Exception:
            return None

    def translate(self, text: str, source: str = "auto", target: str = "uz") -> str:
        """
        Translate *text* from *source* to *target*.
        *source* can be 'auto' to let Google detect.
        Returns translated string or an error message.
        """
        if not DEEP_TRANSLATOR_AVAILABLE:
            return "❌ deep-translator kutubxonasi o'rnatilmagan."
        if not text or not text.strip():
            return "❌ Bo'sh matn tarjima qilinmaydi."
        try:
            translator = GoogleTranslator(source=source, target=target)
            result = translator.translate(text.strip())
            return result or "❌ Tarjima topilmadi."
        except Exception as e:
            return f"❌ Tarjima xatoligi: {e}"

    def auto_translate_en_uz(self, text: str) -> str:
        """
        Auto-detect language and translate:
        - If detected English → Uzbek
        - If detected Uzbek (or anything else) → English
        Returns a formatted result string.
        """
        detected = self.detect_language(text)

        if detected == ENGLISH_CODE:
            result = self.translate(text, source="en", target="uz")
            flag = "🇬🇧→🇺🇿"
            lang_label = "Inglizcha → O'zbekcha"
        else:
            result = self.translate(text, source="auto", target="en")
            flag = "🇺🇿→🇬🇧"
            lang_label = "O'zbekcha → Inglizcha"

        return (
            f"{flag} *{lang_label}*\n\n"
            f"📝 *Asl:* {text}\n"
            f"✅ *Tarjima:* {result}"
        )

    def auto_translate_en_uz_raw(self, text: str) -> dict[str, Optional[str]]:
        """Return raw translation details for EN↔UZ auto mode."""
        detected = self.detect_language(text) or "auto"
        if detected == ENGLISH_CODE:
            target = UZBEK_CODE
            translated = self.translate(text, source="en", target=target)
        else:
            target = ENGLISH_CODE
            translated = self.translate(text, source="auto", target=target)
        return {
            "detected": detected,
            "target": target,
            "translated": translated,
        }

    def translate_to_language(self, text: str, target_lang_code: str) -> str:
        """Translate text to a specific target language (auto-detect source)."""
        result = self.translate(text, source="auto", target=target_lang_code)
        # Find display name for target lang
        display = next(
            (name for name, code in SUPPORTED_LANGUAGES.items() if code == target_lang_code),
            target_lang_code,
        )
        return (
            f"🌐 *Tarjima ({display})*\n\n"
            f"📝 *Asl:* {text}\n"
            f"✅ *Tarjima:* {result}"
        )
