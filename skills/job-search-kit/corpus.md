# Building the Corpus

Two files, built once, improved forever. Fifteen minutes up front makes every letter and every prep session better. Skipping it means guessing at someone's voice from memory, which is how you get fluent, clean, obviously-machine-written output.

Keep them wherever the user's notes live. Suggested:

```
job-search/
  proof-bank.md
  style-card.md
  applications/
    <company>-<role>.md
```

---

## The proof bank

Start from `templates/proof-bank.md`.

**Interview the user rather than reading their résumé at them.** A résumé is what fit on two pages; the proof bank is what's true. The gap between those is where the good material lives.

Questions that surface it:
- What did you build that people still use after you left?
- What was broken when you arrived, and what was it like when you left?
- What number moved because of something you specifically did?
- What did you do that wasn't in your job description?
- What are you known for internally — what do people come to you for?
- What's a thing you're proud of that never made the résumé because it was hard to explain?

For each proof, capture the **number**, the **mechanism** (how it actually worked — this is what separates someone who ran a project from someone who built it), and **what kind of role it's best evidence for**.

**Rules:**
- Real figures only. If it was measured, cite it. If it was estimated, mark it estimated. If it's unknown, use range language rather than inventing precision.
- Keep a **confirmed tools list**. This is the guardrail against keyword-matching a tool the user has never opened. Note honest depth: *built and owned* is a different claim from *worked somewhere it ran*.
- Note credentials, languages, and any hard requirements that recur in postings.

## The style card

Start from `templates/style-card.md`.

**Distill it from real writing the user actually produced** — sent emails, Slack posts, docs, published writing. Not from asking them to describe their style; people describe an idealized version of how they write.

Collect five to ten real samples across the registers they use, then note:
- Sentence length patterns — short and punchy, long and flowing, or mixed?
- How paragraphs open. Straight in, or context first?
- Punctuation habits. Em-dashes? Parentheticals? Fragments? Semicolons?
- Recurring phrases, metaphors, and vocabulary they reach for
- Words they never use
- How they close. A call to action, an open question, a plain stop?
- How they handle transitions — explicit connectors, or just start the next point?

### The override table is the important part

A generic AI-writing cleaner will flag and remove things that are genuinely the person's voice. **Write down which of their patterns are protected**, so a later cleaning pass doesn't strip them.

Frequently mis-flagged as AI tells when they're actually human signatures:
- Em-dashes used as real appositives and asides
- "It's not X. It's Y." parallel construction, when it's how the person genuinely argues
- Rule-of-three lists, when they're substantive rather than three padding adjectives
- Sentence fragments for emphasis
- First person and strong opinions

Stripping these produces text that is clean, correct, and reads *more* machine-generated than what it replaced. The card exists so that doesn't happen.

### Registers

Most people have one voice with two or three settings. Note them, because using the wrong one is a real miss even when every sentence is technically in-voice.

A common and easily-botched split: **short internal messages** (clipped, practical, economical) versus **warm external correspondence** — thank-you notes, outreach, relationship email. The warm register usually runs hotter than the internal one: exclamation points, repeated thanks, self-aware asides, softer logistics. Applying the clipped setting to a note whose whole job is making someone glad they talked to you is a classic mistake.

---

## Keep it alive

When the user hand-edits a draft, that diff is signal. Fold it back:
- A corrected line → into the style card's examples
- A new rule ("never close on a manufactured flourish") → into the card's rules
- A new proof or number → into the proof bank
- A letter that landed → save the whole thing to `applications/`

The corpus should get sharper every time, not just longer.
