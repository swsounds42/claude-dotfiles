---
name: sf-campaign-cloner
description: Clones Salesforce campaigns from one quarter to the next. Handles bulk cloning with name/date updates, ParentId remapping so child campaigns point to new-quarter parents, and gap-checking to catch sub-campaigns (opt-in pages, signup pages, churned sub-campaigns) that miss the primary date filter. Uses the Salesforce MCP server with a direct httpx fallback for bulk operations when the MCP process is stale.
---

# Salesforce Campaign Cloner

Automates end-of-quarter campaign duplication: clone, rename, remap parents, and gap-check in one structured flow.

## Setup

### MCP Server
The Salesforce MCP server at `core/mcp/salesforce_mcp.py` exposes:
- `sf_query` — run SOQL
- `sf_clone_campaign` / `sf_clone_campaigns_bulk` — clone campaigns
- `sf_update_campaign` — update campaign fields

**Important:** The MCP process goes stale between sessions. For bulk clone/patch operations, run scripts directly:
```bash
core/mcp/.venv/bin/python3.14 ~/.claude/commands/sf-campaign-cloner/scripts/<script>.py
```

### Auth
Client Credentials OAuth. Credentials are in the MCP server env config in `~/.claude.json`. Scripts read them as constants — update if rotated:
- `SALESFORCE_INSTANCE_URL` = `https://homebot.my.salesforce.com`
- `SALESFORCE_CLIENT_ID` / `SALESFORCE_CLIENT_SECRET` from the External Client App

## Workflow

### Step 1 — Confirm Quarters
Confirm with the user:
- Source quarter label (e.g. `Q1 2026`)
- Target quarter label (e.g. `Q2 2026`)
- Target date range (e.g. `2026-04-01` to `2026-06-30`)

### Step 2 — Query Source Campaigns
```sql
SELECT Id, Name, StartDate, EndDate, Status, ParentId
FROM Campaign WHERE Name LIKE '%Q1 2026%' ORDER BY Name
```

### Step 3 — Apply Clone Criteria
Present the filtered list to the user before cloning.

**Include** — full-quarter campaigns:
- `StartDate <= [quarter_start + 15 days]` AND `EndDate >= [quarter_end - 15 days]`

**Exclude automatically:**
- VDay / Valentine campaigns (Name contains "VDay" or "Valentine")
- Point-in-time events: `StartDate == EndDate` or duration < 7 days (conferences, webinars, group demos)
- Any campaigns the user explicitly excludes

### Step 4 — Clone
Run `scripts/clone_campaigns.py` with source IDs. It:
1. Fetches each source campaign
2. Renames source quarter label → target quarter label
3. Sets `StartDate`, `EndDate`, `Status = "In Progress"`
4. Preserves other fields from source
5. Saves results to `/tmp/sf_clone_results.json` (`source_id` → `new_id` mapping)

### Step 5 — Remap ParentIds
Run `scripts/remap_parents.py`. For each new campaign:
- ParentId in clone map → PATCH to new-quarter parent ID
- ParentId not in map → flag for review (may already be correct or point to a permanent parent)

### Step 6 — Gap Check
Run `scripts/gap_check.py`. Compares all source-quarter campaigns against what was cloned. Output buckets:

| Bucket | Action |
|---|---|
| Events / one-day campaigns | Skip — correctly excluded |
| VDay / promo | Skip — intentionally excluded |
| Signup / opt-in pages (mid-quarter start) | Offer to clone → parent: corresponding ABM campaign |
| Churned sub-campaigns (late start) | Offer to clone → parent: cloned Churn Winback campaign |
| Other missed | Present to user for decision |

### Step 7 — Clone Gaps
For confirmed gaps, run `scripts/clone_campaigns.py` again with the correct `--parent-override` for each batch.

## Key Patterns

### Mid-Quarter Start Dates
Opt-in pages and signup pages typically start ~Jan 26 and miss a `StartDate <= Jan 15` filter. The gap check always catches them. Clone them with the same setup as other ABM children.

### Fields Cloned
```python
CLONE_FIELDS = [
    'Type', 'IsActive', 'Description', 'ExpectedRevenue',
    'BudgetedCost', 'ActualCost', 'ExpectedResponse',
    'NumberSent', 'CampaignMemberRecordTypeId'
]
# Name, StartDate, EndDate, Status, ParentId always set explicitly
```

### ParentId Remap Logic
Build `source_id → new_id` from `/tmp/sf_clone_results.json`. PATCH every new campaign whose current `ParentId` is a key in that dict. Campaigns with unrecognized parents are either already correct or point to a permanent top-level hierarchy — both are fine.

## Scripts Reference

| Script | Purpose | Key args |
|---|---|---|
| `scripts/clone_campaigns.py` | Clone a list of source IDs | `SOURCE_IDS`, `TARGET_*` constants |
| `scripts/remap_parents.py` | Fix ParentIds using results JSON | reads `/tmp/sf_clone_results.json` |
| `scripts/gap_check.py` | Surface uncovered Q1 campaigns | `SOURCE_QUARTER`, `CLONED_IDS` set |
