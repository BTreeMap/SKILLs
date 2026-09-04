# AGENTS.md

This repository is a central, project-agnostic library of reusable agent skills.
Each skill is a self-contained `SKILL.md` describing a procedure an LLM agent can
load and execute. Downstream projects consume it as a git submodule mounted at
`.github/skills`, as a Claude Code plugin, or through a skills manager such as
`npx skills`, so **every skill here MUST be neutral and reusable across
unrelated projects**. Load linked skills only when a task needs them.

## Repository shape

* One directory per skill, named in kebab-case, containing a file named exactly
  `SKILL.md`. The directory name MUST match the skill's `name` in its frontmatter.
* Naming convention: a task skill is an imperative verb phrase, the command a
  user would speak (`fact-check`, `read-pdf`, `git-commit`); a persona or
  stance skill is a single noun (`caveman`, `ponytail`, `pl-theorist`). No
  filler nouns (`-protocol`, `-helper`, `-skills`), no gerunds.
* Every top-level directory that is neither dotted nor `skills/` IS a skill
  directory; that namespace is reserved. Repository plumbing lives in dotted
  directories (`.github`, `.claude`, `.claude-plugin`) or in single files at
  the root (e.g. `sync-skills.example.yml`).
* `skills/` is the vendor-neutral hub: one committed relative symlink per
  skill, `skills/<skill-name>` to `../<skill-name>`. Every vendor path is one
  symlink to that hub, so another agent costs one link. `.github/skills`
  serves GitHub Copilot and mirrors the path downstream projects mount this
  repository at; `.claude/skills` serves Claude Code.
* `.claude-plugin/` carries the installer manifests: `marketplace.json` lists
  every skill by its canonical root path, the address installers resolve, and
  `plugin.json` declares the same root container to Claude Code. The gate
  regenerates that list from the tree, so adding a skill never edits a
  manifest by hand.
* `LICENSE`: MIT.
* This repository is documentation that other agents read; correctness is an
  editorial property. The exception is the bundled Python, a uv workspace: the
  root `pyproject.toml` lists every member, `uv.lock` pins the whole library,
  and the gate lints, formats, and tests it (see Automated gate).

Each skill loads its reference files on demand from `references/`.

Current skills:

* `aesthete/` - UI design and review with an HCI eye: design read,
  composition dials, precedence ladder, ownership table, a dated WCAG 2.2
  accessibility floor, verbs (design/build/review/audit/redesign/teach/help),
  surface profiles, craft references, and a generated-output tell catalogue.
* `author-skill/` - how to distill a procedure into a reproducible skill; the
  meta-skill governing this repository.
* `caveman/` - token-economical output with lite/full/ultra/wenyan levels and
  commit/review/compress/stats/help modes; compress is guarded by a script.
* `fact-check/` - atomic-claim verification against retrieved evidence:
  calibrated verdicts, evidence-first reports, tiered approval before edits,
  capability-probed orchestration.
* `git-commit/` - Conventional Commits with lite/full/ultra effort levels and
  a push verb.
* `humanize/` - claim-preserving rewrites of AI-sounding prose: 40-pattern
  detection index (Wikipedia's "Signs of AI writing" plus Claude-specific
  tells), invariants, progressive loading, calibration guard.
* `lit-review/` - staged literature reviews with a keyless search script over
  OpenAlex, arXiv, and Crossref: criteria before search, logged queries,
  deduplication, two-pass screening, snowballing, extraction, a gated
  notebook of findings and gaps, DOI and citation checks.
* `peer-review/` - adverse, referenced paper review: verbatim claims,
  signalling-question banks for design, analysis, limitations, and novelty,
  a lit-review corpus for prior work, objections admitted only with a
  resolved quote or a dated corpus key, and a derived recommendation.
* `pl-theorist/` - a PL theorist's discipline via verbs
  (design/build/refactor/review/audit/test/teach/help) with per-language cost
  models, Bash and GitHub Actions YAML included.
* `ponder/` - open-question research with uniform rigor: lead-run first
  round, decomposition to retrievable leaves, a script-owned event ledger,
  fan-out over orthogonal bundles, a mandatory rival sweep, presentation
  derived from ledger state.
* `ponytail/` - laziest-working-solution discipline: YAGNI, stdlib first,
  minimal diffs; lite/full/ultra levels and
  design/refactor/review/audit/test/teach/debt/gain/help verbs.
* `read-pdf/` - text and metadata extraction from PDF files or URLs; URLs
  download once into a capped temp cache.
* `reframe/` - testable target-direction judgments that challenge incremental
  or legacy-bound framing.
* `search-web/` - keyless retrieval for an agent with no harness search
  tool: ranked web results, DuckDuckGo instant answers, Wikipedia summaries,
  papers from OpenAlex, Crossref, or arXiv, and the readable text of one
  page, all in one record shape, with a temp-space cache per query.
* `setup-env/` - isolated per-project dev environments in userspace with uv
  as the only assumption: a typed target algebra of
  `family[:flavor][@version]` tags, micromamba and publisher suppliers, qemu
  user-mode emulation, a typed planner under `scripts/`.
* `thematic-analysis/` - theme development from qualitative text under one
  named school (reflexive, codebook, template, framework matrix, rapid,
  hybrid), with corpus-sourced defaults, a feedback-data adaptation
  disclosure, and its cited evidence base.

## Automated gate

`.github/workflows/gate.yml` runs on every push to `main` and on manual
dispatch. It repairs what is mechanical, commits the repair to `main` as one
GitHub-signed `style:` commit, and fails only on findings no fixer can settle.
Run the same fixers before pushing and the gate has nothing to do:

```bash
ruff check --fix . && ruff format .
uv run --all-packages pytest
uv run --project .github/gate btm-repo-gate fix
```

| Repaired automatically | Reported for a human |
| --- | --- |
| ruff's safe lint fixes and formatting (policy in `ruff.toml`) | Lint findings ruff cannot fix safely |
| A missing, wrong, orphaned, or legacy-shaped hub or vendor alias | A skill directory with no `SKILL.md` |
| Frontmatter `name`, `license`, or field-order drift | Frontmatter judgments: a missing or overlong description, non-spec fields |
| Manifest `name` fields and the declared skill list | A missing or unreadable plugin manifest |
| Skill entries out of alphabetical order in this file and `README.md` | A skill missing from either list, or an entry naming no skill |
| | An alias path occupied by real content, which no repair may destroy |
| | An em-dash (U+2014), whose replacement is a judgment |
| | Skill Python outside its `scripts/` member, or a manifest off `scripts/pyproject.toml` |
| | A workspace member whose Python redefines a kernel symbol |

Rules live in `.github/gate/src/btm_repo_gate/rules/`, one function each. A
rule returns findings, and a finding carries its repair or `None`; that field
alone decides which column above it lands in, so adding a rule never touches
the driver or the workflow. Never silence a ruff rule repository-wide: put a
`# noqa: RULE` carrying its reason on the line that earns it.

## Frontmatter protocol

Every `SKILL.md` header conforms strictly to the
[Agent Skills](https://agentskills.io) open standard, so a skill loads
unchanged in any spec-compliant agent and uploads without hard errors:

* Fields, in canonical order: `name`, `description`, then only as needed
  `license`, `compatibility`, `metadata`, `allowed-tools`. NEVER emit
  agent-specific extension fields (`argument-hint`, `when_to_use`, ...);
  record such hints as quoted string values under `metadata`
  (e.g. `metadata: {argument-hint: "[lite|full|ultra]"}`).
* `name` equals the directory name: 1-64 characters; lowercase letters,
  numbers, and hyphens; no leading, trailing, or consecutive hyphens.
* `description` is a `>-` folded block scalar, ≤1024 characters, third
  person, in two movements: what the skill does (capability statement
  carrying its key search terms), then trigger conditions starting
  "Use when ..."; append "Do not use for ..." when misfires are likely.
  It names the deliverable and the guarantees on it, in the reader's own
  vocabulary: what they get, and when to reach for this skill over a
  neighboring one. How the skill works belongs in the body, so the
  description names no internal record, phase, or file the body defines,
  no library the skill happens to call, and no verb or level that
  `argument-hint` already lists. A guarantee the reader can hold the skill
  to is not an implementation detail: "cites only what it retrieved" and
  "edits nothing without approval" earn their place where the machinery
  behind them does not.
* `metadata.argument-hint` is the invocation grammar and the only place it
  is spelled: one bracket group per independent choice, ordered as a user
  types them, so orthogonal axes never collapse into one alternation
  (`"[lite|full|ultra] [design|review|help]"`, never
  `"[lite|full|ultra|design|review|help]"`, which reads as pick exactly
  one). Every skill carries one; a skill with no vocabulary names its
  subject instead (`"[file-or-section]"`). No check can derive this from
  the body, since verbs, levels, and modes are declared in different
  shapes per skill and nowhere authoritatively, so it is a review
  obligation whenever a verb, level, or mode changes.
* `license: MIT` on every skill; skills are vendored individually and keep
  their terms when copied out of this repository.
* `compatibility` (≤500 characters) only for real environment requirements
  (runtimes, system packages, network access); most skills omit it.

## Authoring and editing skills

* Before creating or modifying any skill, load
  [author-skill/SKILL.md](author-skill/SKILL.md) and follow it. It defines
  the required structure, the distillation workflow, the validation
  checklist, and the full rules for bundled scripts (`script_design`).
* A skill MUST be a reproducible procedure, never a narrative of one past
  session, and MUST NOT hardcode any single project's identity (paths,
  scopes, service or package names). Parameterize project-specific values or
  instruct the agent to derive them from the consuming repository.
* Keep each skill within context economy (~500 lines). Offload bulky reference
  material to sibling files the agent reads on demand.
* When a step uses a capability another skill in this library provides (PDF
  extraction, commit drafting, prose cleanup, environment provisioning),
  command that skill in its slash form as an unconditional instruction:
  "read PDFs with `/read-pdf`". The slash marks a skill invocation, and the
  imperative holds because the library is consumed as a set, so siblings are
  present. A fallback chain responds to conditions of the environment (an
  unreachable file, no network) and names the degraded path to take.
* Write directives, not commentary about the document. A sentence that
  explains why a convention exists, restates a table's headings, or narrates
  the file's structure is paid for on every load. Keep rationale only where
  it changes a judgment call.
* State each directive as the pattern to follow. A prohibition spells out
  the unwanted pattern in full, which raises its salience for the reading
  model; the positive form spends the same tokens on the right path. Reserve
  negation for hard boundaries where the banned form must be named to be
  recognized (secrets, em-dashes, spec violations).
* Bundled files are addressed by **registered name**, never by path, so a
  path cannot drift and two files cannot claim one name:
  * **One declaration site, declared before use.** Every skill that bundles
    files opens with a `## Registry` section, the first `##` heading in the
    file, mapping each name to its path. That table is the only place a path
    appears. It lists every bundled file, including any not loaded during a
    run, such as a maintainer protocol; those say so in their own first line.
  * **A name is the basename without `.md`, in backticks**: `` `a11y` ``,
    `` `interaction` ``. Backticks mark an identifier, so it is never read
    as the ordinary word. Basenames are unique within a skill.
  * **Everything outside the declaration uses the name alone**, in `SKILL.md`
    and inside `references/` alike. Reference files MUST NOT contain Markdown
    links to other reference files: the spec keeps references one level deep
    from `SKILL.md`, and link syntax invites the chaining that rule forbids.
  * **State the name-is-the-file identity once, never per row.** When a
    table is keyed by verb, mode, or level and each row loads the file of
    that name, say so in one sentence above the table and drop the column.
    Rows that deviate (loading nothing, or loading two files) are named in
    that same sentence.
  * **A name is an address, never a sentence's payload.** It appears as the
    object of a word that says what it is: "defined in `review`", "load
    `brief`", "the template in `report`". Never "Full format: `review`.",
    which reads as a value. In a table cell the column heading supplies that
    word.
  * **Runnable commands keep the literal path**, since they are invocations.
  * A citation names the file that actually owns the topic. When ownership
    moves, every citation to it moves in the same change.
* NEVER use em-dash characters (U+2014) anywhere in this repository; use a
  hyphen, a comma, a colon, or restructure the sentence.
* A convention change is total: the same change rewrites every statement,
  example, and docstring of the old convention, so the repository shows one
  convention at a time.
* A bundled script and its invoking agent form a neuro-symbolic pair; the
  `script_design` rules in author-skill govern the split (exact invariants
  in the script, advisory signals for heuristics, witness-gated destruction,
  script-minted identifiers, uniform command surfaces, stdin JSON, the uv
  workspace member layout under `scripts/`, the `btm-corekit` kernel, the
  documented `R=` binding, and the request-origin convention). The gate
  keeps the kernel single-defined and the layout canonical: a member that
  redefines a kernel symbol, skill Python outside `scripts/`, or a manifest
  off `<skill>/scripts/pyproject.toml` is a blocking finding.
* A script is frugal with the user's disk, and its state placement follows
  the XDG base directory standard:
  * Durable, light state (backups, logs, resumable sessions) lives in the
    library's one state root under the XDG state directory:
    `${XDG_STATE_HOME:-$HOME/.local/state}/btm-skills/`
    (`%LOCALAPPDATA%\btm-skills\` on Windows). The `btm-skills` segment
    marks this library as the source of every file under it, and each
    script keeps all of its durable files inside its own skill's
    subdirectory of that root, `btm-skills/<skill-name>/`, in purpose-named
    subdirectories (`backups/`, `logs/`, `sessions/`).
  * Heavy or regenerable artifacts (downloads, toolchains, caches,
    extractions) live in temporary space. Any temp location serves; the
    directory's name identifies its owner, the way `/setup-env` prefixes
    its roots with `denv`.
  * Logs are JSONL with one timestamped record per line and a size cap the
    script enforces at write time by trimming or one-step rotation.
  * Every script that writes state ships a `clean` verb that removes its
    state, one target or `--all`, and reports the bytes freed.
* All of a skill's Python, entry point included, lives inside its member:
  the member's `pyproject.toml` is the single source of truth for what it
  needs, and its console command is the only way in. Skills invoke that
  command with `uv run --project` through the documented binding, never
  with a host `python`/`python3` and never by module path.
* When adding or renaming a skill, create it at `<skill-name>/SKILL.md` in the
  repository root and update the skill lists in `AGENTS.md` and `README.md` in
  the same change. The gate writes the alias symlink and the manifest entry, so
  run it rather than hand-maintaining either.
* Edit skills **here**, in this repository. NEVER edit the vendored copy inside a
  downstream project's `.github/skills` submodule; those changes are discarded on
  the next submodule update.

## Persona verb protocol

A persona skill dispatches work through verbs. Every engineering persona
implements the core eight, each through its own lens:

| Verb | Contract |
| --- | --- |
| design | Plan before code exists |
| build | Write new code |
| refactor | Rewrite existing code, behavior preserved |
| review | Judge a change: total over the diff, sound areas named |
| audit | Judge a codebase: sampled by blast radius, unexamined areas named |
| test | Derive checks from the lens's own laws |
| teach | Explain a judgment, calibrated to audience |
| help | Quick-reference card |

Laws:

* `build` and `refactor` apply changes; every other verb is read-only.
* Same verb, same contract in every persona; only the lens differs.
* A read-only verb names what is outside its lens and routes it to the
  sibling persona's same verb in slash form.
* Dispatch precedence: explicit verb, then unambiguous request shape, then
  the persona's declared default verb.
* One verb file per invocation, registered under the verb's name.

Beyond the core the namespace is free (`ponytail` carries `debt` and
`gain`), and a verb name keeps one meaning across the library: core names
keep the table's semantics, and a name another skill already uses keeps
that skill's meaning. Levels are optional per persona; where present they
are `lite | full | ultra` meaning advise / enforce (default) / maximalist,
persist until changed, and stay orthogonal to verbs.

## Commit conventions

Follow [git-commit/SKILL.md](git-commit/SKILL.md): Conventional Commits, imperative
subject ≤70 characters, scope derived from the change (here, the skill directory
name, e.g. `feat(author-skill): ...`). Drop the scope for repository-wide
changes.

## How downstream projects consume this repository

Skills are added as a submodule:

```bash
git submodule add https://github.com/BTreeMap/SKILLs.git .github/skills
```

The default setup also hard-copies `sync-skills.example.yml` from this
repository's root to the consumer's `.github/workflows/sync-skills.yml`, so
the submodule pointer auto-bumps to the upstream tip on a schedule. The copy
MUST be a real file: GitHub Actions does not resolve symlinks under
`.github/workflows`.

Consumers clone with `--recurse-submodules` (or run
`git submodule update --init --recursive` on an existing checkout), and refresh
with `git submodule update --remote .github/skills` followed by committing the
bumped pointer. A change here reaches a project only after that project
bumps its submodule pointer.

For Claude discovery in a consuming repository, commit a relative parent-level
alias from `.claude/skills` to `../.github/skills`. A submodule cannot create that
entry in its parent repository. The root skill directories remain canonical; this
repository's `skills/` hub and its vendor aliases are relative symlinks.

## Boundaries

* NEVER add secrets, credentials, or project-internal data to a skill; these files
  are public and vendored verbatim into many repositories.
* NEVER make a skill depend on a specific language, framework, or directory layout
  unless the skill's whole purpose is that ecosystem, and say so in the
  `description`.
* When in doubt about a project-specific value, write the skill to discover it from
  the repository at runtime instead of assuming it.

## Types

Every bundled script is typechecked. `uv run mypy` runs strict over every
member's `src/`, with the pydantic plugin so a model's fields are checked at
authoring time, and the gate workflow fails on a finding. Domain records
subclass `Model` from the kernel, which is frozen and refuses unknown fields;
constrained strings use the kernel's refined aliases (`Slug`, `Doi`,
`ArxivId`, `Keyword`, `NonEmpty`) rather than bare `str`.
