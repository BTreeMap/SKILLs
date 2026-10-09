# Working on the backlog

You are an agent contributing one backlog item to this repository. Lead
reviews every return, merges only what needs no fix. Review is cheaper than
doing the work only when return is right first time, so this file states
what "right" means. Read it whole before claiming an item.

## 1. Claim one item

- Backlog is the open issues on BTreeMap/SKILLs (library items) and
  RadonSys/ste-tax (research items), consolidated in ste-tax's
  `docs/friction/backlog.md` with ledger row behind each issue.
- Take one issue. Comment on it with branch name before starting; issue with
  such comment less than a day old is taken.
- Issue's title is the scope. Its body names proposed home. Home you would
  move or scope you would widen is a comment on the issue, never a change;
  lead decides, then you proceed.
- Work on branch named `backlog/<issue number>`; open PR that closes issue.
  Never push to `main`.

## 2. Read the standard before the code

In this order, in full, every time:

1. `AGENTS.md`: repository rules. Never an em-dash (U+2014). Markdown prose
   wraps at 76 columns. Convention change is total: same change rewrites
   every statement, example, docstring, test of old convention. Never add
   secret or project-internal data.
2. `author-skill/SKILL.md`: standard every skill is held to. Load its
   `scripts` reference when item touches a script.
3. `caveman/SKILL.md`: skill text is caveman full (no articles, no filler,
   fragments OK); commit bodies are caveman register.
4. `pl-theorist/SKILL.md` with `references/langs/python.md` and verb file
   for your task (`refactor` for existing script, `build` for new code,
   `test` for tests): engineering standard.
5. Skill you are changing: its `SKILL.md`, every reference, its scripts, its
   tests, in full. Then one sibling doing same kind of thing, as pattern to
   match.
6. `git-commit/SKILL.md`: Conventional Commits, imperative subject of 70
   characters or fewer, scope from the change.

For ste-tax, its own `AGENTS.md` replaces items 1 and 6; its standard is
looser: pl-theorist taste, no kernel laws, caveman prose.

## 3. Laws that bind every change

Set in this repository's audits. Return breaking one is rejected without
review of the rest.

- Exit contract 0 done, 1 fix input and resend, 2 upstream failed. One JSON
  document on stdout via `emit`; advisory `signal:` lines on stderr; nothing
  else prints.
- `CommandError` for authoritative defect, `UpstreamError` for network,
  `Diagnostic` list through `rejection` for admitted batch; batch rejected
  totally, every problem named in one verdict, state unchanged.
- Frozen pydantic `Model` decodes every boundary-crossing shape;
  `extra="forbid"` where agent writes file, `extra="ignore"` where another
  writer owns it. mypy strict with pydantic plugin passes.
- Content enters through named slot (`--x`, `--x:file`, `--x:stdin`, pipe);
  configuration through flags. Floor or cap on a flag is never silent:
  `wire_limit` refuses below one and signals a cap.
- Member composes the kernel (`btm-corekit`), redefines no kernel symbol.
  Kernel exports only what a member imports.
- Helper earns a name only when it carries a law: invariant that could drift
  between copies, decision caller could get wrong, or trust boundary.
  Repetition count never justifies a name. Converse holds too: law stated
  anywhere has exactly one home.
- Heuristics are signals, never refusals. Skipped or vacuous check is
  reported in output.
- Rejection authority follows regenerability: parse failure in a file the
  script wrote is `CommandError`; regenerable file salvaged with a signal.
  Digest mismatch deletes corrupt copy and hard-fails so rerun self-heals.
- Split reference file pays only when some run never loads it; what every
  run loads sits in spine; files always loaded together are one file.
- No rule in any skill text changes what it requires, permits, or forbids
  unless the issue says so. Verb, level, mode, command names are cross-skill
  contracts.
- Library's descriptions total under 7,000 characters, enforced by gate. New
  or longer description needs equal trim elsewhere, listed in return.
- Text in `asd-ste100/SKILL.md` passes its own checker; run it after any
  edit there. Check each section in its mode, `procedure` for "Procedure"
  and `description` for every other section, with committed allow file;
  every report must give `"ok": true`. New technical term goes in
  `asd-ste100/terms.txt` under group that justifies it.

```
R="env -u VIRTUAL_ENV -u UV_PROJECT_ENVIRONMENT uv run --project $(realpath asd-ste100/scripts) btm-asd-ste100"
grep -E '^#+ ' asd-ste100/SKILL.md | sed -E 's/^#+ //' | while read -r h; do
  m=description; [ "$h" = Procedure ] && m=procedure
  $R check --text:file asd-ste100/SKILL.md --format markdown --section "$h" \
    --mode "$m" --allow:file asd-ste100/terms.txt | grep -q '"ok": true' \
    || echo "not ok: $h"
done
```

## 4. How to do the work

- Audit before asserting: read current behavior, confirm defect issue
  describes, then fix it. Every behavior fix ships with test that fails on
  code before fix; say in return that you ran it against old code and what
  it printed.
- Test bridge code: decoders at untrusted boundary, error conversion,
  all-or-nothing admission, witness gating destruction. Test nothing
  pydantic or closed enum already proves.
- New wire decoder written against recorded real response, pasted into test
  as fixture, never against vendor's prose.
- Behavior preserved across refactor: values, ordering, cardinality, error
  behavior, effect order, externally visible identity. Only exceptions are
  bugs the issue names.
- Changed flag, command, verb, or field changed in every place that spells
  it: `SKILL.md`, references, docstrings, tests, `--help`. Run `--help`,
  compare to text.
- State cost of non-trivial shape in its docstring: bound in domain's real
  sizes.
- Before giving a member new top-level class or function, grep
  `.corekit/src/btm_corekit/__init__.py` for the name: gate rejects member
  redefining kernel export, and only at the end.
- Keep diff to the item. Drive-by fix you cannot resist is separate issue
  you file, with line it belongs to.

## 5. Checks, run as a chain that stops on failure

```
.github/check.sh
```

Script runs every fixer, then every assertion: ruff format and lint, tests
not marked `network`, mypy, repository gate, lock check, dash scan. Prints
one line per passing check, stops at first failure with that check's whole
output, exits 1. Paste its lines as check tails. Run network-marked tests of
any index you touched once (`uv run --all-packages pytest -m network`),
paste result; 429 is a result. Include gate's reflow in commit; touch
nothing else it changed.

## 6. Commit

One commit per issue unless two concerns are genuinely separable. Subject
`type(scope): Imperative under 70 chars`, scope the skill name or `corekit`,
type `fix` for behavior, `refactor` for structure, `docs` for text, `feat`
for capability, `test` for tests alone. Body in caveman register: why over
what, line `Closes #N` so push closes issue with its commit, test that pins
a fix. Documented flag or command changing incompatibly carries
`BREAKING CHANGE:` footer with migration path. End with your own attribution
trailer as your harness provides it.

## 7. The return

PR description is the return. Reviewed as untrusted text against this shape,
so shape it exactly:

1. Issue number and one-sentence defect as you confirmed it.
2. Ledger: file, line, what changed, which law or issue line drove it.
3. Behavior fixes: before, after, pinning test's name, its output on old
   code.
4. Decisions you made where issue left room, each with reason in one
   sentence; decision lead must make instead, as a question.
5. Check tails, verbatim, each check on own line.
6. Anything left undone and why.
7. Friction: every point where skill's text or script made job harder than
   it should be, as rows of skill, command, expected, happened, cost in tool
   calls, class (contract gap, text gap, script bug, design question). This
   is how backlog refills; empty table is suspect.
8. Anything else worth improving, in your own words: this brief, a law that
   fought the work, a check that cost more than it caught, a kernel helper
   you wished existed, issue's wording, the process. Nothing here is out of
   bounds; point raised here is read by lead, not graded.

## 8. What the review checks, in order

Lead reads return before diff, stops at first failure:

1. Scope equals issue; nothing outside it moved.
2. Every law in section 3 holds; no check in section 5 skipped, softened, or
   marked `noqa` without reason on the line.
3. Each behavior fix has test that failed on old code.
4. Diff matches ledger; ledger matches diff.
5. Changed name is changed everywhere.
6. Text reads at register of its neighbors; less capable agent could follow
   it without guessing.

Return passing all six is merged as is. Return failing one is sent back with
that one line; nothing is fixed on lead's side.

## 9. In-session agents

When lead spawns you inside this checkout, sections 1 and 7 change and rest
stands:

- Work on `main` directly; do not push. Lead reviews commit and pushes it.
  Claim issue with comment naming "in-session" and date instead of branch.
- Handoff prompt may name a bundle: several issues with one home, listed in
  order to work them. Read standard and skill once, then work issues in that
  order, one commit per issue; hand back one return with a section 7 block
  per issue. Issue in bundle cannot be closed: say why in its block,
  continue with next; bundle never stops at its first blocker.
- Handback to lead is the return, in shape of section 7.
- Disk on this machine is near full. Build no new environment: run uv from
  workspace root only, never in a worktree, never with `uv sync` beyond
  `--locked`, install nothing. Run `df -h /` first; stop if free space is
  under 1.2 GB. Download no file over 5 MB.
- Any open issue off hold list in your handoff prompt is ready; hold list is
  only gate; issue's class never defers it. Where lead decision comment ends
  issue, implement that decision.
- Close issue with `gh issue comment` naming commit when lead has pushed it;
  until then, leave it open.
