#!/usr/bin/env python3
"""
Clone Salesforce campaigns from one quarter to the next.

Usage:
    Edit the constants below, then run:
    core/mcp/.venv/bin/python3.14 scripts/clone_campaigns.py

Output:
    /tmp/sf_clone_results.json  — source_id → new_id mapping for parent remapping
"""

import json
import httpx

# ── Auth ──────────────────────────────────────────────────────────────────────
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
INSTANCE_URL = "https://homebot.my.salesforce.com"
API_VERSION = "v62.0"

# ── Quarter config ─────────────────────────────────────────────────────────────
SOURCE_QUARTER = "Q1 2026"
TARGET_QUARTER = "Q2 2026"
TARGET_START = "2026-04-01"
TARGET_END = "2026-06-30"

# ── Source campaign IDs to clone ───────────────────────────────────────────────
# Paste the list of source campaign IDs here.
# Optional: set PARENT_OVERRIDE to force a specific ParentId on all clones,
# or leave as None to inherit and remap via remap_parents.py.
SOURCE_IDS = [
    # "701Qo00001XXXXXXIAX",
]
PARENT_OVERRIDE = None  # e.g. "701Qo00001Ru2lXIAR" for ABM - Q2 2026

# ── Fields to copy from source ─────────────────────────────────────────────────
CLONE_FIELDS = [
    "Type", "IsActive", "Description", "ExpectedRevenue",
    "BudgetedCost", "ActualCost", "ExpectedResponse",
    "NumberSent", "CampaignMemberRecordTypeId",
]


def get_token(client):
    resp = client.post(f"{INSTANCE_URL}/services/oauth2/token", data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def main():
    results = {"successes": [], "failures": []}

    with httpx.Client(timeout=30) as client:
        token = get_token(client)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        for source_id in SOURCE_IDS:
            # Fetch source
            resp = client.get(
                f"{INSTANCE_URL}/services/data/{API_VERSION}/sobjects/Campaign/{source_id}",
                headers=headers,
            )
            resp.raise_for_status()
            source = resp.json()

            clone_name = source["Name"].replace(SOURCE_QUARTER, TARGET_QUARTER)
            payload = {
                "Name": clone_name,
                "StartDate": TARGET_START,
                "EndDate": TARGET_END,
                "Status": "In Progress",
            }

            if PARENT_OVERRIDE:
                payload["ParentId"] = PARENT_OVERRIDE
            elif source.get("ParentId"):
                payload["ParentId"] = source["ParentId"]

            for field in CLONE_FIELDS:
                if source.get(field) is not None:
                    payload[field] = source[field]

            # Create clone
            create_resp = client.post(
                f"{INSTANCE_URL}/services/data/{API_VERSION}/sobjects/Campaign",
                headers=headers,
                json=payload,
            )

            if create_resp.status_code == 201:
                new_id = create_resp.json()["id"]
                print(f"  ✓ {clone_name}  →  {new_id}")
                results["successes"].append({
                    "success": True,
                    "source_id": source_id,
                    "source_name": source["Name"],
                    "new_id": new_id,
                    "new_name": clone_name,
                })
            else:
                print(f"  ✗ {source['Name']}: {create_resp.status_code} {create_resp.text}")
                results["failures"].append({
                    "source_id": source_id,
                    "source_name": source["Name"],
                    "error": create_resp.text,
                })

    output_path = "/tmp/sf_clone_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDone: {len(results['successes'])} cloned, {len(results['failures'])} failed")
    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
