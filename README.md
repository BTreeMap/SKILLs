# SKILLs

A central, project-agnostic library of reusable [agent skills](https://agentskills.io)
for LLM coding agents. Each skill is a self-contained `SKILL.md` that an agent can
load on demand to perform a task consistently - commit messages, skill authoring,
and more.

Skills here are deliberately **neutral**: they capture reusable procedures and
conventions, never a single project's identity, so the same skill works across many
unrelated repositories.

## Available skills

| Skill | Purpose |
| --- | --- |
| [git-commits](git-commits/SKILL.md) | Enforces Conventional Commits format and best practices for commit messages, with lite/full/ultra effort levels. |
| [authoring-skills](authoring-skills/SKILL.md) | Distills a worked procedure into a reproducible skill; the meta-skill for writing every other skill here. |
| [caveman-protocol](caveman-protocol/SKILL.md) | Compresses agent output when token economy is explicitly requested. |
| [pdf-reading](pdf-reading/SKILL.md) | Extracts and analyzes PDF text and metadata with pypdf without modifying PDF files. |
| [strategic-reframing](strategic-reframing/SKILL.md) | Challenges incremental framing and produces a bold, testable target direction. |
| [pl-theorist-refactoring](pl-theorist-refactoring/SKILL.md) | Refactors code into cost-aware, language-idiomatic functional style. |
| [ponytail](ponytail/SKILL.md) | Forces the laziest working solution: YAGNI, stdlib-first, minimal diffs, with lite/full/ultra intensity and review/audit/debt/gain/help modes. |

## How it works

Each skill lives in its own kebab-case directory with a `SKILL.md` file. The YAML
frontmatter (`name` and `description`) is the routing surface an agent reads to
decide whether to load the full body - so descriptions state both *what* the skill
does and *when* to use it. The body is structured Markdown the agent follows when
the skill is selected.

Headers conform strictly to the [Agent Skills](https://agentskills.io) open
standard - only spec fields (`name`, `description`, `license`, `compatibility`,
`metadata`, `allowed-tools`), so every skill loads in any spec-compliant agent
and uploads without hard errors. The full protocol lives in
[AGENTS.md](AGENTS.md).

## Using these skills in your project

Add this repository as a git submodule mounted at `.github/skills` and expose the
same skills to Claude:

```bash
git submodule add https://github.com/BTreeMap/SKILLs.git .github/skills
mkdir -p .claude .github/workflows
ln -s ../.github/skills .claude/skills
cp .github/skills/sync-skills.example.yml .github/workflows/sync-skills.yml
git add .claude/skills .github/workflows/sync-skills.yml
git commit -m "chore: Add agent skills submodule with scheduled auto-sync"
```

The `cp` line opts you into the auto-updating norm: the copied workflow bumps
the submodule pointer to the upstream tip twice a day (details below). It MUST
be a hard copy: GitHub Actions does not resolve symlinks under
`.github/workflows`, so a symlinked workflow file is silently ignored.

Clone consuming projects with submodules included:

```bash
git clone --recurse-submodules <your-repo-url>
# or, on an existing checkout:
git submodule update --init --recursive
```

## Keeping the submodule current

The setup above already installs [sync-skills.example.yml](sync-skills.example.yml)
as `.github/workflows/sync-skills.yml` (do this now if you skipped the `cp`
step, and keep it a real copy, not a symlink). Twice a day it
fast-forwards the `.github/skills` gitlink to the upstream tip on each branch
you list (default: `main` and `master`) and pushes one `chore:` commit per
branch; branches that are missing, unconfigured, or already current are
skipped, and anything else that goes wrong surfaces as a warning rather than
a failed run. The upstream is whatever each branch's `.gitmodules` records -
a fork of this repository with the same layout works unchanged, or can be
forced with the `upstream-url`/`upstream-ref` inputs.

The caller is a thin shell - schedule plus a `contents: write` grant - around
the reusable workflow in
[.github/workflows/sync-skills.yml](.github/workflows/sync-skills.yml), which
is built for containment: checkout keeps no credentials
(`persist-credentials: false`), only the final push step ever sees the token,
and the submodule is never cloned - its tip is read with `git ls-remote` and
recorded directly into the index as a gitlink, so no submodule code or git
hook can run. If your organization restricts third-party actions, allowlist
`BTreeMap/SKILLs/.github/workflows/sync-skills.yml@main`.

Pull the latest skills and record the new pointer:

```bash
git submodule update --remote .github/skills
git commit -m "chore(skills): bump skills submodule"
```

Then point your agent configuration (e.g. `AGENTS.md`) at the relevant skill, for
example: `.github/skills/git-commits/SKILL.md`.

## Skill discovery aliases

The root skill directories are canonical. This repository also exposes each one
through a committed `.github/skills/<skill-name>` relative symlink, so agents that
scan either location see the same source without duplicated files. `.claude/skills`
is a relative symlink to `.github/skills`, allowing Claude to use that same set.

Git preserves these symlinks on Linux and macOS. On Windows, enable Developer Mode
or configure Git to create symlinks before cloning. Do not replace an alias with a
copy: edit the root skill directory instead.

When this repository is mounted as a submodule at a consuming repository's
`.github/skills`, the submodule cannot create a `.claude/skills` entry in its parent.
The setup sequence above creates and commits that parent-level alias.

The link target is relative to `.claude/skills`; it remains valid when the
repository moves or is cloned elsewhere.

## Contributing a skill

Read [authoring-skills/SKILL.md](authoring-skills/SKILL.md) first - it defines the
required structure and a validation checklist. In short:

1. Create a kebab-case directory with a single `SKILL.md`.
2. Add frontmatter with a `name` matching the directory and a `description` that
   states what the skill does and when to invoke it.
3. Write a reproducible, project-agnostic procedure: deterministic steps, isolated
   examples, a Gotchas section, and a validation checklist.
4. Keep it within context economy (~500 lines); offload bulky references to sibling
   files.
5. Commit the discovery alias and listings in the same change:
   `ln -s ../../<skill-name> .github/skills/<skill-name>`, plus a row in this
   README's table and a bullet in [AGENTS.md](AGENTS.md).

Repository conventions for agents are documented in [AGENTS.md](AGENTS.md). Commit
messages follow the [git-commits](git-commits/SKILL.md) skill.

## License

[MIT](LICENSE)
