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

## Frontmatter

Restrict the header to Agent Skills spec fields (agentskills.io), in this
order, with `allowed-tools` last and only when a harness needs it; put any
agent-specific hint under `metadata` as a quoted string.

| Field | Rule |
| --- | --- |
| `name` | Equals the directory of `<name>/SKILL.md`: 1-64 lowercase letters, digits, hyphens, none leading, trailing, or doubled. A task skill is the imperative a user would speak (`fact-check`); a persona is one noun (`caveman`). No filler noun (`-helper`). |
| `description` | `>-` folded, 1-1024 characters, third person: what the skill does and delivers, one or two guarantees a reader can hold it to, its search terms; then triggers starting "Use when". Names no internal record, phase, file, library, verb, or level. 100 to 150 tokens; the library's descriptions total under 7,000 characters. |
| `license` | `MIT`. |
| `compatibility` | Only for runtimes, system packages, network access, or a full repository checkout; at most 500 characters. |
| `metadata.argument-hint` | The invocation grammar, spelled here only: one bracket group per independent choice in typing order (`"[lite|full|ultra] [design|review|help]"`); a skill with no vocabulary names its subject (`"[file-or-section]"`). Update on any verb, level, or mode change. |

## Layout

Sections in execution order; a heading names a task, decision, contract, or
reference topic.

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

* Outside the Registry, use a name alone, as the object of a word that says
  what it is ("load `brief`", "the template in `report`"); keep literal
  paths only in runnable commands.
* When a table is keyed by verb, mode, or level and each row loads the file
  of that name, say so once above the table and drop the column, naming any
  row that deviates.
* Keep `SKILL.md` near 500 lines: core contracts, routing, indispensable
  judgments. Move bulky material to `references/`, loaded under a stated
  condition, one level deep: a reference cites a sibling by name and never
  links to it.
* Number a list when order matters; bullet it otherwise; use a table only
  when shared columns make lookup cheaper.
* Command a sibling skill's capability in slash form as an unconditional
  step ("read PDFs with `/read-pdf`"). Answer an environment condition (no
  network, unreachable file) with a fallback chain that names the degraded
  path.
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
* Define success by observable outputs or checks. Mark obligation with one
  word each: "must" for a requirement, "may" for permission, "can" for a
  capability.
* State a prerequisite before the step that needs it; state branches,
  fallbacks, and stopping conditions at the step they apply to.
* Give judgment criteria, not persona labels such as "expert". Mark a
  recommendation apart from a guarantee and an observation apart from a
  requirement. Name a required assumption, or say how the agent resolves it.
* Define each topic in one file. Where a second file would restate a value,
  threshold, or enumeration, cite the owner instead, and only when that
  owner is in context when the copy is read (the spine, or a kernel loaded
  with it); a file loaded alone keeps its own copy.
* Parameterize every project-specific value (paths, scopes, hostnames,
  service and package names) or derive it from the consuming repository at
  runtime. Tie a skill to a language, framework, or layout only when that
  ecosystem is its purpose, stated in the description.
* When distilling from a session, keep only verified tool calls and
  successful commands; write the current rule, and keep a failure only as an
  actionable gotcha.
* When a skill's value is a judgment (a persona, a review, a reading), test
  the draft before finalizing: brief a delegate through `/summon` with the
  draft and a held-out case, score the return against criteria fixed in
  advance, and change the text until it holds. Keep scores and runs out of
  the skill.
* Use an example only to resolve a likely mistake; make every positive
  example conform to this standard and label an intentional counterexample.
* State a contract in a docstring or comment in at most two lines, plus one
  sentence only where a reader would otherwise make the wrong call. Put
  history in the commit.

## Writing

* Write direct, neutral instructions. Lead with the verb; put a condition
  before its dependent action ("If X, do Y"). Name the actor where
  responsibility could be ambiguous; keep "it", "this", and "the latter"
  locally unambiguous.
* Split obligations that execute independently; keep clauses together when
  splitting would hide their dependency. Use grammatical sentences in prose;
  use a fragment only in a label, table, or checklist.
* Make each sentence supply an action, a condition, a decision rule,
  necessary context, or a useful example.
* Delete greetings, praise, wind-ups, heading restatements, process history,
  summaries that add no check, slogans, unsupported rankings, and claims of
  uniqueness. Replace a slogan or metaphor with the action or condition it
  implies. Keep a contrast only where it separates plausible choices or
  enforces a boundary. Keep rationale only where it changes a decision or
  prevents a likely error.
* Use one term for one concept; define an unfamiliar term at first use;
  introduce a label only when reusing it shortens the procedure. Remove
  unnecessary words before shortening meaningful ones; invent no
  abbreviation and drop no grammar as a presumed saving.
* Preserve: negation, exception, exclusivity, scope, necessary versus
  sufficient, uncertainty and evidential strength, numbers, units,
  thresholds, execution order, stopping conditions, permissions,
  irreversible-action boundaries, commands, identifiers, literals, schemas,
  error strings, quotations, intentional bad examples. Cut only empty
  hedges.
* State the pattern to follow; name a banned form only where it must be
  recognized (secrets, em-dashes, spec violations). Never emit an em-dash
  (U+2014).
* Reject a shorter rewrite when a fresh, less capable agent would have to
  guess. Claim a token reduction only when measured with a named tokenizer;
  report word and character counts as such.
* Draft under `/caveman lite`; sweep with `/humanize` and treat its patterns
  as signals.

## Delegation

Hand work to another agent through `/summon`, supplying only what its caller
table asks for: the unit one delegate closes, the record it receives, the
rules of this skill that unit can break, the return shape by registered
name, the cap, and the gate the lead admits the return through. Leave mode,
brief shape, bounds, sizing, trust, and review of the return to summon;
carry no worker prompt, delegation threshold, or cost figure.

## Scripts

### Placement

Place each responsibility by the first row it matches.

| Responsibility | Owner | Form |
| --- | --- | --- |
| Computable exactly from bytes, no taste involved | script | invariant that hard-fails |
| A fact the agent would otherwise remember across turns (an admitted record, an identifier, a count) | script | stored once, echoed in every output |
| A verdict that follows from stored facts (a standing, a coverage, a ratio, the next legal step) | script | derived from live state on every call, never stored |
| A judgment about meaning, relevance, quality, or intent | agent | the script hands over evidence as a signal |
| An irreversible effect | agent decides | the script executes behind an explicit witness and keeps an undo where the agent's judgment could be wrong |

| Script owns | Agent owns |
| --- | --- |
| Existence, size, encoding, digests, schemas, structural equality, cross-record links | Whether a claim is supported, a paper relevant, a sentence clear |
| Session files, ledgers, minted identifiers, admitted records | Which rung, school, level, or sibling fits |
| Derived scaffolds and a `next` advisory | Every draft, rewrite, and brief; retrieved text read as data |
| HTTP with retries and rate limits; wire decoding | Weighing a signal against the user's request |
| Idempotent repairs; witnessed effects | The decision to take an irreversible step |

* Validate only what a derivation branches, joins, or counts on: closed
  vocabularies at the envelope, open payloads inside. Reject only
  unparseable transport, a dangling reference, or a value outside a
  branching vocabulary; make everything else at most an advisory. Reject a
  missing required field; admit an extra one. Return everything admitted in
  some view.
* Give the agent free memory beside the gate: a pad (`jot`, `recall`) that
  admits any JSON object or prose under a script-stamped envelope and never
  rejects content. Let a gated record cite pad ids as provenance, each
  checked to exist.
* Store a claim's inputs (support keys, probes, a watch regex, the log
  position) and derive its verdict on every read. Branch on structure (a
  variant keyed by field presence), never on a vocabulary value. Make
  append-only what must never move, such as citation markers. Surface a
  contradiction candidate (a watch hit) and leave the judgment to the agent.
* Design for the agent's loop, not a pipeline: give evolving beliefs objects
  and verbs (findings, gaps, open threads) with supersede chains; record a
  bulk judgment as one rule with its matched keys; keep a zero-result search
  in the log as evidence of absence; ship a resume view (`brief`, `status`)
  that re-enters the loop after compaction with derived verdicts, drift
  since the last snapshot, coverage, and the pad tail.
* Encode no taste as a hard rule. Put a style threshold or a file-kind guess
  in a signal that names its evidence, and let the skill text say when a
  signal stops the run (a guessed code file stops unless the user named it).
  Memoize a repeatable query and say so in a signal. Report a skipped,
  vacuous, or partial check in the output.
* Treat a consumer agent's friction report as requirements, and reproduce
  the reported failure session as the acceptance test.

### Interface

* Document the full command surface and output conventions in `SKILL.md`,
  with one line beside the commands reserving source reading for
  user-instructed troubleshooting. Show a round's calls chained with `&&`,
  so a rejection stops the chain; instruct the agent to bind the command and
  the session identifier to shell variables.
* Keep the surface uniform: one record is a batch of one; sibling record
  kinds share one plural-array container decoded row by row; every
  subcommand names its subject with the same positional and holds no ambient
  current-subject state.

| Verb | Effect, the same in every skill |
| --- | --- |
| `init` | Mint a session from two or three keywords |
| `schema` | Print every record shape |
| `note` | Admit one batch through the gate |
| `check` | Derive verdicts and the drafting scaffold from live state |
| `status` | The cheap resume view, with an advisory `next` |
| `jot`, `recall` | Write to and read from the pad |
| `clean` | Remove one target or `--all`, reporting bytes freed |

* Pass configuration as flags: closed vocabularies, counts, booleans, and
  identifiers are shell-safe. Give free-form content a named slot instead,
  generating its whole flag family from one declaration: `--<slot>` for a
  short value, `--<slot>:file PATH` for a file, `--<slot>:stdin` for the
  pipe, plus the pipe as the fallback of the one required slot, of which a
  command declares at most one: two would drain one stdin between them, so a
  second is a defect at wiring. Two provenances for one slot is a rejection
  naming both; a second slot claiming the pipe is a rejection naming the
  first, since one process has one stdin. Prose, queries, regexes, and JSON
  bodies carry characters the shell rewrites, so give a JSON body no inline
  spelling. Interpret nothing inside a value, so content needs no escape,
  and reject an empty one rather than reading it as absent. Reject a
  malformed argument line as a located exit-1 rejection.
* Mint identifiers in the script: the agent supplies two or three keywords;
  return the lowercase dash-joined slug plus a 128-bit suffix
  (`b32hexencode(os.urandom(16)).decode().rstrip("=").lower()`) and echo it
  in every output. Accept a keyword subset as recovery for a lost
  identifier, signaling and re-echoing it, and error with candidates on
  ambiguity. Keep a natural key (DOI, path) where one exists.
* Spend output freely and reject totally: run every row before committing
  anything, then return one verdict naming every problem as an imperative
  fix with its field path (`findings[0].claim`) and a hint (a did-you-mean,
  the valid vocabulary, the schema fragment), with state unchanged. Echo
  receipts (minted ids, marker tables) so the agent copies instead of
  deriving. Accept an alias an agent plausibly writes (a DOI, an arXiv id)
  with a resolution advisory.

| Exit | Meaning |
| --- | --- |
| 0 | Done; `signal:` lines on stderr are advisory and never abort a batch loop |
| 1 | Fix the input; the corrective verdict is in the output |
| 2 | Upstream failed; retry |

### State

* Decode every boundary-crossing shape with one pydantic model: a wire kind
  with variants as a union discriminated on its tag, a state file as a
  record, an untrusted value as a refined alias (`Slug`, `Doi`, `Count`).
  Subclass the kernel's frozen `Model`; set `extra="forbid"` where the agent
  writes the file and `extra="ignore"` where another writer owns it. Keep in
  the script only what a model cannot see: resolving against live state,
  minting, proving a cross-record link. Pass `uv run mypy`, strict with the
  pydantic plugin.
* Gate a destructive or hard-to-reverse effect on an exact witness (a marker
  file, an identity record, an explicit flag) and provide an undo path where
  the agent's judgment could be wrong; a user-directed `clean` needs the
  witness alone. On a digest mismatch, delete the corrupt artifact and
  hard-fail so a re-run self-heals. Keep mechanical, idempotent repairs in
  the script; leave judgment calls to the agent.

| Shape | Use |
| --- | --- |
| `Model`, serialized with `dump` | A record parsed from or written to disk |
| `TypedDict` | A view a command computes and indexes |
| `dict[str, JSON]` | The document a command emits |

| State | Location |
| --- | --- |
| Durable and light (backups, logs, sessions) | `${XDG_STATE_HOME:-$HOME/.local/state}/btm-skills/<skill-name>/` (`%LOCALAPPDATA%\btm-skills\` on Windows), in purpose-named subdirectories |
| Heavy or regenerable (downloads, toolchains, caches) | Temporary space, under a directory named for its owner |
| Logs | JSONL, one timestamped record per line, capped at write time |

### Workspace

* Make a skill that bundles Python a uv workspace member rooted at
  `scripts/`: `scripts/pyproject.toml`, `scripts/src/btm_<skill>/`,
  `scripts/tests/`, listed in the root `pyproject.toml`, with no code
  outside `scripts/`. Expose one entry point, the console command
  `btm-<skill>`, invoked through one binding,
  `R="env -u VIRTUAL_ENV uv run --project $(realpath <skill-root>/scripts) btm-<skill>"`;
  `realpath` is required because uv resolves the project path lexically and
  an alias path has no workspace root above it. Invoke no host `python` and
  no module path.
* Put logic shared across members once in the kernel `btm-corekit` under
  `.corekit/`, declared as `dependencies = ["btm-corekit"]` with source
  `btm-corekit = { workspace = true }`. Compose its gate mechanics
  (`SessionStore`, `EventLog`, `Admission` with `Pool`, `read_batch` and
  `rejection`, `wire_pad` and `wire_clean`) and add only the member's record
  semantics; redefine no kernel symbol.
* Mark a network request's origin by the first defined of `BTM_USER_AGENT`
  (sent verbatim), `BTM_CONTACT`, and `skills@oss.joefang.org`, the latter
  two in the header `btm-skills/1.0 (<skill-name>; mailto:<contact>)`.
  Disclose the contact through polite pools (an OpenAlex or Crossref
  `mailto` parameter) only from a contact-derived identity. Read the
  variables in the script alone; mention them in no skill text.

### Tests

* Scan text with `str` methods (`translate` and `split`, `find` and
  `partition`) or one compiled pattern with one class per quantifier; keep
  Python iteration proportional to tokens produced, never characters read;
  cap the length of an agent-supplied pattern. Prefer a maintained C library
  over a hand-rolled index. Benchmark realistic and adversarial inputs and
  report both.
* Audit behavior before asserting it: fix what is wrong, test the corrected
  behavior, and confirm a bug-pinning test fails against the old code. Test
  the bridge code (the decoder at an untrusted boundary, the error
  conversion, an all-or-nothing law, a witness gating destruction); test
  nothing pydantic or a closed union already proves. Move a failure to
  authoring time (an exhaustive `match`) before writing a test for it.

## Persona verbs

Dispatch a persona through verbs. Implement from this table the verbs the
lens can honor, each with the table's contract.

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
* Give the same verb the same contract in every persona; vary only the lens.
* In a read-only verb, name what is outside the lens and route it to the
  sibling skill in slash form.
* Dispatch by explicit verb, then by unambiguous request shape, then by the
  persona's declared default verb.
* Load one verb file per invocation, registered under the verb's name.
* Add verbs beyond the core freely (`ponytail` carries `debt` and `stats`);
  give a verb name one meaning across the library, and reuse a name another
  skill already carries with that skill's meaning.
* Offer levels only where the lens needs them: `lite | full | ultra` (advise
  / enforce, the default / maximalist). Persist a level until changed and
  keep it orthogonal to verbs.

## Output

Write the finished `SKILL.md` into the codebase, or return it as one raw
Markdown block with nothing around it. Before finalizing, check the edit for
lost meaning, altered scope or order, weakened gates, and broken references.

<checklist>
  <item>Frontmatter holds only spec fields in canonical order; `name` matches the directory; the description follows the capability-then-"Use when" form and the library's descriptions total under 7,000 characters; the argument hint matches the body's verbs, levels, and modes.</item>
  <item>The opening paragraph names task and deliverable; Registry is the first `##`; Redirects follows it with condition-colon-destination bullets.</item>
  <item>Every bundled file is cited by registered name; examples, templates, and payloads sit in closed-set XML tags.</item>
  <item>Every step names exact tools, flags, inputs, outputs, and stopping conditions; project-specific values are parameterized or derived.</item>
  <item>Delegation, where any, goes through `/summon` with only the caller's unit, record, rules, return shape, cap, and gate.</item>
  <item>Each sentence supplies an action, condition, rule, context, or example; a `/humanize` sweep finds no filler; negations, numbers, literals, and boundaries survived every cut.</item>
  <item>Any bundled script places each responsibility by the placement table, signals heuristics, reports skipped checks, follows the member layout, and resolves its request origin by the `BTM_USER_AGENT` / `BTM_CONTACT` / default chain with no `SKILL.md` naming those variables.</item>
  <item>Gotchas hold non-obvious traps; no placeholder text remains outside templates.</item>
  <item>A fresh agent can execute the skill from its text alone, with no session memory or clarifying question.</item>
</checklist>

## Examples

<examples>

  <example for="distillation">
    <context>Converting raw history into a reproducible step.</context>
    <before>I tried bumping the dependency directly, the lockfile drifted and CI failed, then I realized this repo regenerates the lock via `make lock`, so I ran that and CI passed.</before>
    <after>
      <step>Regenerate the lockfile with the repository's command: `make lock`.</step>
      <step>Commit the manifest and the lockfile together.</step>
      Gotcha: editing the lockfile by hand drifts CI; regenerate it.
    </after>
  </example>

  <example for="description">
    <context>Writing a routing description.</context>
    <before>This skill helps format python code using black and flake8.</before>
    <after>Formats and lints Python code with Black and Flake8. Use when asked to format Python, lint a file, or run either tool.</after>
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
