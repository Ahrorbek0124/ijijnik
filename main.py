from __future__ import annotations

import argparse
import os
import threading
import http.server
import socketserver
from pathlib import Path

try:
    from .english_bot import build_application
except ImportError:
    from english_bot import build_application

# --- RENDER UCHUN SOXTA SERVER ---
def run_dummy_server():
    """Render port scan xatosini tuzatish uchun kichik server"""
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    # Bu server Render'ga 'men ishlayapman' degan signal beradi
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Render uchun dummy server {port}-portda ishlamoqda...")
        httpd.serve_forever()

def _load_token_from_file() -> str:
    token_file = Path(__file__).with_name("bot_token.txt")
    if not token_file.exists():
        return ""
    content = token_file.read_text(encoding="utf-8").strip()
    return content

def main() -> None:
    parser = argparse.ArgumentParser(prog="english-bot")
    parser.add_argument(
        "--token",
        default=None,
        help="Telegram bot token (or set TELEGRAM_BOT_TOKEN env var, or put it in bot_token.txt).",
    )
    args = parser.parse_args()

    token = (args.token or "").strip()
    if not token:
        token = _load_token_from_file()
    if not token:
        token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()

    if not token:
        raise RuntimeError(
            "Missing token. Provide it via --token, TELEGRAM_BOT_TOKEN env var, or bot_token.txt file."
        )

    # --- RENDER UCHUN SERVERNI ALOHIDA OQIMDA ISHGA TUSHIRAMIZ ---
    if os.environ.get("RENDER"): # Faqat Render'da ishlashi uchun
        threading.Thread(target=run_dummy_server, daemon=True).start()
    # ---------------------------------------------------------

    app = build_application(token)
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
