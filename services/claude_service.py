"""
Claude AI service for natural language task extraction.
Supports Arabic, English, and mixed (code-switched) input.
Also handles image OCR via Claude Vision.
"""
import json
import re
import base64
import logging
from datetime import date

import anthropic

from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

TASK_EXTRACTION_PROMPT = """\
You are an intelligent task extraction assistant.

Analyze the message below and extract all tasks from it.
The message may be in Arabic, English, or a mix of both (Arabizi / code-switching).

Today's date: {today}

Priority rules:
- High  → urgent / عاجل / ضروري / مهم جداً / ASAP / critical / before a very close deadline
- Medium → tomorrow / بكرة / next week / الأسبوع الجاي / normal
- Low   → whenever / في وقت فراغ / later / مافي تاريخ محدد

Due date rules:
- Convert relative expressions (tomorrow, next week, الخميس…) to ISO 8601 (YYYY-MM-DD) based on today.
- If no due date is mentioned, return null.

Return ONLY a valid JSON array — no markdown fences, no extra text.
Each element must have exactly these keys:
  "title"    : string  — concise task title in English
  "priority" : string  — "High" | "Medium" | "Low"
  "due_date" : string | null  — "YYYY-MM-DD" or null
  "notes"    : string | null  — any extra context, or null

Examples:
  Input:  "اتصل على العميل بكرة"
  Output: [{"title":"Call client","priority":"Medium","due_date":"<tomorrow>","notes":null}]

  Input:  "لازم أخلص الريبورت قبل الخميس وهو urgent"
  Output: [{"title":"Finish report","priority":"High","due_date":"<next Thursday>","notes":null}]

  Input:  "remind me to follow up with Ahmed next week"
  Output: [{"title":"Follow up with Ahmed","priority":"Medium","due_date":"<next Monday>","notes":null}]

Message:
{message}
"""

IMAGE_TASK_PROMPT = """\
You are an intelligent task extraction assistant.

First, perform OCR on this image and extract all visible text.
Then analyze the extracted text for tasks (notes, to-do lists, reminders, etc.).

Today's date: {today}

Return ONLY a valid JSON array — no markdown fences, no extra text.
Each element must have exactly these keys:
  "title"    : string  — concise task title in English
  "priority" : string  — "High" | "Medium" | "Low"
  "due_date" : string | null  — "YYYY-MM-DD" or null
  "notes"    : string | null  — any extra context, or null

If no tasks are found, return an empty array: []
"""


def _parse_json_response(text: str) -> list:
    """Robustly extract a JSON array from Claude's response."""
    text = text.strip()

    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    patterns = [
        r"```json\s*([\s\S]*?)\s*```",
        r"```\s*([\s\S]*?)\s*```",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

    # Find first [...] block
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    logger.error("Could not parse JSON from Claude response: %s", text[:500])
    return []


def extract_tasks(text: str, source: str = "text") -> list[dict]:
    """
    Extract structured tasks from a text message using Claude.

    Args:
        text:   The user's raw message (Arabic, English, or mixed).
        source: 'text' | 'voice' | 'photo'

    Returns:
        List of task dicts with keys: title, priority, due_date, notes, source.
    """
    today = date.today().isoformat()
    prompt = TASK_EXTRACTION_PROMPT.format(today=today, message=text)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    tasks = _parse_json_response(raw)

    for task in tasks:
        task["source"] = source
        # Normalise priority casing
        task["priority"] = task.get("priority", "Medium").capitalize()
        if task["priority"] not in ("High", "Medium", "Low"):
            task["priority"] = "Medium"

    logger.info("Extracted %d task(s) from %s message", len(tasks), source)
    return tasks


def extract_tasks_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> list[dict]:
    """
    OCR + task extraction from an image using Claude Vision.

    Args:
        image_bytes: Raw bytes of the image file.
        mime_type:   MIME type of the image (image/jpeg, image/png, etc.).

    Returns:
        List of task dicts with source='photo'.
    """
    today = date.today().isoformat()
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": IMAGE_TASK_PROMPT.format(today=today),
                    },
                ],
            }
        ],
    )

    raw = response.content[0].text
    tasks = _parse_json_response(raw)

    for task in tasks:
        task["source"] = "photo"
        task["priority"] = task.get("priority", "Medium").capitalize()
        if task["priority"] not in ("High", "Medium", "Low"):
            task["priority"] = "Medium"

    logger.info("Extracted %d task(s) from photo", len(tasks))
    return tasks
