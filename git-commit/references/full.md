# Full Level: Body, Footer, and Scope Resolution

Applies on top of the core rules in SKILL.md.

<full_directives>
  <body_constraints>
    <rule>Separate the subject line and the body with exactly one blank line.</rule>
    <rule>Wrap all body lines at 72 characters.</rule>
    <rule>Explain exactly what changed and the rationale behind the chosen solution.</rule>
    <rule>Apply token-economical phrasing (Caveman formatting) to the body text: dense syntax, no conversational filler.</rule>
  </body_constraints>

  <footer_constraints>
    <rule>Place issue tracker references in the footer (e.g., Fixes #123, Resolves #456).</rule>
    <rule>Start breaking changes with 'BREAKING CHANGE: ' followed by the detailed migration path.</rule>
  </footer_constraints>

  <scope_resolution_procedure>
    <step>Inspect recent history, e.g. `git log --pretty=format:'%s' -50`.</step>
    <step>Reuse an existing scope from the log when it fits the current changes.</step>
    <step>When none applies, derive a new scope from the repository's top-level packages, crates, modules, or directories.</step>
    <step>Format new scopes as short, lowercase, single tokens using hyphens for multiple words.</step>
    <step>Omit the scope entirely for repository-wide changes.</step>
  </scope_resolution_procedure>

  <gotchas>
    <item>Git tooling structurally requires the blank line between subject and body.</item>
    <item>Imperative mood is strict (use "Add" instead of "Added" or "Adding").</item>
    <item>The body explains the "what" and "why"; rely entirely on the code diff for the "how".</item>
    <item>Failing to reuse scopes discovered via `git log` fragments the history with duplicate synonyms.</item>
    <item>Terminating the subject line with punctuation violates the standard.</item>
  </gotchas>

  <validation_checklist>
    <directive>Silently verify these conditions before outputting the commit.</directive>
    <item>Subject follows `<type>(<scope>): <subject>` and is 70 characters or less.</item>
    <item>Type is explicitly chosen from `<allowed_types>`.</item>
    <item>Scope (if present) is lowercase, a single token, and verified via `git log`.</item>
    <item>Subject description is imperative, capitalized, and period-free.</item>
    <item>A blank line separates the subject and body.</item>
    <item>Body lines wrap at 72 characters and detail the what/why without restating the diff.</item>
    <item>Issue references and breaking changes reside strictly in the footer.</item>
    <item>Output contains zero conversational filler per the `<output_contract>`.</item>
  </validation_checklist>
</full_directives>

## Examples

<examples>
  <example type="valid">
    <context>A well-formed feature commit with a scope, body, and issue reference.</context>
    <raw_output>
feat(auth): Reject tokens that omit an expiry claim

Tokens minted before the rotation fix lacked an `exp` claim, so the
validator treated them as non-expiring. Requiring `exp` closes the
window in which a leaked token would stay valid indefinitely.

Resolves #142
    </raw_output>
  </example>

  <example type="invalid">
    <context>Common failure modes to avoid.</context>
    <raw_output>
fixed the bug
added a token refresh thing so users dont get logged out randomly anymore. also updated the ui to show a loading spinner while it happens
    </raw_output>
    <violations>
      <item>Missing type and scope.</item>
      <item>Past tense used instead of imperative mood ("fixed", "added").</item>
      <item>Missing blank line between subject and body.</item>
      <item>Body lines exceed 72 characters.</item>
      <item>Missing capitalization.</item>
    </violations>
  </example>
</examples>
