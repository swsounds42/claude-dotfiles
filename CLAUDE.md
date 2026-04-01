## Skill Auto-Routing

When a user request matches an installed skill, invoke it automatically via the Skill tool. Do NOT wait for a slash command — detect the intent and activate the skill.

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

### Routing Rules

- Match on intent, not exact keywords. "Help me write a blog post" triggers `content-research-writer`. "Make my tweet better" triggers `twitter-algorithm-optimizer`.
- If multiple skills could apply, pick the most specific one. Ask only if genuinely ambiguous.
- Skills with supporting files store resources in `~/.claude/commands/skill-resources/{skill-name}/`. Reference these paths when the skill instructions mention scripts, templates, themes, or examples.
- Some skills require external dependencies (Composio API key for `connect`/`connect-apps`, Playwright for `webapp-testing`, yt-dlp for `video-downloader`, langsmith-fetch CLI for `langsmith-fetch`). If a dependency is missing, tell the user what to install and offer to set it up.
