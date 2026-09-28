# Notices

Most of this repo is other people's work. Nearly all the agents, most of the
skills and most of the slash commands are vendored from open-source projects
so a restore works offline and stays pinned. Vendored files keep their original licenses.
The MIT license in `LICENSE` covers only the files listed under
[My files](#my-files).

One file is not under a permissive license:
`commands/twitter-algorithm-optimizer.md` is AGPL-3.0. See
[Composio's AGPL skill](#composios-agpl-skill).

Vendored files are unmodified unless a section below says otherwise. This is a
record of where things came from and which license applies. It isn't legal
advice.

## Quick map

| Path in this repo | Source | License | License text in this repo |
|---|---|---|---|
| `agents/` (130 agents + `README.md`) | [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) | MIT | `agents/LICENSE-VoltAgent.txt` |
| `agents/gsd-*.md` (33 agents) | [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done) | MIT | `agents/LICENSE-get-shit-done.txt` |
| `agents/refactor-cleaner.md`, `agents/silent-failure-hunter.md` | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT | `agents/LICENSE-ECC.txt` |
| `commands/subagent-catalog/` | [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) | MIT | `commands/subagent-catalog/LICENSE` |
| 9 Anthropic commands (list below) | [anthropics/skills](https://github.com/anthropics/skills), copied from [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | Apache-2.0 | `commands/skill-resources/<name>/LICENSE.txt` |
| 17 Composio commands (list below) | [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | Apache-2.0 | `licenses/Apache-2.0.txt` |
| `commands/twitter-algorithm-optimizer.md` | [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | **AGPL-3.0** | `commands/skill-resources/twitter-algorithm-optimizer/LICENSE.txt` |
| `commands/n8n-*.md` (7 commands) + `commands/skill-resources/n8n-*/` | [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) | MIT | `commands/skill-resources/n8n-*/LICENSE` |
| `commands/prompt-master.md` + `commands/skill-resources/prompt-master/` | [nidhinjs/prompt-master](https://github.com/nidhinjs/prompt-master) | MIT | `commands/skill-resources/prompt-master/LICENSE` |
| `commands/prompt-mini.md` + `commands/skill-resources/prompt-mini/` | [nidhinjs/prompt-mini](https://github.com/nidhinjs/prompt-mini) | MIT | `commands/skill-resources/prompt-mini/LICENSE` |
| `skills/ui-ux-pro-max/`, `banner-design/`, `brand/`, `design/`, `design-system/`, `slides/`, `ui-styling/` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | MIT | `skills/<name>/LICENSE` |
| `skills/ui-styling/` (Anthropic canvas-design material) | [anthropics/skills](https://github.com/anthropics/skills), bundled by ui-ux-pro-max-skill | Apache-2.0 | `skills/ui-styling/LICENSE.txt` |
| `canvas-fonts/` (two copies) | Font families bundled with Anthropic's canvas-design skill | SIL OFL 1.1 | `*-OFL.txt` next to each font |
| `skills/frontend-slides/` | [zarazhangrui/frontend-slides](https://github.com/zarazhangrui/frontend-slides) | MIT | `skills/frontend-slides/LICENSE` |
| `skills/last30days/` | [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) | MIT | `skills/last30days/LICENSE` |
| `skills/last30days/vendor/`, `skills/last30days/scripts/lib/vendor/` | [steipete/bird](https://github.com/steipete/bird), vendored by last30days | MIT | `LICENSE` inside each vendor folder |
| `skills/humanizer/` | [blader/humanizer](https://github.com/blader/humanizer) | MIT | `skills/humanizer/LICENSE` |
| `skills/grill-with-docs/`, `skills/improve-codebase-architecture/` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | `skills/<name>/LICENSE` |
| `skills/caveman/` | [mattpocock/skills](https://github.com/mattpocock/skills), reworked from [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | MIT | `skills/caveman/LICENSE` |
| `hooks/context-statusline.js`, `hooks/context-watchdog.js` | Adapted from [Nelson](https://github.com/Aspegio/nelson) | MIT | [below](#nelson) |
| `RTK.md` | [rtk-ai/rtk](https://github.com/rtk-ai/rtk) | Apache-2.0 | `licenses/Apache-2.0.txt` |

License files inside `agents/` and `commands/` use `.txt` names or no
extension on purpose. Claude Code loads every `.md` file in those folders as
an agent or a command.

## Agents

### VoltAgent

MIT, Copyright (c) 2025 VoltAgent. 130 agent definitions from the
`categories/` folders, plus `agents/README.md`, which is VoltAgent's
research-analysis category page. `commands/subagent-catalog/` is VoltAgent's
`tools/subagent-catalog`. Every file matches a past or current upstream
version exactly. Some are older revisions, so they differ from what VoltAgent
ships today.

### GSD (Get Shit Done)

MIT, Copyright (c) 2025 Lex Christopherson. All 33 `agents/gsd-*.md` files.
Seven of them (`gsd-ai-researcher`, `gsd-domain-researcher`,
`gsd-eval-auditor`, `gsd-eval-planner`, `gsd-framework-selector`,
`gsd-ui-researcher`, `gsd-user-profiler`) carry the path rewrite GSD's
installer makes (`~/.claude/...` becomes `$HOME/.claude/...`). The rest match
upstream exactly.

### ECC

MIT, Copyright (c) 2026 Affaan Mustafa. `agents/refactor-cleaner.md` and
`agents/silent-failure-hunter.md`, unmodified.

## Commands

### Anthropic's skills

Apache-2.0, Copyright Anthropic, PBC. These nine came from Anthropic's
[skills](https://github.com/anthropics/skills) repo by way of Composio's
[awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills)
copies:

`artifacts-builder`, `brand-guidelines`, `canvas-design`, `internal-comms`,
`mcp-builder`, `skill-creator`, `slack-gif-creator`, `theme-factory`,
`webapp-testing`

Each lives here as `commands/<name>.md` plus `commands/skill-resources/<name>/`.
Their frontmatter says "Complete terms in LICENSE.txt". That file sits in
`commands/skill-resources/<name>/LICENSE.txt`, the same license file Composio's
copies shipped with. The canvas-design fonts are covered separately, under
[Fonts](#fonts).

### Composio's skills

Apache-2.0, per the awesome-claude-skills README ("This repository is licensed
under the Apache License 2.0"). The upstream repo has no LICENSE file, so the
full Apache-2.0 text is in `licenses/Apache-2.0.txt`. Composio and its
contributors wrote these; the upstream git history shows who added each one.

`changelog-generator`, `competitive-ads-extractor`, `connect`, `connect-apps`,
`content-research-writer`, `developer-growth-analysis`,
`domain-name-brainstormer`, `file-organizer`, `image-enhancer`,
`invoice-organizer`, `langsmith-fetch`, `lead-research-assistant`,
`meeting-insights-analyzer`, `raffle-winner-picker`, `skill-share`,
`tailored-resume-generator`, `video-downloader` (plus
`commands/skill-resources/video-downloader/scripts/download_video.py`)

`skill-share.md` says "Complete terms in LICENSE.txt", but its upstream
folder never had one. The README's Apache-2.0 statement is the license that
applies.

### Composio's AGPL skill

`commands/twitter-algorithm-optimizer.md` came from the same Composio repo.
Its author tagged it `license: AGPL-3.0 (referencing Twitter's algorithm
source)` in the frontmatter, so it's under the GNU Affero General Public
License v3.0, not MIT. The full text is in
`commands/skill-resources/twitter-algorithm-optimizer/LICENSE.txt`. If you
copy or share this file, AGPL-3.0 terms apply to it.

### n8n-skills

MIT, Copyright (c) 2025 Romuald Członkowski. The seven `commands/n8n-*.md`
files and their `commands/skill-resources/n8n-*/` folders are unmodified
copies of upstream versions from October 2025 to January 2026. Later upstream
versions add hooks adapted from n8n-io/skills under Apache-2.0. None of those
are here.

### prompt-master and prompt-mini

MIT, Copyright (c) 2026 Nidhin Joseph Nelson. Both are edited versions.
`commands/prompt-master.md` and its two reference files in
`commands/skill-resources/prompt-master/` are trimmed and reworked from
upstream. `commands/prompt-mini.md` has an edited description and rules. Its
four reference files in `commands/skill-resources/prompt-mini/` are
unmodified.

## Skills

### ui-ux-pro-max-skill

MIT, Copyright (c) 2024 Next Level Builder. Seven skills from the repo's
`.claude/skills/` folder: `ui-ux-pro-max`, `banner-design`, `brand`, `design`,
`design-system`, `slides` and `ui-styling`, unmodified. Six of them carry
`author: claudekit` in their frontmatter. ClaudeKit's author is one of the
main contributors to the MIT repo they're published in.

`skills/ui-styling/` also bundles material from Anthropic's canvas-design
skill. Upstream ships it with Anthropic's Apache-2.0 license as
`skills/ui-styling/LICENSE.txt`, kept here as-is. The MIT file next to it,
`skills/ui-styling/LICENSE`, covers the rest of the skill.

### Fonts

The `canvas-fonts/` folders in `skills/ui-styling/` and
`commands/skill-resources/canvas-design/` hold 108 font files from 27 font
families that ship with Anthropic's canvas-design skill. Each family is under
the SIL Open Font License 1.1, and its license text sits next to it as
`<Family>-OFL.txt`. The fonts are not MIT.

### frontend-slides

MIT, Copyright (c) 2025 Zara Zhang. Unmodified, with its LICENSE.

### last30days

MIT, Copyright (c) 2026 Matt Van Horn. Unmodified, with its LICENSE. It
vendors [bird](https://github.com/steipete/bird) (MIT, Copyright (c) 2025
Peter Steinberger), and each vendor folder keeps its LICENSE.

### humanizer

MIT, Copyright (c) 2025 Siqi Chen. Unmodified.

### Matt Pocock's skills

MIT, Copyright (c) 2026 Matt Pocock. `grill-with-docs`,
`improve-codebase-architecture` and `caveman`, unmodified.

`caveman` in Matt's repo is a rework of Julius Brussee's
[caveman](https://github.com/JuliusBrussee/caveman) skill (MIT, Copyright (c)
2026 Julius Brussee). `skills/caveman/LICENSE` carries both notices. Julius's
repo now puts its engine under the Business Source License, but the skill
has always been under MIT, and none of the engine is here.

## Hooks and root files

### Nelson

<https://github.com/Aspegio/nelson>

- `hooks/context-statusline.js` and `hooks/context-watchdog.js`: the
  session-log parsing and the token count (input + cache creation + cache
  read from the last assistant turn) are ported to JavaScript from Nelson's
  `scripts/count-tokens.py`. The status line's 75/60/40 thresholds follow
  Nelson's hull-integrity levels.

```
MIT License

Copyright (c) 2025 Harry Munro

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### RTK

Apache-2.0, Copyright 2024 rtk-ai and rtk-ai Labs. `RTK.md` is an unmodified
copy of rtk's `hooks/claude/rtk-awareness.md`. The full license text is in
`licenses/Apache-2.0.txt`. `.rtk/filters.toml` is my own config, written in
RTK's filter format.

## My files

These are mine and MIT-licensed under `LICENSE`:

- `CLAUDE.md`, `README.md`, `NOTICE.md`, `bootstrap.sh`,
  `settings.json.template`, `zshrc`, `.gitignore`, `.rtk/filters.toml`
- `hooks/model-router.cjs`, `hooks/rtk-bootstrap.js`
- `agents/recap-analyst.md`, `commands/recap.md`
- `skills/cascade-brain/`, `skills/cascade-discover/`, `skills/efficiency/`,
  `skills/job-search-kit/`

## Earlier commits

Commits before this file was added contain the same third-party files
without their license files, under a README that described the whole repo as
MIT. Those files were always under their original licenses, as listed above,
not MIT.
