---
name: git-commit
description: >-
  Drafts and reviews git commit messages that follow Conventional Commits,
  resolving scopes from repository history while minimizing output tokens.
  Supports effort levels: lite (subject line only, no history scan), full
  (default: scoped subject plus wrapped body and footer), and ultra (adds an
  atomicity and history-consistency audit), plus a push verb that commits at
  lite level and pushes to the tracked remote. Use when the user asks to
  draft a commit, write a message for a diff, review a commit message, run
  `git commit`, or commit and push.
license: MIT
metadata:
  argument-hint: "[lite|full|ultra] [push]"
---

# Git Commit

Draft and review Conventional Commits messages, saying why over what, at
the cheapest effort level that does the job.

## Registry

| Name | Path |
| --- | --- |
| `full` | [references/full.md](references/full.md) |
| `ultra` | [references/ultra.md](references/ultra.md) |

Effort levels gate history scanned and text produced. Default: **full**.
Switch per invocation: `/git-commit lite|full|ultra`. Each level's name is
its registered name, so the level selects the file; **lite** loads none,
**ultra** loads `full` before its own.

| Level | Behavior |
| --- | --- |
| **lite** | Subject line only; scope from staged paths; no history scan. Cheapest. |
| **full** | Scoped subject plus wrapped body and footer; scope resolved from recent history. Default. |
| **ultra** | Full, plus an atomicity and history-consistency audit before drafting. |

Read ONLY the reference files the active level lists. The core rules below
apply at every level.

## Push Verb

`push` is a quick-ship action: stage as directed, commit, then push to the
tracked remote, reporting the pushed range in one line. Without an explicit
level, `push` implies **lite** (nothing extra loads); an explicit level wins,
so `full push` and `ultra push` draft at that level first. Run `git push`
ONLY when the user passed the push verb or asked to push.

<system_directives>
  <commit_schema>
<type>(<scope>): <subject>
<BLANK LINE>
<body>
<BLANK LINE>
<footer>
  </commit_schema>

  <subject_constraints>
    <rule>Limit the entire subject line to 70 characters or fewer.</rule>
    <rule>Select a lowercase type from the allowed list.</rule>
    <rule>Enclose the optional lowercase scope in parentheses.</rule>
    <rule>Write the subject description in the imperative mood (e.g., Add, Fix, Refactor).</rule>
    <rule>Capitalize the first letter of the subject description.</rule>
    <rule>Terminate the subject line without a period.</rule>
  </subject_constraints>

  <allowed_types>
    feat, fix, refactor, docs, style, perf, test, build, ci, chore, revert
  </allowed_types>

  <lite_procedure>
    <rule>Derive the scope from the staged file paths: the single top-level directory, package, or module touched. Omit the scope when changes span several.</rule>
    <rule>Reuse a scope visible in `git log --oneline -10`; run no wider history scan.</rule>
    <rule>Output the subject line only. Add a body and footer solely for a breaking change, which always requires `BREAKING CHANGE: ` plus the migration path.</rule>
  </lite_procedure>

  <exception_handling>
    <rule>Retain bot-authored commits (e.g., Renovate, Dependabot) and platform-generated merge commits exactly as they are; reformat nothing.</rule>
  </exception_handling>

  <output_contract>
    <rule>Output strictly the raw commit text or the executable `git commit -m` command.</rule>
    <rule>Omit conversational filler, preambles, formatting acknowledgments, and concluding remarks.</rule>
  </output_contract>
</system_directives>
