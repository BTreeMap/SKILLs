# Caveman Commit Verb

Write a terse, exact Conventional Commits message, why over what: the diff
already says what. Output the message ready to paste. Generate the message
only: do not stage, commit, or amend unless the user asks.

## Rules

Subject: `<type>(<scope>): <Imperative summary>`; scope optional; types
feat, fix, refactor, docs, style, perf, test, build, ci, chore, revert;
imperative mood, first letter capitalized, no trailing period; aim for 50
characters or fewer, hard cap 70.

Write a body only for a non-obvious why, breaking changes, migration notes,
or linked issues; skip it when the subject is self-explanatory. Always
include a body for breaking changes, security fixes, data migrations, and
reverts: never compress these to subject-only, since future debuggers need
the context. Wrap the body at 72 characters, start bullets with `-`, and put
issue references last (`Closes #42`, `Refs #17`).

Never include: "This commit does X", I/we/now/currently, restating the file
name a scope already names, emoji (unless project convention), or AI
attribution (unless the user's own rules require a trailer; then add it as a
trailer).

## Examples

<examples for="commit">
  <before>feat: add a new endpoint to get user profile information from the database</before>

  <after>
feat(api): Add GET /users/:id/profile

Mobile client needs profile data without the full user payload to
reduce LTE bandwidth on cold-launch screens.

Closes #128
  </after>

  <after for="breaking">
feat(api)!: Rename /v1/orders to /v1/checkout

BREAKING CHANGE: clients on /v1/orders must migrate to /v1/checkout
before 2026-06-01. Old route returns 410 after that date.
  </after>
</examples>
