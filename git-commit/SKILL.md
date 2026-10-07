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
| `ultra` | [references/ultra.md](references/ultra.md) |

## Levels

A level gates the history scanned and the text produced. Default: **full**.
Switch per invocation: `/git-commit lite|full|ultra`. The message rules and
output contract below apply at every level; the Full section applies at
**full** and **ultra**; load `ultra` ONLY at **ultra**. A review judges a
supplied message against the active level's rules, reports each violation
with the rule it breaks, proposes the corrected message, and writes nothing.

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
  <rule>Beyond that, add only the push verb's one-line pushed range, a review's violations, and at ultra a split proposal before the draft and a synonym note after it.</rule>
</directives>

## Lite

<procedure for="lite">
  <step>Derive the scope from the staged file paths: the single top-level directory, package, or module touched. Omit the scope when changes span several.</step>
  <step>Reuse a scope visible in `git log --oneline -10`; run no wider history scan.</step>
  <step>Output the subject line only. Add a body and footer solely for a breaking change.</step>
</procedure>

## Full

<procedure for="scope">
  <step>Inspect recent history, e.g. `git log --pretty=format:'%s' -50`.</step>
  <step>Reuse an existing scope from the log when it fits the change; a synonym fragments the history.</step>
  <step>When none fits, derive a new scope from the repository's top-level packages, crates, modules, or directories: one short lowercase token, hyphens joining multiple words.</step>
  <step>Omit the scope entirely for a repository-wide change.</step>
</procedure>

<directives for="body">
  <rule>Separate the subject line and the body with exactly one blank line; git tooling requires it.</rule>
  <rule>Wrap all body lines at 72 characters.</rule>
  <rule>Explain exactly what changed and the rationale behind the chosen solution; leave the how to the diff and never restate it.</rule>
  <rule>Write the body in the `/caveman` register: terse, why over what, no filler.</rule>
</directives>

<directives for="footer">
  <rule>Place issue tracker references in the footer (e.g., Fixes #123, Resolves #456).</rule>
</directives>

<checklist for="full">
  <item>Subject follows `<type>(<scope>): <subject>`, is 70 characters or fewer, and takes its type from the allowed list.</item>
  <item>Scope, if present, is lowercase, a single token, and verified via `git log`.</item>
  <item>Subject description is imperative, capitalized, and ends without punctuation.</item>
  <item>One blank line separates the subject and body.</item>
  <item>Body lines wrap at 72 characters and give the what and why without restating the diff.</item>
  <item>Issue references and breaking changes reside only in the footer.</item>
  <item>Output contains no conversational filler.</item>
</checklist>

<examples for="message">

  <example for="valid">
    <context>A feature commit with a scope, body, and issue reference.</context>
    <variant>
feat(auth): Reject tokens that omit an expiry claim

Tokens minted before the rotation fix lacked an `exp` claim, so the
validator treated them as non-expiring. Requiring `exp` closes the
window in which a leaked token would stay valid indefinitely.

Resolves #142
    </variant>
  </example>

  <example for="invalid">
    <context>Intentional counterexample. Violations: missing type and scope; past tense ("fixed", "added") instead of imperative mood; no blank line between subject and body; body lines exceed 72 characters; missing capitalization.</context>
    <variant>
fixed the bug
added a token refresh thing so users dont get logged out randomly anymore. also updated the ui to show a loading spinner while it happens
    </variant>
  </example>
</examples>
