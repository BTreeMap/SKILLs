# Ultra Level: Atomicity and History-Consistency Audit

Applies on top of SKILL.md and `full`. Run the audits below BEFORE
drafting; they may change what gets committed as well as the message.

<ultra-directives>

  <atomicity-audit>
    <step>Inspect the staged set with `git status --short` and `git diff --staged --stat`.</step>
    <step>Group the staged files by concern: one logical change per commit (a feature, a fix, a rename, a format pass are separate concerns).</step>
    <step>If more than one concern is staged, propose a split before drafting: name each commit-to-be with its own subject and the files it takes (`git reset` then stage per group, or `git add -p` for mixed files).</step>
    <step>Never fold a format-only or rename-only sweep into a behavior change; the diff noise buries the review signal.</step>
  </atomicity-audit>

  <scope-consistency-survey>
    <step>Survey scope usage frequency, e.g. `git log --pretty=format:'%s' -200 | grep -oE '^[a-z]+\([a-z0-9-]+\)' | sort | uniq -c | sort -rn`.</step>
    <step>Choose the most frequent scope that fits the change; treat near-synonyms (e.g. `auth` vs `authn`) as one and prefer the dominant spelling.</step>
    <step>Flag any synonym fragmentation you find as a one-line note after the commit output.</step>
  </scope-consistency-survey>

  <breaking-change-hunt>
    <step>Scan the staged diff for removed or renamed public functions, endpoints, CLI flags, config keys, environment variables, and schema or persisted-format changes.</step>
    <step>Each hit requires a `BREAKING CHANGE: ` footer with the concrete migration path; absence of a hit requires no footer.</step>
  </breaking-change-hunt>

  <reference-resolution>
    <step>Derive issue references from the branch name (e.g. `feature/142-token-expiry`), from `Fixes #N` markers in removed TODO or FIXME comments, and from the user's request.</step>
    <step>Add each as a footer line (`Resolves #142`); invent none.</step>
  </reference-resolution>

  <verbose-validation>
    <directive>Run the `full` validation checklist explicitly, item by item, before outputting. On any failure, fix and re-verify instead of shipping the violation.</directive>
  </verbose-validation>
</ultra-directives>

## Boundaries

The audit reads history and the staged diff; it never restages, resets, or
commits on its own. Splits are proposals until the user accepts them. Output
still follows the SKILL.md output contract: after any split proposal or
synonym note, strictly the raw commit text or `git commit -m` command.
