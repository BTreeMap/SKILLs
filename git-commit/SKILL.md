---
name: git-commit
description: >-
  Drafts and reviews Conventional Commits messages, why over what; can
  commit and push in one step. Use when writing or reviewing a commit
  message, or asked to commit or push.
license: MIT
metadata:
  argument-hint: "[basic|full|maximum] [push]"
---

# Git Commit

Draft and review Conventional Commits messages saying why over what, at
cheapest effort level that works.

## Registry

| Name | Path |
| --- | --- |
| `maximum` | [references/maximum.md](references/maximum.md) |

## Levels

Level gates history scanned and text produced. Default: **full**. Switch per
invocation: `/git-commit basic|full|maximum`. Message rules and output
contract below apply at every level; Full section applies at **full** and
**maximum**; load `maximum` ONLY at **maximum**. Review judges supplied
message against active level's rules, reports each violation with rule it
breaks, proposes corrected message, writes nothing.

| Level | Scans | Produces |
| --- | --- | --- |
| **basic** | Staged paths; `git log --oneline -10` | Subject line only. Cheapest. |
| **full** | Recent `git log` subjects | Scoped subject, wrapped body, footer. Default. |
| **maximum** | Staged diff, scope frequency, branch name | Full's message after atomicity and history audit; may propose split first. |

## Push Verb

For `push`, stage as directed, commit, push to tracked remote, then report
pushed range in one line. Without explicit level, `push` implies **basic**;
explicit level wins, so `full push` and `maximum push` draft at that level
first. Run `git push` ONLY when user passed push verb or asked to push.

## Message Rules

**Template: commit**

```text
<type>(<scope>): <subject>
<BLANK LINE>

<body>
<BLANK LINE>

<footer>
```

**Rules: message**

- Limit entire subject line to 70 characters or fewer.
- Select lowercase type from allowed list: feat, fix, refactor, docs, style,
  perf, test, build, ci, chore, revert.
- Enclose optional lowercase scope in parentheses.
- Write subject description in strict imperative mood (e.g., Add, Fix,
  Refactor): "Add", not "Added" or "Adding".
- Capitalize first letter of subject description.
- End subject line without period or any other punctuation.
- Breaking change always requires footer starting `BREAKING CHANGE: `
  followed by detailed migration path.
- Retain bot-authored commits and platform-generated merge commits exactly
  as they are; reformat nothing.

**Rules: output**

- Output strictly raw commit text or executable `git commit -m` command, no
  conversational filler, preamble, formatting acknowledgment, or concluding
  remark.
- Beyond that, add only push verb's one-line pushed range, review's
  violations, and at maximum split proposal before draft and synonym note
  after it.

## Basic

1. Derive scope from staged file paths: single top-level directory, package,
   or module touched. Omit scope when changes span several.
2. Reuse scope visible in `git log --oneline -10`; run no wider history
   scan.
3. Output subject line only. Add body and footer solely for breaking change.

## Full

**Procedure: scope**

1. Inspect recent history, e.g. `git log --pretty=format:'%s' -50`.
2. Reuse existing scope from log when it fits change; synonym fragments
   history.
3. None fits: derive new scope from repository's top-level packages, crates,
   modules, or directories: one short lowercase token, hyphens joining
   multiple words.
4. Omit scope entirely for repository-wide change.

**Rules: body**

- Separate subject line and body with exactly one blank line; git tooling
  requires it.
- Wrap all body lines at 72 characters.
- Explain exactly what changed and rationale behind chosen solution; leave
  the how to diff, never restate it.
- Write body in `/caveman` register: terse, why over what, no filler.

**Rules: footer**

- Place issue tracker references in footer (e.g., Fixes #123, Resolves
  #456).

**Checklist: full**

- Subject follows `<type>(<scope>): <subject>`, is 70 characters or fewer,
  takes type from allowed list.
- Scope, if present, lowercase, single token, verified via `git log`.
- Subject description imperative, capitalized, ends without punctuation.
- One blank line separates subject and body.
- Body lines wrap at 72 characters, give what and why without restating
  diff.
- Issue references and breaking changes reside only in the footer.
- Output contains no conversational filler.

**Example: valid**

Context: Feature commit with scope, body, issue reference.

Variant:

```text
feat(auth): Reject tokens that omit an expiry claim

Tokens minted before the rotation fix lacked an `exp` claim, so the
validator treated them as non-expiring. Requiring `exp` closes the
window in which a leaked token would stay valid indefinitely.

Resolves #142
```

**Example: invalid**

Context: Intentional counterexample. Violations: missing type and scope;
past tense ("fixed", "added") instead of imperative mood; no blank line
between subject and body; body lines exceed 72 characters; missing
capitalization.

Variant:

```text
fixed the bug
added a token refresh thing so users dont get logged out randomly anymore. also updated the ui to show a loading spinner while it happens
```
