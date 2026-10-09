---
name: humanize
description: >-
  Rewrites AI-sounding prose so it reads like its writer, keeping every
  claim, number, citation at original strength, inventing nothing. Writing
  sample or style file outranks its catalogue of AI writing signs. Pasted
  text comes back rewritten; named file edited in place. Use when asked to
  humanize, de-AI, or naturalize prose, or remove AI writing patterns.
license: MIT
metadata:
  argument-hint: "[text-or-file]"
---

# Humanize

Rewrite AI-sounding text so it reads like its writer, replacing generic with
specific. §1-35 come from Wikipedia's ["Signs of AI
writing"](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing);
§36-40 and added cases in older entries cover signs that survive vocabulary
scrub.

## Registry

| Name | Path |
| --- | --- |
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

Hold in every mode. Each outranks any pattern fix.

1. **Keep every claim.** Shorten dull parts, expand useful parts, merge or
   split paragraphs, but keep information.
2. **Invent no facts.** Add no fact, name, number, date, quote, or citation
   source or user did not supply. Sentence needs missing detail: ask for it
   or write simpler sentence. Opinion or reaction allowed where writer's
   voice calls for one; factual claim is not. Fiction exempt: invented
   detail is the task.
3. **Match the voice.** Formal, casual, or technical to fit text. Read any
   supplied sample first: note sentence length, word choice, paragraph
   openings, punctuation, repeated phrases, transitions. Keep casual words
   casual, deliberate quirks intact. Personal style file (voice guide, style
   document, explicit voice instructions) or sample outranks every pattern
   here: load it before any owner file; where it permits construction a
   pattern flags (em-dash habit, personification of systems, candid asides,
   placement verbs), keep construction without asking. Sample full of em
   dashes keeps its rate, so §14 is not a ban.
4. **Personality only where it fits.** Blog posts, essays, opinion, personal
   writing: keep writer's opinions, uncertainty, mixed feelings, humor,
   asides, uneven rhythm. Keep reference, technical, legal, factual text
   neutral.
5. **Preserve logical strength.** Cutting negation, hedge, or comparative
   can change what sentence claims. After any such cut, re-read claim:
   criterion stays criterion, evidence stays evidence, possibility stays
   possible. "Passes not when X but when Y" becomes "passes only when Y",
   never "passes when Y"; "there is evidence that A and B pull apart" keeps
   "evidence suggests". Restore lost strength with only, can, may, suggests,
   or equivalent.

   <checklist for="modality">
     <item>necessary became sufficient: restore "only", "requires", "unless"</item>
     <item>evidential became assertive: restore "suggests", "reports", "found"</item>
     <item>possible became actual: restore "can", "may", "sometimes"</item>
     <item>comparative became absolute: restore "more than", "than the alternative"</item>
   </checklist>

## Output modes

Procedure same in every mode.

| Mode | Takes | Returns |
| --- | --- | --- |
| Pasted text (default) | Text in conversation | Draft, short list of remaining AI patterns, final rewrite |
| File | File user names | Only final text, written to file with prose changed only (code blocks, YAML metadata, data, link targets kept); then short summary |
| Embedded | Text from another task invoking skill (PR text, commit message, docs) | Final text only |

## Procedure

1. Load personal style file or voice sample first when one exists (invariant
   3).
2. Scan input against detection index; collect suspected hits.
3. Zero hits: return text unchanged per output mode, state no AI patterns
   found (Embedded: say nothing), load nothing.
4. Otherwise load exactly owner files of hits.
5. Check §14-19 mechanically: search for U+2014, U+2013, `**`, heading case,
   emoji, curly quotes, ` -- `, `---` lines. Measure §36 with command in
   `register` on prose over about 40 sentences, before and after rewrite.
6. Mark each pattern instance from scan, confirm against owner file. Drop
   false positives entry's exceptions and False positives section name; keep
   what Details to keep lists.
7. Draft. Read aloud for rhythm, concrete detail, simple verbs, right
   formality. State each point fresh instead of patching flagged phrases one
   at a time: word swap leaves shape; word list applied as ban flattens
   prose, removing ordinary English while suppressed term tends to
   resurface. Sentence stays awkward: rewrite paragraph around its main
   point.
8. Self-check three questions; yes to any is error to fix:
   - What still sounds AI-generated?
   - Did rewrite add or drop any fact, name, number, date, quote, citation,
     or ranking?
   - Did removing negation, hedge, or comparative strengthen claim
     (invariant 5)?
9. Sweep final text for U+2014 and U+2013 per §14; re-measure §36 where it
   applied.

## Detection index

40 patterns, owned by contiguous range: §1-6 `content`, §7-13 `language`,
§14-19 `style`, §20-22 `chatbot`, §23-26 `filler`, §27-35 `rhetoric`, §36-40
`register`. Cues below route only; each owner file holds its patterns'
watch-lists, problem statements, exceptions, before/after examples.

Every entry occurs in human writing; hit is style signal, never proof of
authorship. Structural and rhetorical entries diagnostic alone or in pairs;
lexical entries (§7, §37) count only in clusters or above density owner file
states. Unsure: look for several patterns together; several stock patterns
in one passage are stronger evidence than any one. Vocabulary signs drift by
model and year; structural ones last.

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

## False positives

Beyond each entry's own exceptions, person may show any of following; treat
none as evidence by itself:

- **Perfect grammar and consistent style.** Many writers are professionals
  or have been edited.
- **Mixed casual and formal styles.** Can reflect writer's field, age, or
  personal habits.
- **"Bland" or "robotic" prose.** AI prose has specific signs. Generic
  dryness without those signs is just dry writing.
- **Unsourced claims.** Most of the web is unsourced.
- **Correct, complex formatting.** Visual editors and templates produce
  clean output without any AI.
- **Edits made before November 30, 2022.** ChatGPT's public launch. Anything
  older is, with very rare exceptions, not AI-written.

## Details to keep

- **Useful limits and disclaimers.** Scope statements, legal and safety
  notices, real corrections, named objections, replies, FAQ answers.
- **Secondhand text.** Do not rewrite watched phrases inside quotations,
  titles, proper names, or examples where phrase is discussed, not used.

Keep these human details unless they hurt meaning; they often carry writer's
voice:

- **Specific, unusual details.** Real address, odd quote, phrase such as
  "the lawyer who used to work upstairs from my dentist."
- **Mixed feelings and unresolved tension.** Lines such as "I think this is
  mostly good, but it bothers me, and I can't fully explain why."
- **Dated, era-bound references.** Slang, memes, or in-jokes mapping to
  specific year and subculture. Models lag by a year or more.
- **Deliberate first-person choices.** Cut or word choice writer can
  explain.
- **Variety in sentence length.** Real writing alternates short and long. AI
  writing tends toward even, mid-length cadence.
- **Genuine asides, parentheticals, self-corrections.** "(I keep wanting to
  say 'almost' here, but it really was certain.)" Models rarely interrupt
  themselves like this.
