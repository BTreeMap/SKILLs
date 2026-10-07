---
name: author-skill
description: >-
  Turns a procedure or task history into a SKILL.md another agent can follow
  with no memory of the original session, and reviews existing skills
  against the Agent Skills standard. Use when asked to create, refactor,
  review, or distill a skill.
license: MIT
metadata:
  argument-hint: "[skill name or path]"
---

# Author Skill

Distill a procedure into a `SKILL.md` a fresh agent can follow, and review
an existing skill against the Agent Skills standard. Minimize loaded tokens
while preserving reliable execution; correctness, safety, and clarity
outrank brevity.

## Registry

| Name | Path |
| --- | --- |
| `scripts` | [references/scripts.md](references/scripts.md) |

Before writing or reviewing a skill that bundles code, load `scripts`.

## Frontmatter

Restrict the header to Agent Skills spec fields (agentskills.io), in this
order; put any agent-specific hint under `metadata` as a quoted string.

| Field | Rule |
| --- | --- |
| `name` | Equals the directory of `<name>/SKILL.md`: 1-64 lowercase letters, digits, hyphens, none leading, trailing, or doubled. A task skill is the imperative a user would speak (`fact-check`); a persona is one noun (`caveman`). No filler noun (`-helper`). |
| `description` | `>-` folded, 1-1024 characters, third person: what the skill does and delivers, one or two guarantees a reader can hold it to, its search terms; then triggers starting "Use when". Names no internal record, phase, file, library, verb, or level. 100 to 150 tokens; the library's descriptions total under 7,000 characters. |
| `license` | `MIT`. |
| `compatibility` | Only for runtimes, system packages, network access, or a full repository checkout; at most 500 characters. |
| `metadata.argument-hint` | The invocation grammar, spelled here only: one bracket group per independent choice in typing order (`"[lite|full|ultra] [design|review|help]"`); a skill with no vocabulary names its subject (`"[file-or-section]"`). Update on any verb, level, or mode change. |
| `allowed-tools` | Last, only when a harness needs it. |

## Layout

Order sections by execution, each heading naming a task, decision, contract,
or reference topic.

1. Opening paragraph under the title: one to three sentences, the task and
   the deliverable, naming no sibling.
2. `## Registry`, first `##`, only where files are bundled: one row per
   file, name to path. A name is the basename without `.md`, in backticks; a
   file no run loads says so in its first line.
3. `## Redirects`, only where something is redirected: one bullet per task,
   the condition, a colon, then the sibling in slash form or, with no
   sibling, the plain action to take instead. Where two personas pair verb
   for verb, route from the spine per verb ("`/pl-theorist`, same verb").
4. Invariants, procedure, reference material, gotchas, completion checks.

* Keep `SKILL.md` near 500 lines of core contracts, routing, and
  indispensable judgments; the cap never moves out text every run reads.
  Move bulky material some run skips to `references/`, loaded under a stated
  condition, one level deep: a reference cites a sibling by name and never
  links to it.
* Split a file out only where the split pays: it costs a Registry row, a
  load sentence, headings, and cross-citations that can drift, and pays only
  when some invocation never loads the file or a long run loads it late
  enough that reloading it near its use beats carrying it from the start.
  Fold into the spine what every run loads at its start, and merge files
  that always load together at the same moment. Keep a split only where it
  spares some run text it does not need, judged by expected words loaded per
  invocation.
* Define each topic in one file. Where a second file would restate a value,
  threshold, or enumeration, cite the owner instead, and only when that
  owner is in context when the copy is read (the spine, or a kernel loaded
  with it); a file loaded alone keeps its own copy.
* Outside the Registry, use a name alone, as the object of a word that says
  what it is ("load `brief`", "the template in `report`"); keep literal
  paths only in runnable commands.
* When a table is keyed by verb, mode, or level and each row loads the file
  of that name, say so once above the table and drop the column, naming any
  row that deviates.
* Number a list when order matters; bullet it otherwise; use a table only
  when shared columns make lookup cheaper.
* Command a sibling skill's capability in slash form as an unconditional
  step ("read PDFs with `/read-pdf`"). Answer an environment condition (no
  network, unreachable file) with a fallback chain that names the degraded
  path.
* Use an example only to resolve a likely mistake; make every positive
  example conform to this standard and label an intentional counterexample.
* Wrap every example, template, and payload in XML from this closed set; a
  tag names the kind of block and `for` carries the subject. Write tags in
  kebab-case, leave a blank line before an opening tag, and open `<![CDATA[`
  on its own line inside a tag whose payload a formatter would rewrap.

| Container | Children |
| --- | --- |
| `directives` | `rule` |
| `checklist` | `item` |
| `procedure` | `phase`, `step` |
| `examples` | `example` holding `before`, `after`, `variant`, `context` |
| `template`, `commands` | none |

## Content

* Carry only what changes what the agent does: the contract (what a verb
  takes, returns, and refuses), the routing, and the judgments the agent
  owns. Leave out which library or endpoint implements a verb, policy and
  licensing framing, and anything the script states at the moment it matters
  (a `signal:` line, a rejection hint, a `next` field).
* Define success by observable outputs or checks.
* State a prerequisite before the step that needs it; state branches,
  fallbacks, and stopping conditions at the step they apply to.
* Give judgment criteria, not persona labels such as "expert". Mark a
  recommendation apart from a guarantee and an observation apart from a
  requirement. Name a required assumption, or say how the agent resolves it.
* Parameterize every project-specific value (paths, scopes, hostnames,
  service and package names) or derive it from the consuming repository at
  runtime. Tie a skill to a language, framework, or layout only when that
  ecosystem is its purpose, stated in the description.
* When distilling from a session, keep only verified tool calls and
  successful commands; write the current rule, and keep a failure only as an
  actionable gotcha.

## Writing

* Draft under `/caveman lite`; sweep with `/humanize` and treat its patterns
  as signals.
* Write direct, neutral instructions. Lead with the verb; put a condition
  before its dependent action ("If X, do Y"). Name the actor where
  responsibility could be ambiguous; keep "it", "this", and "the latter"
  locally unambiguous.
* Split obligations that execute independently; keep clauses together when
  splitting would hide their dependency. Use grammatical sentences in prose;
  use a fragment only in a label, table, or checklist.
* Use one term for one concept; define an unfamiliar term at first use;
  introduce a label only when reusing it shortens the procedure. Mark
  obligation with one word each: "must" for a requirement, "may" for
  permission, "can" for a capability.
* Make each sentence supply an action, a condition, a decision rule,
  necessary context, or a useful example. Delete greetings, praise,
  wind-ups, heading restatements, process history, summaries that add no
  check, slogans, unsupported rankings, and claims of uniqueness. Replace a
  slogan or metaphor with the action or condition it implies. Keep a
  contrast only where it separates plausible choices or enforces a boundary.
  Keep rationale only where it changes a decision or prevents a likely
  error.
* State the pattern to follow; name a banned form only where it must be
  recognized (secrets, em-dashes, spec violations). Never emit an em-dash
  (U+2014).
* Remove unnecessary words before shortening meaningful ones; invent no
  abbreviation and drop no grammar as a presumed saving. Preserve: negation,
  exception, exclusivity, scope, necessary versus sufficient, uncertainty
  and evidential strength, numbers, units, thresholds, execution order,
  stopping conditions, permissions, irreversible-action boundaries,
  commands, identifiers, literals, schemas, error strings, quotations,
  intentional bad examples. Cut only empty hedges.
* Reject a shorter rewrite when a fresh, less capable agent would have to
  guess. Claim a token reduction only when measured with a named tokenizer;
  report word and character counts as such.

## Delegation

Hand work to another agent through `/summon`, supplying only what its caller
table asks for: the unit one delegate closes, the record it receives, the
rules of this skill that unit can break, the return shape by registered
name, the cap, and the gate the lead admits the return through. Leave mode,
brief shape, bounds, sizing, trust, and review of the return to summon;
carry no worker prompt, delegation threshold, or cost figure.

## Persona verbs

Dispatch a persona through verbs: by explicit verb, then by unambiguous
request shape, then by the persona's declared default verb. Implement from
this table the verbs the lens can honor, each with the table's contract in
every persona; vary only the lens.

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

* Apply changes only in `build` and `refactor`; keep every other verb
  read-only.
* In a read-only verb, name what is outside the lens and route it to the
  sibling skill in slash form.
* Load one verb file per invocation, registered under the verb's name.
* Add verbs beyond the core freely (`ponytail` carries `debt` and `stats`);
  give a verb name one meaning across the library, and reuse a name another
  skill already carries with that skill's meaning.
* Offer levels only where the lens needs them: `lite | full | ultra` (advise
  / enforce, the default / maximalist). Persist a level until changed and
  keep it orthogonal to verbs.

## Output

Before finalizing, check the edit for lost meaning, altered scope or order,
weakened gates, and broken references. When a skill's value is a judgment (a
persona, a review, a reading), also test the draft: brief a delegate through
`/summon` with the draft and a held-out case, score the return against
criteria fixed in advance, and change the text until it holds. Keep scores
and runs out of the skill. Then write the finished `SKILL.md` into the
codebase, or return it as one raw Markdown block with nothing around it.

<checklist>
  <item>Frontmatter holds only spec fields in canonical order; `name` matches the directory; the description follows the capability-then-"Use when" form and the library's descriptions total under 7,000 characters; the argument hint matches the body's verbs, levels, and modes.</item>
  <item>The opening paragraph names task and deliverable; Registry is the first `##`; Redirects follows it with condition-colon-destination bullets.</item>
  <item>Every bundled file is cited by registered name; examples, templates, and payloads sit in closed-set XML tags.</item>
  <item>Every bundled file spares some invocation text it does not need; what every run loads at its start sits in the spine, and files that always load together are one file.</item>
  <item>Every step names exact tools, flags, inputs, outputs, and stopping conditions; project-specific values are parameterized or derived.</item>
  <item>Delegation, where any, goes through `/summon` with only the caller's unit, record, rules, return shape, cap, and gate.</item>
  <item>Each sentence supplies an action, condition, rule, context, or example; a `/humanize` sweep finds no filler; negations, numbers, literals, and boundaries survived every cut.</item>
  <item>Any bundled script follows `scripts` on responsibility placement, heuristic signals, skipped-check reporting, the member layout, and the request-origin chain, and no `SKILL.md` names `BTM_USER_AGENT` or `BTM_CONTACT`.</item>
  <item>Gotchas hold non-obvious traps; no placeholder text remains outside templates.</item>
  <item>A fresh agent can execute the skill from its text alone, with no session memory or clarifying question.</item>
</checklist>

## Examples

<examples>

  <example for="distillation">
    <context>Converting raw history into a reproducible step.</context>
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
    <context>Writing a routing description.</context>
    <before>This skill helps format python code using black and flake8.</before>
    <after>Formats and lints Python code to the project's configured style, changing no behavior. Use when asked to format Python, lint a file, or fix style warnings.</after>
  </example>

  <example for="parameterization">
    <context>Removing incidental project specifics.</context>
    <before>Run the build script located at `/users/joe/projects/manifold/scripts/build.sh`.</before>
    <after>Run the build script at `<repository-root>/scripts/build.sh`.</after>
  </example>

  <example for="xml-isolation">
    <context>Fencing a payload so it reads as data.</context>
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
