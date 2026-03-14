"""
photo_translator.py
Extract text from images using OCR (EasyOCR offline).

Dependencies:
  - easyocr
  - Pillow
"""
from __future__ import annotations

import io
from typing import Tuple


def extract_text_from_image_bytes(image_bytes: bytes) -> Tuple[str, bool]:
    """
    Perform OCR on image bytes.

    Returns:
        (extracted_text_or_error, success: bool)
    """
    try:
        from PIL import Image  # type: ignore
        import easyocr  # type: ignore
    except ImportError as e:
        missing = str(e).split("'")[-2] if "'" in str(e) else str(e)
        return f"❌ `{missing}` kutubxonasi o'rnatilmagan. `pip install {missing}`", False

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = _preprocess_image(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        reader = _get_reader(easyocr)
        results = reader.readtext(_pil_to_rgb_array(image), detail=0)
        text = "\n".join([t.strip() for t in results if t and str(t).strip()]).strip()

        if not text:
            return (
                "❌ Rasmda tanib olinadigan matn topilmadi.\n"
                "Iltimos, aniqroq va yaxshiroq sifatli rasm yuboring.",
                False,
            )
        return text, True

    except Exception as e:
        return f"❌ OCR xatoligi: {e}", False


def translate_image_bytes(image_bytes: bytes, translator, target_lang: str = "uz") -> Tuple[bytes, bool]:
    """Best-effort: replace recognized words with translated ones and return PNG bytes."""
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
        import easyocr  # type: ignore
    except Exception:
        return b"", False

    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        ocr_img = _preprocess_image(img.copy())
        if ocr_img.mode not in ("RGB", "L"):
            ocr_img = ocr_img.convert("RGB")

        reader = _get_reader(easyocr)
        detections = reader.readtext(_pil_to_rgb_array(ocr_img), detail=1)
        if not detections:
            return b"", False

        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 18)
        except Exception:
            font = ImageFont.load_default()

        for det in detections:
            bbox, text, conf = det
            word = (text or "").strip()
            try:
                conf_v = float(conf)
            except Exception:
                conf_v = 0.0
            if not word:
                continue
            if conf_v < 0.4:
                continue

            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            x = int(min(xs))
            y = int(min(ys))
            w = int(max(xs) - min(xs))
            h = int(max(ys) - min(ys))

            translated = translator.translate(word, source="auto", target=target_lang)
            if not translated or translated.startswith("❌"):
                continue

            pad = 2
            draw.rectangle([x - pad, y - pad, x + w + pad, y + h + pad], fill="white")

            # Fit text roughly into the box
            text_to_draw = translated
            max_w = max(10, w)
            while len(text_to_draw) > 1:
                bbox = draw.textbbox((0, 0), text_to_draw, font=font)
                if (bbox[2] - bbox[0]) <= max_w:
                    break
                text_to_draw = text_to_draw[:-1]

            draw.text((x, y), text_to_draw, fill="black", font=font)

        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue(), True
    except Exception:
        return b"", False


_EASYOCR_READER = None


def _get_reader(easyocr_module):
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        _EASYOCR_READER = easyocr_module.Reader(["en"], gpu=False)
    return _EASYOCR_READER


def _pil_to_rgb_array(image):
    import numpy as np  # type: ignore

    if image.mode != "RGB":
        image = image.convert("RGB")
    return np.array(image)


def _preprocess_image(image):
    """Convert to RGB and enhance for better OCR."""
    try:
        from PIL import ImageEnhance, ImageFilter  # type: ignore
        # Convert to RGB (handle RGBA, P mode, etc.)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        # Sharpen slightly
        image = image.filter(ImageFilter.SHARPEN)
        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        return image
    except Exception:
        return image
