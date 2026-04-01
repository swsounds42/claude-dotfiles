#!/usr/bin/env python3
"""
Apply attribution decisions to Salesforce opportunities.

Reads /tmp/sf_attribution_decisions.json (output of Claude's reasoning),
PATCHes the opportunities, and logs results.

Usage:
    python3 scripts/apply_attribution.py [--dry-run]
"""

import json
import os
import sys
import httpx
from datetime import datetime, timezone

# ── Auth ──────────────────────────────────────────────────────────────────────
from auth import load_sf_credentials
CLIENT_ID, CLIENT_SECRET, INSTANCE_URL = load_sf_credentials()
API_VERSION = "v62.0"

DECISIONS_PATH = "/tmp/sf_attribution_decisions.json"
LOG_PATH = os.path.expanduser("~/Desktop/personal-os-main/Knowledge/sf-attribution/attribution_log.jsonl")
SF_BASE_URL = INSTANCE_URL


def get_token(client):
    resp = client.post(f"{INSTANCE_URL}/services/oauth2/token", data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def main():
    dry_run = "--dry-run" in sys.argv

    with open(DECISIONS_PATH) as f:
        decisions = json.load(f)

    if not decisions:
        print("No decisions to apply.")
        return

    auto_apply = [d for d in decisions if d.get("action") == "auto_apply"]
    needs_review = [d for d in decisions if d.get("action") == "needs_review"]
    skip = [d for d in decisions if d.get("action") == "skip"]

    print(f"Decisions loaded: {len(decisions)} total")
    print(f"  Auto-apply  : {len(auto_apply)}")
    print(f"  Needs review: {len(needs_review)}")
    print(f"  Skip        : {len(skip)}")
    print()

    if dry_run:
        print("── DRY RUN — no changes will be made ──")
        print()
        for d in auto_apply:
            opp_url = f"{SF_BASE_URL}/{d['opp_id']}"
            print(f"  WOULD UPDATE: {d['opp_name'][:50]}")
            print(f"    {opp_url}")
            print(f"    LeadSource: {d['lead_source']}")
            print(f"    Lead_Source_Detail: {d['lead_source_detail']}")
            print(f"    Touch Source: {d.get('touch_source', '(none)')}")
            print(f"    Confidence: {d['confidence']} | Reason: {d['reasoning'][:80]}")
            print()
        if needs_review:
            print("  NEEDS REVIEW:")
            for d in needs_review:
                opp_url = f"{SF_BASE_URL}/{d['opp_id']}"
                print(f"    {d['opp_name'][:50]}")
                print(f"    {opp_url}")
                print(f"    Reason: {d['reasoning'][:100]}")
        return

    with httpx.Client(timeout=30) as client:
        token = get_token(client)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        success_count = 0
        fail_count = 0
        skip_count = 0

        for d in auto_apply:
            # Overwrite protection: verify LeadSource is still null
            check_resp = client.get(
                f"{INSTANCE_URL}/services/data/{API_VERSION}/sobjects/Opportunity/{d['opp_id']}",
                headers={"Authorization": f"Bearer {token}"},
                params={"fields": "LeadSource"},
            )
            if check_resp.status_code == 404:
                print(f"  ⊘ {d['opp_name'][:50]} — opp deleted/merged, skipping")
                skip_count += 1
                continue
            if check_resp.status_code == 200 and check_resp.json().get("LeadSource") is not None:
                print(f"  ⊘ {d['opp_name'][:50]} — already attributed by someone else, skipping")
                skip_count += 1
                continue
            payload = {
                "LeadSource": d["lead_source"],
            }
            if d.get("lead_source_detail"):
                payload["Lead_Source_Detail__c"] = d["lead_source_detail"]
            if d.get("touch_source"):
                payload["Contact_Conversion_Touch_Source__c"] = d["touch_source"]
            if d.get("touch_source_detail"):
                payload["Contact_Conversion_Touch_Source_Detail__c"] = d["touch_source_detail"]
            if d.get("touch_source_detail_2"):
                payload["Contact_Conversion_Touch_Source_Detail_2__c"] = d["touch_source_detail_2"]
            if d.get("campaign_id"):
                payload["CampaignId"] = d["campaign_id"]

            resp = client.patch(
                f"{INSTANCE_URL}/services/data/{API_VERSION}/sobjects/Opportunity/{d['opp_id']}",
                headers=headers,
                json=payload,
            )

            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "opp_id": d["opp_id"],
                "opp_name": d["opp_name"],
                "action": "applied",
                "payload": payload,
                "confidence": d["confidence"],
                "reasoning": d["reasoning"],
                "status_code": resp.status_code,
            }

            opp_url = f"{SF_BASE_URL}/{d['opp_id']}"
            if resp.status_code == 204:
                print(f"  ✓ {d['opp_name'][:50]} → {d['lead_source']}")
                print(f"    {opp_url}")
                success_count += 1
            else:
                print(f"  ✗ {d['opp_name'][:50]} → {resp.status_code}: {resp.text[:100]}")
                print(f"    {opp_url}")
                log_entry["error"] = resp.text
                fail_count += 1

            # Append to log
            with open(LOG_PATH, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

        # Log needs_review items
        for d in needs_review:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "opp_id": d["opp_id"],
                "opp_name": d["opp_name"],
                "action": "needs_review",
                "suggested_lead_source": d.get("lead_source"),
                "confidence": d["confidence"],
                "reasoning": d["reasoning"],
            }
            with open(LOG_PATH, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

        print(f"\nDone: {success_count} applied, {fail_count} failed, {skip_count} skipped, {len(needs_review)} need review")
        print(f"Log appended to {LOG_PATH}")


if __name__ == "__main__":
    main()
