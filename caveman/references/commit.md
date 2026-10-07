# Caveman Commit Verb

Write a terse, grammatical commit message with no filler, why over what: the
diff already says what. Take every format rule (type, scope, subject, body,
footer, length, wrapping) from `/git-commit`. Output the message ready to
paste; do not stage, commit, or amend unless the user asks.

Never include "This commit does X", I/we/now/currently, a file name the
scope already names, or emoji unless the project uses them.

## Examples

<examples for="commit">

  <example for="register">
    <before>feat: add a new endpoint to get user profile information from the database</before>
    <after>
feat(api): Add GET /users/:id/profile

Mobile client needs profile data without the full user payload to
reduce LTE bandwidth on cold-launch screens.

Closes #128
    </after>
  </example>
</examples>
