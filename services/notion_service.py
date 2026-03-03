"""
Notion API service for task CRUD operations.

Expected database schema
────────────────────────
Property name  │ Notion type
───────────────┼────────────
Title          │ title       (built-in)
Priority       │ select      options: High | Medium | Low
Due Date       │ date
Status         │ select      options: To Do | In Progress | Done
Source         │ select      options: text | voice | photo
Notes          │ rich_text

Run setup_notion_database() once to create the database automatically,
or create it manually and paste the database ID into .env.
"""
import logging
from datetime import date

from notion_client import Client

from config import NOTION_API_KEY, NOTION_DATABASE_ID

logger = logging.getLogger(__name__)

notion = Client(auth=NOTION_API_KEY)

# ──────────────────────────────────────────────────────────────────────────────
# Dynamic title property name lookup
# ──────────────────────────────────────────────────────────────────────────────

_title_prop_name: str | None = None


def _get_title_property_name() -> str:
    """
    Return the name of the title-type property in the Notion database.

    Notion databases always have exactly one title property, but its *display
    name* varies: "Title", "Name", "Task name", etc.  This function queries
    the database schema once, caches the result, and returns the correct name
    so the code works regardless of how the user named that column.
    """
    global _title_prop_name
    if _title_prop_name is not None:
        return _title_prop_name
    try:
        db = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        for name, prop in db["properties"].items():
            if prop.get("type") == "title":
                _title_prop_name = name
                logger.info("Notion title property detected: %r", name)
                return name
    except Exception as exc:
        logger.warning("Could not retrieve Notion DB schema: %s — falling back to 'Title'", exc)
    _title_prop_name = "Title"
    return _title_prop_name


# ──────────────────────────────────────────────────────────────────────────────
# Write operations
# ──────────────────────────────────────────────────────────────────────────────

def add_task(
    title: str,
    priority: str = "Medium",
    due_date: str | None = None,
    status: str = "To Do",
    source: str = "text",
    notes: str | None = None,
) -> str:
    """
    Create a new task page in the Notion database.

    Returns:
        The new page's Notion ID (UUID string).
    """
    properties: dict = {
        _get_title_property_name(): {
            "title": [{"text": {"content": title}}]
        },
        "Priority": {
            "select": {"name": priority}
        },
        "Status": {
            "select": {"name": status}
        },
        "Source": {
            "select": {"name": source}
        },
    }

    if due_date:
        properties["Due Date"] = {"date": {"start": due_date}}

    if notes:
        properties["Notes"] = {
            "rich_text": [{"text": {"content": notes[:2000]}}]
        }

    page = notion.pages.create(
        parent={"database_id": NOTION_DATABASE_ID},
        properties=properties,
    )
    page_id: str = page["id"]
    logger.info("Created Notion task '%s' (id=%s)", title, page_id)
    return page_id


def mark_task_done(page_id: str) -> None:
    """Update a task's Status to 'Done'."""
    notion.pages.update(
        page_id=page_id,
        properties={"Status": {"select": {"name": "Done"}}},
    )
    logger.info("Marked task %s as Done", page_id)


def mark_task_in_progress(page_id: str) -> None:
    """Update a task's Status to 'In Progress'."""
    notion.pages.update(
        page_id=page_id,
        properties={"Status": {"select": {"name": "In Progress"}}},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Read operations
# ──────────────────────────────────────────────────────────────────────────────

def get_tasks_for_today() -> list[dict]:
    """Return all non-done tasks whose Due Date is today."""
    today = date.today().isoformat()
    response = notion.databases.query(
        database_id=NOTION_DATABASE_ID,
        filter={
            "and": [
                {"property": "Due Date", "date": {"equals": today}},
                {"property": "Status", "select": {"does_not_equal": "Done"}},
            ]
        },
        sorts=[{"property": "Priority", "direction": "descending"}],
    )
    return _parse_pages(response["results"])


def get_pending_tasks() -> list[dict]:
    """Return all tasks with Status = 'To Do' or 'In Progress'."""
    response = notion.databases.query(
        database_id=NOTION_DATABASE_ID,
        filter={
            "or": [
                {"property": "Status", "select": {"equals": "To Do"}},
                {"property": "Status", "select": {"equals": "In Progress"}},
            ]
        },
        sorts=[
            {"property": "Due Date", "direction": "ascending"},
            {"property": "Priority", "direction": "descending"},
        ],
    )
    return _parse_pages(response["results"])


def get_all_tasks() -> list[dict]:
    """Return all tasks regardless of status."""
    response = notion.databases.query(
        database_id=NOTION_DATABASE_ID,
        sorts=[{"property": "Due Date", "direction": "ascending"}],
    )
    return _parse_pages(response["results"])


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _safe_select(prop: dict) -> str | None:
    sel = prop.get("select")
    return sel["name"] if sel else None


def _safe_title(prop: dict) -> str:
    parts = prop.get("title", [])
    return parts[0]["text"]["content"] if parts else "Untitled"


def _safe_rich_text(prop: dict) -> str | None:
    parts = prop.get("rich_text", [])
    return parts[0]["text"]["content"] if parts else None


def _safe_date(prop: dict) -> str | None:
    d = prop.get("date")
    return d["start"] if d else None


def _parse_pages(results: list) -> list[dict]:
    tasks = []
    for page in results:
        props = page["properties"]
        tasks.append(
            {
                "id": page["id"],
                "title": _safe_title(props.get(_get_title_property_name(), {})),
                "priority": _safe_select(props.get("Priority", {})) or "Medium",
                "status": _safe_select(props.get("Status", {})) or "To Do",
                "source": _safe_select(props.get("Source", {})) or "text",
                "due_date": _safe_date(props.get("Due Date", {})),
                "notes": _safe_rich_text(props.get("Notes", {})),
            }
        )
    return tasks


# ──────────────────────────────────────────────────────────────────────────────
# One-time database setup (optional)
# ──────────────────────────────────────────────────────────────────────────────

def setup_notion_database(parent_page_id: str) -> str:
    """
    Create the tasks database under a given Notion page.
    Call this once from a setup script; not needed if you create the DB manually.

    Args:
        parent_page_id: The Notion page ID that will contain the database.

    Returns:
        The newly created database ID.
    """
    db = notion.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "Task Manager"}}],
        properties={
            "Title": {"title": {}},
            "Priority": {
                "select": {
                    "options": [
                        {"name": "High", "color": "red"},
                        {"name": "Medium", "color": "yellow"},
                        {"name": "Low", "color": "green"},
                    ]
                }
            },
            "Due Date": {"date": {}},
            "Status": {
                "select": {
                    "options": [
                        {"name": "To Do", "color": "gray"},
                        {"name": "In Progress", "color": "blue"},
                        {"name": "Done", "color": "green"},
                    ]
                }
            },
            "Source": {
                "select": {
                    "options": [
                        {"name": "text", "color": "default"},
                        {"name": "voice", "color": "purple"},
                        {"name": "photo", "color": "orange"},
                    ]
                }
            },
            "Notes": {"rich_text": {}},
        },
    )
    db_id: str = db["id"]
    logger.info("Created Notion database: %s", db_id)
    return db_id
