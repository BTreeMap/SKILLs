---
name: git-commit
description: >-
  Drafts and reviews Conventional Commits messages, saying why over what,
  and can commit and push in one step. Use when writing or reviewing a
  commit message, or when asked to commit or push.
license: MIT
metadata:
  argument-hint: "[lite|full|ultra] [push]"
---

# Git Commit

Draft and review Conventional Commits messages that say why over what, at
the cheapest effort level that works.

## Registry

| Name | Path |
| --- | --- |
| `full` | [references/full.md](references/full.md) |
| `ultra` | [references/ultra.md](references/ultra.md) |

## Levels

A level gates the history scanned and the text produced. Default: **full**.
Switch per invocation: `/git-commit lite|full|ultra`. Read ONLY the active
level's reference files: none for **lite**, `full` for **full**, `full` then
`ultra` for **ultra**. The message rules and output contract below apply at
every level.

| Level | Scans | Produces |
| --- | --- | --- |
| **lite** | Staged paths; `git log --oneline -10` | Subject line only. Cheapest. |
| **full** | Recent `git log` subjects | Scoped subject, wrapped body, footer. Default. |
| **ultra** | Staged diff, scope frequency, branch name | Full's message after an atomicity and history audit; may propose a split first. |

## Push Verb

For `push`, stage as directed, commit, and push to the tracked remote, then
report the pushed range in one line. Without an explicit level, `push`
implies **lite**; an explicit level wins, so `full push` and `ultra push`
draft at that level first. Run `git push` ONLY when the user passed the push
verb or asked to push.

## Message Rules

<template for="commit">
<type>(<scope>): <subject>
<BLANK LINE>

<body>
<BLANK LINE>

<footer>
</template>

<directives for="message">
  <rule>Limit the entire subject line to 70 characters or fewer.</rule>
  <rule>Select a lowercase type from the allowed list: feat, fix, refactor, docs, style, perf, test, build, ci, chore, revert.</rule>
  <rule>Enclose the optional lowercase scope in parentheses.</rule>
  <rule>Write the subject description in the strict imperative mood (e.g., Add, Fix, Refactor): "Add", not "Added" or "Adding".</rule>
  <rule>Capitalize the first letter of the subject description.</rule>
  <rule>End the subject line without a period or any other punctuation.</rule>
  <rule>A breaking change always requires a footer starting `BREAKING CHANGE: ` followed by the detailed migration path.</rule>
  <rule>Retain bot-authored commits and platform-generated merge commits exactly as they are; reformat nothing.</rule>
</directives>

<directives for="output">
  <rule>Output strictly the raw commit text or the executable `git commit -m` command, with no conversational filler, preamble, formatting acknowledgment, or concluding remark.</rule>
  <rule>Beyond that, add only the push verb's one-line pushed range, and at ultra a split proposal before the draft and a synonym note after it.</rule>
</directives>

## Lite

<procedure for="lite">
  <step>Derive the scope from the staged file paths: the single top-level directory, package, or module touched. Omit the scope when changes span several.</step>
  <step>Reuse a scope visible in `git log --oneline -10`; run no wider history scan.</step>
  <step>Output the subject line only. Add a body and footer solely for a breaking change.</step>
</procedure>
