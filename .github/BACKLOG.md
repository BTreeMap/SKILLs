# Working on the backlog

You are an agent contributing one backlog item to this repository. The lead
reviews every return and merges only what needs no fix. Review is cheaper
than doing the work only when the return is right the first time, so this
file states what "right" means. Read it whole before you claim an item.

## 1. Claim one item

- The backlog is the open issues on BTreeMap/SKILLs (library items) and
  RadonSys/ste-tax (research items), consolidated in ste-tax's
  `docs/friction/backlog.md` with the ledger row behind each issue.
- Take one issue. Comment on it with the branch name before you start; an
  issue with such a comment less than a day old is taken.
- The issue's title is the scope. Its body names the proposed home. A home
  you would move or a scope you would widen is a comment on the issue, never
  a change; the lead decides, then you proceed.
- Work on a branch named `backlog/<issue number>`; open a PR that closes the
  issue. Never push to `main`.

## 2. Read the standard before the code

In this order, in full, every time:

1. `AGENTS.md`: repository rules. Never an em-dash (U+2014). Markdown prose
   wraps at 76 columns. A convention change is total: the same change
   rewrites every statement, example, docstring, and test of the old
   convention. Never add a secret or project-internal data.
2. `author-skill/SKILL.md`: the standard every skill is held to. Load its
   `scripts` reference when the item touches a script.
3. `caveman/SKILL.md`: skill text is caveman lite (no filler, no hedging,
   full sentences); commit bodies are caveman register.
4. `pl-theorist/SKILL.md` with `references/langs/python.md` and the verb
   file for your task (`refactor` for an existing script, `build` for new
   code, `test` for tests): the engineering standard.
5. The skill you are changing: its `SKILL.md`, every reference, its scripts,
   and its tests, in full. Then one sibling that does the same kind of
   thing, as the pattern to match.
6. `git-commit/SKILL.md`: Conventional Commits, imperative subject of 70
   characters or fewer, scope from the change.

For ste-tax, its own `AGENTS.md` replaces items 1 and 6 and its standard is
looser: pl-theorist taste, no kernel laws, caveman prose.

## 3. Laws that bind every change

These were set in this repository's audits. A return that breaks one is
rejected without review of the rest.

- Exit contract 0 done, 1 fix the input and resend, 2 upstream failed. One
  JSON document on stdout via `emit`; advisory `signal:` lines on stderr;
  nothing else prints.
- `CommandError` for an authoritative defect, `UpstreamError` for the
  network, a `Diagnostic` list through `rejection` for an admitted batch; a
  batch is rejected totally, every problem named in one verdict, state
  unchanged.
- A frozen pydantic `Model` decodes every boundary-crossing shape;
  `extra="forbid"` where the agent writes the file, `extra="ignore"` where
  another writer owns it. mypy strict with the pydantic plugin passes.
- Content enters through a named slot (`--x`, `--x:file`, `--x:stdin`,
  pipe); configuration through flags. A floor or cap on a flag is never
  silent: `wire_limit` refuses below one and signals a cap.
- A member composes the kernel (`btm-corekit`) and redefines no kernel
  symbol. The kernel exports only what a member imports.
- A helper earns a name only when it carries a law: an invariant that could
  drift between copies, a decision a caller could get wrong, or a trust
  boundary. Repetition count never justifies a name. The converse holds too:
  a law stated anywhere has exactly one home.
- Heuristics are signals, never refusals. A skipped or vacuous check is
  reported in the output.
- Rejection authority follows regenerability: a parse failure in a file the
  script wrote is a `CommandError`; a regenerable file is salvaged with a
  signal. A digest mismatch deletes the corrupt copy and hard-fails so a
  rerun self-heals.
- A split reference file pays only when some run never loads it; what every
  run loads sits in the spine, and files that always load together are one
  file.
- No rule in any skill text changes what it requires, permits, or forbids
  unless the issue says so. Verb, level, mode, and command names are
  cross-skill contracts.
- The library's descriptions total under 7,000 characters, enforced by the
  gate. A new or longer description needs an equal trim elsewhere, listed in
  the return.
- Text in `asd-ste100/SKILL.md` passes its own checker; run it after any
  edit there.

## 4. How to do the work

- Audit before asserting: read the current behavior, confirm the defect the
  issue describes, then fix it. Every behavior fix ships with a test that
  fails on the code before the fix; say in the return that you ran it
  against the old code and what it printed.
- Test bridge code: decoders at an untrusted boundary, error conversion, an
  all-or-nothing admission, a witness gating destruction. Test nothing
  pydantic or a closed enum already proves.
- A new wire decoder is written against a recorded real response, pasted
  into the test as a fixture, never against a vendor's prose.
- Behavior is preserved across a refactor: values, ordering, cardinality,
  error behavior, effect order, externally visible identity. The only
  exceptions are the bugs the issue names.
- A changed flag, command, verb, or field is changed in every place that
  spells it: `SKILL.md`, references, docstrings, tests, `--help`. Run
  `--help` and compare it to the text.
- State the cost of a non-trivial shape in its docstring: the bound in the
  domain's real sizes.
- Keep the diff to the item. A drive-by fix you cannot resist is a separate
  issue you file, with the line it belongs to.

## 5. Checks, run as a chain that stops on failure

```
set -e
ruff check --fix . && ruff format .
uv run --all-packages pytest -q -m 'not network'
uv run --all-packages mypy
uv run --project .github/gate btm-repo-gate fix
uv lock --check
test -z "$(grep -rnP '\x{2014}|\x{2013}' --include=*.md --include=*.py . \
  | grep -v '^./.venv' | grep -v 'humanize/references/style.md')"
```

Never pipe a check's status into `tail` or `grep -c`; a hidden failure
reached `main` once that way. Run the network-marked tests of any index you
touched once (`-m network`) and paste the result; a 429 is a result. Include
the gate's reflow in your commit; touch nothing else it changed.

## 6. Commit

One commit per issue unless two concerns are genuinely separable. Subject
`type(scope): Imperative under 70 chars`, scope the skill name or `corekit`,
type `fix` for behavior, `refactor` for structure, `docs` for text, `feat`
for a capability, `test` for tests alone. Body in the caveman register: why
over what, the issue number, the test that pins a fix. A documented flag or
command that changes incompatibly carries a `BREAKING CHANGE:` footer with
the migration path. End with your own attribution trailer as your harness
provides it.

## 7. The return

The PR description is the return. It is reviewed as untrusted text against
this shape, so shape it exactly:

1. Issue number and the one-sentence defect as you confirmed it.
2. A ledger: file, line, what changed, which law or issue line drove it.
3. Behavior fixes: before, after, the pinning test's name, its output on the
   old code.
4. Decisions you made where the issue left room, each with the reason in one
   sentence; a decision the lead must make instead, as a question.
5. Check tails, verbatim, each check on its own line.
6. Anything left undone and why.
7. Friction: every point where a skill's text or script made the job harder
   than it should be, as rows of skill, command, expected, happened, cost in
   tool calls, class (contract gap, text gap, script bug, design question).
   This is how the backlog refills; an empty table is suspect.

## 8. What the review checks, in order

The lead reads the return before the diff and stops at the first failure:

1. Scope equals the issue; nothing outside it moved.
2. Every law in section 3 holds; no check in section 5 was skipped,
   softened, or marked `noqa` without a reason on the line.
3. Each behavior fix has a test that failed on the old code.
4. The diff matches the ledger; the ledger matches the diff.
5. A changed name is changed everywhere.
6. The text reads at the register of its neighbors and a less capable agent
   could follow it without guessing.

A return that passes all six is merged as is. A return that fails one is
sent back with that one line; nothing is fixed on the lead's side.

## 9. In-session agents

When the lead spawns you inside this checkout, sections 1 and 7 change and
the rest stands:

- Work on `main` directly; do not push. The lead reviews the commit and
  pushes it. Claim the issue with a comment naming "in-session" and the date
  instead of a branch.
- The handback to the lead is the return, in the shape of section 7.
- Disk on this machine is near full. Build no new environment: run uv from
  the workspace root only, never in a worktree, never with `uv sync` beyond
  `--locked`, and install nothing. Run `df -h /` first and stop if free
  space is under 1.2 GB. Download no file over 5 MB.
- An issue the lead has put on hold is named in your handoff prompt; skip
  it. An issue whose body ends with a lead decision comment is ready:
  implement that decision.
- Close the issue with `gh issue comment` naming the commit when the lead
  has pushed it; until then, leave it open.
