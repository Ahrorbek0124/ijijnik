from __future__ import annotations

import argparse
import os
from pathlib import Path

try:
    from .english_bot import build_application
except ImportError:
    from english_bot import build_application

def _load_token_from_file() -> str:
    """
    Try to read the bot token from a local text file.
    The file should contain only the token string.
    """
    token_file = Path(__file__).with_name("bot_token.txt")
    if not token_file.exists():
        return ""
    content = token_file.read_text(encoding="utf-8").strip()
    return content


def main() -> None:
    """
    Entry point for the Python version of the English bot.

    Token priority (first non-empty wins):
    1) --token argument
    2) bot_token.txt file next to this script
    3) TELEGRAM_BOT_TOKEN environment variable
    """

    parser = argparse.ArgumentParser(prog="english-bot")
    parser.add_argument(
        "--token",
        default=None,
        help="Telegram bot token (or set TELEGRAM_BOT_TOKEN env var, or put it in bot_token.txt).",
    )
    args = parser.parse_args()

    # 1) CLI arg
    token = (args.token or "").strip()

    # 2) Local file (preferred over environment variable)
    if not token:
        token = _load_token_from_file()

    # 3) Environment variable (fallback)
    if not token:
        token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()

    if not token:
        raise RuntimeError(
            "Missing token. Provide it via --token, TELEGRAM_BOT_TOKEN env var, or bot_token.txt file."
        )

    app = build_application(token)
    app.run_polling()


if __name__ == "__main__":
    main()

