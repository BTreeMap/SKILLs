---
name: git-commits
description: Enforces Conventional Commits format and best practices for commit messages. Use this skill whenever drafting, reviewing, or validating git commit messages in any repository.
---

# Git Commit Message Standards

You MUST adhere strictly to the Conventional Commits specification. A clean,
structured commit history ensures accurate changelog generation, easier
debugging, and rapid code reviews. These standards are project-agnostic: apply
them in every repository, and derive any project-specific details (such as the
scope vocabulary) from the repository itself rather than from any single
project.

## 1. Commit Message Anatomy
Every commit message must follow this exact schema:

```text
<type>(<scope>): <subject>
<BLANK LINE>
<body>
<BLANK LINE>
<footer>
```

## 2. Subject Line Rules

The subject line contains the `<type>`, `<scope>`, and `<subject>` description.

* **Length Constraint:** The entire subject line must be **strictly 70 characters or less**.
* **Type:** Must be lowercase and chosen from the approved list below.
* **Scope:** Optional, but highly recommended. Must be lowercase, enclosed in parentheses, and represent the specific domain or component modified (e.g., `auth`, `ui`, `db`).
* **Imperative Mood:** The subject description must act as a command (e.g., "Add feature", "Fix bug", "Refactor logic"). Never use past or present continuous tense ("Added", "Adding").
* **Formatting:** Capitalize the first letter of the subject description. Do not end the line with a period.

## 3. Approved Types

* **`feat`**: Introduces a new feature to the codebase.
* **`fix`**: Patches a bug or addresses an error.
* **`refactor`**: Modifies code without changing external behavior or adding features (e.g., renaming variables, simplifying logic).
* **`docs`**: Updates documentation, READMEs, or inline comments.
* **`style`**: Adjusts code formatting, whitespace, or missing semicolons (no logic changes).
* **`perf`**: Improves performance and execution speed.
* **`test`**: Adds missing tests or corrects existing ones.
* **`build`**: Modifies build systems or external dependencies (e.g., npm, Cargo, Gradle, uv, Make).
* **`ci`**: Updates continuous integration configurations or scripts (e.g., GitHub Actions).
* **`chore`**: Handles routine maintenance tasks that do not modify source or test files.
* **`revert`**: Reverts a previous commit.

## 4. Body Rules

The body provides the context necessary to understand the structural reasoning behind the commit.

* **Separation:** Always separate the subject line and the body with a single blank line.
* **Line Wrapping:** Wrap all lines in the body at **72 characters** to maintain terminal readability.
* **Content:** Explain the **"what"** and the **"why"**. Detail the problem being solved and the rationale behind the chosen solution. Omit the "how", as the exact implementation details are inherently visible in the code diff.

## 5. Footer Rules (Optional)

* Use the footer to reference issue trackers (e.g., `Fixes #123`, `Resolves #456`).
* Highlight breaking changes by starting the footer with `BREAKING CHANGE:` followed by a space and a detailed description of the migration path.

## 6. Choosing a Scope

The scope is optional but recommended. It is a single lowercase token naming the
component, package, or domain a change touches (e.g., `auth`, `ui`, `api`,
`build`, `ci`, `docs`).

Do NOT memorize or hardcode any specific project's scopes. Instead, align with
the repository you are currently working in:

* **Reuse before you invent.** Before committing, inspect recent history and
  reuse the scopes that already appear. You MUST run a command such as
  `git log --pretty=format:'%s' -50` (or `git log --oneline -50`) rather than
  guessing the project's conventions.
* **Derive new scopes from structure.** When no existing scope fits, name the
  scope after the repository's own top-level packages, crates, modules, or
  directories. Keep it short, lowercase, and a single token (use `-` to join
  words, e.g., `data-layer`).
* **Stay consistent.** Once a scope exists in the history, never introduce a
  near-duplicate synonym (e.g., do not add `frontend` when `ui` is already in
  use).
* **Omit when repository-wide.** Drop the scope entirely for changes that span
  the whole repository and belong to no single component.

## 7. Automated and Exceptional Commits

* **Bot-authored commits** (e.g., Renovate, Dependabot, and similar automation)
  often use their own format, including emoji prefixes such as `⬆️`. This is
  intentional and accepted. NEVER rewrite, "fix", or reformat bot commits to
  match this specification.
* **Platform-generated merge commits** are exempt from these rules.
* These standards are **documentation, not a blocking gate**. There is
  intentionally no commit-lint hook or CI check that rejects non-conforming
  messages, so automated and historical commits are never blocked. Humans and
  agents MUST follow them for all hand-authored commits.

## 8. Gotchas

* The blank line between the subject and the body is required, not cosmetic.
  Omitting it merges the body into the subject in most Git tooling.
* Imperative mood is the single most common mistake. Write "Add", not "Added"
  or "Adding".
* The body explains **what** changed and **why**. NEVER restate the diff or
  narrate the implementation steps ("how").
* A new scope that duplicates an existing one fragments the history. Always
  check the log first (see Section 6).
* The subject line never ends with a period.

## 9. Examples

<example type="valid">
```text
fix(auth): Reject tokens that omit an expiry claim

Tokens minted before the rotation fix lacked an `exp` claim, so the
validator treated them as non-expiring. Requiring `exp` closes the
window in which a leaked token would stay valid indefinitely.

Resolves #142
```
</example>

<example type="invalid" note="Do not produce.">
```text
fixed the bug
added a token refresh thing so users dont get logged out randomly anymore. also updated the ui to show a loading spinner while it happens
```

**Violations:** Missing type, missing scope, past tense, missing blank line,
missing capitalization, body lines exceed 72 characters, missing issue
reference.
</example>

## 10. Validation Checklist

Before finalizing any hand-authored commit message, silently verify every item:

* [ ] Subject is `<type>(<scope>): <subject>` and 70 characters or less.
* [ ] Type is lowercase and from the approved list in Section 3.
* [ ] Scope (if present) is lowercase, a single token, and reuses an existing
      project scope where one applies (verified against `git log`).
* [ ] Subject is imperative, capitalized, and has no trailing period.
* [ ] A blank line separates the subject from the body (when a body exists).
* [ ] Body lines wrap at 72 characters and explain what/why, not how.
* [ ] Breaking changes and issue references are in the footer, not the subject.
* [ ] No placeholder text (e.g., `<scope>`, `TODO`) remains in the message.
