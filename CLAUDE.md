# ROUTING IMPERATIVE — read this first, every prompt

**Default to delegation.** Before responding to ANY user request:

1. Check the Cascade hook output (top of context — `[CASCADE SKILLS]` and `[CASCADE ROUTING]` blocks). If a skill or agent appears with score ≥ 0.20, **INVOKE IT before doing inline work**.
2. Scan the routing table below. If the request matches a row, **MUST invoke the listed skill** — do not paraphrase or do it yourself.
3. Spawn a specialist subagent for any task spanning > 1 file or requiring domain depth (SF, HubSpot, Python, frontend, security, etc.).

**Bias toward skill/agent invocation, not inline action.** A 299-skill stack only pays off if it fires. Every prompt is a routing decision first, an action second.

**Anti-patterns — NEVER do these inline:**

| Pattern | MUST invoke |
|---|---|
| Code review / PR review / "looks good?" | `code-reviewer` agent + `tob-differential-review` skill |
| SOQL / Salesforce query | `sf-soql` skill |
| SF report / dashboard / list view changes | `sf-reports` skill |
| SF opportunity attribution | `sf-attribution` skill |
| Salesforce contact deduplication / merge contacts / clean up dupes / "same contact twice" | `sf-contact-dedup` skill |
| HubSpot workflow / property mismatch | `hubspot-ops` skill |
| Gong forecast prep / weekly check | `homebot-forecast-checker` or `gong-forecast-ops` skill |
| Salesforce campaign clone | `sf-campaign-cloner` skill |
| Writing in Sam's voice / samwarren.io essay | `dispatch-draft` skill |
| AI-sounding text → make natural | `humanizer` skill |
| New Claude tool discovery | `cascade-discover` skill |
| Brain introspection — stats, audit weak descriptions, rebuild index, trace routing, "why didn't X fire" | `cascade-brain` skill |
| Multi-step code feature | `gsd-plan-phase` or `gsd-quick` skill |
| Hard bug crossing systems | `gsd-debug` skill |
| Internal Slack post / FAQ / status update | `internal-comms` skill |
| Marketing positioning / campaign strategy | `product-marketing-context` first, then relevant marketing skill |
| McKinsey-grade strategic memo / board update | `mbb-frame` skill |
| PDF/DOCX/PPTX/XLSX manipulation | `anthropic-skills:*` skill (the matching one) |

If the work matches an anti-pattern row above, **do not start typing** — invoke the skill first.

## Skill Auto-Routing

When a user request matches an installed skill, **MUST invoke it automatically via the Skill tool**. Do NOT wait for a slash command — detect the intent and activate the skill.

### Routing Table

| If the request involves... | Invoke skill |
|---|---|
| Writing blog posts, articles, newsletters, content with research/citations | `content-research-writer` |
| Optimizing tweets, Twitter engagement, social media reach | `twitter-algorithm-optimizer` |
| Creating visual art, posters, designs, static graphics (PNG/PDF) | `canvas-design` |
| Styling artifacts with themes (slides, docs, reports, landing pages) | `theme-factory` |
| Generating changelogs from git history | `changelog-generator` |
| Organizing messy files, deduplicating, restructuring folders | `file-organizer` |
| Organizing invoices/receipts for tax prep | `invoice-organizer` |
| Writing internal comms (status reports, newsletters, FAQs, 3P updates) | `internal-comms` |
| Building MCP servers for external API integration | `mcp-builder` |
| Creating or updating Claude skills | `skill-creator` |
| Testing local web apps with Playwright | `webapp-testing` |
| Building complex HTML artifacts (React, Tailwind, shadcn/ui) | `artifacts-builder` |
| Enhancing image quality/resolution for screenshots | `image-enhancer` |
| Creating animated GIFs for Slack | `slack-gif-creator` |
| Brainstorming domain names and checking availability | `domain-name-brainstormer` |
| Researching and qualifying sales leads | `lead-research-assistant` |
| Extracting/analyzing competitor ads from ad libraries | `competitive-ads-extractor` |
| Analyzing meeting transcripts for behavioral patterns | `meeting-insights-analyzer` |
| Tailoring resumes for specific job descriptions | `tailored-resume-generator` |
| Downloading YouTube videos | `video-downloader` |
| Picking raffle/giveaway winners from lists | `raffle-winner-picker` |
| Connecting Claude to external apps (Gmail, Slack, GitHub actions) | `connect` |
| Debugging LangChain/LangGraph agents via LangSmith traces | `langsmith-fetch` |
| Applying Anthropic brand colors/typography | `brand-guidelines` |
| Analyzing coding patterns and developer growth | `developer-growth-analysis` |
| Creating skills and sharing on Slack | `skill-share` |
| Building n8n workflows, designing automations in n8n | `n8n-workflow-patterns` |
| Writing n8n expressions, {{}} syntax, $json/$node variables | `n8n-expression-syntax` |
| Using n8n-mcp tools, searching nodes, managing workflows via MCP | `n8n-mcp-tools-expert` |
| Fixing n8n validation errors, debugging workflow issues | `n8n-validation-expert` |
| Configuring n8n nodes, operation-specific settings | `n8n-node-configuration` |
| Writing JavaScript in n8n Code nodes | `n8n-code-javascript` |
| Writing Python in n8n Code nodes | `n8n-code-python` |
| Creating slide decks, presentations, pitch decks, visual HTML slides | `frontend-slides` |
| Creating markdown-based developer presentations with Slidev | `slidev` |
| Writing, fixing, improving, or adapting prompts for any AI tool (Cursor, GPT, Midjourney, etc.) | `prompt-master` |
| Starting a project that will involve multiple AI tools and needs sharp first-attempt prompts | `prompt-master` |
| Pasting a bad prompt and asking to fix, optimize, or adapt it for a different tool | `prompt-master` |
| Vague Claude Code coding request — missing scope, file paths, or clear task definition | `prompt-mini` |
| Building something with a named stack (Next.js, Supabase, etc.) but no specific file targets | `prompt-mini` |
| Managing SF reports — listing, creating, updating filters, bulk filter flips, running reports | `sf-reports` |
| Managing SF dashboards — listing, creating, updating, refreshing dashboards | `sf-reports` |
| Quarterly report updates, flipping date filters across multiple SF reports | `sf-reports` |
| Managing SF list views — creating, editing, or running Contact/Lead/Opp list views | `sf-reports` |
| SF contact deduplication — finding, merging, or cleaning up duplicate contacts | `sf-contact-dedup` |
| UI/UX design decisions, accessibility checks, interaction patterns, visual consistency | `ui-ux-pro-max` |
| Brand voice, visual identity, messaging frameworks, brand compliance | `brand` |
| Design tokens, CSS variable systems, component specs, spacing/typography scales | `design-system` |
| HubSpot workflow management, branch filter updates, workflow inspection | `hubspot-ops` |
| HubSpot contact hygiene, HS/SF property mismatches, bulk contact updates | `hubspot-ops` |
| Cross-system HubSpot-Salesforce sync checks, property alignment | `hubspot-ops` |
| "hey Ernie", "ask Ernie", "what would Ernie say", "Ernie mode", CEO feedback in Ernie's voice | `ernie` |
| Pressure-testing a product or strategy decision as if Ernie Graham were reviewing it | `ernie` |
| Writing an email, Slack post, or doc in Ernie's voice | `ernie` |
| Converting a PDF, DOCX, EPUB, PPTX, or web page into Markdown Claude can read | `convert-document` |
| "Read this report", "extract this deck", "scrape this page", user drops a binary file or URL | `convert-document` |
| Applying MBB / McKinsey structure (SCQA, Pyramid, MECE, Data Three Essentials) to any doc | `mbb-frame` |
| "Make this executive-ready", "sharpen the argument", board updates, investor updates, strategic memos | `mbb-frame` |

### Routing Rules

- Match on intent, not exact keywords. "Help me write a blog post" triggers `content-research-writer`. "Make my tweet better" triggers `twitter-algorithm-optimizer`.
- If multiple skills could apply, pick the most specific one. Ask only if genuinely ambiguous.
- Skills with supporting files store resources in `~/.claude/commands/skill-resources/{skill-name}/`. Reference these paths when the skill instructions mention scripts, templates, themes, or examples.
- Some skills require external dependencies (Composio API key for `connect`/`connect-apps`, Playwright for `webapp-testing`, yt-dlp for `video-downloader`, langsmith-fetch CLI for `langsmith-fetch`). If a dependency is missing, tell the user what to install and offer to set it up.
