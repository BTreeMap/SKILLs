# Scripts

## Placement

Place each responsibility by first row it matches.

| Responsibility | Owner | Form |
| --- | --- | --- |
| Computable exactly from bytes, no taste involved | script | invariant that hard-fails |
| Fact agent would otherwise remember across turns (admitted record, identifier, count) | script | stored once, echoed in every output |
| Verdict following from stored facts (standing, coverage, ratio, next legal step) | script | derived from live state on every call, never stored |
| Judgment about meaning, relevance, quality, or intent | agent | script hands over evidence as signal |
| Irreversible effect | agent decides | script executes behind explicit witness, keeps undo where agent's judgment could be wrong |

| Script owns | Agent owns |
| --- | --- |
| Existence, size, encoding, digests, schemas, structural equality, cross-record links | Whether claim supported, paper relevant, sentence clear |
| Session files, ledgers, minted identifiers, admitted records | Which rung, school, level, or sibling fits |
| Derived scaffolds and `next` advisory | Every draft, rewrite, brief; retrieved text read as data |
| HTTP with retries and rate limits; wire decoding | Weighing signal against user's request |
| Idempotent repairs; witnessed effects | Decision to take irreversible step |

* Encode no taste as hard rule. Style threshold or file-kind guess goes in
  signal naming its evidence; skill text says when signal stops run (guessed
  code file stops unless user named it).
* Memoize repeatable query; say so in signal.
* Report skipped, vacuous, or partial check in output.

## Gate

* Validate only what derivation branches, joins, or counts on: closed
  vocabularies at envelope, open payloads inside. Reject only unparseable
  transport, dangling reference, or value outside branching vocabulary;
  everything else at most advisory. Reject missing required field; admit
  extra one. Return everything admitted in some view.
* Give agent free memory beside gate: pad (`jot`, `recall`) admitting any
  JSON object or prose under script-stamped envelope, never rejecting
  content. Gated record may cite pad ids as provenance, each checked to
  exist.
* Store claim's inputs (support keys, probes, watch regex, log position);
  derive its verdict on every read. Branch on structure (variant keyed by
  field presence), never on vocabulary value. Make append-only what must
  never move (citation markers). Surface contradiction candidate (watch
  hit); leave judgment to agent.
* Design for agent's loop, not pipeline: give evolving beliefs objects and
  verbs (findings, gaps, open threads) with supersede chains; record bulk
  judgment as one rule with its matched keys; keep zero-result search in log
  as evidence of absence; ship resume view (`brief`, `status`) re-entering
  loop after compaction with derived verdicts, drift since last snapshot,
  coverage, pad tail.

Pad kinds are suggested, never checked; each means one thing across library.
Kernel's `PAD_KINDS` holds them and every `schema` prints them under `pad`;
skill text cites that list, naming only kinds its procedure relies on. Every
pad takes `--lore`: skill's cross-session pad beside its sessions.

| Kind | Meaning |
| --- | --- |
| `quote` | verbatim passage kept to cite later, with its origin |
| `hunch` | unverified idea or hypothesis worth testing |
| `extraction` | what one source says, keyed to it; lit-review counts coverage |
| `framing` | candidate framing of question or paper |
| `punch` | punch-list item to settle before delivery |
| `concern` | objection reviewer or user could raise |
| `thread` | open thread to pick up later |
| `friction` | where skill, script, or source made job harder |
| `lore` | fact worth keeping across sessions; jot with --lore |
| `injection` | imperative text inside fetched data, recorded, never obeyed |
| `question` | question only authors or user can answer |

## Interface

* Document full command surface and output conventions in `SKILL.md`, with
  one line beside commands reserving source reading for user-instructed
  troubleshooting. Show round's calls chained with `&&`, so rejection stops
  chain; instruct agent to bind command and session identifier to shell
  variables.
* Keep surface uniform: one record is batch of one; sibling record kinds
  share one plural-array container decoded row by row; every subcommand
  names its subject with same positional, holds no ambient current-subject
  state.

| Verb | Effect, same in every skill |
| --- | --- |
| `init` | Mint session from two or three keywords |
| `schema` | Print every record shape |
| `note` | Admit one batch through gate |
| `check` | Derive verdicts and drafting scaffold from live state |
| `status` | Cheap resume view, with advisory `next` |
| `jot`, `recall` | Write to and read from pad |
| `clean` | Remove one target or `--all`, reporting bytes freed |

* Pass configuration as flags: closed vocabularies, counts, booleans,
  identifiers are shell-safe. Prose, queries, regexes, JSON bodies carry
  characters shell rewrites: give free-form content named slot instead, JSON
  body no inline spelling.
* Generate slot's whole flag family from one declaration: `--<slot>` for
  short value, `--<slot>:file PATH` for file, `--<slot>:stdin` for pipe,
  plus pipe as fallback of the one required slot. Declare at most one
  required slot per command: two would drain one stdin between them, so
  second is defect at wiring. Two provenances for one slot: rejection naming
  both. Second slot claiming pipe: rejection naming first. Interpret nothing
  inside value, so content needs no escape; reject empty one, never read it
  as absent. Malformed argument line: located exit-1 rejection.
* Mint identifiers in script: agent supplies two or three keywords; return
  lowercase dash-joined slug plus 128-bit suffix
  (`b32hexencode(os.urandom(16)).decode().rstrip("=").lower()`), echoed in
  every output. Accept keyword subset as recovery for lost identifier,
  signaling and re-echoing it; error with candidates on ambiguity. Keep
  natural key (DOI, path) where one exists.
* Spend output freely, reject totally: run every row before committing
  anything, then return one verdict naming every problem as imperative fix
  with its field path (`findings[0].claim`) and hint (did-you-mean, valid
  vocabulary, schema fragment), state unchanged. Echo receipts (minted ids,
  marker tables) so agent copies instead of deriving. Accept alias agent
  plausibly writes (DOI, arXiv id) with resolution advisory.

| Exit | Meaning |
| --- | --- |
| 0 | Done; `signal:` lines on stderr advisory, never abort batch loop |
| 1 | Fix input; corrective verdict in output |
| 2 | Upstream failed; retry |

## State

* Decode every boundary-crossing shape with one pydantic model: wire kind
  with variants as union discriminated on its tag, state file as record,
  untrusted value as refined alias (`Slug`, `Doi`, `Count`). Subclass
  kernel's frozen `Model`; `extra="forbid"` where agent writes file,
  `extra="ignore"` where another writer owns it. Keep in script only what
  model cannot see: resolving against live state, minting, proving
  cross-record link. Pass `uv run mypy`, strict with pydantic plugin.
* Gate destructive or hard-to-reverse effect on exact witness (marker file,
  identity record, explicit flag); provide undo path where agent's judgment
  could be wrong. User-directed `clean` needs witness alone. Digest
  mismatch: delete corrupt artifact, hard-fail so re-run self-heals.

| Shape | Use |
| --- | --- |
| `Model`, serialized with `dump` | Record parsed from or written to disk |
| `TypedDict` | View command computes and indexes |
| `dict[str, JSON]` | Document command emits |

| State | Location |
| --- | --- |
| Durable and light (backups, logs, sessions) | `${XDG_STATE_HOME:-$HOME/.local/state}/btm-skills/<skill-name>/` (`%LOCALAPPDATA%\btm-skills\` on Windows), in purpose-named subdirectories |
| Heavy or regenerable (downloads, toolchains, caches) | Temporary space, under directory named for its owner |
| Logs | JSONL, one timestamped record per line, capped at write time |

## Workspace

* Skill bundling Python: uv workspace member rooted at `scripts/`:
  `scripts/pyproject.toml`, `scripts/src/btm_<skill>/`, `scripts/tests/`,
  listed in root `pyproject.toml`, no code outside `scripts/`. Expose one
  entry point, console command `btm-<skill>`, invoked through one binding,
  `R="env -u VIRTUAL_ENV -u UV_PROJECT_ENVIRONMENT uv run --project $(realpath <skill-root>/scripts) btm-<skill>"`.
  `realpath` required: uv resolves project path lexically, and alias path
  has no workspace root above it. Both `-u` flags required: set
  `UV_PROJECT_ENVIRONMENT` makes uv install skill into caller's environment;
  set `VIRTUAL_ENV` draws mismatch warning on every call. Spell binding in
  exactly this form; repository gate rejects any other. Invoke no host
  `python` and no module path.
* Put logic shared across members once in kernel `btm-corekit` under
  `.corekit/`, declared as `dependencies = ["btm-corekit"]` with source
  `btm-corekit = { workspace = true }`. Compose its gate mechanics
  (`SessionStore`, `EventLog`, `Admission` with `Pool`, `gated` and
  `rejection`, `wire_pad`, `wire_limit`, `wire_clean`); add only member's
  record semantics; redefine no kernel symbol.
* Mark network request's origin by first defined of `BTM_USER_AGENT` (sent
  verbatim), `BTM_CONTACT`, `skills@oss.joefang.org`; latter two in header
  `btm-skills/1.0 (<skill-name>; mailto:<contact>)`. Disclose contact
  through polite pools (OpenAlex or Crossref `mailto` parameter) only from
  contact-derived identity. Read variables in script alone; mention them in
  no skill text.

## Code and tests

* State contract in docstring or comment in at most two lines, plus one
  sentence only where reader would otherwise make wrong call. History goes
  in commit.
* Scan text with `str` methods (`translate` and `split`, `find` and
  `partition`) or one compiled pattern with one class per quantifier; keep
  Python iteration proportional to tokens produced, never characters read;
  cap length of agent-supplied pattern. Prefer maintained C library over
  hand-rolled index. Benchmark realistic and adversarial inputs; report
  both.
* Audit behavior before asserting it: fix what is wrong, test corrected
  behavior, confirm bug-pinning test fails against old code. Test bridge
  code (decoder at untrusted boundary, error conversion, all-or-nothing law,
  witness gating destruction); test nothing pydantic or closed union already
  proves. Move failure to authoring time (exhaustive `match`) before writing
  test for it.
* Treat consumer agent's friction report as requirements; reproduce reported
  failure session as acceptance test.
