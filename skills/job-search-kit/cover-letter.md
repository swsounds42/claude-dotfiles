# Cover Letter Tailoring

Turn a job description into a tailored, in-voice letter in about ten minutes. Voice-matching on the candidate's *own* content and facts, so it's honest by construction.

## Step 1 — Load the system

1. The **proof bank** (`templates/proof-bank.md` shape) — builds, roles, numbers.
2. The **style card** — how they write. Load it *before* drafting any line, not after.
3. Any past worked application in `applications/` for a similar role. Reuse what landed.

## Step 2 — Get the job description

Fetch the URL or read the pasted text. Pull the exact title, team, location, seniority, company stage, the full responsibilities and requirements, and every tool or system named. Quote key phrases verbatim — you'll mirror some of them back.

## Step 3 — Read it twice and pull four things

1. **The company's actual problem.** What is this role being hired to fix? Scaling chaos? No attribution? A forecast leadership doesn't trust? A function that doesn't exist yet? It's usually in the first two or three responsibilities, stated in the negative.
2. **The three or four must-have keywords.** The tools, motions, and outcomes the posting repeats. These go in the letter *where they're genuinely true* — nowhere else.
3. **The seniority and scope.** IC, manager, director, VP? Building from zero, optimizing something that exists, or owning a segment? This sets how much "I build from scratch" versus "I lead and grow a team" to lean on.
4. **The stage and model.** Seed/Series A wants a builder-operator. Growth wants process and scale. Public or enterprise wants governance, forecasting, and executive reporting. PLG, sales-led, or hybrid changes the vocabulary.

## Step 4 — The greeting

Find the hiring manager or team lead on LinkedIn or in the posting. "Dear Jordan," or "Dear Jordan Rivera,". If a real search turns up nothing, "Dear Hiring Manager," — **never** "To Whom It May Concern."

## Step 5 — The tailoring paragraph

This is the only fully custom block, and it's the one that decides whether the letter gets read to the end.

> **[Something specific and true about the company] + [the exact challenge from the posting] + [the concrete thing they've built that maps to it] + [why that makes them want this role].**

Rules:
- Name something real — a product, a recent raise, a market, a stated problem. It has to prove they read past the posting.
- Connect it to a **specific build**, not a trait.
- Two to four sentences. If it runs long, cut the adjective and keep the number.
- End it pointing at *their* problem, not back at the candidate's résumé.

**Worked example.** Posting: Series B fintech, "own the CRM and build our first attribution model, forecast for the board."

> "You're at the stage where the CRM is full but the story it tells leadership still gets assembled by hand every Friday. I've built exactly that layer — an attribution engine that went from roughly half-accurate to almost fully trusted, and a forecast that moved off spreadsheets into real-time deal intelligence. Standing that up *before* the numbers get quoted to a board is the work I want to be doing."

## Step 6 — Order the proof

The body paragraphs are modular. Lead with the proof that matches the role; don't cram everything in. **Three strong role-relevant proofs beat six.**

Common heuristics:

| Role type | Lead with |
|---|---|
| Analytics / BI / data | The reporting or data-infrastructure build |
| AI-forward / platform | The automation or agent work, named concretely |
| Classic ops / systems | The architecture build and the data-quality fix |
| Post-sale / CS | The retention or customer-facing deliverable |
| "Rhythm of the business" / segment owner | The recurring-reporting build; foreground years leading teams |
| Early-stage / builder-operator | Built-from-scratch work and time reclaimed; downplay governance |
| Enterprise / public company | Frameworks, forecasting, team leadership, credentials; downplay the scrappy solo build |

## Step 7 — Honesty checks, do not skip

- **Tools.** Only name tools the candidate has confirmed using. If the posting names one that isn't on their list, **ask them** before it goes in the letter. Never claim a tool to match a keyword.
- **Requirements.** If a required qualification isn't addressed — team leadership, a domain, a certification — flag it to the candidate rather than inventing coverage. Ask for the real fact and weave that in, or lean on the closest adjacent proof and let range language carry it.
- **Numbers.** Every figure comes from the proof bank. No invented stats, no rounded-up estimates presented as measured.

## Step 8 — The in-voice pass

Draft with the style card loaded, then check for residual machine-writing tells. Preserve the candidate's signatures per the card's override table — that's the whole point.

Universal checks:
- **Don't open with throat-clearing.** "I am writing to express my interest in…" is dead on arrival. Open warm, on something true about *them*, then bring the thesis. A pure-positioning opener reads cold as a letter's first line even when it's the candidate's genuine register elsewhere.
- **Kill filler transitions** — Furthermore, Moreover, Additionally, It's worth noting.
- **No inflated significance.** "Marks a pivotal moment," "a testament to."
- **Vary sentence length.** Uniform rhythm is the most reliable tell there is.
- **Don't end on a manufactured flourish.** No engineered "not X, but Y" as the closing line, no tidy upbeat bow, no cute wordplay. Earned and concrete, an open question, or a plain stop. A flat honest ending beats a forced profound one every time.
- **If a rhetorical move is the candidate's signature, cap it at one per letter.** Even a genuine tic reads as machine-generated when it's stacked three paragraphs running.

Read it out loud once. If a line sounds like a committee wrote it, cut it.

## Step 9 — Present

Give them the letter plus:
- a short honest fit read,
- keyword coverage against Step 3,
- **every honesty call made** — tools not claimed, requirements not addressed, gaps flagged.

That last item matters more than the letter. It tells the candidate where they'll get pressed in the interview.

On approval, save a worked reference to `applications/<company>-<role>.md`: the posting's four things, the tailoring decisions, the final letter. Fold any new proof or voice correction back into the proof bank and style card so the next letter starts sharper.

## Success criteria

- [ ] Every must-have keyword appears where it's genuinely true
- [ ] The tailoring paragraph names something real and maps to a specific build
- [ ] No invented tools or stats; gaps flagged rather than faked
- [ ] Voice signatures intact; no residual AI tells
- [ ] Worked reference saved
