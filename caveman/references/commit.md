# Caveman Commit Mode

Write the commit message terse and exact. Conventional Commits. No fluff.
Why over what: the diff already says what.

## Rules

Subject: `<type>(<scope>): <Imperative summary>`; scope optional; types
feat, fix, refactor, docs, style, perf, test, build, ci, chore, revert;
imperative mood, first letter capitalized, no trailing period; aim for 50
characters or fewer, hard cap 70.

Body only for a non-obvious why, breaking changes, migration notes, or
linked issues; skip entirely when the subject is self-explanatory. Wrap at
72 characters, bullets use `-`, issue references last (`Closes #42`,
`Refs #17`).

Never include: "This commit does X", I/we/now/currently, restating the file
name a scope already names, emoji (unless project convention), or AI
attribution (unless the user's own rules require a trailer; then add it as a
trailer).

## Examples

<commit-examples>
  <invalid>feat: add a new endpoint to get user profile information from the database</invalid>

  <valid>
feat(api): Add GET /users/:id/profile

Mobile client needs profile data without the full user payload to
reduce LTE bandwidth on cold-launch screens.

Closes #128
  </valid>

  <valid type="breaking">
feat(api)!: Rename /v1/orders to /v1/checkout

BREAKING CHANGE: clients on /v1/orders must migrate to /v1/checkout
before 2026-06-01. Old route returns 410 after that date.
  </valid>
</commit-examples>

## Auto-Clarity

Always include a body for: breaking changes, security fixes, data
migrations, reverts. Never compress these to subject-only; future debuggers
need the context.

## Boundaries

Generates the message only: does not stage, commit, or amend unless the
user asks. Output the message ready to paste. One-shot: the active
intensity level is untouched.
