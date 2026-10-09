---
name: author-skill
description: >-
  Turns procedure or task history into a SKILL.md another agent can follow
  with no memory of original session; reviews existing skills against Agent
  Skills standard. Use when asked to create, refactor, review, or distill a
  skill.
license: MIT
metadata:
  argument-hint: "[skill name or path]"
---

# Author Skill

Distill procedure into `SKILL.md` fresh agent can follow; review existing
skill against Agent Skills standard. Minimize loaded tokens, keep execution
reliable; correctness, safety, clarity outrank brevity.

## Registry

| Name | Path |
| --- | --- |
| `scripts` | [references/scripts.md](references/scripts.md) |

Skill bundles code: load `scripts` before writing or reviewing it.

## Frontmatter

Restrict header to Agent Skills spec fields (agentskills.io), in this order;
put agent-specific hint under `metadata` as quoted string.

| Field | Rule |
| --- | --- |
| `name` | Equals directory of `<name>/SKILL.md`: 1-64 lowercase letters, digits, hyphens; none leading, trailing, or doubled. Task skill: imperative user would speak (`fact-check`); persona: one noun (`caveman`). No filler noun (`-helper`). |
| `description` | `>-` folded, 1-1024 characters, third person: what skill does and delivers, one or two guarantees reader can hold it to, search terms; then triggers starting "Use when". Names no internal record, phase, file, library, verb, or level. 100 to 150 tokens; library's descriptions total under 7,000 characters. |
| `license` | `MIT`. |
| `compatibility` | Only for runtimes, system packages, network access, or full repository checkout; at most 500 characters. Run builds environment: name its location and size on disk. |
| `metadata.argument-hint` | Invocation grammar, spelled here only: one bracket group per independent choice, in typing order (`"[lite|full|ultra] [design|review|help]"`); skill with no vocabulary names its subject (`"[file-or-section]"`). Update on any verb, level, or mode change. |
| `allowed-tools` | Last, only when harness needs it. |

## Layout

Order sections by execution; each heading names task, decision, contract, or
reference topic.

1. Opening paragraph under title: one to three sentences, task and
   deliverable, no sibling named.
2. `## Registry`, first `##`, only where files bundled: one row per file,
   name to path. Name: basename without `.md`, in backticks. File no run
   loads says so in its first line.
3. `## Redirects`, only where something redirected: one bullet per task:
   condition, colon, then sibling in slash form or, with no sibling, plain
   action to take instead. Two personas pair verb for verb: route from spine
   per verb ("`/pl-theorist`, same verb").
4. Invariants, procedure, reference material, gotchas, completion checks.

* Keep `SKILL.md` near 500 lines: core contracts, routing, indispensable
  judgments. Cap never moves out text every run reads. Move bulky material
  some run skips to `references/`, loaded under stated condition, one level
  deep: reference cites sibling by name, never links to it.
* Split file out only where split pays. Cost: Registry row, load sentence,
  headings, cross-citations that can drift. Pays only when some invocation
  never loads file, or long run loads it late enough that reloading near use
  beats carrying it from start. Judge by expected words loaded per
  invocation. Fold into spine what every run loads at start; merge files
  always loaded together at same moment.
* Define each topic in one file. Second file would restate value, threshold,
  or enumeration: cite owner instead, only when owner is in context when
  copy is read (spine, or kernel loaded with it). File loaded alone keeps
  own copy.
* Outside Registry, use name alone, as object of word saying what it is
  ("load `brief`", "the template in `report`"); literal paths only in
  runnable commands.
* Table keyed by verb, mode, or level, each row loading file of that name:
  say so once above table, drop column, name any row that deviates.
* Number list when order matters; bullet otherwise; table only when shared
  columns make lookup cheaper.
* Command sibling skill's capability in slash form as unconditional step
  ("read PDFs with `/read-pdf`"). Answer environment condition (no network,
  unreachable file) with fallback chain naming degraded path.
* Use example only to resolve likely mistake. Every positive example
  conforms to this standard; label intentional counterexample.
* Wrap every example, template, payload in XML from this closed set; tag
  names kind of block, `for` carries subject. Tags in kebab-case; blank line
  before opening tag; open `<![CDATA[` on own line inside tag whose payload
  formatter would rewrap.

| Container | Children |
| --- | --- |
| `directives` | `rule` |
| `checklist` | `item` |
| `procedure` | `phase`, `step` |
| `examples` | `example` holding `before`, `after`, `variant`, `context` |
| `template`, `commands` | none |

## Content

* Carry only what changes what agent does: contract (what verb takes,
  returns, refuses), routing, judgments agent owns. Leave out which library
  or endpoint implements verb, policy and licensing framing, anything script
  states at moment it matters (`signal:` line, rejection hint, `next`
  field).
* Define success by observable outputs or checks.
* State prerequisite before step needing it; state branches, fallbacks,
  stopping conditions at step they apply to.
* Give judgment criteria, not persona labels ("expert"). Mark recommendation
  apart from guarantee, observation apart from requirement. Name required
  assumption, or say how agent resolves it.
* Parameterize every project-specific value (paths, scopes, hostnames,
  service and package names) or derive it from consuming repository at
  runtime. Tie skill to language, framework, or layout only when that
  ecosystem is its purpose, stated in description.
* Distilling from session: keep only verified tool calls and successful
  commands; write current rule; keep failure only as actionable gotcha.

## Writing

* Register: caveman full. Draft under `/caveman full`; sweep with
  `/humanize`, its patterns as signals.
* Drop articles and filler; fragments OK; short synonyms. Every instruction
  imperative, verb first. Condition before dependent action ("If X, do Y").
  Name actor where responsibility could be ambiguous; keep "it", "this",
  "the latter" locally unambiguous.
* Independent obligations: separate lines. Keep clauses together when
  splitting hides their dependency.
* One term per concept; define unfamiliar term at first use; introduce label
  only when reuse shortens procedure. Obligation, one word each: "must"
  requirement, "may" permission, "can" capability.
* Each sentence supplies action, condition, decision rule, necessary
  context, or useful example. Delete greetings, praise, wind-ups, heading
  restatements, process history, summaries adding no check, slogans,
  unsupported rankings, claims of uniqueness. Replace slogan or metaphor
  with action or condition it implies. Keep contrast only where it separates
  plausible choices or enforces boundary. Keep rationale only where it
  changes decision or prevents likely error.
* State pattern to follow; name banned form only where it must be recognized
  (secrets, em-dashes, spec violations). Never emit em-dash (U+2014).
* Cut unnecessary words before shortening meaningful ones; invent no
  abbreviation. Never drop not, never, no, only, except. Preserve: negation,
  exception, exclusivity, scope, necessary versus sufficient, uncertainty
  and evidential strength, numbers, units, thresholds, execution order,
  stopping conditions, permissions, irreversible-action boundaries,
  commands, identifiers, literals, schemas, error strings, quotations,
  intentional bad examples. Cut only empty hedges.
* Readability floor: sentence follower would read twice keeps longer form.
  Reject shorter rewrite when fresh, less capable agent would have to guess.
* Claim token reduction only when measured with named tokenizer; report word
  and character counts as such.

## Delegation

Hand work to another agent through `/summon`, supplying only what its caller
table asks: unit one delegate closes, record it receives, rules of this
skill that unit can break, return shape by registered name, cap, gate lead
admits return through. Leave mode, brief shape, bounds, sizing, trust,
return review to summon; carry no worker prompt, delegation threshold, or
cost figure.

## Persona verbs

Dispatch persona through verbs: explicit verb, then unambiguous request
shape, then persona's declared default verb. Implement from this table verbs
lens can honor, each with table's contract in every persona; vary only lens.

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

* Apply changes only in `build` and `refactor`; every other verb read-only.
* Read-only verb: name what is outside lens; route it to sibling skill in
  slash form.
* Load one verb file per invocation, registered under verb's name.
* Add verbs beyond core freely (`ponytail` carries `debt` and `stats`). One
  meaning per verb name across library; reuse name another skill carries
  only with that skill's meaning.
* Offer levels only where lens needs them: `lite | full | ultra` (advise /
  enforce, the default / maximalist). Level persists until changed;
  orthogonal to verbs.

## Output

Before finalizing, check edit for lost meaning, altered scope or order,
weakened gates, broken references. Skill's value is judgment (persona,
review, reading): also test draft. Brief delegate through `/summon` with
draft and held-out case, score return against criteria fixed in advance,
change text until it holds. Keep scores and runs out of skill. Then write
finished `SKILL.md` into codebase, or return it as one raw Markdown block
with nothing around it.

<checklist>
  <item>Frontmatter: only spec fields, canonical order; `name` matches directory; description in capability-then-"Use when" form; library's descriptions total under 7,000 characters; argument hint matches body's verbs, levels, modes.</item>
  <item>Opening paragraph names task and deliverable; Registry first `##`; Redirects follows with condition-colon-destination bullets.</item>
  <item>Every bundled file cited by registered name; examples, templates, payloads in closed-set XML tags.</item>
  <item>Every bundled file spares some invocation text it does not need; what every run loads at start sits in spine; files always loaded together are one file.</item>
  <item>Every step names exact tools, flags, inputs, outputs, stopping conditions; project-specific values parameterized or derived.</item>
  <item>Delegation, where any, through `/summon` with only caller's unit, record, rules, return shape, cap, gate.</item>
  <item>Each sentence supplies action, condition, rule, context, or example; `/humanize` sweep finds no filler; negations, numbers, literals, boundaries survived every cut.</item>
  <item>Any bundled script follows `scripts` on responsibility placement, heuristic signals, skipped-check reporting, member layout, request-origin chain; no `SKILL.md` names `BTM_USER_AGENT` or `BTM_CONTACT`.</item>
  <item>Gotchas hold non-obvious traps; no placeholder text outside templates.</item>
  <item>Fresh agent can execute skill from its text alone, with no session memory or clarifying question.</item>
</checklist>

## Examples

<examples>

  <example for="distillation">
    <context>Raw history to reproducible step.</context>
    <before>I tried bumping the dependency directly, the lockfile drifted and CI failed, then I realized this repo regenerates the lock via `make lock`, so I ran that and CI passed.</before>
    <after>
      <procedure>
        <step>Regenerate the lockfile with the repository's command: `make lock`.</step>
        <step>Commit the manifest and the lockfile together.</step>
      </procedure>
      Gotcha: editing the lockfile by hand drifts CI; regenerate it.
    </after>
  </example>

  <example for="description">
    <context>Routing description.</context>
    <before>This skill helps format python code using black and flake8.</before>
    <after>Formats and lints Python code to the project's configured style, changing no behavior. Use when asked to format Python, lint a file, or fix style warnings.</after>
  </example>

  <example for="parameterization">
    <context>Incidental project specifics removed.</context>
    <before>Run the build script located at `/users/joe/projects/manifold/scripts/build.sh`.</before>
    <after>Run the build script at `<repository-root>/scripts/build.sh`.</after>
  </example>

  <example for="xml-isolation">
    <context>Payload fenced so it reads as data.</context>
    <before>
      Your config file should look like this:
      { "port": 8080 }
    </before>
    <after>
      Create the configuration file from this template:
      <template for="config">
      { "port": 8080 }
      </template>
    </after>
  </example>
</examples>
