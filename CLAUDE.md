# ROUTING IMPERATIVE — read this first, every prompt

**Default to delegation.** Before responding to ANY user request:

1. Check the Cascade hook output (top of context — `[CASCADE SKILLS]`, `[CASCADE ROUTING]`, and `[CASCADE MODEL]` blocks). If a skill or agent appears with score ≥ 0.20, **INVOKE IT before doing inline work**. If `[CASCADE MODEL]` recommends Opus or Haiku, **delegate the work via the Task tool with that `model:` parameter** rather than running on the session's default model.
2. Scan the routing table below. If the request matches a row, **MUST invoke the listed skill** — do not paraphrase or do it yourself.
3. Spawn a specialist subagent for any task spanning > 1 file or requiring domain depth (SF, HubSpot, Python, frontend, security, etc.).

**Bias toward skill/agent invocation, not inline action.** A 299-skill stack only pays off if it fires. Every prompt is a routing decision first, an action second.

## Read-before-edit discipline (CodeBurn-flagged: 6.8M tokens/mo)

Before editing any file, **read it first**. Before modifying a function, **grep for all callers**. Research before you edit. Edit-to-read ratio should be 1:4 or better — if you're editing without reading, you're causing retries that compound token waste.

Avoid re-reading the same file. If you need to look at `<file>` again, point Claude at exact lines or function names in your prompt: `In <file> lines <start>-<end>, look at the <function> function.` Top historical re-read offenders: `sf_attribution_context.json`, `page.tsx`, `generate_all_digests.py`.

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
| Gong call data / transcript / summary / submission status / library folder pull | `mcp__gong__*` tools (gongio-mcp) — never paste screenshots when MCP can fetch |
| Find a past Claude Code session by topic ("which session did I work on X") | `session-finder` or `session-search` skill |
| "Should I automate this?" / structured automation triage | `automation-advisor` skill |
| Tufte-style data report / publication-quality HTML dashboard with sparklines + Chart.js | `tufte-report` skill |
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
| Token waste audit / "which skills/MCPs am I not using" / Claude Code health check | `codeburn optimize --provider claude -p 30days` (CLI) |
| AI-slop UI detection / pre-ship HTML design check / find purple gradients/Inter/cards-in-cards | `npx impeccable detect <path>` (CLI) |
| Stress-test plan against project context / build CONTEXT.md / ADR-as-you-go interrogation | `grill-with-docs` skill (manual: invoke `/grill-with-docs`) |
| Find refactor candidates / Ousterhout deep-module review / surface architectural friction | `improve-codebase-architecture` skill |
| "Be terse" / "cut output tokens" / "caveman mode" / long debugging sessions where output bloat is killing you | `caveman` skill (toggles persistent compressed-output mode) |

If the work matches an anti-pattern row above, **do not start typing** — invoke the skill first.

## Cascade Model Router (aggressive mode)

The Cascade `UserPromptSubmit` hook automatically classifies every prompt and emits a `[CASCADE MODEL]` directive when the work would be better handled by a Claude tier other than Sonnet 4.6 (the recommended session default). The router is silent for standard work — only Opus escalations and Haiku downgrades produce a directive.

The router is in **aggressive mode**: it leans toward Haiku for ambiguous prompts and demands strong evidence before recommending Opus. Asymmetric thresholds:
- Opus emits at confidence ≥ **0.85** (narrow, conservative)
- Haiku emits at confidence ≥ **0.65** (broad, eager)
- Plus a length-based fallback: prompts under **80 chars / 12 words** default to Haiku unless a stronger pattern fires

Rationale: Opus on trivia wastes ~5× credits silently. Haiku failing on hard work wastes one turn the user retries with `!opus`. Recoverable failures are the cheaper failure mode.

**How to act on `[CASCADE MODEL]` blocks:**

| Tag | What to do |
|---|---|
| `[CASCADE MODEL] ⚡ ESCALATE: ... Opus 4.7 ...` | Spawn the actual reasoning work via the Task tool with `model: 'opus'`. Don't run inline if the session is on Sonnet/Haiku — the lighter session model will do worse on the work the router flagged as Opus-tier. |
| `[CASCADE MODEL] DOWNGRADE: ... Haiku 4.5 ...` | Spawn via Task tool with `model: 'haiku'` to save credits. Run inline only if the session is already on Haiku. |
| (no `[CASCADE MODEL]` block) | Sonnet 4.6 is sufficient. Run inline. |

**Tier intent (aggressive mode):**
- **Opus 4.7** — GSD planning/debug/research skills, "design a [system\|architecture\|pipeline\|layer\|...]", security audits, strategic memos, board updates, mbb-frame, Ernie persona, production-grade hard debugging (race conditions, intermittent failures, root-cause analysis)
- **Sonnet 4.6** *(silent default)* — standard build tasks (implement/build/create/write + code noun), code review, bug fixes, test writing, doc updates, refactors, multi-file work, drafting messages
- **Haiku 4.5** — confirmations (yes/lgtm/ship-it), typo/lint fixes, commit messages, Cascade/GSD quick commands, `gws-*` / `recipe-*` / `sf-(soql\|metadata\|deploy\|...)` mechanical ops, single-field updates, deletions, run/execute, lookups, **and any short prompt without a stronger signal**

**Manual overrides** — include in any prompt:
- `!opus` / `--opus` / `force opus` → escalate
- `!sonnet` / `--sonnet` / `force sonnet` → standard
- `!haiku` / `--haiku` / `force haiku` → downgrade

**Kill switch:** `export CASCADE_MODEL_ROUTER=off` disables the router for the session.

**Tuning:** decisions are logged to `~/Desktop/personal-os-main/.cascade/sessions/model-decisions.jsonl`. Inspect with:
- `node ~/Desktop/personal-os-main/scripts/hooks/model-router.cjs --stats` — distribution of recent decisions
- `node ~/Desktop/personal-os-main/scripts/hooks/model-router.cjs --tail 20` — last 20 with confidence + reason
- `node ~/Desktop/personal-os-main/scripts/hooks/model-router.cjs "<prompt>"` — classify a specific prompt

Thresholds and pattern lists live in `~/Desktop/personal-os-main/scripts/hooks/model-router.cjs` — tune `EMIT_THRESHOLD_OPUS`, `EMIT_THRESHOLD_HAIKU`, `SHORT_PROMPT_CHARS`, `SHORT_PROMPT_WORDS`, or the `MODEL_PATTERNS` array directly.

**Recommended baseline:** **Sonnet 4.6 is the configured default** — set via the `"model"` key in `settings.json`, so new sessions start on Sonnet. Opt *up* to Opus per-session with `/model opus` (or `!opus`) for marathon ship-work and hard reasoning; the router still escalates the cases that genuinely need Opus and downgrades trivial work to Haiku. The content-aware guard (`hasRealWorkSignal()`) rescues short real-work prompts — troubleshooting, scoped questions, review/feedback — so they fall through to Sonnet instead of getting downgraded.

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
| Token waste audit, "what skills/MCPs am I not using", Claude Code health grade, optimize CLAUDE.md | run `codeburn optimize --provider claude -p 30days` (CLI, read-only) |
| Per-model one-shot rate, validate model-router thresholds, productive-vs-reverted spend | run `codeburn compare -p 30days` or `codeburn yield -p 30days` |
| AI-slop UI detection, audit HTML for design anti-patterns (purple gradients, Inter, cards-in-cards, gray-on-color), pre-ship design check | run `npx impeccable detect <path>` (CLI, no LLM, suitable for CI) |
| Stress-test a plan against project's domain language, build/maintain CONTEXT.md, capture ADRs as you decide | `grill-with-docs` skill — manual invocation via `/grill-with-docs` (skill has `disable-model-invocation: true`) |
| Find refactor candidates, surface deepening opportunities, Ousterhout deep-module review, identify shallow modules earning their keep | `improve-codebase-architecture` skill |
| "Be terse", "cut output tokens", "caveman mode", "talk like caveman", long debug sessions where output bloat is expensive | `caveman` skill (toggles persistent compressed-output mode; "stop caveman" to disable) |

### Routing Rules

- Match on intent, not exact keywords. "Help me write a blog post" triggers `content-research-writer`. "Make my tweet better" triggers `twitter-algorithm-optimizer`.
- If multiple skills could apply, pick the most specific one. Ask only if genuinely ambiguous.
- Skills with supporting files store resources in `~/.claude/commands/skill-resources/{skill-name}/`. Reference these paths when the skill instructions mention scripts, templates, themes, or examples.
- Some skills require external dependencies (Composio API key for `connect`/`connect-apps`, Playwright for `webapp-testing`, yt-dlp for `video-downloader`, langsmith-fetch CLI for `langsmith-fetch`, `codeburn` Node CLI for token-waste audits, `impeccable` Node CLI for HTML anti-pattern detection). If a dependency is missing, tell the user what to install and offer to set it up.

@RTK.md
