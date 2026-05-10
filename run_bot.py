"""Start the Telegram bot in polling mode."""

import logging

from tradecoach.bot.handlers import build_application

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

if __name__ == "__main__":
    app = build_application()
    print("TradeCoach bot starting... Press Ctrl+C to stop.")
    app.run_polling()
