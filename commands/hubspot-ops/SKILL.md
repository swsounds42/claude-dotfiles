---
name: hubspot-ops
description: HubSpot operations skill for workflow management, contact hygiene, and cross-system HS/SF maintenance. Manages workflow branch filters, automates contact record cleanup, and keeps HubSpot in sync with Salesforce.
---

# HubSpot Ops

Operational layer for HubSpot automation management and contact hygiene. Works alongside the native HubSpot MCP connector (CRM reads) and Salesforce MCP connector (cross-system checks).

## Setup

### Auth
API key stored in `~/.hubspot-ops.env`:
```
HUBSPOT_API_KEY=your-key-here
```

Accepts any of these env var names: `HUBSPOT_API_KEY`, `HUBSPOT_ACCESS_TOKEN`, `HUBSPOT_PRIVATE_APP_TOKEN`.

Auto-detects key type:
- **Private app token** (`pat-na1-xxx`) → Bearer auth header
- **OAuth access token** → Bearer auth header
- **Legacy API key** (UUID format) → `hapikey` query param (deprecated, may not work with v4 APIs)

The key needs access to:
- Automation/Workflows API (v4)
- CRM Contacts (read/write)
- Sensitive contact properties (if workflows reference them)

### Scripts
All scripts at `~/.claude/commands/hubspot-ops/scripts/`.

---

## Module 1: Workflow Management

### List Workflows
```bash
cd ~/.claude/commands/hubspot-ops/scripts && python3 workflows.py list --search "NAME"
```

Present results as a clean table: name, flowId, type, enabled status.

### Inspect Branch Structure
```bash
cd ~/.claude/commands/hubspot-ops/scripts && python3 workflows.py branches FLOW_ID
```

Display output as a readable breakdown:
- Workflow name + enabled status
- Each branch action with its branches listed
- Per-branch: name, filter summary (plain English), raw filter details
- Enrollment criteria if present

### Preview Branch Filter Update (dry run)
```bash
cd ~/.claude/commands/hubspot-ops/scripts && python3 workflows.py preview-update FLOW_ID ACTION_ID BRANCH_INDEX --filters-json '...'
```

**ALWAYS preview before applying.** Show the user a clear before/after comparison:
1. Current filter conditions
2. Proposed filter conditions
3. What will change (added, removed, modified values)

Ask for explicit confirmation before proceeding to the actual update.

### Apply Branch Filter Update
```bash
cd ~/.claude/commands/hubspot-ops/scripts && python3 workflows.py update-filters FLOW_ID ACTION_ID BRANCH_INDEX --filters-json '...'
```

**Safety protocol — follow every time:**
1. Backup is automatic (script saves pre-update JSON)
2. Always preview-update first and show the diff
3. Get explicit "yes, apply" from user before running update-filters
4. If the workflow is **enabled**, warn the user that this is a live workflow edit
5. Report the new revisionId and backup path after success
6. NEVER update without user confirmation

### Backup a Workflow
```bash
cd ~/.claude/commands/hubspot-ops/scripts && python3 workflows.py backup FLOW_ID
```

Backups go to `/tmp/hubspot-workflow-backups/`.

### Full Workflow JSON Dump
```bash
cd ~/.claude/commands/hubspot-ops/scripts && python3 workflows.py get FLOW_ID
```

Use this when you need to inspect the full action tree, not just branches.

---

## Building Filter JSON

When the user describes a filter change in natural language, translate it into a `filterBranch` object.

### Structure
```json
{
  "filterBranchType": "AND",
  "filterBranchOperator": "AND",
  "filterBranches": [],
  "filters": [
    {
      "filterType": "PROPERTY",
      "property": "property_internal_name",
      "operation": {
        "operationType": "ENUMERATION",
        "operator": "IS_ANY_OF",
        "values": ["value1", "value2"],
        "includeObjectsWithNoValueSet": false
      }
    }
  ]
}
```

### operationType by Property Type

| HubSpot property type | operationType |
|---|---|
| Dropdown / Checkbox / Radio | `ENUMERATION` |
| Single-line / Multi-line text | `STRING` |
| Number | `NUMBER` |
| Date / DateTime | `TIME_POINT` or `TIME_RANGED` |
| Boolean | `BOOLEAN` |

### Common Operators

**ENUMERATION:** `IS_ANY_OF`, `IS_NONE_OF`, `IS_KNOWN`, `IS_NOT_KNOWN`
**STRING:** `IS_EQUAL_TO`, `IS_NOT_EQUAL_TO`, `CONTAINS`, `DOES_NOT_CONTAIN`, `STARTS_WITH`, `ENDS_WITH`, `IS_KNOWN`, `IS_NOT_KNOWN`
**NUMBER:** `IS_EQUAL_TO`, `IS_NOT_EQUAL_TO`, `IS_GREATER_THAN`, `IS_LESS_THAN`, `IS_BETWEEN`, `IS_NOT_BETWEEN`, `IS_KNOWN`, `IS_NOT_KNOWN`

### Combining Conditions

- Multiple filters in the same `filters` array = AND (all must match)
- Use nested `filterBranches` with `filterBranchOperator: "OR"` for OR logic
- Nest groups for complex AND/OR trees

### Example: "Change lifecycle stage filter from Lead to Customer"

Before:
```json
{"filterType": "PROPERTY", "property": "lifecyclestage", "operation": {"operationType": "ENUMERATION", "operator": "IS_ANY_OF", "values": ["lead"]}}
```

After:
```json
{"filterType": "PROPERTY", "property": "lifecyclestage", "operation": {"operationType": "ENUMERATION", "operator": "IS_ANY_OF", "values": ["customer"]}}
```

---

## Module 2: Contact Hygiene

### Scan Paid Leads for Issues
```bash
cd ~/.claude/commands/hubspot-ops/scripts && python3 hygiene.py scan --days 7 --limit 100
```

Replicates the manual review of the "Paid Social & Search Leads" list view (ID: 38147346). Scans recent PAID_SOCIAL and PAID_SEARCH contacts sorted by conversion date and flags:

| Rule | Severity | What it catches |
|---|---|---|
| `utm_placeholder` | error | UTM fields with unresolved `{{placeholders}}` from Meta forms |
| `missing_conversion_type` | warning | Has conversion but `conversion_type` is empty (suggests Demo/Sign-Up/etc.) |
| `missing_touch_source` | warning | Has UTM data but `conversion_touch_source` is empty (suggests Paid Social/Search/etc.) |
| `mql_no_date` | warning | Lifecycle = MQL but MQL date stamp is missing |
| `missing_lead_source` | warning | Has conversion activity but `leadsource` is empty |
| `lifecycle_numeric_id` | info | Lifecycle stage stored as custom numeric ID (e.g., 122237331 = Unqualified) |
| `source_mismatch` | info | Original source is paid but latest source drifted to DIRECT_TRAFFIC |
| `existing_customer` | info | Contact is active/archived customer showing up in lead gen |

Present results as a prioritized list: errors first, then warnings, then info. For each contact show the issues and any suggested fixes.

### Detail a Single Contact
```bash
cd ~/.claude/commands/hubspot-ops/scripts && python3 hygiene.py detail CONTACT_ID
```

Full property dump + hygiene check for one contact. Use when drilling into a specific issue.

### Cross-System Mismatch Detection (SF)
When the Salesforce MCP connector is available, cross-reference hygiene scan results:

1. Take emails from contacts with issues
2. Query SF via `sf_query`: `SELECT Id, Email, LeadSource, Lead_Source_Detail__c, Lifecycle_Stage__c, Status, Contact_Conversion_Touch_Source__c, Demo_Type__c, MQL_Date__c FROM Contact WHERE Email IN (...)`
3. Compare HS ↔ SF values and flag discrepancies
4. Present a combined report showing what needs fixing in each system

### Property Updates
- **Individual updates:** use HubSpot MCP `manage_crm_objects` (already available)
- **SF updates:** use SF MCP `sf_query` for reads, present changes for Sam's review before applying
- **Always present changes for review** — never auto-apply contact property changes

### Hygiene Rules (extensible)
Add rules as patterns emerge. Current set covers UTM normalization, qualification stamping, touch source, and lifecycle sync.

---

## Cross-System Architecture

```
HubSpot MCP Connector ──── CRM reads (contacts, deals, companies, properties)
     │
     │  This skill bridges the gap:
     │
HubSpot Ops Scripts ─────── Workflow API (list, read, update branches)
     │                       Contact batch API (bulk updates, Phase 2)
     │
Salesforce MCP Connector ── Queries, reports, campaigns, attribution
```

- HubSpot MCP handles CRM object reads/writes
- This skill's scripts handle everything the MCP connector can't (workflows, batch ops)
- SF MCP handles the Salesforce side of cross-system checks

---

## Routing

Invoke this skill when the user asks about:
- HubSpot workflows (list, inspect, update branches/filters)
- Contact record cleanup or hygiene
- Cross-system HS/SF property mismatches
- HubSpot automation management
- Bulk contact property updates in HubSpot
