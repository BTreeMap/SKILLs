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
| [git-commit](git-commit/SKILL.md) | Enforces Conventional Commits format and best practices for commit messages, with lite/full/ultra effort levels and a quick-ship push verb. |
| [author-skill](author-skill/SKILL.md) | Distills a worked procedure into a reproducible skill; the meta-skill for writing every other skill here. |
| [caveman](caveman/SKILL.md) | Compresses agent output when token economy is explicitly requested, with lite/full/ultra/wenyan levels and commit/review/compress/stats/help modes. |
| [read-pdf](read-pdf/SKILL.md) | Extracts and analyzes PDF text and metadata with pypdf without modifying PDF files. |
| [reframe](reframe/SKILL.md) | Challenges incremental framing and produces a bold, testable target direction. |
| [pl-theorist](pl-theorist/SKILL.md) | Applies a PL theorist's discipline across the lifecycle - design, build, refactor, review, audit, test, teach - with per-language cost models including Bash and GitHub Actions. |
| [ponytail](ponytail/SKILL.md) | Forces the laziest working solution: YAGNI, stdlib-first, minimal diffs, with lite/full/ultra intensity and review/audit/debt/gain/help modes. |
| [fact-check](fact-check/SKILL.md) | Verifies document claims against retrieved evidence with calibrated verdicts and user-approved corrections, auto-detecting sub-agent, web, and editing capabilities. |
| [aesthete](aesthete/SKILL.md) | Designs, builds, reviews, and reworks interfaces with an HCI eye and a PL-informed component discipline: design read, dials, laws of taste, a precedence ladder for supplied design documents and palettes, a dated WCAG 2.2 accessibility floor as the single source of accessibility truth, with verbs, surface profiles, craft references, and a mechanical ship gate. |
| [setup-env](setup-env/SKILL.md) | Provisions isolated per-project dev environments entirely in userspace via a typed target algebra (python@3.12, kotlin:android, go:cgo), with micromamba, uv, publisher toolchains, and qemu-emulated foreign binaries behind transparent shims. |

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
git submodule add https://github.com/BTreeMap/SKILLs.git .github/skills 2>/dev/null \
  || git submodule update --init --remote .github/skills
mkdir -p .claude .github/workflows
ln -sfn ../.github/skills .claude/skills
cp .github/skills/sync-skills.example.yml .github/workflows/sync-skills.yml
git add .gitmodules .claude/skills .github/skills .github/workflows/sync-skills.yml
git commit -m "chore: Add or update agent skills submodule with auto-sync" \
  || echo "Already up to date."
```

The script is idempotent: on first install it adds the submodule; on re-run
the fallback updates it to the latest upstream tip instead, `ln -sfn`
replaces a stale alias without descending into it, and `cp` refreshes the
workflow to the current example (skip that line if you have customized your
copy). When nothing changed, the commit is skipped.

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
you list (default: `main` and `master`) as one GitHub-signed `chore:` commit
per branch; branches that are missing, unconfigured, or already current are
skipped, and anything else that goes wrong surfaces as a warning rather than
a failed run. The upstream is whatever URL each branch records for the gitlink -
a fork of this repository with the same layout works unchanged, or can be
forced with the `upstream-url`/`upstream-ref` inputs.

The caller is a thin shell - schedule plus a `contents: write` grant - around
the reusable workflow in
[.github/workflows/sync-skills.yml](.github/workflows/sync-skills.yml), which
is built for containment: nothing is cloned or checked out, so no submodule
code and no git hook can run; the token is split across two jobs, a read-only
one that decides what to bump and a write one that only creates the commit
and fast-forwards the ref. That commit is made through the Git Data API with
no author, committer, or signature field, which is the documented condition
for GitHub to sign a bot commit with its own key - so the bumps satisfy a
`Require signed commits` ruleset with no signing key, secret, or bypass actor
anywhere. If your organization restricts third-party actions, allowlist
`BTreeMap/SKILLs/.github/workflows/sync-skills.yml@main`.

Pull the latest skills and record the new pointer:

```bash
git submodule update --remote .github/skills
git commit -m "chore(skills): bump skills submodule"
```

Then point your agent configuration (e.g. `AGENTS.md`) at the relevant skill, for
example: `.github/skills/git-commit/SKILL.md`.

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

Read [author-skill/SKILL.md](author-skill/SKILL.md) first - it defines the
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
messages follow the [git-commit](git-commit/SKILL.md) skill.

## License

[MIT](LICENSE)
