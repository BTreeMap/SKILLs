# Maximum: Atomicity and History-Consistency Audit

Applies on top of SKILL.md, its Full section included. Run these audits
BEFORE drafting; they may change what gets committed as well as message.
Audit reads history and staged diff; never restages, resets, or commits on
its own; split stays proposal until user accepts it.

**Procedure: atomicity**

1. Inspect staged set with `git status --short` and
   `git diff --staged --stat`.
2. Group staged files by concern: one logical change per commit. Feature,
   fix, rename, format pass are separate concerns.
3. More than one concern staged: propose split before drafting; name each
   commit-to-be with own subject and files it takes (`git reset` then stage
   per group, or `git add -p` for mixed files).
4. Never fold format-only or rename-only sweep into behavior change.

**Procedure: scope-consistency**

1. Survey scope usage frequency, e.g.
   `git log --pretty=format:'%s' -200 | grep -oE '^[a-z]+\([a-z0-9-]+\)' | sort | uniq -c | sort -rn`.
2. Choose most frequent scope fitting change; treat near-synonyms (e.g.
   `auth` vs `authn`) as one, prefer dominant spelling.
3. Flag any synonym fragmentation found as one-line note after commit
   output.

**Procedure: breaking-change**

1. Scan staged diff for removed or renamed public functions, endpoints, CLI
   flags, config keys, environment variables, schema or persisted-format
   changes.
2. Each hit requires `BREAKING CHANGE: ` footer with concrete migration
   path; no hit requires no footer.

**Procedure: reference-resolution**

1. Derive issue references from branch name (e.g.
   `feature/142-token-expiry`), from `Fixes #N` markers in removed TODO or
   FIXME comments, from user's request.
2. Add each as footer line (`Resolves #142`); invent none.

**Rules: verification**

- Before output, run Full checklist in SKILL.md item by item. Any failure:
  fix and re-verify instead of shipping violation.
