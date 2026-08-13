# AGENTS.md

This repository is a central, project-agnostic library of reusable agent skills.
Each skill is a self-contained `SKILL.md` describing a procedure an LLM agent can
load and execute. Downstream projects consume this repository as a git submodule
mounted at `.github/skills`, so **every skill here MUST be neutral and reusable
across unrelated projects**.

This file is the entry point. Load linked skills just in time - only when the task
needs them - to keep context lean.

## Repository shape

* One directory per skill, named in kebab-case, containing a file named exactly
  `SKILL.md`. The directory name MUST match the skill's `name` in its frontmatter.
* Naming convention: a task skill is an imperative verb phrase, the command a
  user would speak (`fact-check`, `read-pdf`, `git-commit`); a persona or
  stance skill is a single noun (`caveman`, `ponytail`, `pl-theorist`). No
  filler nouns (`-protocol`, `-helper`, `-skills`), no gerunds.
* Every top-level directory not starting with a dot IS a skill directory; that
  namespace is reserved. Repository plumbing lives in dotted directories
  (`.github`, `.claude`) or in single files at the root (e.g.
  `sync-skills.example.yml`).
* `LICENSE`: MIT.
* There is no build system, dependency manifest, or test runner. This repository is
  documentation that other agents read; treat correctness as an editorial property,
  not a compiled one.

Current skills:

* `git-commit/` - Conventional Commits standard for commit messages, with
  lite/full/ultra effort levels loaded on demand from `references/` and a
  push verb that commits at lite level and pushes.
* `author-skill/` - how to distill a procedure into a reproducible skill (the
  meta-skill governing this repository).
* `caveman/` - token-economical output formatting for coding workflows,
  with lite/full/ultra/wenyan levels and one-shot commit/review/compress/stats/
  help modes; the compress mode is guarded by a deterministic bundled script.
* `read-pdf/` - text and metadata extraction from PDF files for analysis.
* `pl-theorist/` - a PL theorist's discipline across the lifecycle via verbs
  (design/build/refactor/review/audit/test/teach/help), with per-language cost
  models (including Bash and GitHub Actions YAML) and verb files loaded on
  demand from `references/`.
* `reframe/` - bold, testable target-direction judgments that challenge
  incremental or legacy-bound framing.
* `ponytail/` - laziest-working-solution discipline: YAGNI, stdlib-first, minimal
  diffs, with lite/full/ultra intensity levels and one-shot review/audit/debt/
  gain/help modes loaded on demand from `references/`.
* `aesthete/` - UI/UX design discipline with an HCI eye and a PL-informed
  structural discipline: the design read, composition dials, laws of taste,
  a precedence ladder, and a source-of-truth ownership table in the spine,
  with a dated WCAG 2.2 accessibility floor as the sole source of
  accessibility truth, verbs (design/build/review/audit/redesign/
  teach/help), supplied design-document and palette ingestion, surface profiles (marketing,
  product), craft references (typography, color, layout, motion, interaction,
  components, platform), design-system selection, the generated-output tell
  catalogue, and a mechanical ship gate loaded on demand from `references/`.
* `fact-check/` - atomic-claim verification of documents against retrieved
  evidence: calibrated verdict taxonomy, evidence-first reporting, tiered
  user approval before edits, and capability-probed orchestration (parallel
  sub-agents or an identical sequential pipeline), with claim routing,
  evidence rules, report templates, and a maintainer evaluation protocol
  loaded on demand from `references/`.

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
* Bundled files are addressed by **registered name**, never by path, so a
  path cannot drift and two files cannot claim one name:
  * **One declaration site.** Every skill that bundles files carries a
    `## Registry` section as its final section, mapping each name to its
    path. That table is the only place a path appears; a path written
    anywhere else is a defect. The registry lists every bundled file,
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
  * **Do not restate a name that the row key already carries.** If a table
    is keyed by verb or mode and the file shares that name, say so once and
    drop the column.
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
* Every bundled Python script starts with `#!/usr/bin/env -S uv run --script`
  and a PEP 723 `# /// script` block declaring `requires-python` and
  `dependencies` (an empty list for stdlib-only scripts). Skills invoke them
  with `uv run --script` at the script's canonical bundled path, never with a
  host `python`/`python3`.
* When adding or renaming a skill, commit its discovery alias in the same change:
  `ln -s ../../<skill-name> .github/skills/<skill-name>`. The root directory is
  canonical; `.claude/skills` is a single symlink to `.github/skills`, so the
  alias surfaces there automatically. Update the skill lists in `AGENTS.md` and
  `README.md` too.
* Edit skills **here**, in this repository. NEVER edit the vendored copy inside a
  downstream project's `.github/skills` submodule; those changes are discarded on
  the next submodule update.

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
bumped pointer. Keep this in mind: a change here only reaches a project after that
project bumps its submodule pointer.

For Claude discovery in a consuming repository, commit a relative parent-level
alias from `.claude/skills` to `../.github/skills`. A submodule cannot create that
entry in its parent repository. The root skill directories remain canonical; the
repository's `.github/skills/<skill-name>` entries are relative symlink aliases,
not copies.

## Boundaries

* NEVER add secrets, credentials, or project-internal data to a skill; these files
  are public and vendored verbatim into many repositories.
* NEVER make a skill depend on a specific language, framework, or directory layout
  unless the skill's whole purpose is that ecosystem - and say so in the
  `description`.
* When in doubt about a project-specific value, write the skill to discover it from
  the repository at runtime rather than assuming it.
