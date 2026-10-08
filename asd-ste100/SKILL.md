---
name: asd-ste100
description: >-
  Writes, rewrites, and checks text in ASD-STE100 Simplified Technical
  English against the Issue 9 dictionary and writing rules, naming each
  unapproved word with its approved alternatives. Use when asked for STE,
  controlled English, or an STE check.
license: MIT
compatibility: >-
  Requires uv and a full SKILLs repository checkout. The first run needs
  network access to download the pinned dictionary and rules; later runs
  read the cache.
metadata:
  argument-hint: "[build|refactor|review|help] [file-or-text]"
---

# ASD-STE100

Write new text, rewrite existing text, or review text in ASD-STE100
Simplified Technical English (STE), Issue 9. The deliverable is the STE text
plus the checker's last report, or the report alone for `review`.

## Verbs

Choose the verb by, in order: an explicit verb; the request shape below;
otherwise `review` when the user supplies text and asks nothing else.

| Verb | Request shape | Deliverable |
| --- | --- | --- |
| `build` | New text from a brief, notes, or facts | STE text and a clean report |
| `refactor` | Existing text into STE, meaning preserved | STE text, a clean report, and a list of meaning changes |
| `review` | Judge text, change nothing | The report, read out as fixes named by rule |
| `help` | What this skill does | The card under Help |

`review` never edits the text. `build` and `refactor` edit only the draft
they produce; a named file changes only when the user asked for an in-place
edit.

## Commands

Bind the command once per shell and re-bind after a reset; `realpath` is
required. Invoke this surface and read its output; read the source only when
the user instructs troubleshooting.

<commands for="bind">
R="env -u VIRTUAL_ENV uv run --project $(realpath <skill-root>/scripts) btm-asd-ste100"
</commands>

<commands for="surface">
$R fetch [--version TAG]
$R check --text:file draft.txt [--allow:file terms.txt] [--mode procedure|description] [--format text|markdown] [--section HEADING]
$R lookup WORD [WORD ...]
$R clean
</commands>

* `check` takes the text in a named slot: `--text` inline, `--text:file
  PATH`, `--text:stdin`, or the pipe when no flag claims it. Put more than
  one sentence in a file. An empty text is a rejection.
* `--format markdown` skips front matter, fenced code, and the payload of a
  `<commands>` or `<template>` element; each heading, list item, table row,
  and line opening with a tag is a paragraph, and each table cell a
  sentence. `--section HEADING` keeps one heading and its lines, up to the
  next heading of any level. In either format an inline code span counts as
  one word and its words are not checked.
* `--allow:file PATH` names the declared technical nouns and technical
  verbs, one term per line, `#` for comments. A one-word term passes, and
  so does a declared noun's regular plural and possessive. A multi-word term
  passes only whole: its words alone are still checked. A hyphenated word
  passes when each part is approved, declared, or a number.
* `--mode procedure` (the default) sets the procedural sentence limit and a
  note limit for sentences that start `NOTE:`; `--mode description` sets the
  descriptive sentence limit and the paragraph limit. The report's `limits`
  echoes the numbers in force.
* `lookup` takes one or more words and returns one item in `words` per
  word: every dictionary entry whose headword or form is the word, with its
  approved meaning or its alternatives and the spec's examples. A regular
  inflection of an unapproved headword resolves to it under `headword`.
  When the spec gives one example per alternative, `choices` pairs each
  alternative with its STE sentence and the sentence it replaces. An empty
  `entries` means the word is not in the dictionary.
* `fetch` downloads the pinned release and verifies each file's digest.
  `check` and `lookup` fetch on their own when the cache is empty and say so
  in a `signal:` line. `clean` drops the cache; the next run fetches again.
* Each command prints one JSON document on stdout; `signal:` lines on stderr
  are advisory. Exit 0 done; 1 fix the input and resend; 2 the download
  failed or a cached file was corrupt and was deleted, so rerun the same
  command. With no network, exit 2 names the release it needed: report that
  the check could not run, and never claim compliance without a report.

## Reading the report

* `summary` counts findings and signals by kind and lists each word to
  replace; read it first on a long text.
* `ok` is true only when no decidable finding remains. It is necessary, not
  sufficient: the checker cannot see meaning, so text with `ok: true` can
  still break STE.
* `findings` are decidable, each with its `rule` and the source `line` or
  `lines` it occurs on. `sentence_length` gives
  the sentence index, its word count, and the limit. `paragraph_length`
  gives the paragraph's sentence count. `not_approved` gives the token, every
  sentence it occurs in, and `alternatives` when the word is an unapproved
  headword, with the `headword` when the word is a regular inflection of
  one. `ing_form` names the verb it inflects. `contraction` and
  `punctuation` (a semicolon) name the token or mark.
* `signals` are heuristic; weigh each one, and change the text only when it
  is right. `passive_candidate` shows the words and whether an agent follows
  with "by". `second_instruction` shows "and" or "then" before a verb.
  `part_of_speech` marks an approved word that is also an unapproved
  headword in another part of speech, with what to use for that one and,
  in `context`, each use with the word before it.
  `abbreviation` marks an all-capitals token that passed as a label.
  `quotation` marks quoted text, which passes as a technical noun (rule 1.5)
  and is not checked word by word.
* `skipped` lists what this run did not decide. Read it before you report.
* Word count follows the spec: text in parentheses, a quotation, an inline
  code span, a hyphenated word, and a number with its unit each count as
  one word.

## Technical nouns and verbs

The dictionary holds no technical nouns or technical verbs. Declare them in
the allow file before the first check.

1. Collect the candidate terms: names of parts, tools, materials, systems,
   places, units, people's roles, documents, and the processes of a subject
   field (drill, solder, download).
2. Declare a word only as a technical noun or a technical verb. Never
   declare a general word to silence a finding: "utilize", "ensure", and
   "perform" are not technical terms.
3. Use a technical noun only as a noun and a technical verb only as a verb.
4. Use one term for one item throughout, the shortest clear one. Keep a
   multi-word noun to three words; write a longer technical noun in full
   first, then shorten it or join it with hyphens.
5. Before you declare a word, run `$R lookup WORD`. If the dictionary lists
   it as unapproved, use the alternative unless the word is the name of a
   thing in the user's field.

## Writing STE

* Choose each word's approved alternative by meaning, not by position: read
  the entry's examples with `lookup` and take the alternative whose example
  says what the sentence means. A form alternative ("fast (adj): faster")
  names the form to write.
* When no alternative fits word for word, change the sentence: make the
  agent the subject, make the action a verb, or split the sentence.
* Give each approved word only its approved part of speech and meaning.
  CHECK is a noun, so "do a check of the valve", not "check the valve".
* Procedures: one instruction per sentence, in the imperative; put a
  condition first and end it with a comma ("If the light comes on, stop the
  engine."); write a note for information only.
* Descriptions: no imperatives; one topic per paragraph; the passive only
  when the agent is unknown.
* Split a long sentence at its clauses: one action, one condition, or one
  fact per sentence. Keep the order of actions as they occur. Use a
  vertical list for a series; each item counts as a sentence.
* Write words in full: no contractions, no dropped articles, no semicolons.
  Use the past participle only as an adjective, and no -ing word except a
  technical noun or one the dictionary approves.

## Procedure

<procedure>
  <phase name="prepare">
    <step>Decide the mode: `procedure` for instructions, `description` for text that gives information. Text that holds both is checked in two parts, each in its own mode.</step>
    <step>Write the allow file from the text and the brief (Technical nouns and verbs).</step>
  </phase>
  <phase name="draft">
    <step>`build`: draft from the brief in STE (Writing STE). `refactor`: draft from the source sentence by sentence, keeping every fact, number, condition, and warning. `review`: skip to the loop and edit nothing.</step>
  </phase>
  <phase name="loop">
    <step>Run `$R check --text:file draft.txt --allow:file terms.txt --mode MODE`.</step>
    <step>Fix every finding: replace each `not_approved` word with an alternative or a new construction, split each long sentence, divide each long paragraph, remove each contraction and semicolon.</step>
    <step>Weigh every signal and fix the true ones.</step>
    <step>Run the check again. Stop when `ok` is true, or when every remaining finding is a technical noun or verb the allow file missed: declare those, rerun, and stop.</step>
  </phase>
  <phase name="deliver">
    <step>Read the final text for meaning against the source or brief: same facts, same order of actions, same warnings.</step>
    <step>Return the text and the last report's `ok`, counts, and signals you kept. For `refactor`, list each place where STE forced a change of meaning or detail. For `review`, return the report as a list of fixes with sentence numbers, plus what `skipped` names.</step>
  </phase>
</procedure>

## Help

<template for="help">
asd-ste100: build, refactor, or review text in ASD-STE100 STE (Issue 9).
  build    <brief>   new STE text, checked until clean
  refactor <file>    existing text into STE, meaning preserved
  review   <file>    report only; changes nothing
  help               this card
Declare technical nouns and verbs first; ok: true is necessary, not sufficient.
</template>

## Gotchas

* A capitalized word in mixed-case text passes as a label and is signaled;
  in all-capitals text (a warning) every word is checked.
* The allow file passes a word in every sentence. A word you declare as a
  noun still passes where you used it as a verb; read the
  `part_of_speech` signals and the text for that.
* Meaning is not checked. "Fall" is approved only for movement by gravity,
  not for a decrease; `lookup` shows each approved meaning.

## Completion checks

<checklist>
  <item>Technical nouns and verbs were declared before the first check, and no general word was declared to silence a finding.</item>
  <item>The final report has `ok: true`, or each remaining finding is explained.</item>
  <item>Every signal was weighed; the kept ones are reported.</item>
  <item>The text keeps every fact, number, condition, and warning of its source or brief.</item>
  <item>No claim of compliance rests on `ok` alone, and none is made when the check could not run.</item>
</checklist>
