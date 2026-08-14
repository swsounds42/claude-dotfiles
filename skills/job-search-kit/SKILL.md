---
name: job-search-kit
description: "Tailor a cover letter to a job description, prep for interview rounds, and capture what happened after — all in the candidate's own voice, using only facts they actually have. Use when someone pastes a job listing, asks to tailor a cover letter or application, wants to practice or prepare for an interview round (recruiter screen, hiring manager, panel, exec), or wants to debrief a round they just finished. Builds on a personal corpus (proof bank + style card) the user maintains. SKIP for résumé formatting/layout, and for producing deliverables a candidate will submit as their own AI-free work in a process that requires an AI-free attestation."
---

# Job Search Kit

Three connected jobs across one application: **tailor** the letter, **prep** for the round, **debrief** what happened so the next round is sharper.

## The two rules everything else hangs on

**1. Truth-preserving.** Never invent a number, a tool, an employer, or a detail of a conversation you weren't given. Where a job description asks for something the candidate doesn't have, *flag the gap* — don't paper it. A letter that wins an interview by claiming Databricks experience loses the interview twenty minutes in. Reframe and re-emphasize what's real; fabricate nothing.

**2. Voice-preserving.** The output has to sound like the candidate, not like a language model and not like a committee. A person's writing signatures — their em-dashes, their sentence fragments, their particular rhythms — are **not** AI tells to be sanded off. Stripping them produces something worse than the original: fluent, clean, and unmistakably machine-written. Load the style card before writing a line.

These two rules are the same rule wearing different clothes. The application should be *them*, accurately.

## Routing

| The ask | Read |
|---|---|
| "Tailor my cover letter" · a pasted job listing · "help me apply to X" | `cover-letter.md` |
| "Prep me for [round]" · "mock interview me" · "practice for X" | `interview-prep.md` |
| "I just finished the [round]" · "here's how it went" | `interview-prep.md` § Debrief |
| First time using this, or no corpus exists yet | `corpus.md` |

## The corpus

Everything here runs on two files the candidate owns and improves over time:

- **A proof bank** — their builds, roles, and numbers, with a note on which kind of role each proof is best for.
- **A style card** — how they actually write, distilled from their own real writing, including the signatures a generic humanizer would wrongly strip.

Templates for both are in `templates/`. If neither exists, start at `corpus.md` — it's a fifteen-minute setup that makes every later use of this skill better. Don't skip it and wing the voice from memory.

Worked applications get saved too (`applications/<company>-<role>.md`): the JD's demands, what was tailored and why, the letter, and round-by-round debriefs. That folder is the skill's memory. Read it before starting a similar role.

## Working principles

- **Read the whole job description twice before writing anything.** Most tailoring failures are comprehension failures.
- **One researched sentence beats three generic ones.** Naming something real about the company — a product, a market, a stated problem — proves the candidate read past the posting.
- **Specific builds beat traits.** "I built X and it did Y" outperforms "I'm passionate about scaling."
- **Numbers instead of adjectives.** Kill any adjective a figure could replace.
- **Ask rather than assume** when a required fact is missing. A single clarifying question is cheaper than a fabrication.
- **Don't over-produce.** A cover letter is one page. A prep doc is a reference to glance at, not an essay to memorize.

## The honesty line

Writing application material — cover letters, thank-you notes, outreach — in a candidate's own voice and facts is ordinary professional help. Fair game.

**Producing work a candidate will submit as their own AI-free output, in a process where they've attested no AI was used, is not.** Some companies require that attestation for take-homes, assessments, and live rounds. Where it applies, this skill prepares the candidate to *do* the work — drills, practice cases, feedback — and does not do the work for them. That boundary is in `interview-prep.md` in full, and it holds even when the candidate asks otherwise.

The honest version is also the stronger one. Prep that makes someone able to do the job is what survives the interview, the reference check, and the first ninety days.
