---
name: humanize
description: >-
  Rewrites AI-sounding prose so it reads like its writer, keeping every
  claim, number, and citation at its original strength and inventing
  nothing. A writing sample or style file outranks its catalogue of AI
  writing tells. Pasted text comes back rewritten; a named file is edited in
  place. Use when asked to humanize, de-AI, or naturalize prose, or to
  remove AI writing patterns.
license: MIT
metadata:
  argument-hint: "[text-or-file]"
---

# Humanize

Rewrite AI-sounding text so it reads like its writer, replacing the generic
with the specific. §1-35 come from Wikipedia's ["Signs of AI
writing"](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing);
§36-40 and added cases in older entries cover tells that survive a
vocabulary scrub.

## Registry

| Name | Path |
| --- | --- |
| `calibration` | [references/calibration.md](references/calibration.md) |
| `chatbot` | [references/chatbot.md](references/chatbot.md) |
| `content` | [references/content.md](references/content.md) |
| `filler` | [references/filler.md](references/filler.md) |
| `language` | [references/language.md](references/language.md) |
| `register` | [references/register.md](references/register.md) |
| `rhetoric` | [references/rhetoric.md](references/rhetoric.md) |
| `style` | [references/style.md](references/style.md) |

## Redirects

- Checking a document's facts: `/fact-check`

## Invariants

Hold these in every mode. Each outranks any pattern fix.

1. **Keep every claim.** Shorten dull parts, expand useful parts, merge or
   split paragraphs, but keep the information.
2. **Invent no facts.** Add no fact, name, number, date, quote, or citation
   the source or user did not supply. When a sentence needs a missing
   detail, ask for it or write a simpler sentence. An opinion or reaction is
   allowed where the writer's voice calls for one; a factual claim is not.
   Fiction is exempt: invented detail is the task.
3. **Match the voice.** Formal, casual, or technical to fit the text. Read
   any supplied sample first: note sentence length, word choice, paragraph
   openings, punctuation, repeated phrases, and transitions. Keep casual
   words casual and deliberate quirks intact. A personal style file (voice
   guide, style document, explicit voice instructions) or sample outranks
   every pattern here: load it before any owner file, and where it permits a
   construction a pattern flags (an em-dash habit, personification of
   systems, candid asides, placement verbs), keep the construction without
   asking. A sample full of em dashes keeps its rate, so §14 is not a ban.
4. **Personality only where it fits.** In blog posts, essays, opinion, and
   personal writing, keep the writer's opinions, uncertainty, mixed
   feelings, humor, asides, and uneven rhythm. Keep reference, technical,
   legal, and factual text neutral.
5. **Preserve logical strength.** Cutting a negation, a hedge, or a
   comparative can change what a sentence claims. After any such cut,
   re-read the claim: a criterion stays a criterion, evidence stays
   evidence, a possibility stays possible. "Passes not when X but when Y"
   becomes "passes only when Y", never "passes when Y"; "there is evidence
   that A and B pull apart" keeps "evidence suggests". Restore lost strength
   with only, can, may, suggests, or an equivalent.

   <checklist for="modality">
     <item>necessary became sufficient: restore "only", "requires", "unless"</item>
     <item>evidential became assertive: restore "suggests", "reports", "found"</item>
     <item>possible became actual: restore "can", "may", "sometimes"</item>
     <item>comparative became absolute: restore "more than", "than the alternative"</item>
   </checklist>

## Output modes

The procedure is the same in every mode.

| Mode | Takes | Returns |
| --- | --- | --- |
| Pasted text (default) | Text in the conversation | Draft, short list of remaining AI patterns, final rewrite |
| File | A file the user names | Only the final text, written to the file with prose changed only (code blocks, YAML metadata, data, and link targets kept); then a short summary |
| Embedded | Text from another task that invokes the skill (PR text, commit message, docs) | Final text only |

## Procedure

1. Load the personal style file or voice sample first when one exists
   (invariant 3).
2. Scan the input against the detection index and collect suspected hits.
3. Zero hits: return the text unchanged per output mode, state that no AI
   patterns were found, and load nothing.
4. Otherwise load exactly the owner files of the hits, plus `calibration`.
   Never rewrite flagged text without `calibration`.
5. Check §14-19 mechanically: search for U+2014, U+2013, `**`, heading case,
   emoji, curly quotes, ` -- `, and `---` lines. Measure §36 with the
   command in `register` on prose over about 40 sentences, before and after
   the rewrite.
6. Mark each pattern instance from the scan and confirm it against its owner
   file. Drop the false positives that `calibration` and the entry's
   exceptions name.
7. Draft. Read it aloud for rhythm, concrete detail, simple verbs, and the
   right formality. State each point fresh rather than patching flagged
   phrases one at a time: a word swap leaves the shape, and a word list
   applied as a ban flattens prose, removing ordinary English while the
   suppressed term tends to resurface. When a sentence stays awkward,
   rewrite the paragraph around its main point.
8. Self-check three questions, treating a yes to any as an error to fix:
   - What still sounds AI-generated?
   - Did the rewrite add or drop any fact, name, number, date, quote,
     citation, or ranking?
   - Did removing a negation, hedge, or comparative strengthen a claim
     (invariant 5)?
9. Sweep the final text for U+2014 and U+2013 per §14, and re-measure §36
   where it applied.

## Detection index

40 patterns, owned by contiguous range: §1-6 `content`, §7-13 `language`,
§14-19 `style`, §20-22 `chatbot`, §23-26 `filler`, §27-35 `rhetoric`, §36-40
`register`. The cues below route only; each owner file holds its patterns'
watch-lists, problem statements, exceptions, and before/after examples.

Every entry occurs in human writing; a hit is a style signal, never proof of
authorship. Structural and rhetorical entries are diagnostic alone or in
pairs; lexical entries (§7, §37) count only in clusters or above the density
the owner file states. When unsure, look for several patterns together:
several stock patterns in one passage are stronger evidence than any one.
Vocabulary tells drift by model and year; structural ones last.

| § | Cue |
| --- | --- |
| 1 | Ordinary detail cast as pivotal moment, legacy, or broader trend |
| 2 | Media outlets or follower counts listed to prove importance |
| 3 | Fact plus trailing -ing phrase adding fake depth (highlighting..., reflecting...) |
| 4 | Ad-copy tone: vibrant, nestled, breathtaking, rich heritage |
| 5 | Unnamed authorities: experts argue, industry reports; first-person versions (most people I've talked to); borrowed consensus (famously, as we all know) |
| 6 | Stock Challenges or Future Outlook section restating vague claims |
| 7 | AI-favored vocabulary, clustered: delve, tapestry, testament, pivotal; Claude-era: genuine, latent, quietly, seam |
| 8 | serves as, boasts, features dodging is, are, has |
| 9 | Not X but Y frames; clipped negative endings (no guessing); staccato negation (No X. No Y. Just Z.) |
| 10 | Ideas forced into triads |
| 11 | Synonym cycling for one subject; repeated sentence openings |
| 12 | from X to Y where X and Y form no real range |
| 13 | Passive voice or dropped subject hiding the actor |
| 14 | Em or en dashes (U+2014, U+2013) beyond the writer's own rate |
| 15 | Bold scattered without reason |
| 16 | Lists where every item is a bold label plus colon |
| 17 | Title Case In Headings |
| 18 | Emoji as decoration on headings and bullets; `---` rules between sections |
| 19 | Curly quotes where the writer or format uses straight |
| 20 | Chat frame left in: greetings, offers, hope this helps |
| 21 | Knowledge-cutoff disclaimers; guessed gap-fill stated as fact |
| 22 | Praise and eager agreement before the answer |
| 23 | Wind-up phrases: in order to, it is important to note that |
| 24 | Stacked qualifiers: could potentially possibly |
| 25 | Generic upbeat send-off instead of a last fact |
| 26 | Hyphenated pairs kept after the noun (the report is high-quality) |
| 27 | Fake-depth framing: the real question, at its core; manufactured interiority: worth sitting with, I keep coming back to |
| 28 | Announcing the point instead of stating it: let's dive in; announcing the count: there are three things here |
| 29 | First sentence restating its heading or the question asked |
| 30 | Prose about the previous version outside a changelog |
| 31 | Consecutive dramatic fragments as punchlines |
| 32 | Aphorism templates: X is the Y of Z, the currency of; invented compound labels: the specification vacuum |
| 33 | Fake-candid openers: Honestly?, Look, Here's the thing; honesty qualifiers: the honest version, honest caveat |
| 34 | Rebutting objections nobody raised: I'm not saying, to be clear |
| 35 | Dismissing alternatives nobody would choose: one might be tempted |
| 36 | Uniform sentence rhythm: length variation (SD/mean) under 0.45 per block |
| 37 | Placement and weight verbs in volume: lives in, sits with, carries, load-bearing |
| 38 | Manufactured salience: the one thing, the single most, if I had to pick one |
| 39 | Compressed jargon: noun stacks, coined hyphen compounds, half-sentences |
| 40 | Reasoning residue: the single most important correction, does not survive contact with |
