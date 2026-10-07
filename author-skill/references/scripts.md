# Scripts

## Placement

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

* Encode no taste as a hard rule. Put a style threshold or a file-kind guess
  in a signal that names its evidence, and let the skill text say when a
  signal stops the run (a guessed code file stops unless the user named it).
  Memoize a repeatable query and say so in a signal. Report a skipped,
  vacuous, or partial check in the output.

## Gate

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

## Interface

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
  identifiers are shell-safe. Prose, queries, regexes, and JSON bodies carry
  characters the shell rewrites, so give free-form content a named slot
  instead and a JSON body no inline spelling.
* Generate a slot's whole flag family from one declaration: `--<slot>` for a
  short value, `--<slot>:file PATH` for a file, `--<slot>:stdin` for the
  pipe, plus the pipe as the fallback of the one required slot. Declare at
  most one required slot per command: two would drain one stdin between
  them, so a second is a defect at wiring. Two provenances for one slot is a
  rejection naming both; a second slot claiming the pipe is a rejection
  naming the first. Interpret nothing inside a value, so content needs no
  escape, and reject an empty one rather than reading it as absent. Reject a
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

## State

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
  hard-fail so a re-run self-heals.

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

## Workspace

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
  (`SessionStore`, `EventLog`, `Admission` with `Pool`, `gated` and
  `rejection`, `wire_pad`, `wire_limit`, and `wire_clean`) and add only the
  member's record semantics; redefine no kernel symbol.
* Mark a network request's origin by the first defined of `BTM_USER_AGENT`
  (sent verbatim), `BTM_CONTACT`, and `skills@oss.joefang.org`, the latter
  two in the header `btm-skills/1.0 (<skill-name>; mailto:<contact>)`.
  Disclose the contact through polite pools (an OpenAlex or Crossref
  `mailto` parameter) only from a contact-derived identity. Read the
  variables in the script alone; mention them in no skill text.

## Code and tests

* State a contract in a docstring or comment in at most two lines, plus one
  sentence only where a reader would otherwise make the wrong call. Put
  history in the commit.
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
* Treat a consumer agent's friction report as requirements, and reproduce
  the reported failure session as the acceptance test.
