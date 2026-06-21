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

## How it works

Each skill lives in its own kebab-case directory with a `SKILL.md` file. The YAML
frontmatter (`name` and `description`) is the routing surface an agent reads to
decide whether to load the full body — so descriptions state both *what* the skill
does and *when* to use it. The body is structured Markdown the agent follows when
the skill is selected.

## Using these skills in your project

Add this repository as a git submodule mounted at `.github/skills`:

```bash
git submodule add https://github.com/BTreeMap/SKILLs.git .github/skills
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
