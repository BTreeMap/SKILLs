# Ultra: Atomicity and History-Consistency Audit

Applies on top of SKILL.md, its Full section included. Run these audits
BEFORE drafting; they may change what gets committed as well as the message.
The audit reads history and the staged diff; it never restages, resets, or
commits on its own, and a split stays a proposal until the user accepts it.

<procedure for="atomicity">
  <step>Inspect the staged set with `git status --short` and `git diff --staged --stat`.</step>
  <step>Group the staged files by concern: one logical change per commit. A feature, a fix, a rename, and a format pass are separate concerns.</step>
  <step>If more than one concern is staged, propose a split before drafting: name each commit-to-be with its own subject and the files it takes (`git reset` then stage per group, or `git add -p` for mixed files).</step>
  <step>Never fold a format-only or rename-only sweep into a behavior change.</step>
</procedure>

<procedure for="scope-consistency">
  <step>Survey scope usage frequency, e.g. `git log --pretty=format:'%s' -200 | grep -oE '^[a-z]+\([a-z0-9-]+\)' | sort | uniq -c | sort -rn`.</step>
  <step>Choose the most frequent scope that fits the change; treat near-synonyms (e.g. `auth` vs `authn`) as one and prefer the dominant spelling.</step>
  <step>Flag any synonym fragmentation found as a one-line note after the commit output.</step>
</procedure>

<procedure for="breaking-change">
  <step>Scan the staged diff for removed or renamed public functions, endpoints, CLI flags, config keys, environment variables, and schema or persisted-format changes.</step>
  <step>Each hit requires the `BREAKING CHANGE: ` footer with a concrete migration path; no hit requires no footer.</step>
</procedure>

<procedure for="reference-resolution">
  <step>Derive issue references from the branch name (e.g. `feature/142-token-expiry`), from `Fixes #N` markers in removed TODO or FIXME comments, and from the user's request.</step>
  <step>Add each as a footer line (`Resolves #142`); invent none.</step>
</procedure>

<directives for="verification">
  <rule>Before output, run the Full checklist in SKILL.md item by item. On any failure, fix and re-verify instead of shipping the violation.</rule>
</directives>
