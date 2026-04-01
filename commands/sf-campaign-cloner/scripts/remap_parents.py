#!/usr/bin/env python3
"""
Remap ParentIds on cloned campaigns so they point to new-quarter parents.

Reads /tmp/sf_clone_results.json (output of clone_campaigns.py), builds a
source_id → new_id map, then PATCHes any cloned campaign whose ParentId
appears as a source_id in the map.

Usage:
    core/mcp/.venv/bin/python3.14 scripts/remap_parents.py
"""

import json
import httpx

# ── Auth ──────────────────────────────────────────────────────────────────────
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
INSTANCE_URL = "https://homebot.my.salesforce.com"
API_VERSION = "v62.0"

RESULTS_PATH = "/tmp/sf_clone_results.json"


def get_token(client):
    resp = client.post(f"{INSTANCE_URL}/services/oauth2/token", data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def main():
    with open(RESULTS_PATH) as f:
        results = json.load(f)

    successes = results.get("successes", [])
    source_to_new = {r["source_id"]: r["new_id"] for r in successes}
    new_ids = [r["new_id"] for r in successes]

    if not new_ids:
        print("No cloned campaigns found in results file.")
        return

    with httpx.Client(timeout=30) as client:
        token = get_token(client)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Fetch current ParentIds for all new campaigns
        all_campaigns = []
        chunk_size = 30
        for i in range(0, len(new_ids), chunk_size):
            chunk = new_ids[i:i + chunk_size]
            id_list = "','".join(chunk)
            soql = f"SELECT Id, Name, ParentId FROM Campaign WHERE Id IN ('{id_list}')"
            resp = client.get(
                f"{INSTANCE_URL}/services/data/{API_VERSION}/query",
                headers=headers,
                params={"q": soql},
            )
            resp.raise_for_status()
            all_campaigns.extend(resp.json()["records"])

        print(f"Fetched {len(all_campaigns)} cloned campaigns\n")

        to_update = []
        no_parent = []
        no_match = []

        for camp in all_campaigns:
            pid = camp.get("ParentId")
            if not pid:
                no_parent.append(camp["Name"])
            elif pid in source_to_new:
                to_update.append({
                    "id": camp["Id"],
                    "name": camp["Name"],
                    "old_parent": pid,
                    "new_parent": source_to_new[pid],
                })
            else:
                no_match.append({"name": camp["Name"], "parent_id": pid})

        print(f"Need remapping : {len(to_update)}")
        print(f"No parent      : {len(no_parent)} (top-level)")
        print(f"Unrecognized   : {len(no_match)} (manual review)\n")

        if no_match:
            print("Campaigns with unrecognized parents (may already be correct):")
            for c in no_match:
                print(f"  {c['name']}  →  parent {c['parent_id']}")
            print()

        if not to_update:
            print("Nothing to remap.")
            return

        print("Applying ParentId updates...")
        success_count = 0
        fail_count = 0
        for u in to_update:
            resp = client.patch(
                f"{INSTANCE_URL}/services/data/{API_VERSION}/sobjects/Campaign/{u['id']}",
                headers=headers,
                json={"ParentId": u["new_parent"]},
            )
            if resp.status_code == 204:
                print(f"  ✓ {u['name']}")
                success_count += 1
            else:
                print(f"  ✗ {u['name']}: {resp.status_code} {resp.text}")
                fail_count += 1

        print(f"\nDone: {success_count} remapped, {fail_count} failed")


if __name__ == "__main__":
    main()
