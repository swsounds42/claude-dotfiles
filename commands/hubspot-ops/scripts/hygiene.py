#!/usr/bin/env python3
"""HubSpot Contact Hygiene Checker.

Scans recent paid social/search leads for common data quality issues.
Designed to replicate the manual review of the "Paid Social & Search Leads"
list view (38147346), sorted by recent_conversion_date.

Usage:
    python3 hygiene.py scan [--days N] [--limit N]
    python3 hygiene.py detail CONTACT_ID
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import get_headers, BASE_URL


# ---------------------------------------------------------------------------
# Property sets
# ---------------------------------------------------------------------------

SCAN_PROPERTIES = [
    "email", "firstname", "lastname",
    # Lifecycle & qualification
    "lifecyclestage", "hs_lifecyclestage_marketingqualifiedlead_date",
    "hs_lead_status",
    # Conversion
    "recent_conversion_event_name", "recent_conversion_date",
    "conversion_type", "conversion_touch_source",
    # UTM fields (first-touch)
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    # UTM fields (last-click / LC)
    "lc_utm_source", "lc_utm_medium", "lc_utm_campaign",
    # Analytics
    "hs_analytics_source", "hs_analytics_source_data_1", "hs_analytics_source_data_2",
    "hs_latest_source", "hs_latest_source_data_1", "hs_latest_source_data_2",
    # Object source
    "hs_object_source", "hs_object_source_detail_1",
    # Attribution
    "leadsource", "lead_source_detail",
    # Customer state
    "hb_customer_state",
    # Owner
    "hubspot_owner_id",
]

# Known valid lifecycle stage values (text labels)
VALID_LIFECYCLE = {
    "subscriber", "lead", "marketingqualifiedlead",
    "salesqualifiedlead", "opportunity", "customer",
    "evangelist", "other",
}

# Lifecycle stages stored as numeric IDs (custom stages)
LIFECYCLE_ID_MAP = {
    "122237331": "Unqualified",
}


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_request(method, path, body=None):
    """Make an authenticated HubSpot API request."""
    url = f"{BASE_URL}{path}"
    headers = get_headers()
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def search_contacts(filter_groups, properties, sorts, limit=100):
    """Search contacts with pagination."""
    all_results = []
    after = 0

    while True:
        body = {
            "filterGroups": filter_groups,
            "properties": properties,
            "sorts": sorts,
            "limit": min(limit - len(all_results), 100),
            "after": after,
        }
        result = api_request("POST", "/crm/v3/objects/contacts/search", body=body)
        contacts = result.get("results", [])
        all_results.extend(contacts)

        if len(all_results) >= limit or not result.get("paging"):
            break

        after = result["paging"]["next"]["after"]

    return all_results, result.get("total", len(all_results))


# ---------------------------------------------------------------------------
# Hygiene rules
# ---------------------------------------------------------------------------

def check_contact(props):
    """Run all hygiene checks on a contact. Returns list of issues."""
    issues = []

    # 1. Lifecycle stage stored as numeric ID instead of text
    lc = props.get("lifecyclestage", "")
    if lc and lc not in VALID_LIFECYCLE:
        label = LIFECYCLE_ID_MAP.get(lc, f"unknown ({lc})")
        issues.append({
            "rule": "lifecycle_numeric_id",
            "severity": "info",
            "message": f"Lifecycle stage is custom ID: {lc} = {label}",
            "field": "lifecyclestage",
            "current": lc,
        })

    # 2. MQL with no MQL date
    if lc == "marketingqualifiedlead":
        mql_date = props.get("hs_lifecyclestage_marketingqualifiedlead_date")
        if not mql_date:
            issues.append({
                "rule": "mql_no_date",
                "severity": "warning",
                "message": "Lifecycle is MQL but MQL date is empty",
                "field": "hs_lifecyclestage_marketingqualifiedlead_date",
                "current": None,
            })

    # 3. Missing conversion_type
    conv = props.get("recent_conversion_event_name", "")
    if conv and not props.get("conversion_type"):
        # Suggest based on conversion name
        suggested = None
        conv_lower = conv.lower()
        if "demo" in conv_lower:
            suggested = "Demo"
        elif "sign up" in conv_lower or "signup" in conv_lower:
            suggested = "Direct Sign-Up"
        elif "opt in" in conv_lower or "opt-in" in conv_lower:
            suggested = "Opt In"
        elif "workshop" in conv_lower or "webinar" in conv_lower:
            suggested = "Event"

        issues.append({
            "rule": "missing_conversion_type",
            "severity": "warning",
            "message": f"Has conversion ({conv[:50]}) but conversion_type is empty",
            "field": "conversion_type",
            "current": None,
            "suggested": suggested,
        })

    # 4. Missing touch source when UTMs exist
    has_utm_signal = props.get("lc_utm_source") or props.get("lc_utm_medium") or props.get("utm_source")
    if has_utm_signal and not props.get("conversion_touch_source"):
        # Suggest touch source from UTM data
        lc_medium = (props.get("lc_utm_medium") or "").lower()
        lc_source = (props.get("lc_utm_source") or "").lower()
        analytics = (props.get("hs_analytics_source") or "").upper()

        suggested = None
        if "paidsocial" in lc_medium or analytics == "PAID_SOCIAL":
            suggested = "Paid Social"
        elif "paidsearch" in lc_medium or "cpc" in lc_medium or analytics == "PAID_SEARCH":
            suggested = "Paid Search"
        elif "organic" in lc_medium or analytics == "ORGANIC_SEARCH":
            suggested = "Organic"
        elif "email" in lc_medium or analytics == "EMAIL_MARKETING":
            suggested = "Nurture"
        elif lc_source == "direct" or analytics == "DIRECT_TRAFFIC":
            suggested = "Direct"

        issues.append({
            "rule": "missing_touch_source",
            "severity": "warning",
            "message": f"Has UTM data but conversion_touch_source is empty",
            "field": "conversion_touch_source",
            "current": None,
            "suggested": suggested,
        })

    # 5. UTM normalization — lc_utm_source has placeholder values
    lc_src = props.get("lc_utm_source", "") or ""
    lc_camp = props.get("lc_utm_campaign", "") or ""
    if "{{" in lc_src or "{{" in lc_camp:
        issues.append({
            "rule": "utm_placeholder",
            "severity": "error",
            "message": f"UTM fields contain unresolved placeholders: src={lc_src}, campaign={lc_camp}",
            "field": "lc_utm_source / lc_utm_campaign",
            "current": f"{lc_src} / {lc_camp}",
        })

    # 6. Source mismatch — analytics says paid but latest says direct
    analytics_source = (props.get("hs_analytics_source") or "").upper()
    latest_source = (props.get("hs_latest_source") or "").upper()
    if analytics_source in ("PAID_SOCIAL", "PAID_SEARCH") and latest_source == "DIRECT_TRAFFIC":
        issues.append({
            "rule": "source_mismatch",
            "severity": "info",
            "message": f"Original source is {analytics_source} but latest source is DIRECT_TRAFFIC (likely re-visited directly)",
            "field": "hs_latest_source",
            "current": latest_source,
        })

    # 7. Missing lead source
    if not props.get("leadsource") and conv:
        issues.append({
            "rule": "missing_lead_source",
            "severity": "warning",
            "message": "Has conversion activity but leadsource is empty",
            "field": "leadsource",
            "current": None,
        })

    # 8. Active customer in lead gen workflow
    state = (props.get("hb_customer_state") or "").lower()
    if state in ("active", "archived"):
        issues.append({
            "rule": "existing_customer",
            "severity": "info",
            "message": f"Contact is an existing customer (state={state})",
            "field": "hb_customer_state",
            "current": state,
        })

    return issues


# ---------------------------------------------------------------------------
# UTM fix logic
# ---------------------------------------------------------------------------

# Source derivation: hs_analytics_source_data_1 -> lc_utm_source
_SOURCE_MAP = {
    "facebook": "facebook",
    "instagram": "facebook",  # Instagram ads run through Meta/Facebook
    "linkedin": "linkedin",
    "tiktok": "tiktok",
    "twitter": "twitter",
    "google": "google",
    "bing": "bing",
}

# Medium derivation: hs_analytics_source -> lc_utm_medium
_MEDIUM_MAP = {
    "PAID_SOCIAL": "paidsocial",
    "PAID_SEARCH": "paidsearch",
    "SOCIAL_MEDIA": "organic",  # organic social
    "ORGANIC_SEARCH": "organic",
    "DIRECT_TRAFFIC": "organic",
    "EMAIL_MARKETING": "email",
    "REFERRALS": "referral",
}

# Campaign values that look wrong and should be flagged for review
_SUSPICIOUS_CAMPAIGN_KEYWORDS = [
    "organic",  # e.g. "organic facebook lead" — probably not an ad campaign
]


def derive_utm_fixes(props):
    """Derive correct UTM values from analytics fields.

    Returns (fixes_dict, flags_list).
      fixes_dict: {property_name: new_value} — safe to auto-apply
      flags_list: [{field, current, derived, reason}] — need human review
    """
    fixes = {}
    flags = []

    lc_src = props.get("lc_utm_source", "") or ""
    lc_med = props.get("lc_utm_medium", "") or ""
    lc_camp = props.get("lc_utm_campaign", "") or ""

    a_src = (props.get("hs_analytics_source") or "").upper()
    a_d1 = props.get("hs_analytics_source_data_1", "") or ""
    a_d2 = props.get("hs_analytics_source_data_2", "") or ""

    latest_src = (props.get("hs_latest_source") or "").upper()

    # --- lc_utm_source ---
    if lc_src == "{{site_source_name}}" or (lc_src == "unknown" and a_d1):
        derived = _SOURCE_MAP.get(a_d1.lower())
        if derived:
            fixes["lc_utm_source"] = derived
        else:
            flags.append({
                "field": "lc_utm_source",
                "current": lc_src,
                "derived": a_d1,
                "reason": f"Unknown analytics_data_1 value '{a_d1}' — can't map to source",
            })

    # --- lc_utm_medium ---
    needs_medium_fix = False

    if lc_med == "unknown":
        needs_medium_fix = True
    elif lc_med == "" and (lc_src or "lc_utm_source" in fixes):
        # Empty medium when source exists — check if it should be set
        needs_medium_fix = True

    if needs_medium_fix:
        # LinkedIn special case: if latest source is SOCIAL_MEDIA (organic social),
        # medium = organic, not paidsocial
        effective_source = fixes.get("lc_utm_source", lc_src).lower()
        if effective_source == "linkedin" and latest_src == "SOCIAL_MEDIA":
            fixes["lc_utm_medium"] = "organic"
        elif a_src in _MEDIUM_MAP:
            fixes["lc_utm_medium"] = _MEDIUM_MAP[a_src]
        else:
            flags.append({
                "field": "lc_utm_medium",
                "current": lc_med or "(empty)",
                "derived": a_src,
                "reason": f"Unknown analytics_source '{a_src}' — can't derive medium",
            })

    # --- lc_utm_campaign ---
    if lc_camp == "{{campaign.name}}":
        if a_d2:
            # Check for suspicious campaign values
            is_suspicious = any(kw in a_d2.lower() for kw in _SUSPICIOUS_CAMPAIGN_KEYWORDS)
            if is_suspicious:
                flags.append({
                    "field": "lc_utm_campaign",
                    "current": lc_camp,
                    "derived": a_d2,
                    "reason": f"Campaign value '{a_d2}' looks suspicious (contains organic/non-ad keyword)",
                })
            else:
                fixes["lc_utm_campaign"] = a_d2
        else:
            flags.append({
                "field": "lc_utm_campaign",
                "current": lc_camp,
                "derived": "(empty)",
                "reason": "hs_analytics_source_data_2 is empty — no campaign to derive",
            })

    return fixes, flags


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_scan(days=7, limit=100):
    """Scan recent paid leads for hygiene issues."""
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    filter_groups = [{
        "filters": [
            {
                "propertyName": "hs_analytics_source",
                "operator": "IN",
                "values": ["PAID_SOCIAL", "PAID_SEARCH"],
            },
            {
                "propertyName": "recent_conversion_date",
                "operator": "GTE",
                "value": since,
            },
        ]
    }]

    sorts = [{"propertyName": "recent_conversion_date", "direction": "DESCENDING"}]

    contacts, total = search_contacts(filter_groups, SCAN_PROPERTIES, sorts, limit)

    # Run checks
    results = []
    issue_counts = {}

    for contact in contacts:
        props = contact.get("properties", {})
        issues = check_contact(props)
        if issues:
            for iss in issues:
                rule = iss["rule"]
                issue_counts[rule] = issue_counts.get(rule, 0) + 1

            results.append({
                "contactId": contact["id"],
                "email": props.get("email", "?"),
                "link": f"https://app.hubspot.com/contacts/5690529/contact/{contact['id']}",
                "name": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                "conversion": (props.get("recent_conversion_event_name") or "")[:60],
                "conversion_date": props.get("recent_conversion_date", ""),
                "lifecycle": props.get("lifecyclestage", ""),
                "issues": issues,
            })

    output = {
        "scan_params": {
            "since": since,
            "source_filter": ["PAID_SOCIAL", "PAID_SEARCH"],
            "total_matching": total,
            "scanned": len(contacts),
        },
        "summary": {
            "contacts_with_issues": len(results),
            "clean_contacts": len(contacts) - len(results),
            "issue_breakdown": issue_counts,
        },
        "contacts": results,
    }

    print(json.dumps(output, indent=2))


def cmd_detail(contact_id):
    """Detailed hygiene report for a single contact."""
    props_list = SCAN_PROPERTIES + [
        "createdate", "lastmodifieddate",
        "hs_email_last_open_date", "hs_email_last_click_date",
        "num_associated_deals",
    ]

    result = api_request(
        "GET",
        f"/crm/v3/objects/contacts/{contact_id}?properties={','.join(props_list)}",
    )

    props = result.get("properties", {})
    issues = check_contact(props)

    output = {
        "contactId": contact_id,
        "email": props.get("email", "?"),
        "name": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
        "properties": {k: v for k, v in props.items() if v is not None and v != ""},
        "issues": issues,
        "issue_count": len(issues),
    }

    print(json.dumps(output, indent=2))


def cmd_fix_utms(days=7, limit=100, apply=False):
    """Find contacts with broken UTMs, derive fixes, and optionally apply."""
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Search for paid leads with placeholder UTMs
    # We use multiple filter groups (OR) to catch different broken patterns
    filter_groups = [
        {
            "filters": [
                {"propertyName": "hs_analytics_source", "operator": "IN", "values": ["PAID_SOCIAL", "PAID_SEARCH"]},
                {"propertyName": "recent_conversion_date", "operator": "GTE", "value": since},
                {"propertyName": "lc_utm_source", "operator": "CONTAINS_TOKEN", "value": "{{"},
            ]
        },
        {
            "filters": [
                {"propertyName": "hs_analytics_source", "operator": "IN", "values": ["PAID_SOCIAL", "PAID_SEARCH"]},
                {"propertyName": "recent_conversion_date", "operator": "GTE", "value": since},
                {"propertyName": "lc_utm_campaign", "operator": "CONTAINS_TOKEN", "value": "{{"},
            ]
        },
        {
            "filters": [
                {"propertyName": "hs_analytics_source", "operator": "IN", "values": ["PAID_SOCIAL", "PAID_SEARCH"]},
                {"propertyName": "recent_conversion_date", "operator": "GTE", "value": since},
                {"propertyName": "lc_utm_source", "operator": "EQ", "value": "unknown"},
            ]
        },
        {
            "filters": [
                {"propertyName": "hs_analytics_source", "operator": "IN", "values": ["PAID_SOCIAL", "PAID_SEARCH"]},
                {"propertyName": "recent_conversion_date", "operator": "GTE", "value": since},
                {"propertyName": "lc_utm_medium", "operator": "EQ", "value": "unknown"},
            ]
        },
        {
            "filters": [
                {"propertyName": "hs_analytics_source", "operator": "IN", "values": ["PAID_SOCIAL"]},
                {"propertyName": "recent_conversion_date", "operator": "GTE", "value": since},
                {"propertyName": "lc_utm_source", "operator": "EQ", "value": "linkedin"},
                {"propertyName": "lc_utm_medium", "operator": "NOT_HAS_PROPERTY"},
            ]
        },
    ]

    sorts = [{"propertyName": "recent_conversion_date", "direction": "DESCENDING"}]
    contacts, total = search_contacts(filter_groups, SCAN_PROPERTIES, sorts, limit)

    # Deduplicate (multiple filter groups can match same contact)
    seen = set()
    unique = []
    for c in contacts:
        cid = c["id"]
        if cid not in seen:
            seen.add(cid)
            unique.append(c)
    contacts = unique

    auto_fixes = []   # contacts with safe auto-fixes
    flagged = []       # contacts needing human review
    already_clean = 0

    for contact in contacts:
        props = contact.get("properties", {})
        fixes, flags = derive_utm_fixes(props)

        if not fixes and not flags:
            already_clean += 1
            continue

        entry = {
            "contactId": contact["id"],
            "email": props.get("email", "?"),
            "link": f"https://app.hubspot.com/contacts/5690529/contact/{contact['id']}",
            "conversion": (props.get("recent_conversion_event_name") or "")[:60],
        }

        if flags:
            entry["flags"] = flags
            entry["safe_fixes"] = fixes
            flagged.append(entry)
        elif fixes:
            entry["fixes"] = fixes
            auto_fixes.append(entry)

    output = {
        "mode": "apply" if apply else "dry_run",
        "scan_params": {"since": since, "total_matching": total, "scanned": len(contacts)},
        "summary": {
            "auto_fixable": len(auto_fixes),
            "needs_review": len(flagged),
            "already_clean": already_clean,
        },
        "auto_fixes": auto_fixes,
        "flagged_for_review": flagged,
    }

    if apply and auto_fixes:
        applied = 0
        errors = []
        for entry in auto_fixes:
            cid = entry["contactId"]
            try:
                api_request(
                    "PATCH",
                    f"/crm/v3/objects/contacts/{cid}",
                    body={"properties": entry["fixes"]},
                )
                applied += 1
            except Exception as e:
                errors.append({"contactId": cid, "error": str(e)})

        output["applied"] = applied
        output["apply_errors"] = errors

    print(json.dumps(output, indent=2))


def cmd_fix_mql_dates(days=14, limit=100, apply=False):
    """Find contacts where Funnel Date MQL (Latest) is set but (First) is empty.

    Scans HubSpot directly — no SF data needed. Fixes by setting First = Latest.
    The native HS→SF sync carries the fix to MQL_Date__c.
    """
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Find contacts with Latest set but First empty
    filter_groups = [
        {
            "filters": [
                {"propertyName": "funnel_date___mql__latest_", "operator": "HAS_PROPERTY"},
                {"propertyName": "funnel_date___mql__first_", "operator": "NOT_HAS_PROPERTY"},
                {"propertyName": "createdate", "operator": "GTE", "value": since},
            ]
        }
    ]

    properties = SCAN_PROPERTIES + [
        "funnel_date___mql__first_",
        "funnel_date___mql__latest_",
    ]

    sorts = [{"propertyName": "createdate", "direction": "DESCENDING"}]
    contacts, total = search_contacts(filter_groups, properties, sorts, limit)

    fixable = []

    for contact in contacts:
        props = contact.get("properties", {})
        latest = props.get("funnel_date___mql__latest_")
        first = props.get("funnel_date___mql__first_")

        if latest and not first:
            fixable.append({
                "contactId": contact["id"],
                "email": props.get("email", "?"),
                "link": f"https://app.hubspot.com/contacts/5690529/contact/{contact['id']}",
                "lifecycle": props.get("lifecyclestage", ""),
                "mql_first": first,
                "mql_latest": latest,
                "fix": {"funnel_date___mql__first_": latest},
            })

    output = {
        "mode": "apply" if apply else "dry_run",
        "scan_params": {"since": since, "scanned": len(contacts), "total_matching": total},
        "summary": {
            "fixable": len(fixable),
            "already_clean": len(contacts) - len(fixable),
        },
        "contacts": fixable,
    }

    if apply and fixable:
        applied = 0
        errors = []
        for entry in fixable:
            cid = entry["contactId"]
            try:
                api_request(
                    "PATCH",
                    f"/crm/v3/objects/contacts/{cid}",
                    body={"properties": entry["fix"]},
                )
                applied += 1
            except Exception as e:
                errors.append({"contactId": cid, "error": str(e)})

        output["applied"] = applied
        output["apply_errors"] = errors

    print(json.dumps(output, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="HubSpot Contact Hygiene Checker")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("scan", help="Scan recent paid leads for issues")
    p.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    p.add_argument("--limit", type=int, default=100, help="Max contacts to scan (default: 100)")

    p = sub.add_parser("detail", help="Detailed report for one contact")
    p.add_argument("contact_id")

    p = sub.add_parser("fix-utms", help="Find and fix broken UTM placeholders")
    p.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    p.add_argument("--limit", type=int, default=100, help="Max contacts to scan (default: 100)")
    p.add_argument("--apply", action="store_true", default=False, help="Apply fixes (default: dry run)")

    p = sub.add_parser("fix-mql-dates", help="Fix MQL Date First where Latest exists but First is empty")
    p.add_argument("--days", type=int, default=14, help="Look back N days (default: 14)")
    p.add_argument("--limit", type=int, default=100, help="Max contacts (default: 100)")
    p.add_argument("--apply", action="store_true", default=False, help="Apply fixes (default: dry run)")

    args = parser.parse_args()

    cmds = {
        "scan": lambda: cmd_scan(days=args.days, limit=args.limit),
        "detail": lambda: cmd_detail(args.contact_id),
        "fix-utms": lambda: cmd_fix_utms(days=args.days, limit=args.limit, apply=args.apply),
        "fix-mql-dates": lambda: cmd_fix_mql_dates(days=args.days, limit=args.limit, apply=args.apply),
    }

    fn = cmds.get(args.command)
    if fn:
        fn()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
