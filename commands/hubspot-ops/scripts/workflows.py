#!/usr/bin/env python3
"""HubSpot Workflow Management CLI.

Usage:
    python3 workflows.py list [--search NAME] [--limit N]
    python3 workflows.py get FLOW_ID
    python3 workflows.py branches FLOW_ID
    python3 workflows.py backup FLOW_ID
    python3 workflows.py preview-update FLOW_ID ACTION_ID BRANCH_INDEX --filters-json '...'
    python3 workflows.py update-filters FLOW_ID ACTION_ID BRANCH_INDEX --filters-json '...'
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import get_headers, get_auth_params, BASE_URL, is_bearer_token, load_hubspot_key

BACKUP_DIR = Path("/tmp/hubspot-workflow-backups")


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_request(method, path, body=None):
    """Make an authenticated HubSpot API request."""
    # Handle legacy API key auth via query params
    auth_params = get_auth_params()
    if auth_params:
        separator = "&" if "?" in path else "?"
        param_str = "&".join(f"{k}={v}" for k, v in auth_params.items())
        path = f"{path}{separator}{param_str}"

    url = f"{BASE_URL}{path}"
    headers = get_headers()

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(
            json.dumps(
                {
                    "error": True,
                    "status": e.code,
                    "message": str(e),
                    "detail": error_body[:2000],
                }
            ),
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Filter parsing helpers
# ---------------------------------------------------------------------------

def parse_filter_branch(fb):
    """Recursively parse a filterBranch into a readable dict."""
    if not fb:
        return {"operator": "EMPTY", "conditions": []}

    result = {
        "operator": fb.get("filterBranchOperator") or fb.get("filterBranchType", "AND"),
        "conditions": [],
    }

    for f in fb.get("filters", []):
        condition = _parse_single_filter(f)
        if condition:
            result["conditions"].append(condition)

    for sub_fb in fb.get("filterBranches", []):
        sub = parse_filter_branch(sub_fb)
        if sub["conditions"]:
            result["conditions"].append({"group": sub})

    return result


def _parse_single_filter(f):
    """Parse one filter entry into a readable dict."""
    op = f.get("operation", {})
    return {
        "filterType": f.get("filterType", "UNKNOWN"),
        "property": f.get("property", ""),
        "operationType": op.get("operationType", ""),
        "operator": op.get("operator", ""),
        "values": op.get("values", []),
        "value": op.get("value"),
        "includeNoValue": op.get("includeObjectsWithNoValueSet", False),
    }


def _readable_filter(f):
    """One-line human-readable summary of a filter condition."""
    prop = f.get("property", "?")
    operator = f.get("operator", "?")
    values = f.get("values") or ([f["value"]] if f.get("value") else [])
    val_str = ", ".join(str(v) for v in values) if values else "(any)"
    inc = " [+blanks]" if f.get("includeNoValue") else ""
    return f"{prop} {operator} [{val_str}]{inc}"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(search=None, limit=20):
    """List all workflows, optionally filtered by name."""
    result = api_request("GET", "/automation/v4/flows")
    flows = result.get("flows", result.get("results", []))

    if search:
        q = search.lower()
        flows = [f for f in flows if q in f.get("name", "").lower()]

    flows = flows[:limit]

    output = []
    for f in flows:
        output.append(
            {
                "flowId": f.get("flowId") or f.get("id"),
                "name": f.get("name", "Unnamed"),
                "type": f.get("type", "unknown"),
                "enabled": f.get("enabled", False),
                "objectType": f.get("objectTypeId", "unknown"),
            }
        )

    print(json.dumps({"count": len(output), "workflows": output}, indent=2))


def cmd_get(flow_id):
    """Dump full workflow definition as JSON."""
    result = api_request("GET", f"/automation/v4/flows/{flow_id}")
    print(json.dumps(result, indent=2))


def cmd_branches(flow_id):
    """Display branch structure in a readable format."""
    wf = api_request("GET", f"/automation/v4/flows/{flow_id}")

    header = {
        "workflow": wf.get("name", "Unnamed"),
        "flowId": wf.get("flowId") or wf.get("id"),
        "revisionId": wf.get("revisionId", "unknown"),
        "enabled": wf.get("enabled", False),
        "branches": [],
    }

    for action in wf.get("actions", []):
        atype = action.get("type", "")
        if atype not in ("LIST_BRANCH", "BRANCH"):
            continue

        action_info = {
            "actionId": action.get("actionId", "unknown"),
            "actionType": atype,
            "defaultBranchName": action.get("defaultBranchName", "Default"),
            "branches": [],
        }

        for idx, branch in enumerate(action.get("listBranches", [])):
            fb = branch.get("filterBranch", {})
            parsed = parse_filter_branch(fb)

            # Build plain-English summaries
            summaries = []
            for c in parsed.get("conditions", []):
                if "group" in c:
                    group = c["group"]
                    sub = [_readable_filter(sc) for sc in group.get("conditions", []) if "group" not in sc]
                    op = group.get("operator", "AND")
                    joined = f" {op} ".join(sub)
                    summaries.append(f"({joined})")
                else:
                    summaries.append(_readable_filter(c))

            action_info["branches"].append(
                {
                    "index": idx,
                    "name": branch.get("branchName", f"Branch {idx}"),
                    "summary": f" {parsed['operator']} ".join(summaries) if summaries else "(no filters)",
                    "filters_raw": parsed,
                }
            )

        header["branches"].append(action_info)

    # Enrollment criteria summary
    enrollment = wf.get("enrollmentCriteria", {})
    if enrollment:
        header["enrollmentCriteria"] = {
            "type": enrollment.get("type", "unknown"),
            "shouldReEnroll": enrollment.get("shouldReEnroll", False),
        }

    print(json.dumps(header, indent=2))


def cmd_backup(flow_id):
    """Save full workflow JSON to backup directory."""
    wf = api_request("GET", f"/automation/v4/flows/{flow_id}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = wf.get("name", "unnamed").replace(" ", "_").replace("/", "_")[:50]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = BACKUP_DIR / f"{safe_name}_{flow_id}_{ts}.json"

    with open(filepath, "w") as f:
        json.dump(wf, f, indent=2)

    print(
        json.dumps(
            {
                "backed_up": True,
                "path": str(filepath),
                "workflow": wf.get("name"),
                "revisionId": wf.get("revisionId"),
            },
            indent=2,
        )
    )


def cmd_preview_update(flow_id, action_id, branch_index, filters_json):
    """Dry-run: show current vs. proposed filters without applying."""
    wf = api_request("GET", f"/automation/v4/flows/{flow_id}")
    new_filters = json.loads(filters_json)

    target = _find_action(wf, action_id)
    branches = target.get("listBranches", [])
    _check_branch_index(branches, branch_index)

    current_fb = branches[branch_index].get("filterBranch", {})

    print(
        json.dumps(
            {
                "dry_run": True,
                "workflow": wf.get("name"),
                "flowId": flow_id,
                "action_id": action_id,
                "branch_name": branches[branch_index].get("branchName", f"Branch {branch_index}"),
                "current_filters": parse_filter_branch(current_fb),
                "proposed_filters": (
                    parse_filter_branch(new_filters)
                    if isinstance(new_filters, dict) and "filterBranchType" in new_filters
                    else new_filters
                ),
                "revisionId": wf.get("revisionId"),
            },
            indent=2,
        )
    )


def cmd_update_filters(flow_id, action_id, branch_index, filters_json):
    """Apply a branch filter update via GET-modify-PUT."""
    # 1. GET
    wf = api_request("GET", f"/automation/v4/flows/{flow_id}")

    # 2. Auto-backup
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = wf.get("name", "unnamed").replace(" ", "_").replace("/", "_")[:50]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"{safe_name}_{flow_id}_{ts}_pre_update.json"
    with open(backup_path, "w") as f:
        json.dump(wf, f, indent=2)

    # 3. Locate action + branch and swap filters
    new_filters = json.loads(filters_json)
    target = _find_action(wf, action_id)
    branches = target.get("listBranches", [])
    _check_branch_index(branches, branch_index)

    branches[branch_index]["filterBranch"] = new_filters

    # 4. Strip server-only fields
    for key in ("createdAt", "updatedAt", "dataSources"):
        wf.pop(key, None)

    # 5. PUT full workflow
    result = api_request("PUT", f"/automation/v4/flows/{flow_id}", body=wf)

    print(
        json.dumps(
            {
                "updated": True,
                "workflow": result.get("name"),
                "flowId": flow_id,
                "newRevisionId": result.get("revisionId"),
                "backupPath": str(backup_path),
                "branch_updated": branches[branch_index].get(
                    "branchName", f"Branch {branch_index}"
                ),
            },
            indent=2,
        )
    )


# ---------------------------------------------------------------------------
# Enrollment trigger commands
# ---------------------------------------------------------------------------

def cmd_add_enrollment_form(flow_id, form_id, dry_run=False):
    """Add a form submission trigger to a workflow's enrollment criteria.

    Clones the first existing OR group as a template, swaps in the new formId,
    and appends it.  Works for LIST_BASED enrollment workflows that use the
    standard pattern: hb_customer_state guard + FORM_SUBMISSION.
    """
    wf = api_request("GET", f"/automation/v4/flows/{flow_id}")

    ec = wf.get("enrollmentCriteria", {})
    lfb = ec.get("listFilterBranch", {})
    groups = lfb.get("filterBranches", [])

    if not groups:
        print(json.dumps({"error": True, "message": "No existing enrollment filter groups to clone"}))
        sys.exit(1)

    # Check if form already exists
    existing_forms = []
    for i, g in enumerate(groups):
        for filt in g.get("filters", []):
            if filt.get("filterType") == "FORM_SUBMISSION" and filt.get("formId") == form_id:
                existing_forms.append(i)

    if existing_forms:
        print(
            json.dumps(
                {
                    "warning": True,
                    "message": f"Form {form_id} already exists in enrollment groups: {existing_forms}",
                    "action": "none" if dry_run else "will add duplicate (HubSpot may auto-deduplicate)",
                },
                indent=2,
            )
        )
        if dry_run:
            return

    # Clone template
    template = json.loads(json.dumps(groups[0]))
    for filt in template["filters"]:
        if filt["filterType"] == "FORM_SUBMISSION":
            filt["formId"] = form_id

    if dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "workflow": wf.get("name"),
                    "flowId": flow_id,
                    "current_groups": len(groups),
                    "proposed_groups": len(groups) + 1,
                    "new_form_id": form_id,
                    "template_from": "OR Group 0",
                    "revisionId": wf.get("revisionId"),
                },
                indent=2,
            )
        )
        return

    # Auto-backup
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = wf.get("name", "unnamed").replace(" ", "_").replace("/", "_")[:50]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"{safe_name}_{flow_id}_{ts}_pre_enroll.json"
    with open(backup_path, "w") as f:
        json.dump(wf, f, indent=2)

    # Append the new form group
    groups.append(template)

    # --- Re-enrollment safety ---
    # Temporarily disable re-enrollment during the PUT so HubSpot doesn't
    # backfill-enroll contacts who historically submitted the newly-added form.
    original_re_enroll = ec.get("shouldReEnroll", False)
    ec["shouldReEnroll"] = False

    for key in ("createdAt", "updatedAt", "dataSources"):
        wf.pop(key, None)

    # PUT 1: add the form with re-enrollment OFF
    result = api_request("PUT", f"/automation/v4/flows/{flow_id}", body=wf)
    mid_revision = result.get("revisionId")

    # PUT 2: restore original re-enrollment setting
    restored = False
    if original_re_enroll:
        result["enrollmentCriteria"]["shouldReEnroll"] = True
        for key in ("createdAt", "updatedAt", "dataSources"):
            result.pop(key, None)
        result2 = api_request("PUT", f"/automation/v4/flows/{flow_id}", body=result)
        final_revision = result2.get("revisionId")
        restored = True
    else:
        final_revision = mid_revision

    new_groups = len(
        (result2 if restored else result)
        .get("enrollmentCriteria", {})
        .get("listFilterBranch", {})
        .get("filterBranches", [])
    )

    print(
        json.dumps(
            {
                "updated": True,
                "workflow": (result2 if restored else result).get("name"),
                "flowId": flow_id,
                "newRevisionId": final_revision,
                "backupPath": str(backup_path),
                "enrollment_groups_before": len(groups) - 1,
                "enrollment_groups_after": new_groups,
                "form_added": form_id,
                "re_enrollment_safety": {
                    "original_shouldReEnroll": original_re_enroll,
                    "temporarily_disabled": True,
                    "restored": restored,
                },
            },
            indent=2,
        )
    )


def cmd_find_form(search_term):
    """Find a Meta/LinkedIn lead form GUID by searching contact form submissions."""
    body = {
        "filterGroups": [
            {
                "filters": [
                    {
                        "propertyName": "recent_conversion_event_name",
                        "operator": "CONTAINS_TOKEN",
                        "value": search_term,
                    }
                ]
            }
        ],
        "properties": ["email", "recent_conversion_event_name", "recent_conversion_date"],
        "sorts": [{"propertyName": "recent_conversion_date", "direction": "DESCENDING"}],
        "limit": 5,
    }

    results = api_request("POST", "/crm/v3/objects/contacts/search", body=body)
    contacts = results.get("results", [])

    if not contacts:
        print(json.dumps({"error": True, "message": f"No contacts found with conversion matching '{search_term}'"}))
        sys.exit(1)

    # For each contact, pull form submissions to get the GUID
    forms_found = {}
    for contact in contacts:
        vid = contact["id"]
        profile = api_request("GET", f"/contacts/v1/contact/vid/{vid}/profile")
        for sub in profile.get("form-submissions", []):
            title = sub.get("title", "")
            form_id = sub.get("form-id", "")
            if search_term.lower() in title.lower() and form_id:
                if form_id not in forms_found:
                    forms_found[form_id] = {
                        "formId": form_id,
                        "title": title,
                        "example_contact": vid,
                    }

    print(
        json.dumps(
            {"search": search_term, "forms_found": list(forms_found.values())},
            indent=2,
        )
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_action(wf, action_id):
    for action in wf.get("actions", []):
        if str(action.get("actionId")) == str(action_id):
            return action
    print(json.dumps({"error": True, "message": f"Action '{action_id}' not found in workflow"}))
    sys.exit(1)


def _check_branch_index(branches, idx):
    if idx >= len(branches):
        print(
            json.dumps(
                {
                    "error": True,
                    "message": f"Branch index {idx} out of range (max {len(branches) - 1})",
                }
            )
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="HubSpot Workflow Management")
    sub = parser.add_subparsers(dest="command")

    # list
    p = sub.add_parser("list", help="List workflows")
    p.add_argument("--search", help="Filter by name (case-insensitive)")
    p.add_argument("--limit", type=int, default=20)

    # get
    p = sub.add_parser("get", help="Full workflow JSON dump")
    p.add_argument("flow_id")

    # branches
    p = sub.add_parser("branches", help="Readable branch structure")
    p.add_argument("flow_id")

    # backup
    p = sub.add_parser("backup", help="Backup workflow JSON")
    p.add_argument("flow_id")

    # preview-update
    p = sub.add_parser("preview-update", help="Dry-run filter update")
    p.add_argument("flow_id")
    p.add_argument("action_id")
    p.add_argument("branch_index", type=int)
    p.add_argument("--filters-json", required=True)

    # update-filters
    p = sub.add_parser("update-filters", help="Apply filter update")
    p.add_argument("flow_id")
    p.add_argument("action_id")
    p.add_argument("branch_index", type=int)
    p.add_argument("--filters-json", required=True)

    # add-enrollment-form
    p = sub.add_parser("add-enrollment-form", help="Add form to enrollment triggers")
    p.add_argument("flow_id")
    p.add_argument("form_id")
    p.add_argument("--dry-run", action="store_true", default=False)

    # find-form
    p = sub.add_parser("find-form", help="Find Meta/LinkedIn lead form GUID by name")
    p.add_argument("search_term")

    args = parser.parse_args()

    cmds = {
        "list": lambda: cmd_list(search=args.search, limit=args.limit),
        "get": lambda: cmd_get(args.flow_id),
        "branches": lambda: cmd_branches(args.flow_id),
        "backup": lambda: cmd_backup(args.flow_id),
        "preview-update": lambda: cmd_preview_update(
            args.flow_id, args.action_id, args.branch_index, args.filters_json
        ),
        "update-filters": lambda: cmd_update_filters(
            args.flow_id, args.action_id, args.branch_index, args.filters_json
        ),
        "add-enrollment-form": lambda: cmd_add_enrollment_form(
            args.flow_id, args.form_id, dry_run=args.dry_run
        ),
        "find-form": lambda: cmd_find_form(args.search_term),
    }

    fn = cmds.get(args.command)
    if fn:
        fn()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
