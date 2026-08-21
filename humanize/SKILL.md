---
name: humanize
description: >-
  Rewrites AI-sounding text so it reads like its writer without changing what
  it says: detects 35 patterns from Wikipedia's "Signs of AI writing"
  (inflated claims, sales language, vague sources, overused AI words,
  formulaic rhetoric, chatbot artifacts, dash and formatting tells), preserves
  every claim, invents no facts, and matches a supplied voice sample. Returns
  a full rewrite for pasted text, edits prose in place for files, and emits
  bare text when embedded in another task. Use when asked to humanize, de-AI,
  or naturalize prose, edit text that sounds like a chatbot, or remove AI
  writing patterns. Do not use for code, for judging whether a text is
  AI-authored, or for fact-checking claims.
license: MIT
---

# Humanize: remove AI writing patterns

Rewrite AI-sounding text so it reads like the writer, not a chatbot. Patterns
come from Wikipedia's ["Signs of AI writing"](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing),
maintained by WikiProject AI Cleanup. Its diagnosis: LLMs tend toward the most
statistically likely phrasing for the widest variety of cases. The cure is the
specific over the generic.

## Registry

| Name | Path |
| --- | --- |
| `calibration` | [references/calibration.md](references/calibration.md) |
| `chatbot` | [references/chatbot.md](references/chatbot.md) |
| `content` | [references/content.md](references/content.md) |
| `filler` | [references/filler.md](references/filler.md) |
| `language` | [references/language.md](references/language.md) |
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
3. **Match the voice.** Formal, casual, or technical to fit the text. When the
   user supplies a sample of their prior prose, read it before
   rewriting: note sentence length, word choice, paragraph openings,
   punctuation, repeated phrases, and transitions, then match those habits.
   Keep casual words casual and deliberate quirks intact. The sample outranks
   every pattern: a sample full of em dashes keeps its em-dash rate, so §14 in
   `style` is not a ban.
4. **Personality only where it fits.** In blog posts, essays, opinion, and
   personal writing, keep the writer's opinions, uncertainty, mixed feelings,
   humor, asides, and uneven rhythm. Keep reference, technical, legal, and
   factual text neutral. Never invent facts to add warmth.

## Detection index

35 patterns. Ownership by contiguous range: §1-6 `content`, §7-13 `language`,
§14-19 `style`, §20-22 `chatbot`, §23-26 `filler`, §27-35 `rhetoric`. Owner
files hold the full watch-lists, problem statements, and before/after
examples; the cues below are routing summaries only.

| § | Cue |
| --- | --- |
| 1 | Ordinary detail cast as pivotal moment, legacy, or broader trend |
| 2 | Media outlets or follower counts listed to prove importance |
| 3 | Fact plus trailing -ing phrase adding fake depth (highlighting..., reflecting...) |
| 4 | Ad-copy tone: vibrant, nestled, breathtaking, rich heritage |
| 5 | Unnamed authorities: experts argue, observers cite, industry reports |
| 6 | Stock Challenges or Future Outlook section restating vague claims |
| 7 | AI-favored vocabulary, especially clustered: delve, tapestry, testament, pivotal |
| 8 | serves as, boasts, features dodging is, are, has |
| 9 | Not X but Y frames; clipped negative endings (no guessing) |
| 10 | Ideas forced into triads |
| 11 | Synonym cycling for one subject; repeated sentence openings |
| 12 | from X to Y where X and Y form no real range |
| 13 | Passive voice or dropped subject hiding the actor |
| 14 | Em or en dashes (U+2014, U+2013) beyond the writer's own rate |
| 15 | Bold scattered without reason |
| 16 | Lists where every item is a bold label plus colon |
| 17 | Title Case In Headings |
| 18 | Emoji as decoration on headings and bullets |
| 19 | Curly quotes where the writer or format uses straight |
| 20 | Chat frame left in: greetings, offers, hope this helps |
| 21 | Knowledge-cutoff disclaimers; guessed gap-fill stated as fact |
| 22 | Praise and eager agreement before the answer |
| 23 | Wind-up phrases: in order to, it is important to note that |
| 24 | Stacked qualifiers: could potentially possibly |
| 25 | Generic upbeat send-off instead of a last fact |
| 26 | Hyphenated pairs kept after the noun (the report is high-quality) |
| 27 | Fake-depth framing: the real question, at its core |
| 28 | Announcing the point instead of stating it: let's dive in |
| 29 | First sentence restating its heading |
| 30 | Prose about the previous version outside a changelog |
| 31 | Consecutive dramatic fragments as punchlines |
| 32 | Aphorism templates: X is the Y of Z, the currency of |
| 33 | Fake-candid openers: Honestly?, Look, Here's the thing |
| 34 | Rebutting objections nobody raised: I'm not saying, to be clear |
| 35 | Dismissing alternatives nobody would choose: one might be tempted |

## Progressive loading

1. Scan the input against the index and collect suspected hits.
2. Zero hits: return the text unchanged per output mode, state that no AI
   patterns were found, and load nothing.
3. Otherwise load exactly the owner files of the hits, plus `calibration`,
   the guard against overcorrection. Never rewrite flagged text without
   `calibration`.
4. §14-19 are mechanically checkable: a search for U+2014, U+2013, `**`,
   heading case, emoji, curly quotes, and ` -- ` settles whether `style`
   loads.

## Rewrite process

1. Mark each pattern instance from the scan. Confirm against the loaded owner
   files; drop the false positives `calibration` names.
2. Draft. Read it aloud for rhythm, concrete detail, simple verbs, and the
   right formality. State each point naturally rather than patching flagged
   phrases one at a time; when a sentence stays awkward, rewrite the
   paragraph around its main point.
3. Self-check two questions, treating a yes to either as an error to fix:
   - What still sounds AI-generated?
   - Did the rewrite add or drop any fact, name, number, date, quote,
     citation, or ranking?
4. Sweep the final text for U+2014 and U+2013 per §14 in `style`.

## Output modes

| Mode | Trigger | Return |
| --- | --- | --- |
| Pasted text (default) | Text in the conversation | Draft, short list of remaining AI patterns, final rewrite |
| File | User names a file | Write only the final text to the file, changing prose only: keep code blocks, YAML metadata, data, and link targets. Then a short summary |
| Embedded | Another task invokes the skill (PR text, commit message, docs) | Final text only |

Same rewrite process in every mode.
