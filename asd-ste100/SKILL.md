---
name: asd-ste100
description: >-
  Writes, rewrites, checks text in ASD-STE100 Simplified Technical English
  against Issue 9 dictionary and writing rules, naming each unapproved word
  with approved alternatives. Use when asked for STE, controlled English, or
  an STE check.
license: MIT
compatibility: >-
  Requires uv and a full SKILLs repository checkout. The first run needs
  network access to download the pinned dictionary and rules; later runs
  read the cache. `--data DIR` reads a local release with no network. The
  first run builds the `.venv` at the checkout root that every skill's
  scripts share, about 225 MB.
metadata:
  argument-hint: "[build|refactor|review|help] [file-or-text]"
---

# ASD-STE100

Write new text in ASD-STE100 Simplified Technical English (STE), Issue 9,
change a text into STE, or examine a text for STE errors. The result is the
STE text and the last `check` report. For `review`, the result is only the
report.

## Skill verbs

The skill verb that the user gives comes first. If the user gives no skill
verb, the task in the table sets the skill verb. If the user gives only a
text, the skill verb is `review`.

| Skill verb | Task | Result |
| --- | --- | --- |
| `build` | Write new text from a brief, from notes, or from facts | STE text and a report with no errors |
| `refactor` | Change a text into STE and keep its meaning | STE text, a report with no errors, and a list of the changes in meaning |
| `review` | Examine a text, but do not change it | The report, as a list of corrections, each with its rule |
| `help` | Show how to use this skill | The `help` card |

`review` does not change the text. `build` and `refactor` change only the
draft that they make. They change a file of the user only if the user tells
you to change that file.

## Commands

Bind the command one time in each shell. If the shell starts again, bind it
again. You must use `realpath`. Use these commands and read their output.
Read the source code only when the user tells you to find the cause of a
problem.

<commands for="bind">
R="env -u VIRTUAL_ENV -u UV_PROJECT_ENVIRONMENT uv run --project $(realpath <skill-root>/scripts) btm-asd-ste100"
</commands>

<commands for="surface">
$R fetch [--version TAG]
$R check --text:file draft.txt [--allow:file terms.txt] [--mode procedure|description] [--format text|markdown] [--section HEADING] [--jsonl] [--version TAG | --data DIR]
$R lookup WORD [WORD ...] [--version TAG | --data DIR]
$R clean
</commands>

* `check` reads the text from one of these sources: `--text` for a short
  text, `--text:file PATH`, `--text:stdin`, or the pipe if no flag uses it.
  For more than one sentence, use a file. `check` rejects an empty text.
* With `--format markdown`, `check` ignores the front matter, fenced code,
  and the lines in a `<commands>` or `<template>` element. Each heading,
  list item, table row, and line that starts with a tag is a paragraph. Each
  table cell is a sentence. `--section HEADING` keeps only that heading and
  its lines, until the next heading. With `--format text` (the default), an
  empty line ends a paragraph.
* With `--jsonl`, each line of the text is one JSON object:
  `{"text": "...", "id": "..."}`. The `id` is optional. `check` reads the
  dictionary one time and gives one report for each line in `reports`, with
  its `line` and its `id`. The `ok` at the top is `true` only when each
  report has `ok: true`. Use `--jsonl` to examine many texts. If one line is
  not correct, `check` gives the errors of all lines, with exit 1, and gives
  no reports.
* An inline code span counts as one word, and `check` does not examine the
  words in it. Text in quotation marks is a technical noun. It counts as one
  word, and the report shows it in a `quotation` signal.
* `--allow:file PATH` gives your technical nouns and technical verbs, one
  term on each line. A comment starts with `#`. The checker accepts a
  one-word term and the regular plural of a noun. It accepts a term of two
  or more words only when all its words are together. It does not accept one
  of these words without the other words.
* `--mode procedure` (the default) sets the sentence limit for procedures,
  and a limit for a sentence that starts with `NOTE:`. `--mode description`
  sets the sentence limit and the paragraph limit for descriptions. The
  `limits` in the report shows the numbers that apply.
* `lookup` accepts one or more words, and gives one item in `words` for
  each. It shows each dictionary entry that has the word as its headword, as
  a form, or as the plural of an approved noun. Each entry gives its
  approved meaning or its alternatives, and the examples from the
  specification. For a form of a headword that is not approved, `lookup`
  gives the `headword` and its entries. When the specification gives one
  example for each alternative, `choices` gives each alternative with its
  STE example and with the sentence that it replaces. An empty `entries`
  shows that the word is not in the dictionary.
* Each item in `entries` has the same fields: `word`, `pos`, `qualifier`,
  `forms`, `status`, `ste_example`, `nonste_example`, `page`,
  `alternatives`, and `choices`. If the specification does not give a value,
  the field is `null`. For example, `pos` is `null` for "such as".
  `status.kind` is `approved` or `unapproved`, and `status.meaning` gives
  the approved meaning. Read the alternatives in `alternatives`, not in
  `status`. If `choices` is not empty, `ste_example` and `nonste_example`
  are `null`, because `choices` contains the examples.
* `fetch` downloads the release that this skill uses, and makes sure that
  the digest of each file is correct. If the cache is empty, `check` and
  `lookup` do a `fetch` first and tell you in a `signal:` line. `clean`
  removes the cache, and the next command downloads the release again.
* `--data DIR` gives a local release: the `data/` directory of a ste-tax
  checkout, with `manifest.json` and the files that it shows. Then `check`
  and `lookup` read only that directory, and do not use the network or the
  cache. The report gives `null` in `version`. If a file is missing or its
  digest is not correct, the exit is 1 and the command does not remove the
  file. Do not use `--data` together with `--version`.
* Each command writes one JSON document to `stdout`. The `signal:` lines on
  `stderr` give information only.
* Exit 0: the command is completed. Exit 1: correct the input and send it
  again. Exit 2: the download did not occur, or a file in the cache was not
  correct and the command removed it. Then do the same command again.
* With no network, exit 2 gives the release that is necessary. If you have a
  local release, use `--data DIR`. If not, tell the user that the check did
  not occur. Do not tell the user that a text agrees with STE if you do not
  have a report.

## The report

* The `check` report gives these fields: `schema_version`, `version`,
  `data`, `mode`, `format`, `ok`, `summary`, `limits`, `counts`, `findings`,
  `signals`, `skipped`, and `allowed`. With `--section`, it also gives
  `section`. The `lookup` report gives `schema_version`, `version`, `data`,
  and `words`. These fields, and the other fields that this section and
  Commands name, change only if `schema_version` changes.
* `version` gives the release in the cache. `data` gives the `--data`
  directory. The other field is `null`.
* `allowed` gives the number of terms in the allow file.
* `summary` gives the number of errors and signals of each type, and each
  word to replace. In a long text, read it first.
* `ok` is `true` only when `findings` is empty. This condition is necessary
  but not sufficient. Because the checker cannot see meaning, a text with
  `ok: true` can contain STE errors.
* Each item in `findings` is an error that a rule finds, and it gives its
  `rule`. Each item also gives the `line` or the `lines` in the source text.
  * `sentence_length` gives the sentence number, the number of words, and
    the limit.
  * `paragraph_length` gives the number of sentences in the paragraph.
  * `not_approved` gives the word in `token`, each sentence that contains
    it, and the `alternatives` for a headword that is not approved. For a
    form of that headword, it also gives the `headword`. If the
    specification gives an instruction for the headword, `help` shows it.
    For a word with "re-", read `help`.
  * For a `not_approved` word that is not in the dictionary, `alternatives`
    is empty, and `next` gives an instruction. Write the sentence with
    approved words. If the word is a technical noun or a technical verb,
    write it in the allow file.
  * The report gives one `not_approved` item for each different word, not
    for each time the word occurs. A headword of two or more words, for
    example "carry out" or "a few", is one item. Its `token` shows the words
    of the text.
  * `ing_form` gives the verb of the -ing word.
  * `contraction` gives the word. `punctuation` gives the mark, which is a
    semicolon.
* Each item in `signals` is a possible error. Examine each signal, and
  change the text only if the signal is correct.
  * `passive_candidate` shows the words, and if the word "by" follows them.
  * `second_instruction` shows "and" or "then" before a verb.
  * `part_of_speech` shows an approved word that is also a headword that is
    not approved in a different part of speech. It gives the alternatives
    for that part of speech. Its `context` shows the word with the word that
    comes before it. A number word, for example "zero", is a technical noun.
    If it is also a word that is not approved in a different part of speech,
    this signal shows it.
  * `phrasal_verb` shows a verb of two or more words that is not approved,
    for example "turn off", if each of its words is an approved word. The
    same words can be a verb and a preposition, for example in "turn on the
    sleeves". It gives the `headword` and the alternatives. If the words are
    the verb, replace them.
  * `abbreviation` shows a word in capital letters that the checker accepted
    as a label.
  * `quotation` shows text in quotation marks, which the checker accepts as
    a technical noun.
* `skipped` gives the checks that the command did not do. Read it before you
  give the report.
* The word count obeys the specification. Text in parentheses, a quotation,
  an inline code span, a word with a hyphen, and a number with its unit each
  count as one word.

## Technical nouns and verbs

The dictionary does not contain technical nouns or technical verbs. Before
the first check, write them in the allow file.

1. Find the possible terms. Look for the names of parts, tools, materials,
   physical quantities, systems, locations, units, persons, and documents.
   For example, "oil" and "air" are materials, and "pressure" and
   "temperature" are physical quantities. Also look for the procedures of
   the work of the user, for example "drill" or "download".
2. Write a word in the allow file only if it is a technical noun or a
   technical verb. Do not write a general word there to stop an error.
   "Utilize", "ensure", and "perform" are not technical nouns or technical
   verbs.
3. Use a technical noun only as a noun, and a technical verb only as a verb.
4. Use one term for one item in all of the text. Select the shortest term
   that is clear. Use a maximum of three words in a multi-word noun. Write a
   longer technical noun in full one time. After that, make it shorter, or
   connect its words with hyphens.
5. Before you write a word in the allow file, use `$R lookup WORD` to find
   it. If the dictionary shows that the word is not approved, use an
   alternative. If the word is the name of an item in the user's work, write
   it in the allow file.

## Write STE

* Select each alternative by its meaning, not by its position in the list.
  Use `lookup` to read the examples of the entry. Use the alternative that
  has an example with the same meaning as your sentence. In `choices`, each
  alternative has its example. An alternative with a form ("fast (adj):
  faster") tells you the form to write.
* If no alternative can replace the word directly, write the sentence
  differently. You can start with the person or the item that does the work.
  You can use a verb for the step, or you can divide the sentence.
* Use each approved word only in its approved part of speech and with its
  approved meaning. For example, CHECK is a noun. Write "do a check of the
  valve", not "check the valve".
* In a procedure, write one instruction in each sentence, in the imperative.
  Put a condition first, with a comma after it ("If the light comes on, stop
  the engine."). Use a note only for information.
* In a description, do not use the imperative. Write about one topic in each
  paragraph. Use the passive only if you do not know which person or which
  item does the work.
* Divide a long sentence. Write one step, one condition, or one fact in each
  sentence. Keep the steps in the sequence in which they occur. For a
  sequence of items, use a vertical list. Each list item counts as a
  sentence.
* Write words in full. Do not use contractions or semicolons. Keep all
  articles. Use a past participle only as an adjective. Use an -ing word
  only if it is a technical noun or the dictionary shows it as approved.
  Write each -ing technical noun, for example "wiring" or "parking brake",
  in the allow file, or the report shows it as an `ing_form` error.

## Procedure

<procedure>
  <phase name="prepare">
    <step>Select the mode: `procedure` for instructions, or `description` for text that gives information. A short text that gives only a fact or a value, for example a result that you calculated, gives information.</step>
    <step>If a text has instructions and information, examine each part in its applicable mode. For a Markdown file, use `--format markdown` and one `--section` for each part.</step>
    <step>Write the allow file from the text and the brief (refer to Technical nouns and verbs).</step>
  </phase>
  <phase name="draft">
    <step>For `build`, write a draft from the brief in STE (refer to Write STE).</step>
    <step>For `refactor`, write a draft from the source, one sentence at a time. Keep all facts, numbers, conditions, and warnings.</step>
    <step>For `review`, go to the loop. Do not change the text.</step>
  </phase>
  <phase name="loop">
    <step>Use the command `$R check --text:file draft.txt --allow:file terms.txt --mode MODE`.</step>
    <step>Replace each `not_approved` word with an alternative, or write the sentence differently.</step>
    <step>Divide each sentence that is too long. Divide each paragraph that is too long.</step>
    <step>Remove each contraction and each semicolon.</step>
    <step>Examine each signal. If a signal is correct, correct the text.</step>
    <step>Do the check again. Stop when `ok` is `true`.</step>
    <step>If each error that stays is a technical noun or a technical verb, write it in the allow file. Do the check one more time. Then stop.</step>
  </phase>
  <phase name="deliver">
    <step>Compare the meaning of the last draft with the source or the brief. Make sure that the facts, the sequence of steps, and the warnings are the same.</step>
    <step>Give the text. From the last report, give `ok`, the counts, and the signals that you did not correct.</step>
    <step>For `refactor`, give a list of each location where STE changed the meaning or removed information.</step>
    <step>For `review`, give the report as a list of corrections with line numbers. Also give the items in `skipped`.</step>
  </phase>
</procedure>

## The `help` card

<template for="help">
asd-ste100: build, refactor, or review text in ASD-STE100 STE (Issue 9).
  build    <brief>   write new STE text until the report shows no errors
  refactor <file>    change a text into STE, and keep its meaning
  review   <file>    give only the report, and do not change the text
  help               show this card
Write the technical nouns and verbs first. ok: true is necessary, but not sufficient.
</template>

## Possible problems

* The checker examines the capital letters in each sentence. If a sentence
  has more small letters than capital letters, the checker accepts a word in
  capital letters as a label. It gives an `abbreviation` signal for that
  word. If a sentence has more capital letters, for example a warning, the
  checker examines each word.
* The allow file accepts a term in all sentences. If you write a term as a
  noun, the checker also accepts it where you use it as a verb. Read the
  text for this error.
* The checker does not examine meaning. For example, "fall" is approved only
  for movement by gravity, not for a value that decreases. `lookup` shows
  each approved meaning.
* The alternatives in `lookup` are for the meanings that the specification
  gives. If your meaning is different, no alternative is correct. For
  example, the alternatives for "fix" are for "attach" and "repair", not for
  "correct an error". Then find an approved word for your meaning, here
  `correct (v)`.
* Use quotation marks only for the text on a label or for a word that you
  write about. Read each `quotation` signal.
* Put each command, flag, key, and file name in an inline code span.
* If one section has instructions and information, examine it in
  `description` mode. Keep each instruction in it to the `procedure` limit.

## Checks before you stop

<checklist>
  <item>The allow file had all the terms before the first check, and it contains only technical nouns and technical verbs.</item>
  <item>The last report has `ok: true`, or the result gives the cause of each error that stays.</item>
  <item>You examined each signal, and the result gives the signals that you did not correct.</item>
  <item>The text keeps all facts, numbers, conditions, and warnings of its source or brief.</item>
  <item>You do not tell the user that a text agrees with STE only because of `ok`. If the check did not occur, you do not tell the user that the text agrees with STE.</item>
</checklist>
