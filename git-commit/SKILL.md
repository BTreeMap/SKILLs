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

Draft and review Conventional Commits messages saying why over what, at
cheapest effort level that works.

## Registry

| Name | Path |
| --- | --- |
| `ultra` | [references/ultra.md](references/ultra.md) |

## Levels

Level gates history scanned and text produced. Default: **full**. Switch per
invocation: `/git-commit lite|full|ultra`. Message rules and output contract
below apply at every level; Full section applies at **full** and **ultra**;
load `ultra` ONLY at **ultra**. Review judges supplied message against
active level's rules, reports each violation with rule it breaks, proposes
corrected message, writes nothing.

| Level | Scans | Produces |
| --- | --- | --- |
| **lite** | Staged paths; `git log --oneline -10` | Subject line only. Cheapest. |
| **full** | Recent `git log` subjects | Scoped subject, wrapped body, footer. Default. |
| **ultra** | Staged diff, scope frequency, branch name | Full's message after atomicity and history audit; may propose split first. |

## Push Verb

For `push`, stage as directed, commit, push to tracked remote, then report
pushed range in one line. Without explicit level, `push` implies **lite**;
explicit level wins, so `full push` and `ultra push` draft at that level
first. Run `git push` ONLY when user passed push verb or asked to push.

## Message Rules

<template for="commit">
<type>(<scope>): <subject>
<BLANK LINE>

<body>
<BLANK LINE>

<footer>
</template>

<directives for="message">
  <rule>Limit entire subject line to 70 characters or fewer.</rule>
  <rule>Select lowercase type from allowed list: feat, fix, refactor, docs, style, perf, test, build, ci, chore, revert.</rule>
  <rule>Enclose optional lowercase scope in parentheses.</rule>
  <rule>Write subject description in strict imperative mood (e.g., Add, Fix, Refactor): "Add", not "Added" or "Adding".</rule>
  <rule>Capitalize first letter of subject description.</rule>
  <rule>End subject line without period or any other punctuation.</rule>
  <rule>Breaking change always requires footer starting `BREAKING CHANGE: ` followed by detailed migration path.</rule>
  <rule>Retain bot-authored commits and platform-generated merge commits exactly as they are; reformat nothing.</rule>
</directives>

<directives for="output">
  <rule>Output strictly raw commit text or executable `git commit -m` command, no conversational filler, preamble, formatting acknowledgment, or concluding remark.</rule>
  <rule>Beyond that, add only push verb's one-line pushed range, review's violations, and at ultra split proposal before draft and synonym note after it.</rule>
</directives>

## Lite

<procedure for="lite">
  <step>Derive scope from staged file paths: single top-level directory, package, or module touched. Omit scope when changes span several.</step>
  <step>Reuse scope visible in `git log --oneline -10`; run no wider history scan.</step>
  <step>Output subject line only. Add body and footer solely for breaking change.</step>
</procedure>

## Full

<procedure for="scope">
  <step>Inspect recent history, e.g. `git log --pretty=format:'%s' -50`.</step>
  <step>Reuse existing scope from log when it fits change; synonym fragments history.</step>
  <step>None fits: derive new scope from repository's top-level packages, crates, modules, or directories: one short lowercase token, hyphens joining multiple words.</step>
  <step>Omit scope entirely for repository-wide change.</step>
</procedure>

<directives for="body">
  <rule>Separate subject line and body with exactly one blank line; git tooling requires it.</rule>
  <rule>Wrap all body lines at 72 characters.</rule>
  <rule>Explain exactly what changed and rationale behind chosen solution; leave the how to diff, never restate it.</rule>
  <rule>Write body in `/caveman` register: terse, why over what, no filler.</rule>
</directives>

<directives for="footer">
  <rule>Place issue tracker references in footer (e.g., Fixes #123, Resolves #456).</rule>
</directives>

<checklist for="full">
  <item>Subject follows `<type>(<scope>): <subject>`, is 70 characters or fewer, takes type from allowed list.</item>
  <item>Scope, if present, lowercase, single token, verified via `git log`.</item>
  <item>Subject description imperative, capitalized, ends without punctuation.</item>
  <item>One blank line separates subject and body.</item>
  <item>Body lines wrap at 72 characters, give what and why without restating diff.</item>
  <item>Issue references and breaking changes reside only in the footer.</item>
  <item>Output contains no conversational filler.</item>
</checklist>

<examples for="message">

  <example for="valid">
    <context>Feature commit with scope, body, issue reference.</context>
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
