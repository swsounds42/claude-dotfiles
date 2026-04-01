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

### Step 2 — Read and Reason
Read `/tmp/sf_attribution_context.json`. For each opp in the `opps` array, use the **Attribution Rules Reference** below plus the `attribution_campaigns` array (current quarter's campaigns) to determine:

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
| Title, Insurance, Enterprise AE | AE |
| Everything else | Inside Sales |

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

#### REA Direct Attribution (high-volume, ~450/month)

REA Direct opps are auto-created by Integration User when a Real Estate Agent self-signs-up. They were previously unattributed due to capacity. Key signals:

| Signal | Attribution |
|---|---|
| Coupon contains "reactivate" | **Churn Winback** — always trumps other signals |
| Has campaign membership for "Event (Webinar)" like "REA Group Demos" | **Demo Request** — the group demo was the acquisition event, even if a sign-up form came later. Keep the original demo campaign. |
| Has campaign membership linking to LO invite campaign, or campaign type = "LO Referrals", or campaign name contains "Invited by REA" | **Co-Sponsorship Invite** / Homebot Platform |
| Has campaign membership for "Direct Sign-Ups" type (sign-up form) but NO prior demo/event membership | **Direct Sign-Up** + use UTMs for detail |
| No campaign membership, no coupon | **Direct Sign-Up** / Direct — self-service with no tracking |

**REA-specific campaigns:**
- Use **"REA Direct Sign Ups - {current_quarter}"** for REA opps with no campaign data (not the generic "Direct Sign Ups")
- Use **"REA Group Demos - {current_quarter}"** when contact attended a group demo
- If the contact attended a group demo AND later filled a sign-up form, the demo is the real source → **Demo Request** with the group demo campaign

Most REA Direct opps are straightforward: no campaign = Direct Sign-Up (REA Direct Sign Ups campaign), reactivate coupon = Churn Winback, LO invite campaign = Co-Sponsorship. Apply with high confidence.

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

**Engage_Flow_Name__c — key signal for campaign assignment:**
The `engage_flow_name` field on the opp tells you which sales engagement sequence generated the opp. Use it to match to the right campaign:
- "Common Room Outbound - SMB AE - 2026" → **SMB AEs - Common Room - {current_quarter}**
- "MDR_PaidSocial_Handraisers_Get Demo Scheduled" → confirms **Demo Request / Paid Social** path
- Pattern matching: look for keywords (Common Room, Outbound, PaidSocial, etc.) and match to the campaign catalog
- When Engage Flow Name is present, it's a strong signal for both LeadSource and CampaignId

**Campaign assignment — current quarter campaigns:**
Use the current quarter's campaigns for new opps. Previous quarter campaign memberships on the contact are historical context (useful for understanding the journey) but assign the current quarter's campaign to the opp. Exception: in the first ~2 weeks of a new quarter, if the contact's membership is very recent and clearly the acquisition event, the previous quarter campaign may still be appropriate — use judgment.

**When Demo_Type = "Outbound" — distinguish Prospecting vs Direct Email / Call:**
- Demo_Type Outbound means an outbound touch, but there are two flavors:
  - **Prospecting**: Rep is working the contact through an outreach sequence campaign. Use the owner's personal outreach sequence campaign (e.g. "Nina Hein - Title Outbound - {current_quarter}").
  - **Direct Email / Call**: Rep reached out directly, NOT through a sequence. Use "Direct Emails to Inside Sales - {current_quarter}" campaign.
- **How to tell the difference**: If the contact has NO outreach sequence campaign membership and the activities suggest direct/ad-hoc outreach (one-off emails, direct calls without Nooks/Outreach patterns), it's Direct Email / Call. If the contact was part of a systematic sequence, it's Prospecting.
- For both: use owner role to determine AE vs Inside Sales for Lead_Source_Detail.
- Even if the contact has other campaign memberships (sign-up forms, nurture, etc.), the Outbound demo type takes priority for LeadSource.
- Confidence: high for clear cases, medium when ambiguous between the two flavors.

**When description mentions meeting at a conference/event:**
- Do NOT default to Prospecting — look for an Event campaign
- Query: `SELECT Id, Name FROM Campaign WHERE Type LIKE 'Event%' AND Name LIKE '%{current_quarter}%'`
- Match the event name from the description to the campaign
- Attribution: Events (3rd Party) / Events (In-House) / Events (Webinar) based on campaign type
- Lead_Source_Detail: "Event"

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

**Confidence thresholds:**
- **high** — clear signal, single obvious answer
- **medium** — reasonable confidence but worth a second look
- **low** — ambiguous, multiple valid interpretations

**IMPORTANT: ALL decisions are `action: "needs_review"` — do NOT auto-apply.** Present every decision to the user for review. Only apply after explicit confirmation.

### Step 4 — Present for Review (DO NOT AUTO-APPLY)
Present ALL decisions to the user with **clickable Lightning Salesforce links**. Do NOT run the apply script until the user reviews and confirms.

For **auto-applied** opps, format as:
```
1. **Opp Name** → LeadSource / Lead_Source_Detail
   [Open in Salesforce](https://homebot.lightning.force.com/lightning/r/Opportunity/{opp_id}/view)
   Campaign: Campaign Name. Reasoning summary.
```

For **needs_review** opps, format the same way but flag clearly:
```
**NEEDS REVIEW: Opp Name**
[Open in Salesforce](https://homebot.lightning.force.com/lightning/r/Opportunity/{opp_id}/view)
Suggested: LeadSource / Detail. Reason: ...
```

## Scope

**In scope:** VSB (including REA Direct), Title, Insurance record types. All Demo_Types.

**Out of scope:** Renewal, Teams, Corporate, Expansion, New Business record types.

## Auth & Config

- Credentials: `~/.sf-attribution.env` (SALESFORCE_CLIENT_ID, SALESFORCE_CLIENT_SECRET, SALESFORCE_INSTANCE_URL)
- Python: `~/Desktop/personal-os-main/core/mcp/.venv/bin/python3.14`
- Decision log: `~/Desktop/personal-os-main/Knowledge/sf-attribution/attribution_log.jsonl`
- Context (ephemeral): `/tmp/sf_attribution_context.json`
- Decisions (ephemeral): `/tmp/sf_attribution_decisions.json`
