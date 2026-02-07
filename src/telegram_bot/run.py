#!/usr/bin/env python3
"""Entry point for the Telegram bot."""

import sys

from .bot import create_application
from .config import DEV_MODE, TELEGRAM_CHAT_ID, validate
from .messages import MSG_DEV_MODE_SKIP


def main() -> int:
    """Run the Telegram bot."""
    errors, warnings = validate()

    for warning in warnings:
        print(f"Warning: {warning}")

    if errors:
        for error in errors:
            print(f"Error: {error}")
        return 1

    if DEV_MODE:
        print(MSG_DEV_MODE_SKIP)
        return 0

    print("Starting Telegram bot...")
    print(f"  Authorized chat ID: {TELEGRAM_CHAT_ID}")

    app = create_application()
    app.run_polling()

    return 0


if __name__ == "__main__":
    sys.exit(main())
