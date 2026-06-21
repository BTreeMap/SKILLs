---
name: authoring-skills
description: Distills a completed or in-progress procedure (a debugging session, a setup walkthrough, a sequence of tool calls, or any "how I did it" narrative) into a reproducible SKILL.md that a fresh agent with no prior context can follow to reproduce the outcome. Use this skill whenever drafting a new skill, reviewing an existing one for compliance, or capturing a worked process so it can be replayed in future projects.
---

# Authoring Skills

A skill is a reproducible procedure written for an agent that has **none of the
context you have right now**. Your job when authoring one is distillation: take a
messy, real run — full of dead ends, one-off values, and narration — and compress
it into the minimal, deterministic, generalizable path that lets a fresh agent
re-achieve the result.

This skill governs how every other skill in this repository is written. It is
project-agnostic: capture conventions from the source material, never bake one
project's identity into a reusable skill.

## 1. When To Use

Use this skill when you need to:

* Turn a finished task (you just debugged, configured, or built something) into a
  document another agent can replay.
* Author a brand-new `SKILL.md`, or review/refactor an existing one.
* Generalize a one-off procedure so it applies to future, unrelated projects.

Do NOT use this skill to write end-user product documentation, tutorials aimed at
humans, or API reference material. Those have different audiences and contracts.

## 2. The Core Mental Model

You are converting **history** (what happened, once) into a **procedure** (what to
do, every time). These are not the same document.

* History contains backtracks, abandoned attempts, and incidental specifics.
* A procedure contains only the verified path, generalized and parameterized, plus
  the lessons that prevent an executor from repeating the dead ends.

The single most important question to ask of every sentence you write:

> "Would a competent agent with zero memory of the original session need this to
> reproduce the result — or already know it?"

If the model already knows it (standard syntax, universal best practice), delete
it. If it is essential and non-obvious (a project convention, a non-default flag, a
trap that cost you an hour), keep it.

## 3. Anatomy of a Skill

Every skill MUST live in its own directory named in kebab-case, containing a file
named exactly `SKILL.md`, and MUST begin with YAML frontmatter:

```yaml
---
name: <kebab-case, matches the directory, lowercase, hyphens only>
description: <what the skill does AND when to invoke it; this is the routing
  surface the orchestrator reads before loading the body — be specific>
---
```

* **`name`**: Lowercase alphanumeric and hyphens only. Prefer a gerund or a clear
  noun phrase (`writing-runbooks`, `database-migrations`). NEVER use vague names
  like `utils`, `helpers`, or `misc`.
* **`description`**: State both the action and the trigger conditions. A vague
  description is the most common reason a skill never fires. It is NOT a summary of
  the body — it is the selector that decides whether the body is ever loaded.

The body is Markdown. Use `##`/`###` headings to separate rules, context, and
validation. Wrap every example, template, or data payload in XML-style tags (e.g.
`<example>...</example>`) so the model never mistakes illustrative content for an
operational instruction.

## 4. Procedure: Plan, Distill, Validate

Follow these phases in order. Do not start writing prose before you have separated
signal from noise.

### Phase 1 — Gather the raw material

Anchor the skill in what actually happened, not in what you imagine should happen.
A skill invented from generic knowledge will be vague and wrong; a skill distilled
from a real run captures the true commands, flags, and failure modes.

* Collect the concrete steps: the commands run, files touched, decisions made, and
  errors hit. When the source is the current session, reconstruct the verified path
  from the actual tool calls — do NOT guess at steps you did not perform.
* Note every point where you backtracked or were surprised. Those become the
  Gotchas section; they are often the highest-value content in the skill.

### Phase 2 — Distill and generalize

* **Keep the verified path only.** Remove abandoned attempts from the main
  procedure. Demote their lessons to Gotchas.
* **Strip incidental specifics.** Replace one-off literals — absolute paths,
  hostnames, IDs, project names — with named parameters or a short "derive this
  from the repo" instruction. A reusable skill MUST NOT hardcode a single project's
  values.
* **Preserve rationale, not mechanics.** Record *why* a non-obvious choice was made
  (the "what" and "why"); omit step-by-step "how" that is already visible in the
  commands themselves.
* **Make every step deterministic.** Name the exact tool, flag, and expected
  result. Replace "find the config" with the exact search command. Express
  decisions as explicit branches ("if X, do A; if Y, do B"), never as vague
  judgment calls.
* **Honor context economy.** Aim to stay under ~500 lines. If the skill needs bulky
  reference data, move it to a sibling file and instruct the agent to read it on
  demand rather than inlining it.

### Phase 3 — Validate

Before presenting the skill, silently run the Validation Checklist in Section 6.
Then apply the reproduction test in Section 5. Fix every failure before finishing.

## 5. The Reproduction Test

Reread the finished skill while pretending you have never seen the original work.
The skill passes only if, from the document alone, you could execute the procedure
and reach the same outcome without asking a clarifying question. If any step
assumes knowledge that exists only in your head, make it explicit or parameterize
it.

## 6. Gotchas

These are the recurring failure modes when authoring skills:

* **Narrating history instead of writing a procedure.** "First I tried X, then it
  broke, so I…" belongs in Gotchas at most. The main path is the final, working
  sequence.
* **A weak description.** If the skill never triggers, the cause is almost always
  the `description`, not the body. Fix the routing surface first.
* **Hardcoding one project's reality.** Scopes, paths, package names, and service
  names from the originating project leak in and make the skill useless elsewhere.
  Parameterize or derive them.
* **Over-explaining the obvious.** Teaching standard language syntax or universal
  best practice wastes the context budget and buries the project-specific signal.
* **Instruction bleed.** Example text that is not fenced or XML-wrapped gets read as
  a command. Isolate all examples.
* **Vague imperatives.** "Handle errors appropriately" is not executable. Name the
  condition and the action.

## 7. Validation Checklist

Verify every item before finalizing a skill:

* [ ] Directory is kebab-case and contains a file named exactly `SKILL.md`.
* [ ] Frontmatter has `name` (matching the directory) and a `description` that
      states both what the skill does and when to invoke it.
* [ ] The body is a reproducible procedure, not a narrative of one past session.
* [ ] No single project's identity is hardcoded; project-specific values are
      parameterized or derived from the repository.
* [ ] Every step is deterministic: exact tools, flags, and expected results, with
      explicit branches for decisions.
* [ ] All examples, templates, and payloads are fenced or XML-wrapped.
* [ ] A Gotchas section captures the non-obvious traps and abandoned dead ends.
* [ ] The skill passes the reproduction test in Section 5.
* [ ] No placeholder text (e.g. `<...>`, `TODO`) remains outside intentional
      templates.
* [ ] Total length respects context economy (~500 lines); bulky references are
      offloaded to sibling files.

## 8. Example

<example type="distillation">
A raw session: "I tried bumping the dependency directly, the lockfile drifted and
CI failed, then I realized this repo regenerates the lock via `make lock`, so I ran
that and CI passed."

Distilled into a procedure step plus a gotcha:

```text
## Procedure
3. Regenerate the lockfile with the repository's own command (do NOT hand-edit
   the lock). Run `make lock`, then commit both the manifest and the lockfile
   together.

## Gotchas
* Editing the lockfile by hand, or letting it drift from the manifest, fails CI.
  The lock is generated; always regenerate it with `make lock`.
```

The one-off panic is gone; the verified path and the lesson that prevents the
mistake remain, and the only project-specific token (`make lock`) is presented as
"the repository's own command" so the reader knows to confirm it.
</example>
