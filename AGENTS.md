# AGENTS.md

A project-agnostic library of agent skills: each `SKILL.md` is a procedure
an LLM agent loads and follows. Downstream projects consume it as a git
submodule at `.github/skills`, as a Claude Code plugin, or through
`npx skills`, so every skill stays neutral across unrelated projects. Load a
linked skill only when a task needs it.

## Repository shape

* One directory per skill, named in kebab-case, containing a file named
  exactly `SKILL.md`. The directory name MUST match the skill's `name` in
  its frontmatter.
* Every top-level directory that is neither dotted nor `skills/` IS a skill
  directory; that namespace is reserved. Repository plumbing lives in dotted
  directories (`.github`, `.claude`, `.claude-plugin`, `.agents`) or in
  single files at the root (e.g. `sync-skills.example.yml`).
* `skills/` is the vendor-neutral hub: one committed relative symlink per
  skill, `skills/<skill-name>` to `../<skill-name>`. Every vendor path is
  one symlink to that hub, so another agent costs one link. `.github/skills`
  serves GitHub Copilot and mirrors the path downstream projects mount this
  repository at; `.claude/skills` serves Claude Code; `.agents/skills`
  serves OpenAI Codex.
* `.claude-plugin/` carries the installer manifests: `marketplace.json`
  lists every skill by its canonical root path, the address installers
  resolve, and `plugin.json` declares the same root container to Claude
  Code. The gate regenerates that list from the tree, so adding a skill
  never edits a manifest by hand.
* `LICENSE`: MIT.
* Bundled Python is one uv workspace: the root `pyproject.toml` lists every
  member and `uv.lock` pins the library.

Each skill loads its reference files on demand from `references/`.

Current skills:

* `advisor/` - Reads a research project like a principal investigator: what
  it combines, what is outdated, what your lab can afford, and the cheapest
  experiment that settles each claim.
* `aesthete/` - Designs, builds, and reviews web interfaces that meet WCAG
  2.2, honor a supplied brand or design system, and avoid the templated look
  of generated UI.
* `asd-ste100/` - Writes, rewrites, and checks text in ASD-STE100 Simplified
  Technical English, naming each unapproved word with its approved
  alternatives.
* `author-skill/` - Turns a task history, workflow, or procedure into a
  reusable SKILL.md that another agent can follow with no memory of the
  original session.
* `caveman/` - Compresses replies into terse phrasing that keeps every
  technical fact, and can rewrite a prose file in place.
* `draft-paper/` - Drafts conference, workshop, journal, survey, or demo
  papers and answers reviews, tracing each empirical claim to an artifact
  and each citation to a retrieved record.
* `fact-check/` - Checks a document claim by claim against retrieved
  sources, with quotes behind every verdict, and changes nothing until you
  approve each correction.
* `git-commit/` - Drafts and reviews Conventional Commits messages, and can
  commit and push in one step.
* `humanize/` - Rewrites AI-sounding prose so it reads like its writer,
  keeping every claim's original strength.
* `lit-review/` - Produces a literature review in which every citation
  traces to a paper retrieved from OpenAlex, arXiv, or Crossref, never
  memory.
* `peer-review/` - Reviews a paper the way an adverse referee would,
  pressing on claims, design, analysis, limitations, and novelty.
* `pl-theorist/` - Brings a programming-languages theorist's discipline to
  design, code, review, and tests, tuned per language.
* `ponder/` - Answers an open question and shows its work, sourcing every
  load-bearing claim and testing the strongest rival explanation.
* `ponytail/` - Forces the laziest solution that works: standard library and
  native features before custom code or new dependencies.
* `read-pdf/` - Extracts text and metadata from a PDF and answers questions
  about it with page-cited evidence, without OCR.
* `reframe/` - Turns a planning discussion into a testable direction
  judgment with costed routes and the evidence that would prove it wrong.
* `search-web/` - Searches the web, Wikipedia, and the scholarly record when
  the harness has no search tool, and pulls the readable text out of a page.
* `setup-env/` - Provisions a project's development toolchain in userspace,
  with no sudo, no docker, and nothing assumed present but uv.
* `summon/` - Hands work to another agent: whether to delegate, what to tell
  the delegate, how to keep parallel agents apart, and how to judge what
  comes back.
* `thematic-analysis/` - Develops themes from qualitative text under one
  named school, each theme backed by verbatim extracts and counts.

## Automated gate

`.github/workflows/gate.yml` runs on every push to `main` and on manual
dispatch. It repairs what is mechanical, commits the repair to `main` as one
GitHub-signed `style:` commit, and fails only on findings no fixer can
settle. Run the same chain before pushing and the gate has nothing to do:

```bash
.github/check.sh
```

| Repaired automatically | Reported for a human |
| --- | --- |
| ruff's safe lint fixes and formatting (policy in `ruff.toml`) | Lint findings ruff cannot fix safely |
| A missing, wrong, orphaned, or legacy-shaped hub or vendor alias | A skill directory with no `SKILL.md` |
| Frontmatter `name`, `license`, or field-order drift | Frontmatter judgments: a missing or overlong description, non-spec fields, descriptions totalling over the budget |
| Manifest `name` fields and the declared skill list | A missing or unreadable plugin manifest |
| Skill entries out of alphabetical order in this file and `README.md` | A skill missing from either list, or an entry naming no skill |
| Markdown prose off the 76-column wrap; code, tables, and markup keep their width | |
| | An alias path occupied by real content, which no repair may destroy |
| | An em-dash (U+2014), whose replacement is a judgment |
| | Skill Python outside its `scripts/` member, or a manifest off `scripts/pyproject.toml` |
| | A workspace member whose Python redefines a kernel symbol |

Rules live in `.github/gate/src/btm_repo_gate/rules/`, one function each. A
rule returns findings, and a finding carries its repair or `None`; that
field alone decides which column above it lands in, so adding a rule never
touches the driver or the workflow. Never silence a ruff rule
repository-wide: put a `# noqa: RULE` carrying its reason on the line that
earns it.

## Authoring and editing skills

* Before creating or modifying any skill, load
  [author-skill/SKILL.md](author-skill/SKILL.md) and follow it. It holds
  every authoring rule: frontmatter, registry, redirects, the writing
  standard, and persona verbs; its `scripts` reference holds the rules for
  bundled scripts.
* When adding or renaming a skill, create it at `<skill-name>/SKILL.md` in
  the repository root and update the skill lists in `AGENTS.md` and
  `README.md` in the same change. The gate writes the alias symlink and the
  manifest entry.
* Edit skills here. NEVER edit the vendored copy inside a downstream
  project's `.github/skills` submodule; the next submodule update discards
  it.
* NEVER use em-dash characters (U+2014) anywhere in this repository; use a
  hyphen, a comma, a colon, or restructure the sentence.
* Markdown prose wraps at 76 columns. The gate reflows paragraphs and list
  items and leaves frontmatter, code, tables, and XML blocks as written.
* A convention change is total: the same change rewrites every statement,
  example, and docstring of the old convention.
* NEVER add secrets, credentials, or project-internal data to a skill; these
  files are public and vendored verbatim into many repositories.

## Commit conventions

Follow [git-commit/SKILL.md](git-commit/SKILL.md): Conventional Commits,
imperative subject ≤70 characters, scope derived from the change (here, the
skill directory name, e.g. `feat(author-skill): ...`). Drop the scope for
repository-wide changes.

## How downstream projects consume this repository

A consumer adds this repository as a submodule at `.github/skills`, aliases
`.claude/skills` and `.agents/skills` to it (a submodule cannot create
entries in its parent), and copies `sync-skills.example.yml` to
`.github/workflows/sync-skills.yml` as a real file, since GitHub Actions
ignores symlinks there. A change here reaches a project when that project
bumps its submodule pointer; the README carries the recipe.
