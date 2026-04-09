---
name: sf-attribution
description: Automated Salesforce opportunity attribution pipeline. Gathers unattributed opps, reasons about correct LeadSource/Lead_Source_Detail/Touch Source/CampaignId, applies high-confidence decisions, flags ambiguous ones for review. Runs hourly via /loop.
---

# Salesforce Attribution Pipeline

## Execution Flow

When this skill is invoked, execute these steps in order:

### Step 1 — Gather Context
```bash
cd ~/.claude/commands/sf-attribution/scripts && ~/Desktop/personal-os-main/core/mcp/.venv/bin/python3.14 gather_context.py --lookback-hours 2
```

If output says "No unattributed opps found" → report "Attribution pipeline ran — inbox is clean." and stop.

### Step 1b — Enrich from HubSpot (optional, requires HubSpot MCP connector)

If a HubSpot MCP connector is available (tool names containing `hubspot` or matching the pattern `search_crm_objects`), enrich each opp's contact with marketing engagement data. **If HubSpot MCP is not connected, skip this step** — the pipeline works without it, just with less engagement signal.

**For each opp that has a `contact_email`:**

Query HubSpot using `search_crm_objects` with objectType `contacts`, filtering by email, and request these properties:
- `hs_email_last_open_date` — last marketing email open
- `hs_email_last_click_date` — last marketing email click
- `hs_email_open` — total marketing emails opened
- `hs_email_click` — total marketing emails clicked
- `hs_email_sends_since_last_engagement` — emails sent since last open/click
- `recent_conversion_date` — last form submission date
- `recent_conversion_event_name` — last form submitted
- `latest_conversion_touch_source` — touch source at last conversion (custom field)
- `latest_conversion_touch_source_detail` — touch source detail (custom field)
- `latest_conversion_touch_source_detail_2` — touch source detail 2 (custom field)
- `hs_latest_source` — Latest Traffic Source (auto-set by HubSpot analytics, often more reliable)
- `hs_latest_source_data_1` — Latest Traffic Source Drill-Down 1 (e.g. campaign name, invite type)
- `hs_latest_source_data_2` — Latest Traffic Source Drill-Down 2 (e.g. source detail)
- `latest_demo_conversion_date` — last demo form submission
- `self_reported_attribution_source` — self-reported source (if any)

**Batch contacts** — query up to 10 contacts per `search_crm_objects` call using OR filter groups on email. For larger batches, make multiple calls.

**How to use the HubSpot data in reasoning:**

| HubSpot signal | What it tells you |
|---|---|
| `hs_email_last_click_date` within 48h of opp creation | Marketing email likely drove the conversion — use email campaign for attribution, not "Direct" |
| `hs_email_sends_since_last_engagement` > 10 | Contact has been ignoring marketing emails — even if they have campaign memberships, this was likely an organic/direct return |
| `recent_conversion_event_name` contains "Churn Winback" or "Re-Activation" + `recent_conversion_date` within 30 days | Fresh winback signal — supports Churn Winback attribution |
| `recent_conversion_event_name` contains "Demo" or "Group Demo" | Confirms demo attendance even if SF campaign membership hasn't synced yet |
| `latest_conversion_touch_source` populated | Authoritative touch source — use this over guessing from campaign data |
| `hs_latest_source` = "Other campaigns" + drill-down contains "hbn_preferred_pro" or "invite" | Product-driven invite (Preferred Pro, HBN) → LSD = "Homebot Platform", use product campaign |
| `hs_latest_source_data_1` contains campaign/invite identifier | Maps directly to Touch Source Detail — this is the specific campaign or invite that drove the visit |
| `hs_latest_source_data_2` contains source context | Maps to Touch Source Detail 2 — e.g. "customer_admin / web" means invite originated from product UI |
| `hs_latest_source` ≠ `latest_conversion_touch_source` | These are different field sets. **Check BOTH.** The `hs_latest_source*` analytics fields are auto-set and often populated when custom conversion fields are empty |
| `self_reported_attribution_source` populated | Strong signal for Lead_Source_Detail (e.g. "Google search", "friend referral") |

**Precedence:** HubSpot engagement timeline > SF campaign memberships > SF activity records. HubSpot shows what the contact *actually did*; SF campaigns show what they were *enrolled in*.

### Step 2 — Read and Reason
Read `/tmp/sf_attribution_context.json` (and any HubSpot enrichment data from Step 1b). For each opp in the `opps` array, use the **Attribution Rules Reference** below plus the `attribution_campaigns` array (current quarter's campaigns) to determine:

1. **LeadSource** — the primary attribution category
2. **Lead_Source_Detail** — the sub-category (UTM-driven or role-based)
3. **Contact_Conversion_Touch_Source** — the marketing channel
4. **Touch Source Details** — UTM campaign/source/content/term values
5. **CampaignId** — which campaign to associate (if determinable)
6. **Confidence** — high / medium / low
7. **Reasoning** — 1-2 sentences explaining why

#### Attribution Rules Reference

**LeadSource values and when to use them:**

| LeadSource | Signals | Notes |
|---|---|---|
| Demo Request | Demo_Type = "Inbound", campaign type = "Demo Request" / "Nurture Campaign" / "Asset Download" | Most inbound demos |
| Prospecting | Demo_Type = "Outbound", campaign type = "Outreach Sequence" / "Inside Sales" / "ABM Marketing Campaign", or owner role suggests outbound | Often NO campaign member exists at opp creation |
| Direct Sign-Up | Demo_Type = "Direct", campaign type = "Direct Sign-Ups" / "Hunting License Sign Ups" | Self-service sign-ups |
| Churn Winback | Coupon contains "reactivate" | Trumps all other signals |
| Co-Sponsorship Invite | Campaign type = "LO Referrals", campaign name contains "Invited by REA" | REA invited an LO |
| Customer Opt-In | Campaign type = "Customer Opt-In" / "Customer Surveys" | Existing customer expanding |
| Events (Webinar) | Campaign type = "Event (Webinar)" | |
| Events (3rd Party) | Campaign type = "Event (3rd Party)" | |
| Events (In-House) | Campaign type = "Event (In-House)" | |
| Contact Us | Campaign type = "Contact Us Requests" | |
| Website Chat | Campaign type = "Website" / "Website Direct" | |
| Direct Email / Call | Campaign type = "Direct Email / Call" / "Intercom" | |
| Product Tour | Campaign type = "Product Tour" / "Product Interest" | |
| Workshop | Campaign type = "Workshop" | |

**Lead_Source_Detail — UTM-based mapping:**

| UTM Medium contains | Lead_Source_Detail |
|---|---|
| paid_social, paidsocial, cpm | Paid Social |
| cpc, ppc | Paid Search |
| email, nurture | Nurture |
| organic | Organic |
| referral | Referral |
| social (not paid) | Social Media |
| (empty/none/direct) | Direct |

**Lead_Source_Detail — Role-based (for Prospecting):**

| Owner Role contains | Lead_Source_Detail |
|---|---|
| Title, Insurance, Enterprise AE, Strategic | AE |
| SMB, MDR, SDR, Inside Sales, or anything else | Inside Sales |

Note: "SMB AE" maps to **Inside Sales**, not AE. The "AE" detail is reserved for enterprise/strategic/vertical AEs (Insurance, Title, Enterprise, Strategic Account). SMB reps are Inside Sales regardless of their title.

**Touch Source mapping:**

| UTM Medium | Touch Source |
|---|---|
| cpc, ppc | Paid Search |
| organic + google/bing/yahoo | Organic Search |
| email, nurture | Email Marketing |
| paid_social, paidsocial, cpm | Paid Social |
| social (not paid) | Organic Social |
| (empty/direct) | Direct Traffic |
| referral | Referrals |
| other | Other Campaigns |

**Primary UTM data source — Contact `lc_utm_*` fields ("last conversion"):**
The gather script now pulls `contact_utms` for each opp from the Contact record. These are the authoritative UTM fields:
- `lc_utm_source` — e.g. "google", "facebook", "BING"
- `lc_utm_medium` — e.g. "paidsearch", "cpc", "organic"
- `lc_utm_campaign` — e.g. "lg_google_search_alternative branded"
- `lc_utm_content` — e.g. "homebot"
- `lc_utm_term` — keyword term

**ALWAYS check `contact_utms` first** — these override campaign-level UTMs and are the primary signal for Lead_Source_Detail, Touch Source, and Touch Source Details. Even when campaign memberships show no UTMs, the contact may have rich UTM data. Map the `lc_utm_medium` value using the Lead_Source_Detail and Touch Source tables above (e.g. `paidsearch` → Paid Search, `organic` → Organic Search).

**Touch Source Detail fields (use with caution):**
- `Contact_Conversion_Touch_Source_Detail__c` = `lc_utm_source` value (e.g. "google", "BING") or HubSpot `latest_conversion_touch_source_detail`
- `Contact_Conversion_Touch_Source_Detail_2__c` = `lc_utm_campaign` value or HubSpot `latest_conversion_touch_source_detail_2`
- **Do NOT blanket-populate touch source fields on every opp.** Only recommend touch source values when the data is unambiguous and high confidence. When unsure, leave them for Sam to set manually. Writing incorrect UTM data to opps causes downstream reporting headaches.

**Campaign assignment for REA Direct sign-ups:**
- Use **Sign Up Form - {current_quarter}** when contact has tracked conversion data — `lc_utm_*` fields populated (even `direct/organic` with `signup.homebotapp.com/signup` counts as tracked)
- Use **REA Direct Sign Ups - {current_quarter}** only when there is truly zero conversion tracking (all `lc_utm_*` fields null, no HubSpot `latest_conversion_touch_source`)
- When unsure whether the UTM data qualifies as "tracked", flag for review rather than guessing

#### REA Direct Attribution (high-volume, ~450/month)

REA Direct opps are auto-created by Integration User when a Real Estate Agent self-signs-up. They were previously unattributed due to capacity. Key signals:

| Signal | Attribution |
|---|---|
| Coupon contains "reactivate" OR has **recent** "Churn Winback" campaign membership (created within last 30 days) | **Churn Winback** — trumps other signals. Coupon is always definitive regardless of age. But campaign membership alone only counts if created within 30 days of opp creation. Older winback memberships (e.g. Q3 2025 membership on a Q2 2026 opp) are stale — the contact was targeted for winback months ago but came back on their own. Attribute as Direct Sign-Up instead. |
| Has campaign membership for "Event (Webinar)" like "REA Group Demos" AND demo was within ~5 days of sign-up | **Demo Request** — the group demo was the acquisition event. Keep the original demo campaign. But if the demo was 7+ days before the sign-up, check the activity timeline for a more proximate cause (e.g. a nurture email that actually drove the conversion). |
| Has campaign membership linking to LO invite campaign, or campaign type = "LO Referrals", or campaign name contains "Invited by REA" OR "invited by LO" | **Co-Sponsorship Invite** / Homebot Platform — this trumps Direct Sign-Up even if a sign-up form exists. The invite is the acquisition event. |
| Has campaign membership for "Direct Sign-Ups" type (sign-up form) but NO prior demo/event/winback membership | **Direct Sign-Up** + use UTMs for detail. Use the actual sign-up form campaign the contact is a member of (e.g. "Sign Up Form - Q1 2026"), not the generic REA Direct Sign Ups. Set Touch Source from UTMs (e.g. Direct Traffic for organic/direct). |
| REA opp where Sam's review reveals group demo attendance not yet in SF | **Demo Request** with "REA Group Demos" campaign — Sam may have context outside SF that confirms group demo attendance. These get flagged as needs_review when no group demo campaign membership exists yet. |
| No campaign membership, no coupon | **Direct Sign-Up** / Direct — self-service with no tracking |

**REA-specific campaigns:**
- Use **"REA Churn Winback - {current_quarter}"** for REA churn winback opps (note: may not appear in standard campaign type filters — query by name)
- Use **"REA Direct Sign Ups - {current_quarter}"** for REA opps with no campaign data (not the generic "Direct Sign Ups")
- When the contact IS a member of a specific sign-up form campaign, use THAT campaign (e.g. "Sign Up Form - Q1 2026") instead of the generic REA Direct Sign Ups
- Use **"REA Group Demos - {current_quarter}"** when contact attended a group demo
- If the contact attended a group demo AND signed up within ~5 days, the demo is the real source → **Demo Request** with the group demo campaign
- **But if a nurture email was opened on the same day as the sign-up** (email → page view → form submit chain), the nurture email is the proximate cause — attribute as **Direct Sign-Up / Nurture** with the nurture campaign (e.g. "REA Nurture MOFU - Q2 2026"), Touch Source = Email Marketing. The old group demo was context, not the driver.

Most REA Direct opps are straightforward: no campaign = Direct Sign-Up (REA Direct Sign Ups campaign), reactivate coupon = Churn Winback, LO invite campaign = Co-Sponsorship. Apply with high confidence.

**Proximate cause principle (critical):**
Always check the activity timeline for what *actually* drove the conversion, not just campaign memberships. If a nurture email was opened on the same day as a sign-up (email → page view → form submit), that email is the attribution driver — even if older campaign memberships (group demos, product tours) exist. Example: contact registered for a group demo 10 days ago, but a "Spring game plan" MOFU email drove the actual sign-up → **Direct Sign-Up / Nurture** with the nurture campaign, Touch Source = Email Marketing. The old demo was context, not the proximate cause.

#### Key Decision Patterns

**Campaign assignment is as important as LeadSource.** Always set `CampaignId` on the opp. Here's how to find the right one:

**Owner-specific outreach campaigns (for Prospecting):**
Each outbound rep has a personal Outreach Sequence campaign for the quarter. Match the opp owner to their campaign:
- Nina Hein → "Nina Hein - Title Outbound - Q1 2026" (Outreach Sequence)
- Morgan Bell → "SMB Outbound - Q1 2026 - Morgan" (Outreach Sequence)
- Pattern: `[Rep Name] - [Segment] Outbound - {current_quarter}` or `[Segment] Outbound - {current_quarter} - [Rep Name]`
- Query: `SELECT Id, Name FROM Campaign WHERE Type = 'Outreach Sequence' AND Name LIKE '%{current_quarter}%'` to find the right one

**Standard campaigns by LeadSource:**
- Direct Sign-Up → "Hunting License Sign Ups - {current_quarter}" **ONLY** when VSB_Type__c = "Loan Officer - HL" or "Loan Officer - Broker". For other VSB types, use "Direct Sign Ups - {current_quarter}" or "Sign Up Form - {current_quarter}" as appropriate.
- Demo Request → "Demo Requests - {current_quarter}" (Demo Request type)
- Events → The specific event campaign (e.g. "ALTA Edge - Frisco, TX - Q1 2026")

**VSB_Type__c field** (picklist on Opportunity):
- Loan Officer, Insurance, Title, REA, Loan Officer - HL, Loan Officer - Broker
- This determines which "Direct Sign-Up" campaign to use
- **Fairway plan code on non-Fairway accounts → DELETE**: If a non-Fairway account has `fairway-unlimited-pro` plan code, these are cross-company Data POC junk — delete them. Fairway account opps with fairway plan codes are generally legitimate and should be attributed normally (VSB_Type should be "Loan Officer - HL", campaign should be "Hunting License Sign Ups"). Flag for review if a large batch appears at once — could be a bulk plan conversion rather than new revenue.

**Engage_Flow_Name__c — key signal for campaign assignment AND LeadSource:**
The `engage_flow_name` field on the opp tells you which sales engagement sequence generated the opp. Use it to match to the right campaign:
- "Common Room Outbound - SMB AE - 2026" or "Common Room Website Hit" → **Prospecting / Inside Sales** with **SMB AEs - Common Room - {current_quarter}**
- "MDR_PaidSocial_Handraisers_Get Demo Scheduled" → confirms **Demo Request / Paid Social** path
- **"Winback"**, **"Non-Payment"**, **"Auto-Winback"**, **"Price"** in flow name → strong **Churn Winback** signal. Even if LeadSource is already set to something else (e.g. Direct Sign-Up), the winback engage flow means the contact churned and came back. Override LeadSource to Churn Winback and use the matching Churned LOs campaign (e.g. "Churned LOs - Non-Payment - {current_quarter}").
- Pattern matching: look for keywords (Common Room, Outbound, PaidSocial, Winback, Non-Payment, etc.) and match to the campaign catalog
- When Engage Flow Name is present, it's a strong signal for both LeadSource and CampaignId

**Outbound Demo_Type vs existing Demo Request LeadSource:**
If an opp has Demo_Type = Outbound but LeadSource = Demo Request, check for **duplicate or prior opps on the same account/contact** first. If a prior opp exists with Demo Request, this may be a rep re-booking a no-show or cancellation — keep Demo Request. If no prior opp exists, the outbound signal is stronger — change to Prospecting. Flag ambiguous cases for review.

**Ashley Bangura (Customer Support) pattern:**
When owner = Ashley Bangura (Customer Support role) and the opp has a booked/held demo, this is a **Churn Winback / CSM** with **LO Churn Winback - {current_quarter}** campaign. Ashley handles LO winbacks through customer support.

**Campaign assignment — current quarter campaigns:**
Use the current quarter's campaigns for new opps. Previous quarter campaign memberships on the contact are historical context (useful for understanding the journey) but assign the current quarter's campaign to the opp. Exception: in the first ~2 weeks of a new quarter, if the contact's membership is very recent and clearly the acquisition event, the previous quarter campaign may still be appropriate — use judgment.

**When Demo_Type = "Outbound" — distinguish Prospecting vs Direct Email / Call:**
- Demo_Type Outbound means an outbound touch, but there are two flavors:
  - **Prospecting**: Rep is working the contact through an outreach sequence campaign. Use the owner's personal outreach sequence campaign (e.g. "Nina Hein - Title Outbound - {current_quarter}").
  - **Direct Email / Call**: Rep reached out directly, NOT through a sequence. Use "Direct Emails to Inside Sales - {current_quarter}" campaign.
- **How to tell the difference**: If the contact has NO outreach sequence campaign membership and the activities suggest direct/ad-hoc outreach (one-off emails, direct calls without Nooks/Outreach patterns), it's Direct Email / Call. If the contact was part of a systematic sequence, it's Prospecting.
- For both: use owner role to determine AE vs Inside Sales for Lead_Source_Detail.
- **Do NOT set Contact_Conversion_Touch_Source fields** for Prospecting or Direct Email / Call. Those fields are for inbound/marketing attribution only. Leave them null for outbound opps.
- Even if the contact has other campaign memberships (sign-up forms, nurture, etc.), the Outbound demo type takes priority for LeadSource.
- Confidence: high for clear cases, medium when ambiguous between the two flavors.

**When description mentions meeting, partnership, or any face-to-face interaction:**
- Do NOT default to Prospecting — ALWAYS check for an Event campaign first
- Query: `SELECT Id, Name FROM Campaign WHERE Type LIKE 'Event%' AND Name LIKE '%{current_quarter}%'` AND also check previous quarter
- Match keywords from the description (company name, conference name, city) to campaigns
- Even if the opp is a partnership/revshare/non-standard deal, the event is still the acquisition source
- Check BOTH contact-level campaign memberships AND account-level signals (emails, activities mentioning events/conferences)
- Attribution: Events (3rd Party) / Events (In-House) / Events (Webinar) based on campaign type
- Lead_Source_Detail: "Event"
- Example: SoftPro Partnership opp → account-level emails about ALTA Edge → Events (3rd Party) with ALTA Edge campaign (no contact campaign membership existed)

**When Demo_Type = "Inbound" but campaign type is "Umbrella" or "Social Media":**
- Look at the campaign NAME, not just type
- "LO Nurture TOFU" campaigns → likely **Demo Request** with detail from UTMs
- "Google Ad Engagement" → likely **Demo Request** with Paid Search
- If ambiguous, check other campaign memberships for a more specific type
- Set CampaignId to "Demo Requests - {current_quarter}" campaign

**When Demo_Type = "Direct" with no coupon:**
- Usually **Direct Sign-Up**
- Set CampaignId to "Hunting License Sign Ups - {current_quarter}" campaign
- Check if they have campaign memberships that suggest a different source

**When coupon contains "reactivate":**
- Always **Churn Winback**, regardless of other signals
- Still populate Lead_Source_Detail from UTMs if available

**Multi-campaign contacts:**
- Don't just use the most recent — look for the most RELEVANT campaign
- A specific campaign type (Demo Request, Event, etc.) beats a generic Umbrella
- A campaign created close to the opp creation date is more relevant
- Outbound demo type trumps campaign membership signals

### Step 3 — Write Decisions
Write the decisions array to `/tmp/sf_attribution_decisions.json` using the Write tool. Always include `sf_url` for every opp.

```json
[
  {
    "opp_id": "006...",
    "opp_name": "John Smith - VSB",
    "sf_url": "https://homebot.my.salesforce.com/006...",
    "action": "auto_apply",
    "lead_source": "Demo Request",
    "lead_source_detail": "Paid Social",
    "touch_source": "Paid Social",
    "touch_source_detail": "q1_2026_lo_demo",
    "touch_source_detail_2": "facebook",
    "campaign_id": "701...",
    "confidence": "high",
    "reasoning": "Demo_Type is Inbound, most recent campaign is Demo Request type with paidsocial UTM medium"
  },
  {
    "opp_id": "006...",
    "opp_name": "Jane Doe - VSB",
    "action": "needs_review",
    "lead_source": "Prospecting",
    "lead_source_detail": "Inside Sales",
    "confidence": "low",
    "reasoning": "Demo_Type is Outbound but contact has a recent webinar campaign membership that may be the actual source"
  }
]
```

**CampaignMember creation for outbound opps:**
When a decision assigns a Prospecting LeadSource with an Outreach Sequence campaign, include a `add_to_campaign` field in the decision:
```json
"add_to_campaign": {
  "contact_id": "003...",
  "campaign_id": "701...",
  "status": "Demo booked via Sequence"
}
```
This tells the apply step to also create a CampaignMember record (POST `/services/data/v62.0/sobjects/CampaignMember`). Only include this when:
- The opp has a `contact_id` (some outbound opps, especially Insurance, may not)
- The campaign type is "Outreach Sequence"
- The contact is NOT already a member of that campaign (check `campaign_memberships` in the context)

**Confidence thresholds:**
- **high** — clear signal, single obvious answer
- **medium** — reasonable confidence but worth a second look
- **low** — ambiguous, multiple valid interpretations

**IMPORTANT: ALL decisions are `action: "needs_review"` — do NOT auto-apply.** Present every decision to the user for review. Only apply after explicit confirmation.

### Step 4 — Present for Review (DO NOT AUTO-APPLY)
Present ALL decisions to the user with **clickable Lightning Salesforce links**. Do NOT run the apply script until the user reviews and confirms.

**Use this table format — always.** Do not use prose paragraphs or bullet-heavy walls of text. Keep it scannable.

```
| # | Opp | Attribution | Campaign | Confidence | Key Signal |
|---|-----|-------------|----------|------------|------------|
| 1 | [Name](lightning_url) | LeadSource / Detail | Campaign Name | 🟢 high | 1-line reason |
| 2 | [Name](lightning_url) | LeadSource / Detail | Campaign Name | 🟡 medium | 1-line reason |
| 3 | [Name](lightning_url) | LeadSource / Detail | Campaign Name | 🔴 low | 1-line reason |
```

**Column rules:**
- **Opp**: Clickable link using `https://homebot.lightning.force.com/lightning/r/Opportunity/{opp_id}/view`
- **Attribution**: `LeadSource / Lead_Source_Detail` — e.g. "Direct Sign-Up / Nurture"
- **Campaign**: Short campaign name (drop the quarter suffix if space is tight)
- **Confidence**: 🟢 high, 🟡 medium, 🔴 low
- **Key Signal**: The single most important reason in ≤15 words. Not a full reasoning dump.

**After the table**, add a **Details** section ONLY for 🟡 medium and 🔴 low confidence opps. Use this format:

```
**Details (flagged opps):**

**2. Name** — [Full reasoning in 1-2 sentences. What's ambiguous and what are the alternatives.]

**3. Name** — [Full reasoning.]
```

If touch source fields are being set, note them in the details section (e.g. "Touch Source: Email Marketing"). Don't clutter the table with them.

🟢 high confidence opps need no extra detail — the table row is enough.

## Scope

**In scope:** VSB (including REA Direct), Title, Insurance, New_Business (Enterprise), Teams record types. All Demo_Types.

**Out of scope:** Renewal, Corporate, Expansion record types.

## Auth & Config

**Required:**
- Salesforce credentials: `~/.sf-attribution.env` (SALESFORCE_CLIENT_ID, SALESFORCE_CLIENT_SECRET, SALESFORCE_INSTANCE_URL)
- Python with httpx: used by gather_context.py

**Optional (enhances accuracy):**
- HubSpot MCP connector — provides marketing engagement data (email opens/clicks, form submissions, touch source). No API keys needed; uses the MCP connector if available.

**Paths (update for your environment):**
- Python: `~/Desktop/personal-os-main/core/mcp/.venv/bin/python3.14`
- Decision log: `~/Desktop/personal-os-main/Knowledge/sf-attribution/attribution_log.jsonl`
- Context (ephemeral): `/tmp/sf_attribution_context.json`
- Decisions (ephemeral): `/tmp/sf_attribution_decisions.json`
