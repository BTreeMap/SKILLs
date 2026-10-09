# Caveman Commit Verb

Write terse, grammatical commit message, no filler, why over what: diff
already says what. Take every format rule (type, scope, subject, body,
footer, length, wrapping) from `/git-commit`. Output message ready to paste;
do not stage, commit, or amend unless user asks.

Never include "This commit does X", I/we/now/currently, file name scope
already names, or emoji unless project uses them.

## Examples

**Example: register**

Before: feat: add a new endpoint to get user profile information from the
database

After:

```text
feat(api): Add GET /users/:id/profile

Mobile client needs profile data without the full user payload to
reduce LTE bandwidth on cold-launch screens.

Closes #128
```
