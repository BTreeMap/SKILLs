# AGENTS.md

This repository is a central, project-agnostic library of reusable agent skills.
Each skill is a self-contained `SKILL.md` describing a procedure an LLM agent can
load and execute. Downstream projects consume this repository as a git submodule
mounted at `.github/skills`, so **every skill here MUST be neutral and reusable
across unrelated projects**.

This file is the entry point. Load linked skills just in time — only when the task
needs them — to keep context lean.

## Repository shape

* One directory per skill, named in kebab-case, containing a file named exactly
  `SKILL.md`. The directory name MUST match the skill's `name` in its frontmatter.
* `LICENSE` — MIT.
* There is no build system, dependency manifest, or test runner. This repository is
  documentation that other agents read; treat correctness as an editorial property,
  not a compiled one.

Current skills:

* `git-commits/` — Conventional Commits standard for commit messages.
* `authoring-skills/` — how to distill a procedure into a reproducible skill (the
  meta-skill governing this repository).

## Authoring and editing skills

* Before creating or modifying any skill, load
  [authoring-skills/SKILL.md](authoring-skills/SKILL.md) and follow it. It defines
  the required structure, the distillation workflow, and the validation checklist.
* A skill MUST be a reproducible procedure, not a narrative of one past session,
  and MUST NOT hardcode any single project's identity (paths, scopes, service or
  package names). Parameterize project-specific values or instruct the agent to
  derive them from the consuming repository.
* Keep each skill within context economy (~500 lines). Offload bulky reference
  material to sibling files the agent reads on demand.
* Edit skills **here**, in this repository. NEVER edit the vendored copy inside a
  downstream project's `.github/skills` submodule; those changes are discarded on
  the next submodule update.

## Commit conventions

Follow [git-commits/SKILL.md](git-commits/SKILL.md): Conventional Commits, imperative
subject ≤70 characters, scope derived from the change (here, the skill directory
name, e.g. `feat(authoring-skills): ...`). Drop the scope for repository-wide
changes.

## How downstream projects consume this repository

Skills are added as a submodule:

```bash
git submodule add https://github.com/BTreeMap/SKILLs.git .github/skills
```

Consumers clone with `--recurse-submodules` (or run
`git submodule update --init --recursive` on an existing checkout), and refresh
with `git submodule update --remote .github/skills` followed by committing the
bumped pointer. Keep this in mind: a change here only reaches a project after that
project bumps its submodule pointer.

## Boundaries

* NEVER add secrets, credentials, or project-internal data to a skill; these files
  are public and vendored verbatim into many repositories.
* NEVER make a skill depend on a specific language, framework, or directory layout
  unless the skill's whole purpose is that ecosystem — and say so in the
  `description`.
* When in doubt about a project-specific value, write the skill to discover it from
  the repository at runtime rather than assuming it.
