#!/usr/bin/env python3
"""
Gather full context for unattributed Salesforce opportunities.

Pulls opps + campaign memberships + owner roles + contact info,
outputs a structured JSON context blob for Claude to reason about.

Usage:
    python3 scripts/gather_context.py [--lookback-hours 2] [--limit 50]

Output:
    /tmp/sf_attribution_context.json
"""

import json
import math
import sys
import httpx
from datetime import datetime, timedelta, timezone, date

# ── Auth ──────────────────────────────────────────────────────────────────────
from auth import load_sf_credentials
CLIENT_ID, CLIENT_SECRET, INSTANCE_URL = load_sf_credentials()
API_VERSION = "v62.0"

# ── Config ────────────────────────────────────────────────────────────────────
RECORD_TYPES = ("VSB", "Title", "Insurance")
EXCLUDE_DEMO_TYPES = ()  # Include all demo types including REA Direct
OUTPUT_PATH = "/tmp/sf_attribution_context.json"
SF_BASE_URL = INSTANCE_URL


def current_quarter_label():
    """Return the current quarter label, e.g. 'Q2 2026'."""
    today = date.today()
    q = math.ceil(today.month / 3)
    return f"Q{q} {today.year}"


def get_token(client):
    resp = client.post(f"{INSTANCE_URL}/services/oauth2/token", data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def soql_query(client, headers, soql):
    """Run SOQL with pagination."""
    records = []
    resp = client.get(
        f"{INSTANCE_URL}/services/data/{API_VERSION}/query",
        headers=headers,
        params={"q": soql},
    )
    resp.raise_for_status()
    data = resp.json()
    records.extend(data["records"])
    while not data["done"]:
        resp = client.get(
            f"{INSTANCE_URL}{data['nextRecordsUrl']}",
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        records.extend(data["records"])
    return records


def main():
    # Parse args
    lookback_hours = 2
    limit = 50
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--lookback-hours" and i + 1 < len(args):
            lookback_hours = int(args[i + 1])
        elif arg == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])

    # Calculate lookback timestamp
    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    with httpx.Client(timeout=60) as client:
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        # ── Step 1: Fetch unattributed opportunities ──────────────────────
        rt_filter = "'" + "','".join(RECORD_TYPES) + "'"

        demo_clause = ""
        if EXCLUDE_DEMO_TYPES:
            demo_exclude = " AND ".join(
                f"Demo_Type__c != '{dt}'" for dt in EXCLUDE_DEMO_TYPES
            )
            demo_clause = f"AND ({demo_exclude})"

        opp_soql = f"""
            SELECT Id, Name, RecordType.Name, Demo_Type__c, VSB_Type__c,
                   CampaignId, OwnerId, Owner.Name, Owner.UserRole.Name,
                   Coupon_Used__c, Booked_By__c, StageName,
                   CreatedDate, Amount, Description,
                   Account.Name, Account.Id,
                   Lead_Source_Detail__c,
                   Contact_Conversion_Touch_Source__c,
                   Contact_Conversion_Touch_Source_Detail__c,
                   Engage_Flow_Name__c
            FROM Opportunity
            WHERE RecordType.Name IN ({rt_filter})
              AND LeadSource = null
              {demo_clause}
              AND CreatedDate >= {since_str}
            ORDER BY CreatedDate DESC
            LIMIT {limit}
        """
        opps = soql_query(client, headers, opp_soql)
        print(f"Found {len(opps)} unattributed opps since {since_str}")

        if not opps:
            # Nothing to process — write empty result
            with open(OUTPUT_PATH, "w") as f:
                json.dump({"opps": [], "timestamp": datetime.now(timezone.utc).isoformat()}, f)
            print("No unattributed opps found.")
            return

        # ── Step 2: Get primary contacts for each opp ─────────────────────
        opp_ids = [o["Id"] for o in opps]
        opp_contacts = {}
        for i in range(0, len(opp_ids), 30):
            chunk = opp_ids[i:i + 30]
            id_str = "','".join(chunk)
            recs = soql_query(client, headers,
                f"SELECT OpportunityId, ContactId FROM OpportunityContactRole "
                f"WHERE OpportunityId IN ('{id_str}') AND IsPrimary = true")
            for r in recs:
                opp_contacts[r["OpportunityId"]] = r["ContactId"]

        print(f"Found primary contacts for {len(opp_contacts)}/{len(opps)} opps")

        # ── Step 3: Get ALL campaign memberships for these contacts ───────
        contact_ids = list(set(opp_contacts.values()))
        contact_campaigns = {}  # contact_id -> list of campaign memberships
        if contact_ids:
            for i in range(0, len(contact_ids), 20):
                chunk = contact_ids[i:i + 20]
                id_str = "','".join(chunk)
                recs = soql_query(client, headers, f"""
                    SELECT ContactId, CampaignId, Campaign.Name, Campaign.Type,
                           Campaign_UTM_Campaign__c, Campaign_UTM_Source__c,
                           Campaign_UTM_Medium__c, Campaign_UTM_Content__c,
                           Campaign_UTM_Term__c, Status, CreatedDate
                    FROM CampaignMember
                    WHERE ContactId IN ('{id_str}')
                    ORDER BY CreatedDate DESC
                """)
                for r in recs:
                    cid = r["ContactId"]
                    contact_campaigns.setdefault(cid, []).append(r)

        print(f"Fetched campaign memberships for {len(contact_campaigns)} contacts")

        # ── Step 4: Resolve Booked_By to user names ───────────────────────
        booked_by_ids = {o["Booked_By__c"] for o in opps if o.get("Booked_By__c")}
        booked_by_names = {}
        if booked_by_ids:
            id_str = "','".join(booked_by_ids)
            recs = soql_query(client, headers,
                f"SELECT Id, Name, UserRole.Name FROM User WHERE Id IN ('{id_str}')")
            for r in recs:
                role = (r.get("UserRole") or {}).get("Name", "")
                booked_by_names[r["Id"]] = {"name": r["Name"], "role": role}

        # ── Step 5: Get recent tasks/activities on the contacts ───────────
        contact_activities = {}
        if contact_ids:
            for i in range(0, len(contact_ids), 20):
                chunk = contact_ids[i:i + 20]
                id_str = "','".join(chunk)
                try:
                    recs = soql_query(client, headers, f"""
                        SELECT WhoId, Subject, ActivityDate, Status, Type
                        FROM Task
                        WHERE WhoId IN ('{id_str}')
                        AND CreatedDate = LAST_N_DAYS:30
                        ORDER BY CreatedDate DESC
                    """)
                    for r in recs:
                        wid = r["WhoId"]
                        contact_activities.setdefault(wid, []).append(r)
                except Exception:
                    pass  # Tasks may not be accessible, non-critical

        # ── Step 6: Fetch available attribution campaigns ──────────────────
        # Only pull campaigns for the current quarter
        quarter_label = current_quarter_label()
        print(f"Current quarter: {quarter_label}")
        attribution_campaigns = []
        try:
            recs = soql_query(client, headers, f"""
                SELECT Id, Name, Type FROM Campaign
                WHERE Type IN ('Outreach Sequence', 'Demo Request', 'Hunting License Sign Ups',
                               'Event (3rd Party)', 'Event (In-House)', 'Event (Webinar)',
                               'Direct Sign-Ups', 'Inside Sales')
                AND Name LIKE '%{quarter_label}%'
                ORDER BY Type, Name
            """)
            for r in recs:
                attribution_campaigns.append({
                    "id": r["Id"],
                    "name": r["Name"],
                    "type": r["Type"],
                })
            print(f"Loaded {len(attribution_campaigns)} active attribution campaigns")
        except Exception as e:
            print(f"Warning: couldn't load attribution campaigns: {e}")

        # ── Step 7: Build context blobs ───────────────────────────────────
        results = []
        for opp in opps:
            opp_url = f"{SF_BASE_URL}/{opp['Id']}"
            owner = opp.get("Owner") or {}
            owner_role = (owner.get("UserRole") or {}).get("Name", "")
            account = opp.get("Account") or {}
            contact_id = opp_contacts.get(opp["Id"])

            # Campaign memberships
            cms = contact_campaigns.get(contact_id, [])
            campaign_list = []
            for cm in cms:
                camp = cm.get("Campaign") or {}
                campaign_list.append({
                    "campaign_id": cm.get("CampaignId"),
                    "campaign_name": camp.get("Name", ""),
                    "campaign_type": camp.get("Type", ""),
                    "utm_medium": cm.get("Campaign_UTM_Medium__c"),
                    "utm_source": cm.get("Campaign_UTM_Source__c"),
                    "utm_campaign": cm.get("Campaign_UTM_Campaign__c"),
                    "utm_content": cm.get("Campaign_UTM_Content__c"),
                    "utm_term": cm.get("Campaign_UTM_Term__c"),
                    "member_status": cm.get("Status"),
                    "member_created": cm.get("CreatedDate"),
                })

            # Booked by info
            booked_by = None
            if opp.get("Booked_By__c"):
                bb = booked_by_names.get(opp["Booked_By__c"], {})
                booked_by = {
                    "id": opp["Booked_By__c"],
                    "name": bb.get("name", "Unknown"),
                    "role": bb.get("role", ""),
                }

            # Activities
            activities = []
            if contact_id and contact_id in contact_activities:
                for act in contact_activities[contact_id][:10]:
                    activities.append({
                        "subject": act.get("Subject"),
                        "date": act.get("ActivityDate"),
                        "status": act.get("Status"),
                        "type": act.get("Type"),
                    })

            results.append({
                "opp_id": opp["Id"],
                "opp_name": opp["Name"],
                "sf_url": opp_url,
                "record_type": (opp.get("RecordType") or {}).get("Name", ""),
                "stage": opp.get("StageName"),
                "demo_type": opp.get("Demo_Type__c"),
                "vsb_type": opp.get("VSB_Type__c"),
                "engage_flow_name": opp.get("Engage_Flow_Name__c"),
                "coupon_used": opp.get("Coupon_Used__c"),
                "created_date": opp.get("CreatedDate"),
                "amount": opp.get("Amount"),
                "description": opp.get("Description"),
                "owner": {
                    "name": owner.get("Name", ""),
                    "role": owner_role,
                },
                "booked_by": booked_by,
                "account": {
                    "id": account.get("Id"),
                    "name": account.get("Name", ""),
                },
                "campaign_id_on_opp": opp.get("CampaignId"),
                "contact_id": contact_id,
                "campaign_memberships": campaign_list,
                "recent_activities": activities,
            })

        output = {
            "opps": results,
            "attribution_campaigns": attribution_campaigns,
            "current_quarter": quarter_label,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lookback_hours": lookback_hours,
        }
        with open(OUTPUT_PATH, "w") as f:
            json.dump(output, f, indent=2, default=str)

        print(f"\nContext for {len(results)} opps saved to {OUTPUT_PATH}")
        for r in results:
            cm_count = len(r["campaign_memberships"])
            print(f"  {r['opp_name'][:50]:50s} | {r['demo_type'] or '?':10s} | {cm_count} campaigns")
            print(f"    {r['sf_url']}")


if __name__ == "__main__":
    main()
