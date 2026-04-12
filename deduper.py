import pathfix  # noqa — must be first

import hashlib
from datetime import datetime, timedelta


def content_hash(scholarship: dict) -> str:
    key = (
        f"{scholarship.get('name', '')}"
        f"|{scholarship.get('deadline', '')}"
        f"|{scholarship.get('url', '')}"
        f"|{str(scholarship.get('description', ''))[:100]}"
    )
    return hashlib.md5(key.encode()).hexdigest()


def should_update(existing: dict, new_data: dict) -> bool:
    existing_hash = existing.get("content_hash") or content_hash(existing)
    new_hash = new_data.get("content_hash") or content_hash(new_data)
    if existing_hash != new_hash:
        return True
    last_checked = existing.get("last_checked")
    if last_checked:
        try:
            age = datetime.now() - datetime.fromisoformat(last_checked)
            if age > timedelta(days=7):
                return True
        except ValueError:
            return True
    return False
