"""
Telegram message handlers.

Supported message types:
  • Text  → Claude extracts tasks directly
  • Voice → Whisper transcribes → Claude extracts tasks
  • Photo → Claude Vision OCR + task extraction

"done" / "تم" flow:
  User sends "done" or "تم"        → bot shows numbered pending-task list
  User sends a number (e.g. "2")   → bot marks that task done
  User sends "done 2"              → same as above (shortcut)
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from services.claude_service import extract_tasks, extract_tasks_from_image
from services.whisper_service import transcribe_voice
from services.notion_service import (
    add_task,
    get_pending_tasks,
    get_tasks_for_today,
    mark_task_done,
)

logger = logging.getLogger(__name__)

# ── session key names stored in context.user_data ──────────────────────────
_KEY_PENDING = "pending_tasks"   # list[dict] — last shown pending list


# ──────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────────────────────

PRIORITY_EMOJI = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
SOURCE_EMOJI = {"text": "📝", "voice": "🎙️", "photo": "📷"}


def _fmt_confirmation(tasks: list[dict]) -> str:
    """Build a Telegram confirmation message after tasks are added."""
    if len(tasks) == 1:
        t = tasks[0]
        due = t.get("due_date") or "no due date"
        src = SOURCE_EMOJI.get(t.get("source", "text"), "📝")
        return (
            f"✅ Added to Notion: *{t['title']}* — {due} — "
            f"{t['priority']} priority {src}"
        )

    lines = [f"✅ Added *{len(tasks)} tasks* to Notion:\n"]
    for i, t in enumerate(tasks, 1):
        emoji = PRIORITY_EMOJI.get(t.get("priority", "Medium"), "⚪")
        due = f" — {t['due_date']}" if t.get("due_date") else ""
        src = SOURCE_EMOJI.get(t.get("source", "text"), "📝")
        lines.append(f"{i}. {emoji} *{t['title']}*{due} {src}")
    return "\n".join(lines)


def _fmt_task_list(tasks: list[dict], header: str) -> str:
    """Format a numbered task list for display."""
    lines = [header, ""]
    for i, t in enumerate(tasks, 1):
        emoji = PRIORITY_EMOJI.get(t.get("priority", "Medium"), "⚪")
        due = f"\n   📅 {t['due_date']}" if t.get("due_date") else ""
        lines.append(f"{i}. {emoji} *{t['title']}*{due}\n   Status: {t['status']}")
    lines.append("\nReply with a number (e.g. *1*) or *done 2* to mark a task complete.")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Task-adding pipeline (shared by text / voice / photo handlers)
# ──────────────────────────────────────────────────────────────────────────────

async def _add_tasks_and_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tasks: list[dict],
) -> None:
    """Persist tasks to Notion, store in session, and confirm to user."""
    if not tasks:
        await update.message.reply_text(
            "❌ I couldn't extract any tasks from your message. "
            "Try rephrasing or be more specific."
        )
        return

    added: list[dict] = []
    for task in tasks:
        # GPT sometimes uses "name" or "task_title" instead of "title"
        title = (
            task.get("title")
            or task.get("name")
            or task.get("task_title")
            or "Untitled Task"
        )
        page_id = add_task(
            title=title,
            priority=task.get("priority", "Medium"),
            due_date=task.get("due_date"),
            source=task.get("source", "text"),
            notes=task.get("notes"),
        )
        task["id"] = page_id
        added.append(task)

    # Keep for "done N" follow-ups
    context.user_data[_KEY_PENDING] = added

    await update.message.reply_text(_fmt_confirmation(added), parse_mode="Markdown")


# ──────────────────────────────────────────────────────────────────────────────
# Message handlers
# ──────────────────────────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages."""
    text = update.message.text.strip()

    # ── "done" keyword ───────────────────────────────────────────────────────
    if text.lower() in ("done", "تم", "✅"):
        await _show_pending_list(update, context)
        return

    # ── "done N" shortcut ────────────────────────────────────────────────────
    lower = text.lower()
    if lower.startswith(("done ", "تم ")):
        parts = text.split(maxsplit=1)
        if len(parts) == 2 and parts[1].isdigit():
            await _mark_by_number(update, context, int(parts[1]))
            return

    # ── bare number — map to pending list ───────────────────────────────────
    if text.isdigit():
        pending = context.user_data.get(_KEY_PENDING, [])
        if pending:
            await _mark_by_number(update, context, int(text))
            return

    # ── normal task message ──────────────────────────────────────────────────
    await update.message.reply_text("⏳ Analysing your message…")
    try:
        tasks = extract_tasks(text, source="text")
        await _add_tasks_and_reply(update, context, tasks)
    except Exception as exc:
        logger.exception("handle_text error")
        await update.message.reply_text(f"❌ Something went wrong: {exc}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages: Whisper transcription → Claude extraction."""
    await update.message.reply_text("🎙️ Transcribing your voice message…")
    try:
        voice_file = await update.message.voice.get_file(read_timeout=30, connect_timeout=15)
        audio_bytes = bytes(await voice_file.download_as_bytearray(read_timeout=60, connect_timeout=15))

        transcript = transcribe_voice(audio_bytes, file_extension="ogg")
        await update.message.reply_text(
            f"📝 *Transcribed:* _{transcript}_", parse_mode="Markdown"
        )

        tasks = extract_tasks(transcript, source="voice")
        await _add_tasks_and_reply(update, context, tasks)

    except Exception as exc:
        logger.exception("handle_voice error")
        await update.message.reply_text(f"❌ Something went wrong: {exc}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages: Claude Vision OCR → task extraction."""
    await update.message.reply_text("🖼️ Reading your image…")
    try:
        # Telegram provides multiple sizes; take the largest
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        image_bytes = bytes(await photo_file.download_as_bytearray())

        # Determine MIME type from file path (Telegram usually sends JPEGs)
        file_path: str = photo_file.file_path or ""
        if file_path.endswith(".png"):
            mime = "image/png"
        elif file_path.endswith(".webp"):
            mime = "image/webp"
        else:
            mime = "image/jpeg"

        tasks = extract_tasks_from_image(image_bytes, mime_type=mime)
        await _add_tasks_and_reply(update, context, tasks)

    except Exception as exc:
        logger.exception("handle_photo error")
        await update.message.reply_text(f"❌ Something went wrong: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
# "Done" flow helpers
# ──────────────────────────────────────────────────────────────────────────────

async def _show_pending_list(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Fetch pending tasks, show numbered list, store in session."""
    try:
        pending = get_pending_tasks()
        if not pending:
            await update.message.reply_text("✅ You have no pending tasks — great job!")
            return

        context.user_data[_KEY_PENDING] = pending
        msg = _fmt_task_list(pending, "📋 *Your pending tasks:*")
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as exc:
        logger.exception("_show_pending_list error")
        await update.message.reply_text(f"❌ Could not fetch tasks: {exc}")


async def _mark_by_number(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    number: int,
) -> None:
    """Mark the Nth task from the last shown pending list as Done."""
    pending: list[dict] = context.user_data.get(_KEY_PENDING, [])

    # If session is empty, fetch fresh
    if not pending:
        pending = get_pending_tasks()
        context.user_data[_KEY_PENDING] = pending

    if not pending:
        await update.message.reply_text("❌ No pending tasks found. Send 'done' to see the list.")
        return

    if number < 1 or number > len(pending):
        await update.message.reply_text(
            f"❌ Please send a number between 1 and {len(pending)}."
        )
        return

    task = pending[number - 1]
    try:
        mark_task_done(task["id"])
        # Remove from local session
        context.user_data[_KEY_PENDING] = [
            t for t in pending if t["id"] != task["id"]
        ]
        await update.message.reply_text(
            f"✅ Marked as done: *{task['title']}*", parse_mode="Markdown"
        )
    except Exception as exc:
        logger.exception("_mark_by_number error")
        await update.message.reply_text(f"❌ Could not update task: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
# Command handlers
# ──────────────────────────────────────────────────────────────────────────────

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start and /help commands."""
    await update.message.reply_text(
        "👋 *Welcome to your Personal Task Manager!*\n\n"
        "Send me tasks in *Arabic, English, or mixed* — I'll understand and save them to Notion.\n\n"
        "*What I accept:*\n"
        "• 📝 Text — describe your tasks naturally\n"
        "• 🎙️ Voice — record and send a voice note\n"
        "• 📷 Photo — snap a photo of your notes or whiteboard\n\n"
        "*Commands:*\n"
        "• /tasks — view all pending tasks\n"
        "• /today — view today's tasks\n"
        "• /help  — show this message\n\n"
        "*Marking tasks done:*\n"
        "Send `done` or `تم` to see the list, then reply with the task number.\n"
        "Or use `done 2` directly as a shortcut.",
        parse_mode="Markdown",
    )


async def handle_tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tasks — show all pending tasks."""
    try:
        pending = get_pending_tasks()
        if not pending:
            await update.message.reply_text("✅ No pending tasks — you're all caught up!")
            return
        context.user_data[_KEY_PENDING] = pending
        await update.message.reply_text(
            _fmt_task_list(pending, "📋 *All pending tasks:*"),
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.exception("handle_tasks_command error")
        await update.message.reply_text(f"❌ Error fetching tasks: {exc}")


async def handle_today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /today — show tasks due today."""
    try:
        tasks = get_tasks_for_today()
        if not tasks:
            await update.message.reply_text("✅ Nothing due today — enjoy your day!")
            return
        context.user_data[_KEY_PENDING] = tasks
        await update.message.reply_text(
            _fmt_task_list(tasks, "📅 *Today's tasks:*"),
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.exception("handle_today_command error")
        await update.message.reply_text(f"❌ Error fetching today's tasks: {exc}")
