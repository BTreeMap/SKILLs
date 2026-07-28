# SKILLs

A central, project-agnostic library of reusable [agent skills](https://agentskills.io)
for LLM coding agents. Each skill is a self-contained `SKILL.md` that an agent can
load on demand to perform a task consistently — commit messages, skill authoring,
and more.

Skills here are deliberately **neutral**: they capture reusable procedures and
conventions, never a single project's identity, so the same skill works across many
unrelated repositories.

## Available skills

| Skill | Purpose |
| --- | --- |
| [git-commits](git-commits/SKILL.md) | Enforces Conventional Commits format and best practices for commit messages. |
| [authoring-skills](authoring-skills/SKILL.md) | Distills a worked procedure into a reproducible skill; the meta-skill for writing every other skill here. |
| [caveman-protocol](caveman-protocol/SKILL.md) | Compresses agent output when token economy is explicitly requested. |
| [pdf-reading](pdf-reading/SKILL.md) | Extracts and analyzes PDF text and metadata with pypdf without modifying PDF files. |
| [strategic-reframing](strategic-reframing/SKILL.md) | Challenges incremental framing and produces a bold, testable target direction. |
| [pl-theorist-refactoring](pl-theorist-refactoring/SKILL.md) | Refactors code into cost-aware, language-idiomatic functional style. |

## How it works

Each skill lives in its own kebab-case directory with a `SKILL.md` file. The YAML
frontmatter (`name` and `description`) is the routing surface an agent reads to
decide whether to load the full body — so descriptions state both *what* the skill
does and *when* to use it. The body is structured Markdown the agent follows when
the skill is selected.

## Using these skills in your project

Add this repository as a git submodule mounted at `.github/skills` and expose the
same skills to Claude:

```bash
git submodule add https://github.com/BTreeMap/SKILLs.git .github/skills
mkdir -p .claude
ln -s ../.github/skills .claude/skills
git add .claude/skills
git commit -m "chore: add agent skills submodule"
```

Clone consuming projects with submodules included:

```bash
git clone --recurse-submodules <your-repo-url>
# or, on an existing checkout:
git submodule update --init --recursive
```

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

Read [authoring-skills/SKILL.md](authoring-skills/SKILL.md) first — it defines the
required structure and a validation checklist. In short:

1. Create a kebab-case directory with a single `SKILL.md`.
2. Add frontmatter with a `name` matching the directory and a `description` that
   states what the skill does and when to invoke it.
3. Write a reproducible, project-agnostic procedure: deterministic steps, isolated
   examples, a Gotchas section, and a validation checklist.
4. Keep it within context economy (~500 lines); offload bulky references to sibling
   files.

Repository conventions for agents are documented in [AGENTS.md](AGENTS.md). Commit
messages follow the [git-commits](git-commits/SKILL.md) skill.

## License

[MIT](LICENSE)
