"""
Entry point for the Telegram Task Manager bot.

Start with:
    python main.py

The bot uses long-polling (no webhook server required).
APScheduler fires the morning and evening summaries in the background.
"""
import asyncio
import logging
import sys

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import TELEGRAM_BOT_TOKEN, validate_config
from bot.handlers import (
    handle_start,
    handle_text,
    handle_voice,
    handle_photo,
    handle_tasks_command,
    handle_today_command,
)
from bot.scheduler import setup_scheduler

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
# Silence noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main() -> None:
    # ── Validate environment variables before starting ──────────────────────
    try:
        validate_config()
    except EnvironmentError as exc:
        logger.error("Configuration error:\n%s", exc)
        sys.exit(1)

    # ── Build the Telegram application ──────────────────────────────────────
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_start))
    app.add_handler(CommandHandler("tasks", handle_tasks_command))
    app.add_handler(CommandHandler("today", handle_today_command))

    # Message types
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # ── Set up the daily scheduler ──────────────────────────────────────────
    scheduler = setup_scheduler(app.bot)

    # ── Wire scheduler start/stop to application lifecycle ──────────────────
    async def on_startup(application: Application) -> None:
        scheduler.start()
        logger.info("Scheduler started.")

    async def on_shutdown(application: Application) -> None:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")

    app.post_init = on_startup
    app.post_shutdown = on_shutdown

    # ── Run the bot ─────────────────────────────────────────────────────────
    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(
        allowed_updates=["message"],
        drop_pending_updates=True,   # ignore messages sent while offline
    )


if __name__ == "__main__":
    main()
