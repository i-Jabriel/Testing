"""
APScheduler integration for daily morning and evening reminders.

Morning: sends today's tasks.
Evening: sends all still-pending tasks.

Both messages include a numbered list so the user can reply "done N" to
mark items complete without having to type the task name.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.constants import ParseMode

from config import (
    TELEGRAM_CHAT_ID,
    MORNING_HOUR,
    MORNING_MINUTE,
    EVENING_HOUR,
    EVENING_MINUTE,
    TIMEZONE,
)
from services.notion_service import get_tasks_for_today, get_pending_tasks

logger = logging.getLogger(__name__)

PRIORITY_EMOJI = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}


def _fmt_scheduled_list(tasks: list[dict]) -> str:
    lines = []
    for i, t in enumerate(tasks, 1):
        emoji = PRIORITY_EMOJI.get(t.get("priority", "Medium"), "⚪")
        due = f"\n   📅 Due: {t['due_date']}" if t.get("due_date") else ""
        lines.append(f"{i}. {emoji} *{t['title']}*{due}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Scheduled jobs
# ──────────────────────────────────────────────────────────────────────────────

async def _morning_summary(bot: Bot) -> None:
    """Send the morning briefing to the configured chat."""
    try:
        tasks = get_tasks_for_today()
        if not tasks:
            text = (
                "🌅 *Good morning!*\n\n"
                "You have no tasks scheduled for today. Enjoy your day! ☀️"
            )
        else:
            task_list = _fmt_scheduled_list(tasks)
            text = (
                f"🌅 *Good morning! Here are your tasks for today:*\n\n"
                f"{task_list}\n\n"
                f"Reply *done N* to mark a task complete."
            )

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )
        logger.info("Morning summary sent (%d task(s))", len(tasks))

    except Exception:
        logger.exception("Failed to send morning summary")


async def _evening_summary(bot: Bot) -> None:
    """Send the evening briefing with all pending tasks."""
    try:
        pending = get_pending_tasks()
        if not pending:
            text = (
                "🌙 *Good evening!*\n\n"
                "You've cleared all your tasks today — well done! 🎉"
            )
        else:
            task_list = _fmt_scheduled_list(pending)
            text = (
                f"🌙 *Good evening! Here's what's still pending:*\n\n"
                f"{task_list}\n\n"
                f"Reply *done N* to mark a task complete."
            )

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )
        logger.info("Evening summary sent (%d pending task(s))", len(pending))

    except Exception:
        logger.exception("Failed to send evening summary")


# ──────────────────────────────────────────────────────────────────────────────
# Scheduler factory
# ──────────────────────────────────────────────────────────────────────────────

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    Create and configure an AsyncIOScheduler with morning + evening jobs.

    Call scheduler.start() after the bot application has started.
    """
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    scheduler.add_job(
        _morning_summary,
        CronTrigger(hour=MORNING_HOUR, minute=MORNING_MINUTE, timezone=TIMEZONE),
        args=[bot],
        id="morning_summary",
        name="Morning Task Summary",
        replace_existing=True,
        misfire_grace_time=300,   # fire up to 5 min late if the process was down
    )

    scheduler.add_job(
        _evening_summary,
        CronTrigger(hour=EVENING_HOUR, minute=EVENING_MINUTE, timezone=TIMEZONE),
        args=[bot],
        id="evening_summary",
        name="Evening Task Summary",
        replace_existing=True,
        misfire_grace_time=300,
    )

    logger.info(
        "Scheduler configured — morning at %02d:%02d, evening at %02d:%02d (%s)",
        MORNING_HOUR, MORNING_MINUTE, EVENING_HOUR, EVENING_MINUTE, TIMEZONE,
    )
    return scheduler
