---
name: git-commits
description: Triggered when the user asks to draft a commit, write a message for a diff, review a commit, or run `git commit`. Enforces Conventional Commits formatting and repository-specific scope resolution while minimizing output tokens.
---

# Git Commit Message Standards

<commit_schema>
<type>(<scope>): <subject>
<BLANK LINE>
<body>
<BLANK LINE>
<footer>
</commit_schema>

## 1. Execution Directives

Read and strictly execute the constraints defined in the XML blocks below.

<subject_constraints>
  <rule>Limit the entire subject line to exactly 70 characters or fewer.</rule>
  <rule>Select a lowercase type from the allowed list.</rule>
  <rule>Enclose the optional lowercase scope in parentheses.</rule>
  <rule>Write the subject description in the imperative mood (e.g., Add, Fix, Refactor).</rule>
  <rule>Capitalize the first letter of the subject description.</rule>
  <rule>Terminate the subject line without a period.</rule>
</subject_constraints>

<allowed_types>
  feat, fix, refactor, docs, style, perf, test, build, ci, chore, revert
</allowed_types>

<body_constraints>
  <rule>Separate the subject line and the body with exactly one blank line.</rule>
  <rule>Wrap all body lines at exactly 72 characters.</rule>
  <rule>Explain exactly what changed and the rationale behind the chosen solution.</rule>
</body_constraints>

<footer_constraints>
  <rule>Place issue tracker references in the footer (e.g., Fixes #123, Resolves #456).</rule>
  <rule>Start breaking changes with 'BREAKING CHANGE: ' followed by the detailed migration path.</rule>
</footer_constraints>

<scope_resolution_procedure>
  <step>Run a command like `git log --pretty=format:'%s' -50` to inspect recent history.</step>
  <step>Reuse an existing scope from the log if it aligns with the current changes.</step>
  <step>Derive new scopes from the repository's top-level packages, crates, modules, or directories if no existing scope applies.</step>
  <step>Format new scopes as short, lowercase, single tokens using hyphens for multiple words.</step>
  <step>Omit the scope entirely for repository-wide changes.</step>
</scope_resolution_procedure>

<exception_handling>
  <rule>Retain bot-authored commits (e.g., Renovate, Dependabot) and platform-generated merge commits exactly as they are without formatting alterations.</rule>
</exception_handling>

<output_contract>
  <rule>Output strictly the raw commit text or the executable `git commit -m` command.</rule>
  <rule>Omit all conversational filler, preambles, and concluding remarks.</rule>
</output_contract>

## 2. Gotchas

*   Include the blank line between the subject and the body to ensure Git tooling compatibility.
*   Use imperative mood exclusively (e.g., use "Add" instead of "Added" or "Adding").
*   Explain the "what" and "why" in the body; rely entirely on the code diff to communicate the "how".
*   Reuse scopes discovered via `git log` to maintain history consistency and prevent duplicate synonyms.
*   Terminate the subject line with alphanumeric characters rather than punctuation.

## 3. Examples

<example type="valid">
fix(auth): Reject tokens that omit an expiry claim

Tokens minted before the rotation fix lacked an `exp` claim, so the
validator treated them as non-expiring. Requiring `exp` closes the
window in which a leaked token would stay valid indefinitely.

Resolves #142
</example>

## 4. Validation Checklist

Silently verify these conditions before outputting the commit:

* [ ] Subject follows `<type>(<scope>): <subject>` and is 70 characters or less.
* [ ] Type is explicitly chosen from `<allowed_types>`.
* [ ] Scope (if present) is lowercase, a single token, and verified via `git log`.
* [ ] Subject description is imperative, capitalized, and period-free.
* [ ] A blank line separates the subject and body.
* [ ] Body lines wrap at 72 characters and detail the what/why.
* [ ] Issue references and breaking changes reside strictly in the footer.
* [ ] Output contains zero conversational filler per the `<output_contract>`.
