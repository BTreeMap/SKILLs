# Full: Scope, Body, and Footer

Applies on top of the message rules in SKILL.md.

<procedure for="scope">
  <step>Inspect recent history, e.g. `git log --pretty=format:'%s' -50`.</step>
  <step>Reuse an existing scope from the log when it fits the change; a synonym fragments the history.</step>
  <step>When none fits, derive a new scope from the repository's top-level packages, crates, modules, or directories: one short lowercase token, hyphens joining multiple words.</step>
  <step>Omit the scope entirely for a repository-wide change.</step>
</procedure>

<directives for="body">
  <rule>Separate the subject line and the body with exactly one blank line; git tooling requires it.</rule>
  <rule>Wrap all body lines at 72 characters.</rule>
  <rule>Explain exactly what changed and the rationale behind the chosen solution; leave the how to the diff and never restate it.</rule>
  <rule>Phrase the body token-economically, in caveman style: dense syntax, no conversational filler.</rule>
</directives>

<directives for="footer">
  <rule>Place issue tracker references in the footer (e.g., Fixes #123, Resolves #456).</rule>
</directives>

<checklist for="full">
  <item>Subject follows `<type>(<scope>): <subject>`, is 70 characters or fewer, and takes its type from the allowed list.</item>
  <item>Scope, if present, is lowercase, a single token, and verified via `git log`.</item>
  <item>Subject description is imperative, capitalized, and ends without punctuation.</item>
  <item>One blank line separates the subject and body.</item>
  <item>Body lines wrap at 72 characters and give the what and why without restating the diff.</item>
  <item>Issue references and breaking changes reside only in the footer.</item>
  <item>Output contains no conversational filler.</item>
</checklist>

<examples for="message">

  <example for="valid">
    <context>A feature commit with a scope, body, and issue reference.</context>
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
