# AGENTS.md

Project-agnostic library of agent skills: each `SKILL.md` is a procedure an
LLM agent loads and follows. Downstream projects consume it as git submodule
at `.github/skills`, as Claude Code plugin, or through `npx skills`, so
every skill stays neutral across unrelated projects. Load a linked skill
only when a task needs it.

## Repository shape

* One directory per skill, kebab-case, containing file named exactly
  `SKILL.md`. Directory name MUST match skill's `name` in its frontmatter.
* Every top-level directory that is neither dotted nor `skills/` IS a skill
  directory; that namespace is reserved. Repository plumbing lives in dotted
  directories (`.github`, `.claude`, `.claude-plugin`, `.agents`) or single
  files at root (e.g. `sync-skills.example.yml`).
* `skills/` is vendor-neutral hub: one committed relative symlink per skill,
  `skills/<skill-name>` to `../<skill-name>`. Every vendor path is one
  symlink to that hub, so another agent costs one link. `.github/skills`
  serves GitHub Copilot and mirrors path downstream projects mount this
  repository at; `.claude/skills` serves Claude Code; `.agents/skills`
  serves OpenAI Codex.
* `.claude-plugin/` carries installer manifests: `marketplace.json` lists
  every skill by canonical root path, the address installers resolve;
  `plugin.json` declares same root container to Claude Code. Gate
  regenerates that list from tree, so adding a skill never edits a manifest
  by hand.
* `LICENSE`: MIT.
* Bundled Python is one uv workspace: root `pyproject.toml` lists every
  member; `uv.lock` pins the library.

Each skill loads its reference files on demand from `references/`.

Current skills:

* `advisor/` - Reads a research project like a principal investigator: what
  it combines, what is outdated, what your lab can afford, cheapest
  experiment settling each claim.
* `aesthete/` - Designs, builds, reviews web interfaces meeting WCAG 2.2,
  honoring supplied brand or design system, avoiding templated look of
  generated UI.
* `asd-ste100/` - Writes, rewrites, checks text in ASD-STE100 Simplified
  Technical English, naming each unapproved word with approved alternatives.
* `author-skill/` - Turns task history, workflow, or procedure into reusable
  SKILL.md another agent can follow with no memory of original session.
* `caveman/` - Compresses replies into terse phrasing keeping every
  technical fact; can rewrite a prose file in place.
* `draft-paper/` - Drafts conference, workshop, journal, survey, or demo
  papers and answers reviews, tracing each empirical claim to an artifact
  and each citation to a retrieved record.
* `fact-check/` - Checks a document claim by claim against retrieved
  sources, quotes behind every verdict; changes nothing until you approve
  each correction.
* `git-commit/` - Drafts and reviews Conventional Commits messages; can
  commit and push in one step.
* `humanize/` - Rewrites AI-sounding prose so it reads like its writer,
  keeping every claim's original strength.
* `lit-review/` - Produces literature review where every citation traces to
  a paper retrieved from OpenAlex, arXiv, or Crossref, never memory.
* `peer-review/` - Reviews a paper as an adverse referee would, pressing on
  claims, design, analysis, limitations, novelty.
* `pl-theorist/` - Brings a programming-languages theorist's discipline to
  design, code, review, tests, tuned per language.
* `ponder/` - Answers an open question and shows its work, sourcing every
  load-bearing claim, testing strongest rival explanation.
* `ponytail/` - Forces laziest solution that works: standard library and
  native features before custom code or new dependencies.
* `read-pdf/` - Extracts text and metadata from a PDF, answers questions
  about it with page-cited evidence, without OCR.
* `reframe/` - Turns a planning discussion into testable direction judgment
  with costed routes and evidence that would prove it wrong.
* `search-web/` - Searches web, Wikipedia, scholarly record when harness has
  no search tool; pulls readable text out of a page.
* `setup-env/` - Installs a project's development toolchain in userspace: no
  sudo, no docker, nothing assumed present but uv.
* `summon/` - Hands work to another agent: whether to delegate, what to tell
  the delegate, how to keep parallel agents apart, how to judge what comes
  back.
* `thematic-analysis/` - Develops themes from qualitative text under one
  named school, each theme backed by verbatim extracts and counts.

## Automated gate

`.github/workflows/gate.yml` runs on every push to `main` and on manual
dispatch. Repairs what is mechanical, commits repair to `main` as one
GitHub-signed `style:` commit, fails only on findings no fixer can settle.
Run same chain before pushing and gate has nothing to do:

```bash
.github/check.sh
```

| Repaired automatically | Reported for a human |
| --- | --- |
| ruff's safe lint fixes and formatting (policy in `ruff.toml`) | Lint findings ruff cannot fix safely |
| Missing, wrong, orphaned, or legacy-shaped hub or vendor alias | Skill directory with no `SKILL.md` |
| Frontmatter `name`, `license`, or field-order drift | Frontmatter judgments: missing or overlong description, non-spec fields, descriptions totalling over budget |
| Manifest `name` fields and declared skill list | Missing or unreadable plugin manifest |
| Skill entries out of alphabetical order in this file and `README.md` | Skill missing from either list, or entry naming no skill |
| Markdown prose off 76-column wrap; code, tables, markup keep their width | |
| | Skill root entry other than `SKILL.md`, `references/`, `scripts/` |
| | Alias path occupied by real content, which no repair may destroy |
| | Em-dash (U+2014), whose replacement is a judgment |
| | Skill Python outside its `scripts/` member, or manifest off `scripts/pyproject.toml` |
| | Workspace member whose Python redefines a kernel symbol |
| | Skill command binding off the one form, or skill with scripts and no binding |

Rules live in `.github/gate/src/btm_repo_gate/rules/`, one function each.
Rule returns findings; finding carries its repair or `None`; that field
alone decides which column above it lands in, so adding a rule never touches
driver or workflow. Never silence a ruff rule repository-wide: put
`# noqa: RULE` carrying its reason on the line that earns it.

## Authoring and editing skills

* Before creating or modifying any skill, load
  [author-skill/SKILL.md](author-skill/SKILL.md) and follow it. It holds
  every authoring rule: frontmatter, registry, redirects, writing standard,
  persona verbs; its `scripts` reference holds rules for bundled scripts.
* Adding or renaming a skill: create it at `<skill-name>/SKILL.md` in
  repository root; update skill lists in `AGENTS.md` and `README.md` in same
  change. Gate writes alias symlink and manifest entry.
* Edit skills here. NEVER edit vendored copy inside a downstream project's
  `.github/skills` submodule; next submodule update discards it.
* NEVER use em-dash characters (U+2014) anywhere in this repository; use
  hyphen, comma, colon, or restructure sentence.
* Markdown prose wraps at 76 columns. Gate reflows paragraphs and list
  items, leaves frontmatter, fences, tables, literal markup a skill emits or
  reads as written.
* Convention change is total: same change rewrites every statement, example,
  docstring of old convention.
* NEVER add secrets, credentials, or project-internal data to a skill; these
  files are public and vendored verbatim into many repositories.

## Commit conventions

Follow [git-commit/SKILL.md](git-commit/SKILL.md): Conventional Commits,
imperative subject ≤70 characters, scope derived from change (here, skill
directory name, e.g. `feat(author-skill): ...`). Drop scope for
repository-wide changes.

## How downstream projects consume this repository

Consumer adds this repository as submodule at `.github/skills`, aliases
`.claude/skills` and `.agents/skills` to it (submodule cannot create entries
in its parent), copies `sync-skills.example.yml` to
`.github/workflows/sync-skills.yml` as a real file, since GitHub Actions
ignores symlinks there. Change here reaches a project when that project
bumps its submodule pointer; README carries recipe.
