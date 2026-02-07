#!/usr/bin/env python3
"""Entry point for the Telegram bot."""

import sys

from .bot import create_application
from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def main() -> int:
    """Run the Telegram bot."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set")
        return 1

    if not TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_CHAT_ID environment variable not set")
        return 1

    print("Starting Telegram bot...")
    print(f"  Authorized chat ID: {TELEGRAM_CHAT_ID}")

    app = create_application()
    app.run_polling()

    return 0


if __name__ == "__main__":
    sys.exit(main())
