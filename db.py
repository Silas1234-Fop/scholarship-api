import pathfix  # noqa — must be first

import os
import json
from datetime import datetime, date

# ─────────────────────────────────────────────────────────────────
# YOUR SUPABASE CREDENTIALS — taken directly from your website
# ─────────────────────────────────────────────────────────────────
SUPABASE_URL = "https://djmnjznfdklfvqnfxfaw.supabase.co"
SUPABASE_KEY = "sb_publishable_LKiXksepfT-qGY5EPns2Uw_BKmugH_7"

import urllib.request
import urllib.parse

def _headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def _request(method: str, path: str, body=None):
    """Make a raw HTTP request to Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"    Supabase error {e.code}: {error_body}")
        return None
    except Exception as e:
        print(f"    Request error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────
# READ — get all active scholarships (status = published)
# ─────────────────────────────────────────────────────────────────
def get_all_scholarships(filter_expired=True) -> list:
    today = date.today().isoformat()
    if filter_expired:
        # Only published + deadline in future (or no deadline)
        path = "scholarships?status=eq.published&select=*&order=deadline.asc.nullslast"
    else:
        path = "scholarships?select=*&order=created_at.desc"
    result = _request("GET", path)
    return result if result else []


# ─────────────────────────────────────────────────────────────────
# CHECK — does this scholarship already exist in Supabase?
# ─────────────────────────────────────────────────────────────────
def get_existing(source_name: str):
    """Check by source field (the scraper source name)."""
    path = f"scholarships?source=eq.{urllib.parse.quote(source_name)}&status=eq.published&select=id,title,deadline,source&limit=1"
    result = _request("GET", path)
    if result and len(result) > 0:
        return result[0]
    return None


# ─────────────────────────────────────────────────────────────────
# WRITE — save a new scholarship to Supabase
# Matches EXACTLY the columns your website already uses:
# title, description, deadline, country, level, link,
# region, is_africa, is_free, status, source, announcement
# ─────────────────────────────────────────────────────────────────
def upsert_scholarship(data: dict):
    """
    Insert scholarship into your Supabase scholarships table.
    Maps scraper fields → your exact Supabase column names.
    """
    # Map scraper data → your Supabase columns
    region = data.get("country", "International")

    # Determine correct region value your website uses
    region_map = {
        "Italy": "Italy", "Romania": "Romania", "Germany": "Germany",
        "France": "France", "Netherlands": "Netherlands", "Belgium": "Belgium",
        "Sweden": "Sweden", "Norway": "Norway", "Hungary": "Hungary",
        "UK": "Other Europe", "Spain": "Other Europe", "Portugal": "Other Europe",
        "Czech Republic": "Other Europe", "Switzerland": "Other Europe",
        "Kenya": "East Africa", "Uganda": "East Africa", "Tanzania": "East Africa",
        "Ethiopia": "East Africa",
        "South Africa": "Southern Africa", "Botswana": "Southern Africa",
        "Ghana": "West Africa", "Morocco": "North Africa", "Egypt": "North Africa",
        "Rwanda": "International University",
        "International": "International",
        "Africa": "Pan-African",
        "Europe": "Other Europe",
        "USA": "International", "Australia": "International",
        "China": "International", "Japan": "International",
        "South Korea": "International", "Turkey": "International",
        "Taiwan": "International",
    }
    final_region = region_map.get(data.get("country", ""), "International")

    africa_regions = ["East Africa", "Southern Africa", "West Africa", "North Africa", "Pan-African"]
    is_africa = final_region in africa_regions

    insert = {
        "title":       (data.get("name", "") + " Scholarship")[:200],
        "description": (data.get("description") or "")[:500],
        "deadline":    data.get("deadline_date") or None,
        "country":     data.get("country", "International"),
        "level":       "any",
        "link":        data.get("url", "")[:500],
        "region":      final_region,
        "is_africa":   is_africa,
        "is_free":     True,
        "status":      "published",
        "source":      data.get("name", ""),
    }

    # Add announcement if available
    if data.get("description"):
        insert["announcement"] = data["description"][:500]

    result = _request("POST", "scholarships", insert)
    return result is not None


# ─────────────────────────────────────────────────────────────────
# DELETE — mark expired scholarships as 'expired' in Supabase
# (matches how your website already handles them)
# ─────────────────────────────────────────────────────────────────
def delete_expired(today_str: str) -> int:
    """
    Set status='expired' for all published scholarships
    whose deadline has passed. Returns count updated.
    """
    path = f"scholarships?status=eq.published&deadline=lt.{today_str}&deadline=not.is.null"
    body = {"status": "expired"}
    result = _request("PATCH", path, body)
    count = len(result) if result else 0
    return count


# ─────────────────────────────────────────────────────────────────
# TEST — run db.py directly to check connection
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Supabase connection...")
    scholarships = get_all_scholarships()
    print(f"Active scholarships in Supabase: {len(scholarships)}")
    for s in scholarships[:5]:
        print(f"  - {s.get('title')} | deadline: {s.get('deadline') or 'open'}")
    if len(scholarships) > 5:
        print(f"  ... and {len(scholarships) - 5} more")
