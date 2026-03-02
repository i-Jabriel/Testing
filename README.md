# Personal Daily Task Manager — Telegram + Claude + Notion

A personal productivity bot that lets you capture tasks through Telegram in **Arabic, English, or mixed language**. Claude AI understands your intent, extracts structured tasks, and saves them directly to Notion. Daily morning and evening reminders keep you on track.

---

## Features

| Input | How it works |
|---|---|
| **Text** | Claude reads your message and extracts tasks with title, priority, and due date |
| **Voice** | Whisper transcribes the audio → Claude extracts tasks |
| **Photo** | Claude Vision performs OCR on the image → extracts tasks |

**Supported languages:** Arabic, English, or any mix (Arabizi, code-switching)

**Daily reminders:**
- 🌅 Morning — today's tasks
- 🌙 Evening — still-pending tasks

---

## Tech Stack

- **Python 3.11+**
- `python-telegram-bot` v20 — async bot framework
- `anthropic` — Claude Sonnet for NLP task extraction + Vision OCR
- `openai` — Whisper API for voice transcription
- `notion-client` — Notion database CRUD
- `APScheduler` — daily reminder jobs

---

## Project Structure

```
telegram-task-manager/
├── main.py                  # Entry point — wires bot + scheduler
├── config.py                # Environment variable loader + validator
├── bot/
│   ├── handlers.py          # Telegram message & command handlers
│   └── scheduler.py         # Morning / evening APScheduler jobs
├── services/
│   ├── claude_service.py    # Task extraction (text + vision)
│   ├── whisper_service.py   # Voice transcription
│   └── notion_service.py    # Notion CRUD + optional DB setup
├── .env.example             # Copy → .env and fill in your keys
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone & install dependencies

```bash
git clone <repo-url>
cd telegram-task-manager
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create a Telegram bot

1. Open Telegram and message **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **bot token**
4. Find your personal chat ID by messaging **@userinfobot**

### 3. Get API keys

| Service | Where to get it |
|---|---|
| Anthropic (Claude) | https://console.anthropic.com |
| OpenAI (Whisper) | https://platform.openai.com/api-keys |
| Notion | https://www.notion.so/my-integrations → *New integration* |

### 4. Set up the Notion database

**Option A — Automatic (recommended)**

```python
# Run once from a Python shell
from services.notion_service import setup_notion_database
db_id = setup_notion_database("YOUR_NOTION_PAGE_ID")
print("Database ID:", db_id)
```

> The page ID is the last part of any Notion page URL.

**Option B — Manual**

Create a Notion database with these exact property names and types:

| Property | Type | Options |
|---|---|---|
| Title | Title | — |
| Priority | Select | High · Medium · Low |
| Due Date | Date | — |
| Status | Select | To Do · In Progress · Done |
| Source | Select | text · voice · photo |
| Notes | Text | — |

Then share the database with your integration (click **···** → **Add connections**).

### 5. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...
TIMEZONE=Asia/Riyadh
MORNING_HOUR=8
MORNING_MINUTE=0
EVENING_HOUR=20
EVENING_MINUTE=0
```

### 6. Run the bot

```bash
python main.py
```

---

## Usage

### Adding tasks

Send any message to your bot:

```
اتصل على العميل بكرة
→ ✅ Added to Notion: Call client — 2024-01-16 — Medium priority 📝

لازم أخلص الريبورت قبل الخميس وهو urgent
→ ✅ Added to Notion: Finish report — 2024-01-18 — High priority 📝

remind me to follow up with Ahmed next week
→ ✅ Added to Notion: Follow up with Ahmed — 2024-01-22 — Medium priority 📝
```

Or send a **voice note** or **photo** of your handwritten list.

### Bot commands

| Command | Description |
|---|---|
| `/start` or `/help` | Welcome message & usage guide |
| `/tasks` | All pending tasks (To Do + In Progress) |
| `/today` | Tasks due today |

### Marking tasks done

```
done        →  bot shows numbered pending list
تم          →  same (Arabic)
done 2      →  marks task #2 as done directly
2           →  marks task #2 (if a list was just shown)
```

---

## Daily Reminders

The bot sends two automatic messages to `TELEGRAM_CHAT_ID`:

- **Morning** (default 08:00) — today's scheduled tasks
- **Evening** (default 20:00) — all still-pending tasks

Adjust the times and timezone in `.env`.

---

## Running as a service (Linux)

```bash
# /etc/systemd/system/taskbot.service
[Unit]
Description=Telegram Task Manager Bot
After=network.target

[Service]
WorkingDirectory=/path/to/telegram-task-manager
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=/path/to/telegram-task-manager/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable taskbot
sudo systemctl start taskbot
sudo journalctl -u taskbot -f    # tail logs
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | — | Your personal chat ID for reminders |
| `ANTHROPIC_API_KEY` | ✅ | — | Claude API key |
| `OPENAI_API_KEY` | ✅ | — | OpenAI Whisper API key |
| `NOTION_API_KEY` | ✅ | — | Notion integration secret |
| `NOTION_DATABASE_ID` | ✅ | — | Notion tasks database ID |
| `TIMEZONE` | ❌ | `UTC` | tz database name (e.g. `Asia/Riyadh`) |
| `MORNING_HOUR` | ❌ | `8` | Hour for morning reminder |
| `MORNING_MINUTE` | ❌ | `0` | Minute for morning reminder |
| `EVENING_HOUR` | ❌ | `20` | Hour for evening reminder |
| `EVENING_MINUTE` | ❌ | `0` | Minute for evening reminder |
