#!/usr/bin/env python3
"""
Gap check: compare all source-quarter campaigns against what was cloned.
Surfaces campaigns that were missed and categorizes them.

Usage:
    Edit SOURCE_QUARTER and CLONED_IDS below, then run:
    core/mcp/.venv/bin/python3.14 scripts/gap_check.py

Or load CLONED_IDS automatically from /tmp/sf_clone_results.json if it exists.
"""

import json
import httpx
from datetime import date, datetime

# ── Auth ──────────────────────────────────────────────────────────────────────
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
INSTANCE_URL = "https://homebot.my.salesforce.com"
API_VERSION = "v62.0"

# ── Config ────────────────────────────────────────────────────────────────────
SOURCE_QUARTER = "Q1 2026"

# Load from results file automatically, or paste IDs manually
RESULTS_PATH = "/tmp/sf_clone_results.json"

# Campaigns to always skip (adjust as needed)
SKIP_KEYWORDS = ["vday", "valentine", "v-day"]

# Events: campaigns shorter than this many days are considered point-in-time
EVENT_DURATION_THRESHOLD_DAYS = 7


def get_token(client):
    resp = client.post(f"{INSTANCE_URL}/services/oauth2/token", data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


def is_event(camp):
    start = parse_date(camp.get("StartDate"))
    end = parse_date(camp.get("EndDate"))
    if not start or not end:
        return False
    return (end - start).days < EVENT_DURATION_THRESHOLD_DAYS


def is_skip(camp):
    name_lower = camp["Name"].lower()
    return any(kw in name_lower for kw in SKIP_KEYWORDS)


def main():
    # Load already-cloned source IDs
    cloned_source_ids = set()
    try:
        with open(RESULTS_PATH) as f:
            results = json.load(f)
        cloned_source_ids = {r["source_id"] for r in results.get("successes", [])}
        print(f"Loaded {len(cloned_source_ids)} cloned IDs from {RESULTS_PATH}\n")
    except FileNotFoundError:
        print(f"No results file at {RESULTS_PATH} — comparing against empty set.\n")

    with httpx.Client(timeout=30) as client:
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Fetch all source-quarter campaigns
        soql = (
            f"SELECT Id, Name, StartDate, EndDate, Status, ParentId "
            f"FROM Campaign WHERE Name LIKE '%{SOURCE_QUARTER}%' ORDER BY Name"
        )
        resp = client.get(
            f"{INSTANCE_URL}/services/data/{API_VERSION}/query",
            headers=headers,
            params={"q": soql},
        )
        resp.raise_for_status()
        all_q1 = resp.json()["records"]

    print(f"Total {SOURCE_QUARTER} campaigns: {len(all_q1)}\n")

    cloned = []
    events = []
    skipped = []
    missed = []

    for camp in all_q1:
        cid = camp["Id"]
        if cid in cloned_source_ids:
            cloned.append(camp)
        elif is_skip(camp):
            skipped.append(camp)
        elif is_event(camp):
            events.append(camp)
        else:
            missed.append(camp)

    print(f"✅ Cloned        : {len(cloned)}")
    print(f"⏭  Events/skipped: {len(events) + len(skipped)}")
    print(f"❌ Not cloned    : {len(missed)}\n")

    if events:
        print("── Events (correctly skipped) ──────────────────────────────")
        for c in events:
            print(f"  {c['Name']}  ({c.get('StartDate')} → {c.get('EndDate')})")
        print()

    if skipped:
        print("── VDay/promo (intentionally excluded) ─────────────────────")
        for c in skipped:
            print(f"  {c['Name']}")
        print()

    if missed:
        print("── NOT CLONED — review needed ───────────────────────────────")
        for c in missed:
            print(f"  [{c['Id']}]  {c['Name']}")
            print(f"    Dates: {c.get('StartDate')} → {c.get('EndDate')}  |  Parent: {c.get('ParentId')}")
        print()
        print(f"Action: confirm with user which of the {len(missed)} missed campaigns to clone.")
    else:
        print("All non-event, non-excluded campaigns are covered. ✓")


if __name__ == "__main__":
    main()
