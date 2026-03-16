"""
utils/dedup.py — Deduplication Engine
---------------------------------------
Tracks which projects we've already seen/notified so we don't spam
Telegram with duplicates. Uses a local JSON file as a simple KV store.

In GitHub Actions, the workflow commits this file back to the repo after
each run, so state persists across scheduled runs.
"""

import json
import os
from datetime import datetime, timedelta
from config import SEEN_FILE, SEEN_TTL_DAYS


def _load() -> dict:
    """Load the seen-state dictionary from disk."""
    if not os.path.exists(SEEN_FILE):
        os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
        return {}
    with open(SEEN_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save(data: dict):
    """Persist the seen-state dictionary to disk."""
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _purge_old(data: dict) -> dict:
    """Remove entries older than SEEN_TTL_DAYS to keep the file lean."""
    cutoff = (datetime.utcnow() - timedelta(days=SEEN_TTL_DAYS)).isoformat()
    return {k: v for k, v in data.items() if v.get("first_seen", "") > cutoff}


def is_new(project_id: str) -> bool:
    """
    Return True if this project_id has NOT been seen before.
    Side effect: records the project_id with a timestamp if it IS new.
    
    Think of this like a stamp-card: first time you show up, we stamp
    your card. Every visit after that, we recognize you and skip.
    """
    data = _load()
    data = _purge_old(data)

    if project_id in data:
        # Already stamped — not new
        return False

    # New project — record it
    data[project_id] = {"first_seen": datetime.utcnow().isoformat()}
    _save(data)
    return True


def mark_seen(project_id: str):
    """
    Explicitly mark a project as seen without checking first.
    Useful for batch-marking items you decided not to notify about.
    """
    data = _load()
    data = _purge_old(data)
    data[project_id] = {"first_seen": datetime.utcnow().isoformat()}
    _save(data)


def seen_count() -> int:
    """Return total number of tracked projects."""
    return len(_load())
