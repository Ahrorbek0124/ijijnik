from __future__ import annotations

from typing import Dict, List, Optional

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram import InputFile
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from dictionary_manager import DictionaryManager
from tense_manager import TenseManager, TenseInfo
from translator_manager import TranslatorManager, SUPPORTED_LANGUAGES
from history_manager import HistoryManager


class EnglishBotLogic:
    def __init__(self) -> None:
        self.dictionary_manager = DictionaryManager()
        self.tense_manager = TenseManager()
        self.translator = TranslatorManager()
        self.history_manager = HistoryManager()

        self.user_state: Dict[int, str] = {}
        self.user_section: Dict[int, int] = {}
        self.user_subsection: Dict[int, int] = {}
        self.user_tense: Dict[int, str] = {}
        # For "Other Languages" mode: stores the chosen target lang code
        self.user_target_lang: Dict[int, str] = {}

    # ─────────────────────────────── Command handlers ────────────────────────────

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        self.user_state[chat_id] = "main"
        await update.message.reply_text(
            "Ingliz tili zamonlarini o'rganish botiga xush kelibsiz!\n\n"
            "Quyidagi menyudan birini tanlang:",
            reply_markup=self._get_main_menu(),
        )

    async def handle_about(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = (
            "‼️ Assolomu alaykum👋 ‼️\n"
            "Siz bu yerda ingiliz tilini mukammal o'rganishingiz mumkin❗\n"
            "Agar muommolar bo'lsa bizning Adminimiz --> @Mr_Risk ga murojat qiling❗\n"
            "Hello 👋\n"
            "You can learn English perfectly here❗\n"
            "If you have any problems, please contact our Admin --> ⌂@Mr_Risk❗"
        )
        await update.message.reply_text(text, reply_markup=self._get_main_menu())

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = (
            "📚 *Zamonlar*\n"
            "Ingliz tili grammatik zamonlari menyusini ochadi.\n\n"
            "🌐 *Tarjimon*\n"
            "Kuchli tarjima xizmatlari:\n"
            "  📝 Matn tarjimasi – Ingliz/O'zbek matnini tarjima qiladi\n"
            "  🎤 Ovozdan tarjima – Ovozli xabarni transkripsiya qilib tarjima qiladi\n"
            "  📁 Fayl tarjimasi – TXT, DOCX, PDF fayllarni tarjima qiladi\n"
            "  📷 Rasm tarjimasi – Rasmdagi matnni OCR orqali o'qib tarjima qiladi\n"
            "  📜 Tarix – So'nggi tarjimalaringizni ko'rsatadi\n"
            "  🌍 Boshqa tillar – Istalgan tilga tarjima qiladi\n\n"
            "⬅️ *Ortga* – Avvalgi menyuga qaytadi\n"
            "🏠 *Bosh menyu* – Asosiy menyuga qaytadi\n\n"
            "/start – Asosiy menyuni ochadi\n"
            "/about – Bot haqida ma'lumot\n"
            "/help – Funksiyalar haqida yordam"
        )
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=self._get_main_menu())

    # ─────────────────────────────── Text handler ────────────────────────────────

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return

        chat_id = update.effective_chat.id
        text = update.message.text
        current_state = self.user_state.get(chat_id, "main")

        # ── Global navigation ────────────────────────────────────────
        if text == "🏠 Bosh menyu":
            await self._handle_main_menu(update)
        elif text == "⬅️ Ortga":
            await self._handle_back(update, chat_id)

        # ── Main menu ────────────────────────────────────────────────
        elif text == "📚 Zamonlar":
            await self._handle_tenses_menu(update)
        elif text == "🌐 Tarjimon":
            await self._handle_translate_menu(update)
        elif text == "ℹ️ Qo'shimcha":
            await self.handle_help(update, context)

        # ── Translate menu ───────────────────────────────────────────
        elif text == "📝 Matn tarjimasi":
            await self._handle_text_translate_start(update)
        elif text == "🎤 Ovozdan tarjima":
            await self._handle_voice_translate_start(update)
        elif text == "📁 Fayl tarjimasi":
            await self._handle_file_translate_start(update)
        elif text == "📷 Rasm tarjimasi":
            await self._handle_photo_translate_start(update)
        elif text == "📜 Tarix":
            await self._handle_history(update, chat_id)
        elif text == "🌍 Boshqa tillar":
            await self._handle_other_languages_menu(update)

        # ── Other languages: user chose a language ───────────────────
        elif text in SUPPORTED_LANGUAGES and current_state == "other_languages":
            lang_code = SUPPORTED_LANGUAGES[text]
            self.user_target_lang[chat_id] = lang_code
            self.user_state[chat_id] = "other_lang_input"
            await update.message.reply_text(
                f"✅ Tanlangan til: *{text}*\n\n"
                f"Endi tarjima qilmoqchi bo'lgan matnni kiriting:",
                parse_mode="Markdown",
                reply_markup=self._get_back_home_menu(),
            )

        # ── Old dictionary menu (kept for backward compat) ───────────
        elif text == "📖 Lug'at":
            await self._handle_translate_menu(update)

        # ── Tenses ──────────────────────────────────────────────────
        else:
            await self._handle_user_input(update, chat_id, text, current_state)

    # ─────────────────────────────── Voice handler ───────────────────────────────

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        chat_id = update.effective_chat.id
        current_state = self.user_state.get(chat_id, "main")

        if current_state != "voice_translate":
            await update.message.reply_text(
                "🎤 Ovozdan tarjima uchun avval *Tarjimon → Ovozdan tarjima* tugmasini bosing.",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text("⏳ Ovoz tahlil qilinmoqda...")

        from voice_translator import transcribe_audio_with_language, tts_mp3_bytes

        voice = update.message.voice
        voice_file = await context.bot.get_file(voice.file_id)
        audio_bytes = bytes(await voice_file.download_as_bytearray())

        transcribed, detected_lang, ok = transcribe_audio_with_language(audio_bytes, original_ext=".ogg")

        if not ok:
            await update.message.reply_text(transcribed, reply_markup=self._get_translate_menu())
            return

        # Translate with rule:
        # - If detected Uzbek => translate to English
        # - Else (English/any other) => translate to Uzbek
        if (detected_lang or "").startswith("uz"):
            target = "en"
        else:
            target = "uz"

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        translated = self.translator.translate(transcribed, source="auto", target=target)

        lang_label = "O'zbekcha → Inglizcha" if target == "en" else "Inglizcha/Other → O'zbekcha"
        full_msg = (
            f"🎤 Ovozdan aniqlangan matn:\n{transcribed}\n\n"
            f"🌐 {lang_label}\n"
            f"✅ Tarjima: {translated}"
        )
        await update.message.reply_text(full_msg)

        # Send audio of the translation
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VOICE)
        mp3, ok_tts = tts_mp3_bytes(translated, lang=target)
        if ok_tts:
            import io

            bio = io.BytesIO(mp3)
            bio.name = "translation.mp3"
            await update.message.reply_audio(audio=bio)

        await update.message.reply_text("🏠", reply_markup=self._get_translate_menu())
        self.history_manager.add_entry(chat_id, transcribed, translated, mode="voice")

    # ─────────────────────────────── Document handler ────────────────────────────

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        chat_id = update.effective_chat.id
        current_state = self.user_state.get(chat_id, "main")

        if current_state != "file_translate":
            await update.message.reply_text(
                "📁 Fayl tarjimasi uchun avval *Tarjimon → Fayl tarjimasi* tugmasini bosing.",
                parse_mode="Markdown",
            )
            return

        doc = update.message.document
        filename = doc.file_name or "file.txt"

        await update.message.reply_text(f"⏳ `{filename}` fayl o'qilmoqda...", parse_mode="Markdown")

        from file_translator import extract_text_from_bytes

        doc_file = await context.bot.get_file(doc.file_id)
        file_bytes = bytes(await doc_file.download_as_bytearray())

        extracted, ok = extract_text_from_bytes(file_bytes, filename)

        if not ok:
            await update.message.reply_text(extracted, reply_markup=self._get_translate_menu())
            return

        await update.message.reply_text(
            f"📄 Fayldan olingan matn:\n{extracted[:500]}{'...' if len(extracted) > 500 else ''}",
        )

        await update.message.reply_text("⏳ Tarjima qilinmoqda...")
        translation = self.translator.auto_translate_en_uz(extracted)
        await update.message.reply_text(
            translation,
            parse_mode="Markdown",
            reply_markup=self._get_translate_menu(),
        )
        self.history_manager.add_entry(chat_id, extracted[:200], translation, mode="file")

    # ─────────────────────────────── Photo handler ───────────────────────────────

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        chat_id = update.effective_chat.id
        current_state = self.user_state.get(chat_id, "main")

        if current_state != "photo_translate":
            await update.message.reply_text(
                "📷 Rasm tarjimasi uchun avval *Tarjimon → Rasm tarjimasi* tugmasini bosing.",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text("⏳ Rasmdagi matn aniqlanmoqda (OCR)...")

        from photo_translator import extract_text_from_image_bytes, translate_image_bytes
        from voice_translator import tts_mp3_bytes

        # Get highest quality photo
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        image_bytes = bytes(await photo_file.download_as_bytearray())

        extracted, ok = extract_text_from_image_bytes(image_bytes)

        if not ok:
            await update.message.reply_text(extracted, reply_markup=self._get_translate_menu())
            return

        await update.message.reply_text(
            f"🔍 Rasmdan aniqlangan matn:\n{extracted[:500]}{'...' if len(extracted) > 500 else ''}",
        )

        await update.message.reply_text("⏳ Tarjima qilinmoqda...")
        detected = self.translator.detect_language(extracted)
        target = "en" if (detected or "").startswith("uz") else "uz"
        translated_text = self.translator.translate(extracted, source="auto", target=target)

        await update.message.reply_text(
            f"✅ Tarjima: {translated_text}",
        )

        # Generate translated image (best-effort)
        out_img, ok_img = translate_image_bytes(image_bytes, self.translator, target_lang=target)
        if ok_img:
            import io

            img_bio = io.BytesIO(out_img)
            img_bio.name = "translated.png"
            await update.message.reply_photo(photo=img_bio)

        # Send audio in both Uzbek and English
        uz_audio, ok_uz = tts_mp3_bytes(self.translator.translate(translated_text, source="auto", target="uz"), lang="uz")
        en_audio, ok_en = tts_mp3_bytes(self.translator.translate(translated_text, source="auto", target="en"), lang="en")
        if ok_uz:
            import io

            bio = io.BytesIO(uz_audio)
            bio.name = "uz.mp3"
            await update.message.reply_audio(audio=bio, caption="🇺🇿")
        if ok_en:
            import io

            bio = io.BytesIO(en_audio)
            bio.name = "en.mp3"
            await update.message.reply_audio(audio=bio, caption="🇬🇧")

        await update.message.reply_text("🏠", reply_markup=self._get_translate_menu())
        self.history_manager.add_entry(chat_id, extracted[:200], translated_text[:300], mode="photo")

    # ─────────────────────────────── Menu-section handlers ───────────────────────

    async def _handle_main_menu(self, update: Update) -> None:
        chat_id = update.effective_chat.id
        self.user_state[chat_id] = "main"
        await update.message.reply_text("🏠 Asosiy menyu:", reply_markup=self._get_main_menu())

    async def _handle_tenses_menu(self, update: Update) -> None:
        chat_id = update.effective_chat.id
        self.user_state[chat_id] = "tenses"
        await update.message.reply_text("Zamonlardan birini tanlang:", reply_markup=self._get_tenses_menu())

    async def _handle_translate_menu(self, update: Update) -> None:
        chat_id = update.effective_chat.id
        self.user_state[chat_id] = "translate"
        await update.message.reply_text(
            "🌐 *Tarjimon menyusi*\n\nQuyidagi tarjima turlaridan birini tanlang:",
            parse_mode="Markdown",
            reply_markup=self._get_translate_menu(),
        )

    async def _handle_text_translate_start(self, update: Update) -> None:
        chat_id = update.effective_chat.id
        self.user_state[chat_id] = "text_translate"
        await update.message.reply_text(
            "📝 *Matn tarjimasi*\n\n"
            "Inglizcha yoki O'zbekcha matn kiriting — bot avtomatik tilni aniqlab tarjima qiladi.\n\n"
            "💡 Misol: `Hello` yoki `Salom`",
            parse_mode="Markdown",
            reply_markup=self._get_back_home_menu(),
        )

    async def _handle_voice_translate_start(self, update: Update) -> None:
        chat_id = update.effective_chat.id
        self.user_state[chat_id] = "voice_translate"
        await update.message.reply_text(
            "🎤 *Ovozdan tarjima*\n\n"
            "Ovozli xabar yuboring — bot uni matnга o'girib tarjima qiladi.\n\n"
            "⚠️ *Eslatma:* Bu funksiya `ffmpeg` va `vosk` (offline) o'rnatilgan bo'lishini talab qiladi.\n"
            "Shuningdek, Vosk modellari uchun `VOSK_MODEL_UZ` va `VOSK_MODEL_EN` muhit o'zgaruvchilari kerak.",
            parse_mode="Markdown",
            reply_markup=self._get_back_home_menu(),
        )

    async def _handle_file_translate_start(self, update: Update) -> None:
        chat_id = update.effective_chat.id
        self.user_state[chat_id] = "file_translate"
        await update.message.reply_text(
            "📁 *Fayl tarjimasi*\n\n"
            "Qo'llab-quvvatlanadigan formatlar:\n"
            "  • 📄 `.txt` – Oddiy matn fayli\n"
            "  • 📝 `.docx` – Microsoft Word\n"
            "  • 📕 `.pdf` – PDF hujjat\n\n"
            "Faylni yuboring:",
            parse_mode="Markdown",
            reply_markup=self._get_back_home_menu(),
        )

    async def _handle_photo_translate_start(self, update: Update) -> None:
        chat_id = update.effective_chat.id
        self.user_state[chat_id] = "photo_translate"
        await update.message.reply_text(
            "📷 *Rasm tarjimasi*\n\n"
            "Matn mavjud rasm yuboring — OCR texnologiyasi orqali matn o'qiladi va tarjima qilinadi.\n\n"
            "💡 Eng yaxshi natija uchun: aniq, yorug' va matn yaxshi ko'rinadigan rasm yuboring.\n\n"
            "⚠️ *Eslatma:* Bu funksiya `easyocr` (offline) o'rnatilgan bo'lishini talab qiladi.",
            parse_mode="Markdown",
            reply_markup=self._get_back_home_menu(),
        )

    async def _handle_history(self, update: Update, chat_id: int) -> None:
        history_text = self.history_manager.get_history(chat_id)
        await update.message.reply_text(
            history_text,
            parse_mode="Markdown",
            reply_markup=self._get_translate_menu(),
        )

    async def _handle_other_languages_menu(self, update: Update) -> None:
        chat_id = update.effective_chat.id
        self.user_state[chat_id] = "other_languages"
        await update.message.reply_text(
            "🌍 *Boshqa tillar*\n\nQaysi tilga tarjima qilmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=self._get_other_languages_menu(),
        )

    async def _handle_back(self, update: Update, chat_id: int) -> None:
        current_state = self.user_state.get(chat_id, "main")
        # From translate sub-states → back to translate menu
        if current_state in {
            "text_translate",
            "voice_translate",
            "file_translate",
            "photo_translate",
            "history",
            "other_languages",
            "other_lang_input",
        }:
            await self._handle_translate_menu(update)
        # From translate menu → back to main
        elif current_state == "translate":
            await self._handle_main_menu(update)
        # From tenses/dictionary states → back to main
        elif current_state in {"tenses", "dictionary", "word_sections", "word_subsections"}:
            await self._handle_main_menu(update)
        # From tense info → back to tenses
        elif current_state == "tense_info":
            await self._handle_tenses_menu(update)
        # Default
        else:
            await self._handle_main_menu(update)

    # ─────────────────────────────── User input router ───────────────────────────

    async def _handle_user_input(
        self,
        update: Update,
        chat_id: int,
        text: str,
        current_state: str,
    ) -> None:
        # ── Text translation state ──────────────────────────────────
        if current_state == "text_translate":
            await update.message.reply_text("⏳ Tarjima qilinmoqda...")
            result = self.translator.auto_translate_en_uz(text)
            await update.message.reply_text(
                result,
                parse_mode="Markdown",
                reply_markup=self._get_back_home_menu(),
            )
            self.history_manager.add_entry(chat_id, text, result, mode="text")
            return

        # ── Other language input state ──────────────────────────────
        if current_state == "other_lang_input":
            target_lang = self.user_target_lang.get(chat_id, "uz")
            await update.message.reply_text("⏳ Tarjima qilinmoqda...")
            result = self.translator.translate_to_language(text, target_lang)
            await update.message.reply_text(
                result,
                parse_mode="Markdown",
                reply_markup=self._get_other_languages_menu(),
            )
            self.history_manager.add_entry(chat_id, text, result, mode="text")
            # Keep in other_lang_input so user can type more
            return

        # ── Tense button pressed ────────────────────────────────────
        mapped_tense = self._get_tense_info_from_button(text)
        if mapped_tense is not None:
            self.user_state[chat_id] = "tense_info"
            self.user_tense[chat_id] = mapped_tense.name
            await update.message.reply_text(str(mapped_tense), reply_markup=self._get_tense_info_menu())
            return

        # ── In tense_info submenu ───────────────────────────────────
        if current_state == "tense_info":
            await self._handle_tense_info_menu(update, chat_id, text)
            return

        # ── Word list sections ──────────────────────────────────────
        if current_state == "word_sections":
            try:
                section = int(text)
                if 1 <= section <= self.dictionary_manager.get_total_sections():
                    self.user_section[chat_id] = section
                    subsections = self.dictionary_manager.get_subsections_in_section(section)
                    subsections_list = [f"{section}. Bo'lim so'zlari:\n"]
                    for i in range(1, subsections + 1):
                        subsections_list.append(f"{i}. Guruh")
                    msg = "\n".join(subsections_list)
                    self.user_state[chat_id] = "word_subsections"
                    await update.message.reply_text(msg, reply_markup=self._get_subsections_menu(subsections))
                else:
                    await update.message.reply_text("Noto'g'ri bo'lim raqami. Qaytadan tanlang.")
            except ValueError:
                await update.message.reply_text("Iltimos, raqam kiriting.")
            return

        if current_state == "word_subsections":
            try:
                subsection = int(text)
                section = self.user_section.get(chat_id)
                if section is None:
                    await update.message.reply_text("Bo'lim tanlanmagan.")
                    return
                words = self.dictionary_manager.get_subsection(section, subsection)
                words_lines = [f"{i + 1}. {word}" for i, word in enumerate(words)]
                await update.message.reply_text("\n".join(words_lines))
                self.user_state[chat_id] = "dictionary"
            except ValueError:
                await update.message.reply_text("Iltimos, raqam kiriting.")
            return

        # ── States where media messages are expected ────────────────
        if current_state in {"voice_translate", "file_translate", "photo_translate"}:
            state_hints = {
                "voice_translate": "🎤 Iltimos, ovozli xabar yuboring.",
                "file_translate": "📁 Iltimos, .txt, .docx yoki .pdf fayl yuboring.",
                "photo_translate": "📷 Iltimos, rasm yuboring.",
            }
            await update.message.reply_text(
                state_hints[current_state],
                reply_markup=self._get_back_home_menu(),
            )
            return

        # ── Fallback: try tense lookup or show main menu ────────────
        tense_info = self.tense_manager.get_tense_info(text)
        if tense_info is not None:
            self.user_state[chat_id] = "tense_info"
            self.user_tense[chat_id] = tense_info.name
            await update.message.reply_text(str(tense_info), reply_markup=self._get_tense_info_menu())
        else:
            await update.message.reply_text(
                "❓ Noma'lum buyruq. Iltimos, menyudan tanlang.",
                reply_markup=self._get_main_menu(),
            )

    # ─────────────────────────────── Keyboard builders ───────────────────────────

    def _get_main_menu(self) -> ReplyKeyboardMarkup:
        rows = [
            [KeyboardButton("📚 Zamonlar")],
            [KeyboardButton("🌐 Tarjimon")],
            [KeyboardButton("ℹ️ Qo'shimcha")],
        ]
        return self._create_markup(rows)

    def _get_translate_menu(self) -> ReplyKeyboardMarkup:
        rows = [
            [KeyboardButton("📝 Matn tarjimasi"), KeyboardButton("🎤 Ovozdan tarjima")],
            [KeyboardButton("📁 Fayl tarjimasi"), KeyboardButton("📷 Rasm tarjimasi")],
            [KeyboardButton("📜 Tarix"), KeyboardButton("🌍 Boshqa tillar")],
            [KeyboardButton("⬅️ Ortga"), KeyboardButton("🏠 Bosh menyu")],
        ]
        return self._create_markup(rows)

    def _get_other_languages_menu(self) -> ReplyKeyboardMarkup:
        lang_buttons = [KeyboardButton(name) for name in SUPPORTED_LANGUAGES.keys()]
        rows: List[List[KeyboardButton]] = []
        for i in range(0, len(lang_buttons), 2):
            row = [lang_buttons[i]]
            if i + 1 < len(lang_buttons):
                row.append(lang_buttons[i + 1])
            rows.append(row)
        rows.append([KeyboardButton("⬅️ Ortga"), KeyboardButton("🏠 Bosh menyu")])
        return self._create_markup(rows)

    def _get_back_home_menu(self) -> ReplyKeyboardMarkup:
        rows = [[KeyboardButton("⬅️ Ortga"), KeyboardButton("🏠 Bosh menyu")]]
        return self._create_markup(rows)

    def _get_tenses_menu(self) -> ReplyKeyboardMarkup:
        rows = [
            [KeyboardButton("⏰ Present Simple"), KeyboardButton("🔄 Present Continuous")],
            [KeyboardButton("✅ Present Perfect"), KeyboardButton("⏳ Present Perfect Continuous")],
            [KeyboardButton("🕰️ Past Simple"), KeyboardButton("🔄 Past Continuous")],
            [KeyboardButton("✔️ Past Perfect"), KeyboardButton("⏳ Past Perfect Continuous")],
            [KeyboardButton("🔮 Future Simple"), KeyboardButton("🔄 Future Continuous")],
            [KeyboardButton("⭐ Future Perfect"), KeyboardButton("⏳ Future Perfect Continuous")],
            [KeyboardButton("⬅️ Ortga"), KeyboardButton("🏠 Bosh menyu")],
        ]
        return self._create_markup(rows)

    def _get_tense_info_menu(self) -> ReplyKeyboardMarkup:
        rows = [
            [KeyboardButton("ℹ️ Malumot"), KeyboardButton("🎥 Video")],
            [KeyboardButton("⬅️ Ortga"), KeyboardButton("🏠 Bosh menyu")],
        ]
        return self._create_markup(rows)

    def _get_sections_menu(self, total_sections: int) -> ReplyKeyboardMarkup:
        rows: List[List[KeyboardButton]] = []
        for i in range(1, total_sections + 1, 2):
            row = [KeyboardButton(str(i))]
            if i + 1 <= total_sections:
                row.append(KeyboardButton(str(i + 1)))
            rows.append(row)
        rows.append([KeyboardButton("⬅️ Ortga"), KeyboardButton("🏠 Bosh menyu")])
        return self._create_markup(rows)

    def _get_subsections_menu(self, total_subsections: int) -> ReplyKeyboardMarkup:
        rows: List[List[KeyboardButton]] = []
        for i in range(1, total_subsections + 1, 2):
            row = [KeyboardButton(str(i))]
            if i + 1 <= total_subsections:
                row.append(KeyboardButton(str(i + 1)))
            rows.append(row)
        rows.append([KeyboardButton("⬅️ Ortga"), KeyboardButton("🏠 Bosh menyu")])
        return self._create_markup(rows)

    @staticmethod
    def _create_markup(rows: List[List[KeyboardButton]]) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(rows, resize_keyboard=True)

    def _get_tense_info_from_button(self, text: str) -> Optional[TenseInfo]:
        mapping = {
            "⏰ Present Simple": "Present Simple",
            "🔄 Present Continuous": "Present Continuous",
            "✅ Present Perfect": "Present Perfect",
            "⏳ Present Perfect Continuous": "Present Perfect Continuous",
            "🕰️ Past Simple": "Past Simple",
            "🔄 Past Continuous": "Past Continuous",
            "✔️ Past Perfect": "Past Perfect",
            "⏳ Past Perfect Continuous": "Past Perfect Continuous",
            "🔮 Future Simple": "Future Simple",
            "🔄 Future Continuous": "Future Continuous",
            "⭐ Future Perfect": "Future Perfect",
            "⏳ Future Perfect Continuous": "Future Perfect Continuous",
        }
        tense_name = mapping.get(text)
        if not tense_name:
            return None
        return self.tense_manager.get_tense_info(tense_name)

    async def _handle_tense_info_menu(self, update: Update, chat_id: int, text: str) -> None:
        tense_name = self.user_tense.get(chat_id)
        if not tense_name:
            await update.message.reply_text("Avval zamonni tanlang.", reply_markup=self._get_tenses_menu())
            self.user_state[chat_id] = "tenses"
            return

        tense_info = self.tense_manager.get_tense_info(tense_name)
        if tense_info is None:
            await update.message.reply_text("Zamon topilmadi.", reply_markup=self._get_tenses_menu())
            self.user_state[chat_id] = "tenses"
            return

        if text == "ℹ️ Malumot":
            await update.message.reply_text(str(tense_info), reply_markup=self._get_tense_info_menu())
        elif text == "🎥 Video":
            await update.message.reply_text(
                f"{tense_info.name} ({tense_info.uzbek_name}) video: {tense_info.video_link}",
                reply_markup=self._get_tense_info_menu(),
            )
        else:
            await update.message.reply_text(
                "Menyudan buyruq tanlang (ℹ️ Malumot yoki 🎥 Video).",
                reply_markup=self._get_tense_info_menu(),
            )


# ─────────────────────────────── Application builder ─────────────────────────

def build_application(token: str) -> Application:
    """Create a python-telegram-bot Application wired with the EnglishBot logic."""
    logic = EnglishBotLogic()

    app = ApplicationBuilder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", logic.handle_start))
    app.add_handler(CommandHandler("about", logic.handle_about))
    app.add_handler(CommandHandler("help", logic.handle_help))

    # Media handlers (must come BEFORE the generic text handler)
    app.add_handler(MessageHandler(filters.VOICE, logic.handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, logic.handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, logic.handle_photo))

    # Generic text handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, logic.handle_text))

    return app
