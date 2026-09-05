---
name: humanize
description: >-
  Rewrites AI-sounding prose so it reads like its writer. Every claim,
  number, and citation keeps its original strength, and no fact is invented
  to fill a gap. It works from a documented catalogue of AI writing tells,
  Wikipedia's "Signs of AI writing" plus the Claude-specific ones named
  since: inflated claims, sales language, vague sourcing, overused
  vocabulary, formulaic rhetoric, chatbot artifacts, punctuation and
  formatting habits, and flat rhythm. A writing sample or personal style
  file outranks all of them. Pasted text comes back rewritten, and a named
  file is edited in place. Use when asked to humanize, de-AI, or naturalize
  prose, edit text that sounds like a chatbot, or remove AI writing
  patterns. Do not use for code, for judging whether a text is AI-authored,
  or for fact-checking claims.
license: MIT
metadata:
  argument-hint: "[text-or-file]"
---

# Humanize: remove AI writing patterns

Rewrite AI-sounding text so it reads like its writer. §1-35 come from
Wikipedia's ["Signs of AI writing"](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing);
§36-40 and the added cases in older entries cover tells that survive a
vocabulary scrub in current model prose. Cure: the specific over the
generic.

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

## Invariants

Hold these in every mode. Each outranks any pattern fix.

1. **Keep every claim.** Shorten dull parts, expand useful parts, merge or
   split paragraphs, but keep the information.
2. **Invent no facts.** Add no fact, name, number, date, quote, or citation
   the source or user did not supply. When a sentence needs a missing detail,
   ask for it or write a simpler sentence. An opinion or reaction is allowed
   where the writer's voice calls for one; a factual claim is not. Fiction is
   exempt: invented detail is the task.
3. **Match the voice.** Formal, casual, or technical to fit the text. Read
   any supplied sample first: note sentence length, word choice, paragraph
   openings, punctuation, repeated phrases, and transitions. Keep casual
   words casual and deliberate quirks intact. A personal
   style file (voice guide, style document, explicit voice instructions) or
   sample outranks every pattern here: load it before any owner file, and
   where it permits a construction a pattern flags (an em-dash habit,
   personification of systems, candid asides, placement verbs), keep the
   construction without asking. A sample full of em dashes keeps its rate,
   so §14 in `style` is not a ban.
4. **Personality only where it fits.** In blog posts, essays, opinion, and
   personal writing, keep the writer's opinions, uncertainty, mixed feelings,
   humor, asides, and uneven rhythm. Keep reference, technical, legal, and
   factual text neutral.
5. **Preserve logical strength.** Cutting a negation, a hedge, or a
   comparative can change what a sentence claims. After any such cut,
   re-read the claim: a criterion stays a criterion, evidence stays
   evidence, a possibility stays possible. "Passes not when X but when Y"
   becomes "passes only when Y", never "passes when Y"; "there is evidence
   that A and B pull apart" keeps "evidence suggests". Restore lost strength
   with only, can, may, suggests, or an equivalent.

   <checklist for="modality">
   necessary became sufficient: restore "only", "requires", "unless"
   evidential became assertive: restore "suggests", "reports", "found"
   possible became actual: restore "can", "may", "sometimes"
   comparative became absolute: restore "more than", "than the alternative"
   </checklist>

## Detection index

40 patterns. Ownership by contiguous range: §1-6 `content`, §7-13 `language`,
§14-19 `style`, §20-22 `chatbot`, §23-26 `filler`, §27-35 `rhetoric`, §36-40
`register`. Owner files hold the full watch-lists, problem statements, and
before/after examples; the cues below route only. Signal
strength: structural and rhetorical entries are diagnostic alone or in pairs;
lexical entries (§7, §37) count only in clusters or above the density the
owner file states. Every entry occurs in human writing; a hit is a style
signal, never proof of authorship. Vocabulary tells drift by model and year;
structural ones last.

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

## Progressive loading

1. Load the personal style file or voice sample first when one exists
   (invariant 3).
2. Scan the input against the index and collect suspected hits.
3. Zero hits: return the text unchanged per output mode, state that no AI
   patterns were found, and load nothing.
4. Otherwise load exactly the owner files of the hits, plus `calibration`,
   the guard against overcorrection. Never rewrite flagged text without
   `calibration`.
5. §14-19 are mechanically checkable: search for U+2014, U+2013, `**`,
   heading case, emoji, curly quotes, ` -- `, and `---` lines. §36 is
   measurable: run the command in `register` on prose over about 40
   sentences, before and after the rewrite.

## Rewrite process

1. Mark each pattern instance from the scan. Confirm against the loaded owner
   files; drop the false positives `calibration` names.
2. Draft. Read it aloud for rhythm, concrete detail, simple verbs, and the
   right formality. State each point fresh rather than patching flagged
   phrases one at a time. When a sentence stays awkward, rewrite the
   paragraph around its main point.
3. Self-check three questions, treating a yes to any as an error to fix:
   - What still sounds AI-generated?
   - Did the rewrite add or drop any fact, name, number, date, quote,
     citation, or ranking?
   - Did removing a negation, hedge, or comparative strengthen a claim
     (invariant 5)?
4. Sweep the final text for U+2014 and U+2013 per §14 in `style`, and
   re-measure §36 where it applied.

## Output modes

| Mode | Trigger | Return |
| --- | --- | --- |
| Pasted text (default) | Text in the conversation | Draft, short list of remaining AI patterns, final rewrite |
| File | User names a file | Write only the final text to the file, changing prose only: keep code blocks, YAML metadata, data, and link targets. Then a short summary |
| Embedded | Another task invokes the skill (PR text, commit message, docs) | Final text only |

Same rewrite process in every mode.
