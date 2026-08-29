# AGENTS.md

This repository is a central, project-agnostic library of reusable agent skills.
Each skill is a self-contained `SKILL.md` describing a procedure an LLM agent can
load and execute. Downstream projects consume this repository as a git
submodule mounted at `.github/skills`, as a Claude Code plugin, or through a
skills manager such as `npx skills`, so **every skill here MUST be neutral and
reusable across unrelated projects**.

This file is the entry point. Load linked skills just in time - only when the task
needs them - to keep context lean.

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
  skill, `skills/<skill-name>` to `../<skill-name>`. Every vendor path is a
  single symlink to that hub, so supporting another agent costs one link rather
  than one per skill. `.github/skills` serves GitHub Copilot and mirrors the
  path downstream projects mount this repository at; `.claude/skills` serves
  Claude Code.
* `.claude-plugin/` carries the installer manifests: `marketplace.json` lists
  every skill by its canonical root path, which is the address installers
  resolve, and `plugin.json` declares the same root container to Claude Code.
  The gate regenerates that list from the tree, so adding a skill never edits a
  manifest by hand.
* `LICENSE`: MIT.
* This repository is documentation that other agents read; treat correctness as
  an editorial property, not a compiled one. The exception is the bundled
  Python, which is a uv workspace: the root `pyproject.toml` lists every
  member, `uv.lock` pins the whole library, and the gate lints, formats, and
  tests it (see Automated gate).

Current skills:

* `aesthete/` - UI/UX design discipline with an HCI eye and a PL-informed
  structural discipline: the design read, composition dials, laws of taste,
  a precedence ladder, and a source-of-truth ownership table in the spine,
  with a dated WCAG 2.2 accessibility floor as the sole source of
  accessibility truth, verbs (design/build/review/audit/redesign/
  teach/help), supplied design-document and palette ingestion, surface profiles (marketing,
  product), craft references (typography, color, layout, motion, interaction,
  components, platform), design-system selection, the generated-output tell
  catalogue, and a mechanical ship gate loaded on demand from `references/`.
* `author-skill/` - how to distill a procedure into a reproducible skill (the
  meta-skill governing this repository).
* `caveman/` - token-economical output formatting for coding workflows,
  with lite/full/ultra/wenyan levels and one-shot commit/review/compress/stats/
  help modes; the compress mode is guarded by a deterministic bundled script.
* `fact-check/` - atomic-claim verification of documents against retrieved
  evidence: calibrated verdict taxonomy, evidence-first reporting, tiered
  user approval before edits, and capability-probed orchestration (parallel
  sub-agents or an identical sequential pipeline), with claim routing,
  evidence rules, report templates, and a maintainer evaluation protocol
  loaded on demand from `references/`.
* `git-commit/` - Conventional Commits standard for commit messages, with
  lite/full/ultra effort levels loaded on demand from `references/` and a
  push verb that commits at lite level and pushes.
* `humanize/` - claim-preserving rewrites of AI-sounding prose based on
  Wikipedia's "Signs of AI writing": invariants, a 35-pattern detection
  index, and progressive-loading rules in the spine, with pattern groups
  (content, language, style, chatbot, filler, rhetoric) and a false-positive
  calibration guard loaded on demand from `references/`.
* `lit-review/` - staged literature reviews with a keyless search script over
  OpenAlex, arXiv, and Crossref: criteria fixed before any search, logged
  queries, alias deduplication, two-pass screening with reasoned exclusions,
  snowballing, extraction records with appraisal, theme synthesis, and DOI
  verification before delivery, with per-phase files loaded on demand from
  `references/`.
* `pl-theorist/` - a PL theorist's discipline across the lifecycle via verbs
  (design/build/refactor/review/audit/test/teach/help), with per-language cost
  models (including Bash and GitHub Actions YAML) and verb files loaded on
  demand from `references/`.
* `ponder/` - open-question research with uniform rigor across registers: a
  lead-run first round that answers trivial questions without dispatch,
  decomposition to retrievable leaves by governing principle, an append-only
  event ledger owned by a bundled script (transition invariants, derived
  sections, per-round yield, a draft-time outline), fan-out over few orthogonal
  leaf bundles, a mandatory rival sweep, and presentation weight derived from
  ledger state, with per-phase files loaded on demand from `references/`.
* `ponytail/` - laziest-working-solution discipline: YAGNI, stdlib-first, minimal
  diffs, with lite/full/ultra levels and design/refactor/review/audit/test/
  teach/debt/gain/help verbs loaded on demand from `references/`.
* `read-pdf/` - text and metadata extraction from PDF files or URLs for
  analysis; URL inputs download once into a capped temp cache.
* `reframe/` - bold, testable target-direction judgments that challenge
  incremental or legacy-bound framing.
* `setup-env/` - isolated per-project dev environments provisioned entirely
  in userspace (uv is the only assumption): a typed target algebra of
  `family[:flavor][@version]` tags over a closed recipe catalog, micromamba
  and publisher suppliers, qemu user-mode emulation for foreign-architecture
  binaries, an idempotent typed Python planner/executor under `scripts/`,
  and per-target notes plus a maintainer extension protocol under
  `references/`.
* `thematic-analysis/` - theme development from qualitative text under one
  named school (reflexive, codebook, template, framework matrix, rapid,
  hybrid), with corpus-sourced defaults for codebook size, agreement
  sampling, and theme counts, an adaptation disclosure for feedback and
  ticket data, and the cited evidence base loaded on demand from
  `references/`.

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

Rules live in `.github/gate/src/btm_repo_gate/rules/`, one function each. A rule returns
findings, and a finding carries its repair or `None`; that field alone decides
which column above it lands in, so adding a rule never touches the driver or
the workflow. Never silence a ruff rule repository-wide: put a
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
* `license: MIT` on every skill - skills are vendored individually and keep
  their terms when copied out of this repository.
* `compatibility` (≤500 characters) only for real environment requirements
  (runtimes, system packages, network access); most skills omit it.

## Authoring and editing skills

* Before creating or modifying any skill, load
  [author-skill/SKILL.md](author-skill/SKILL.md) and follow it. It defines
  the required structure, the distillation workflow, and the validation checklist.
* A skill MUST be a reproducible procedure, not a narrative of one past session,
  and MUST NOT hardcode any single project's identity (paths, scopes, service or
  package names). Parameterize project-specific values or instruct the agent to
  derive them from the consuming repository.
* Keep each skill within context economy (~500 lines). Offload bulky reference
  material to sibling files the agent reads on demand.
* When a step uses a capability another skill in this library provides (PDF
  extraction, commit drafting, prose cleanup, environment provisioning),
  command that skill in its slash form as an unconditional instruction:
  "read PDFs with `/read-pdf`". The leading slash marks the name as a skill
  invocation to the executing agent, and the imperative holds because the
  library is consumed as a set through the submodule, so siblings are
  present. A fallback chain responds to conditions of the environment (an
  unreachable file, no network) and names the degraded path to take.
* Write directives, not commentary about the document. A sentence that
  explains why a convention exists, restates what a table's own headings
  already say, or narrates the file's structure earns nothing and is paid
  for on every load. Keep rationale only where it changes a judgment call.
* State each directive as the pattern to follow. A prohibition spells out
  the unwanted pattern in full, which raises that pattern's salience for
  the model reading it; the positive form spends the same tokens making the
  right path more likely. Reserve negation for hard boundaries where the
  banned form must be named to be recognized (secrets, em-dashes, spec
  violations).
* Bundled files are addressed by **registered name**, never by path, so a
  path cannot drift and two files cannot claim one name:
  * **One declaration site, declared before use.** Every skill that bundles
    files opens with a `## Registry` section, the first `##` heading in the
    file, mapping each name to its path. Declaring names before the body
    uses them mirrors declaration-before-reference in a program. That table
    is the only place a path appears. The registry lists every bundled file,
    including any not loaded during a run, such as a maintainer protocol;
    those say so in their own first line.
  * **A name is the basename without `.md`, in backticks**: `` `a11y` ``,
    `` `interaction` ``. Backticks mark it as an identifier so it is never
    read as the ordinary word. Basenames are unique within a skill, so a
    name resolves to exactly one file.
  * **Everything outside the declaration uses the name alone**, in `SKILL.md`
    and inside `references/` alike. Reference files MUST NOT contain Markdown
    links to other reference files: the spec keeps references one level deep
    from `SKILL.md`, and link syntax invites the chaining that rule forbids.
  * **State the name-is-the-file identity once, never per row.** When a
    table is keyed by verb, mode, or level and each row loads the file of
    that name, say so in one sentence above the table and drop the column;
    a column repeating its own row key is the identity function written out
    once per row. Rows that deviate (loading nothing, or loading two files)
    are named in that same sentence.
  * **A name is an address, never a sentence's payload.** It appears as the
    object of a word that says what it is: "defined in `review`", "load
    `brief`", "the template in `report`". Never "Full format: `review`.",
    which reads as a value rather than a document. In a table cell the
    column heading supplies that word.
  * **Runnable commands keep the literal path**, since they are invocations
    rather than references.
  * A citation names the file that actually owns the topic. When ownership
    moves, every citation to it moves in the same change.
* NEVER use em-dash characters (U+2014) anywhere in this repository; use a
  hyphen, a comma, a colon, or restructure the sentence.
* A convention change is total: the same change rewrites every statement,
  example, and docstring of the old convention, so the repository shows one
  convention at a time.
* A bundled script and its invoking agent form a neuro-symbolic pair: the
  script is the symbolic half, the agent the neuro half. Give each half the
  work it is suited to:
  * The script owns what is exact and decidable: invariants (existence,
    size, encoding, identity), structural equality, digests, atomic writes,
    backups. It hard-fails (nonzero exit) only on an invariant violation.
  * A heuristic never holds refusal authority. The script emits heuristic
    judgments as advisory signal lines stating their evidence (ratios,
    matched rules, the best-guess classification) for the agent to weigh
    against user intent; a signal never blocks.
  * A destructive or hard-to-reverse effect is gated on an exact witness: a
    marker file, an identity record, or an explicit flag the caller must
    pass. An undo path, such as a verified backup, is what makes advisory
    judgment safe downstream.
  * No silent trust decisions: when a check is skipped or vacuous (no pinned
    digest for a version, a format outside the validator's model), the
    script says so in its output.
  * Mechanical repairs that are exact and idempotent belong to the script
    (for example, deleting a corrupt download on digest mismatch so a re-run
    can succeed); judgment calls belong to the agent, informed by the
    script's diagnostics.
  * The command surface documented in the skill is the handoff point
    between the halves: in production the agent invokes the interface and
    reads its output, so document commands and output conventions
    completely enough that the interface alone carries a run. Source
    reading belongs to user-instructed troubleshooting; each skill that
    bundles a script states this gate in one line beside its commands.
  * Unique identifiers are minted by the script: the agent supplies two
    or three keywords naming the thing, and the script returns the
    identifier as the lowercase dash-joined keyword slug plus a 128-bit
    entropy suffix,
    `b32hexencode(os.urandom(16)).decode().rstrip("=").lower()`. Every
    output echoes the canonical identifier, and the agent supplies that
    full identifier in later calls. Keyword-subset resolution is the
    recovery path for an identifier lost to context compression: a unique
    subset resolves, the script signals the recovery and echoes the full
    identifier again, and an ambiguous reference is an error listing the
    candidates. The split: the model owns the semantics of the name, the
    script owns its uniqueness. Identifiers with a natural key (a DOI, a
    file path) keep that key.
  * Command surfaces are uniform in shape, because each asymmetry is a
    token spent re-reading help text: one record is a batch of one (one
    JSON input carries one record or fifty), sibling record kinds share
    one plural-array container schema, every subcommand addresses its
    subject the same way, and each effect has exactly one spelling.
  * Configuration travels as command-line parameters; JSON content
    travels on stdin. Every call names its subject, because several
    agents may share one state root and the script therefore holds no
    ambient current-subject state. The skill keeps the identifier cheap
    by instructing the agent to bind the command path and the session
    identifier to shell variables, reused while the shell persists and
    re-bound after a reset, and to chain a round's calls in one shell
    invocation.
  * Every skill that bundles Python is a member of the repository's uv
    workspace, declared in the root `pyproject.toml`, and the member is
    the skill's `scripts/` directory: `<skill>/scripts/pyproject.toml`, a
    `scripts/src/btm_<skill>/` package, and `scripts/tests/`, so all
    coding elements live inside `scripts/` and the skill directory itself
    stays documentation. One lock and one environment serve every member,
    so `uv lock --check` and `uv run --all-packages pytest` cover the
    library in one command. Logic shared across members lives once, in
    the `btm-corekit` package under `.corekit/`, which a member declares
    as `dependencies = ["btm-corekit"]` with the source
    `btm-corekit = { workspace = true }`. Kernel edits are live
    immediately, with no copy and no pin. The gate keeps the kernel
    single-defined and the layout canonical: a member that redefines a
    kernel symbol, skill Python outside `scripts/`, or a manifest off
    `<skill>/scripts/pyproject.toml` is a blocking finding.
  * The member's `[project.scripts]` console command, named
    `btm-<skill>`, is the one entry point, and skills document its
    invocation as one binding reused for the whole shell:
    `R="env -u VIRTUAL_ENV uv run --project $(realpath <skill-root>/scripts) btm-<skill>"`.
    The `realpath` is load-bearing: uv resolves the project path
    lexically, and an agent reaches a skill through an alias directory
    such as `.claude/skills/<skill>/`, whose lexical ancestors hold no
    workspace root. `env -u VIRTUAL_ENV` keeps an ambient virtualenv out
    of the resolution. The skill therefore runs from a full repository
    checkout (marketplace install or clone); a skill copied out alone
    fails loudly at environment build.
* A script is frugal with the user's disk, and its state placement follows
  the XDG base directory standard:
  * Durable, light state (backups, logs, resumable sessions) lives in the
    library's one state root under the XDG state directory:
    `${XDG_STATE_HOME:-$HOME/.local/state}/btm-skills/`
    (`%LOCALAPPDATA%\btm-skills\` on Windows). The `btm-skills`
    segment marks this library as the source of every file under it, and
    each script keeps all of its durable files inside its own skill's
    subdirectory of that root, `btm-skills/<skill-name>/`, in
    purpose-named subdirectories (`backups/`, `logs/`, `sessions/`).
  * Heavy or regenerable artifacts (downloads, toolchains, caches,
    extractions) live in temporary space. Any temp location serves; the
    directory's name identifies its owner, the way `/setup-env` prefixes
    its roots with `denv`.
  * Logs are JSONL with one timestamped record per line and a size cap the
    script enforces at write time by trimming or one-step rotation.
  * Every script that writes state ships a `clean` verb that removes its
    state, one target or `--all`, and reports the bytes freed.
* A script that talks to the network marks its request origin by one shared
  convention, first defined wins: `BTM_USER_AGENT`, sent verbatim as the
  User-Agent; else `BTM_CONTACT`, else the project contact
  `skills@oss.joefang.org`, in the derived header
  `btm-skills/1.0 (<skill-name>; mailto:<contact>)`. Only a contact-derived
  identity may also disclose the contact through polite request pools (e.g.
  the OpenAlex and Crossref `mailto` parameter); a verbatim override marks
  the request with nothing else. The script alone reads the variables;
  `SKILL.md` never mentions them.
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
that skill's meaning. Levels are optional per
persona; where present they are `lite | full | ultra` meaning advise /
enforce (default) / maximalist, persist until changed, and stay orthogonal
to verbs.

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
repository's `skills/` hub and its vendor aliases are relative symlinks, not
copies.

## Boundaries

* NEVER add secrets, credentials, or project-internal data to a skill; these files
  are public and vendored verbatim into many repositories.
* NEVER make a skill depend on a specific language, framework, or directory layout
  unless the skill's whole purpose is that ecosystem - and say so in the
  `description`.
* When in doubt about a project-specific value, write the skill to discover it from
  the repository at runtime rather than assuming it.
