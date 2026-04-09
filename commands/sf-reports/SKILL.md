---
name: sf-reports
description: Manage Salesforce reports, dashboards, and list views — list, describe, create, update filters, bulk update, and run reports. Create and refresh dashboards. Create and edit list views with custom filters and columns. Built for quarterly filter flips, ad-hoc report creation, dashboard assembly, and list view management. Uses the Salesforce MCP server's Analytics REST API and Tooling API.
---

# Salesforce Reports, Dashboards & List Views

Full CRUD for Salesforce reports, dashboards, and list views. Built for RevOps workflows like quarterly filter flips, report creation, dashboard assembly, and list view management.

## Setup

### MCP Server
The Salesforce MCP server at `core/mcp/salesforce_mcp.py` exposes all report and dashboard tools. No standalone scripts needed — everything runs through MCP.

### Auth
Client Credentials OAuth. Credentials are configured in the MCP server env config in `~/.claude.json`:
- `SALESFORCE_INSTANCE_URL` = `https://homebot.my.salesforce.com`
- `SALESFORCE_CLIENT_ID` / `SALESFORCE_CLIENT_SECRET` from the External Client App

## Tools Reference

### Report Tools (8)

| Tool | Purpose | Read/Write |
|------|---------|------------|
| `sf_list_reports` | Search reports by name or folder | Read |
| `sf_list_report_types` | Discover available report types for creation | Read |
| `sf_describe_report` | Full metadata — filters (with indices), columns, groupings, date range | Read |
| `sf_create_report` | Build a new report from scratch | Write |
| `sf_update_report_filters` | Update standard date filter or custom filters by index | Write |
| `sf_update_report` | General metadata update — name, columns, groupings | Write |
| `sf_bulk_update_report_filters` | Bulk filter changes across N reports (**dry-run by default**) | Write |
| `sf_run_report` | Execute a report and return summary/detail results | Read |

### Dashboard Tools (5)

| Tool | Purpose | Read/Write |
|------|---------|------------|
| `sf_list_dashboards` | Search dashboards by name or folder | Read |
| `sf_describe_dashboard` | Full metadata — components, source reports, filters | Read |
| `sf_create_dashboard` | Build a dashboard from existing reports | Write |
| `sf_update_dashboard` | Update name, components, filters, layout | Write |
| `sf_refresh_dashboard` | Trigger async data refresh | Write |

## Workflows

### Quarterly Filter Flip (primary use case)

The bulk update tool is **dry-run by default** — always preview before applying.

#### Step 1 — Find Reports
```
sf_list_reports search="Q1" folder_name="Sales Reports"
```
Or search broadly:
```
sf_list_reports search="Pipeline"
```

#### Step 2 — Inspect One Report
```
sf_describe_report report_id="00OXXXX"
```
Check the standard date filter and custom filters. Note the filter index numbers — you'll use them for targeted updates.

#### Step 3 — Preview Bulk Change (dry run)
```
sf_bulk_update_report_filters
  report_ids=["00OXXXX", "00OYYYY", "00OZZZZ"]
  standard_date_duration="THIS_QUARTER"
  dry_run=True
```
For custom filter value swaps:
```
sf_bulk_update_report_filters
  report_ids=[...]
  filter_value_replace="LAST_QUARTER"
  filter_value_replace_with="THIS_QUARTER"
  dry_run=True
```

#### Step 4 — Apply
Re-run with `dry_run=False` after confirming the preview looks correct.

#### Step 5 — Verify
```
sf_run_report report_id="00OXXXX"
```
Spot-check that the report returns expected data with the new filters.

### Single Report Filter Update

```
sf_update_report_filters
  report_id="00OXXXX"
  standard_date_duration="LAST_QUARTER"
  filter_updates={"1": "Nikolas Werner,Kaylie Damore"}
```
- `standard_date_duration` changes the date range token
- `filter_updates` targets specific filters by index (from `sf_describe_report` output)

### Create a New Report

#### Step 1 — Find Report Type
```
sf_list_report_types search="Opportunity"
```

#### Step 2 — Create
```
sf_create_report
  name="Q2 Pipeline by Stage"
  report_type_id="Opportunity"
  folder_id="00lXXXXX"
  report_format="SUMMARY"
  detail_columns=["ACCOUNT_NAME", "OPPORTUNITY_NAME", "AMOUNT", "CLOSE_DATE"]
  standard_date_column="CLOSE_DATE"
  standard_date_duration="THIS_QUARTER"
  groupings_down=[{"name": "STAGE_NAME", "dateGranularity": "NONE"}]
  filters=[{"column": "STAGE_NAME", "operator": "notEqual", "value": "Closed Lost"}]
```

#### Step 3 — Verify
```
sf_run_report report_id="<new_id>" include_details=True
```

### Create a Dashboard

#### Step 1 — Create Reports First
Build the individual reports using `sf_create_report`.

#### Step 2 — Assemble Dashboard
```
sf_create_dashboard
  name="Q2 Sales Overview"
  folder_id="00lXXXXX"
  components=[
    {"reportId": "00OXXXX", "componentType": "Chart", "header": "Pipeline by Stage"},
    {"reportId": "00OYYYY", "componentType": "Table", "header": "Closed Won This Quarter"}
  ]
```

#### Step 3 — Refresh
```
sf_refresh_dashboard dashboard_id="<new_id>"
```

## Key Concepts

### Standard Date Filter
Every report has one standard date filter with a `durationValue` token:
- `THIS_QUARTER`, `LAST_QUARTER`, `THIS_FISCAL_YEAR`, `LAST_FISCAL_YEAR`
- `THIS_MONTH`, `LAST_MONTH`, `LAST_30_DAYS`, `LAST_90_DAYS`
- `THIS_YEAR`, `LAST_YEAR`
- `CUSTOM` — requires explicit `startDate` and `endDate` (YYYY-MM-DD)

### Custom Filter Indices
`sf_describe_report` numbers each custom filter `[0]`, `[1]`, `[2]`... Use these indices with `sf_update_report_filters`'s `filter_updates` parameter to target specific filters.

### Bulk Update Safety
- `dry_run=True` is the default — always previews without changing anything
- Max 50 reports per bulk call
- Each report is updated independently — one failure doesn't stop the rest
- Standard date changes and custom filter find/replace can be combined in one call

### Report Formats
- `TABULAR` — flat list, no groupings
- `SUMMARY` — grouped rows (most common)
- `MATRIX` — grouped rows AND columns (pivot table style)

### Lightning URLs
All tools return clickable Lightning URLs:
- Reports: `{instance}/lightning/r/Report/{id}/view`
- Dashboards: `{instance}/lightning/r/Dashboard/{id}/view`
- List Views: `{instance}/lightning/o/{ObjectType}/list?filterName={id}`

## List View Tools (5)

| Tool | Purpose | Read/Write |
|------|---------|------------|
| `sf_list_listviews` | Search list views by object type and name | Read |
| `sf_describe_listview` | Full metadata — columns, filters (with indices), scope, sort | Read |
| `sf_create_listview` | Build a new list view with filters and columns | Write |
| `sf_update_listview` | Modify filters, columns, scope, name | Write |
| `sf_run_listview` | Execute and return results as a table | Read |

### Create a Contact List View

#### Step 1 — Create
```
sf_create_listview
  sobject_type="Contact"
  name="Q2 Demo Requesters"
  columns=["Name", "Email", "LeadSource", "CreatedDate"]
  filters=[
    {"field": "LeadSource", "operation": "equals", "value": "Demo Request"},
    {"field": "CreatedDate", "operation": "greaterThan", "value": "THIS_QUARTER"}
  ]
  filter_scope="Everything"
```

#### Step 2 — Verify
```
sf_run_listview sobject_type="Contact" listview_id="<new_id>"
```

### Update a List View

```
sf_describe_listview sobject_type="Contact" listview_id="00BXXXX"
```
Then update:
```
sf_update_listview
  listview_id="00BXXXX"
  filters=[
    {"field": "LeadSource", "operation": "equals", "value": "Demo Request"},
    {"field": "CreatedDate", "operation": "greaterThan", "value": "LAST_QUARTER"}
  ]
```
Note: filters are replaced entirely — include all filters you want, not just changes.

### List View Filter Operations
`equals`, `notEqual`, `lessThan`, `greaterThan`, `lessOrEqual`, `greaterOrEqual`, `contains`, `notContain`, `startsWith`, `includes`, `excludes`

### Filter Scope
- `Everything` — all records (default)
- `Mine` — records owned by the running user
- `Team` — records owned by the user's team
- `MyTerritory` / `MyTeamTerritory` — territory-based
