---
name: git-commits
description: Enforces Conventional Commits format and best practices. Use this skill whenever drafting, reviewing, or validating git commit messages for the repository.
---

# Git Commit Message Standards

You must adhere strictly to the Conventional Commits specification. A clean,
structured commit history ensures accurate changelog generation, easier
debugging, and rapid code reviews.

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
* **`build`**: Modifies build systems or external dependencies (e.g., Gradle, Cargo).
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

## 6. Repository Scopes

Prefer one of these common scopes when it fits the change. The list is a guide,
not an exhaustive enum; add a new lowercase scope when a change clearly belongs
to an unlisted component.

* **`proxy`**: Rust WARP image proxy crate (`rust/letterbox-proxy`).
* **`core`**: Rust core crate (`rust/letterbox-core`).
* **`tunnel`**: WireGuard/WARP tunnel internals.
* **`warp`**: WARP provisioning and Cloudflare API integration.
* **`ui`**: Android Compose screens and UI.
* **`app`**: Android application wiring (activities, services, repositories).
* **`ffi`**: UniFFI bindings and the FFI surface.
* **`ci`**: GitHub Actions workflows.
* **`build`**: Gradle / Cargo build configuration.
* **`docs`**: Documentation under `docs/` or READMEs.

## 7. Exceptions

* **Automated dependency commits** from the Renovate bot do not follow this
  format (they use an `⬆️` emoji prefix configured in `renovate.json`). This is
  intentional and accepted. Do not "fix" or rewrite bot commits.
* These standards are **documentation, not a blocking gate**. There is no
  commit-lint hook or CI check that rejects non-conforming messages, precisely
  so automated and historical commits are never blocked. Humans and agents are
  expected to follow them for all hand-authored commits.

## 8. Examples

### Valid Implementation

```text
fix(warp): Drop gzip Accept-Encoding header in provisioning

reqwest is built without the `gzip` feature, so it cannot transparently
decompress responses. Cloudflare honoured the advertised header and
returned a gzip body, which then failed JSON decoding. Omitting the
header makes Cloudflare return plain JSON that reqwest can parse.

Resolves #142
```

### Invalid Implementation (Do Not Produce)

```text
fixed the bug
added a token refresh thing so users dont get logged out randomly anymore. also updated the ui to show a loading spinner while it happens
```

* **Violations:** Missing type, missing scope, past tense, missing blank line, missing capitalization, body lines exceed 72 characters, missing issue reference.
