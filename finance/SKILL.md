---
name: finance
description: >-
  Keeps a private record of slow-money stock bets, each with stated odds and
  kill date, measured by deflated Sharpe, PBO, and purged walk-forward at
  the book's asset cap, sized by evidence under a ruin bound; operator
  replies in chat and sends every trade by hand. Use when setting up or
  continuing an equity research book, or recording holdings, hypotheses,
  critiques, decisions.
license: MIT
compatibility: >-
  Requires uv, git, a POSIX file lock (Linux or macOS), and a full SKILLs
  repository checkout; `start` runs `git init` outside a repository. The
  first run builds the `.venv` at the checkout root that every skill's
  scripts share, about 430 MB with this skill's numeric libraries.
metadata:
  argument-hint: "[start|load|record|measure|check] <book path>"
---

# Finance

Keep one private book per operator: record of bets on stocks held weeks to
years, each with odds, kill date, size from evidence. Agents research, write
code into book, record; operator replies to daily brief in chat and sends
every trade by hand.

## Registry

| Name | Path |
| --- | --- |
| `book` | [references/book.md](references/book.md) |
| `critique` | [references/critique.md](references/critique.md) |
| `scorecard` | [references/scorecard.md](references/scorecard.md) |
| `sources` | [references/sources.md](references/sources.md) |

Load `book` before reading or explaining one book file by hand, editing
`limits.json`, or writing any `lib/` hook. Load `scorecard` before arguing
from a scorecard or standing. Load `sources` before first `load` of a
source, or when `load` fails upstream. Never load `critique` as lead: pass
its absolute path as critique unit value.

## Redirects

- Claim in filing or article: `/fact-check`
- Filing PDF: `/read-pdf`
- Anomaly literature: `/lit-review`
- Method skill lacks: write it in book as `lib/` hook (Extensions); never
  edit skill

## Invariants

No agent, script, or cron changes these four.

1. No program in book or skill talks to broker; book holds no broker
   credential.
2. Held-out names stay hidden from agents: `measure` serves strategy code
   research names only, through `Market`; held-out list lives outside book,
   at path `start` printed; agent never reads it.
3. Ledger is append-only: `record` is only writer; correction is new line
   with `supersedes`.
4. No order without a `decision` naming the proposal, recorded before any
   fill of it; `record` refuses a fill naming a proposal with no such
   decision.

`limits.json`, `preferences.json`, `strategies/*/status` change only on
operator's word in chat, applied by lead same turn, recorded as `decision`
quoting it. Nothing under `ledger/` but `pad/` changes except through
`record`. Never hand operator a command: brief's last line names their
reply.

## Commands

```bash
R="env -u VIRTUAL_ENV -u UV_PROJECT_ENVIRONMENT uv run --project $(realpath <skill-root>/scripts) btm-finance"
U="${R% btm-finance}"
B="<book path>"
$R start "$B" [--cap N] [--universe:file names.csv] [--held-out <path>]
$R load "$B" <csv|french|edgar|tiingo|book source> [--since YYYY-MM-DD] [--config:file <config.json>]
$R record "$B" --batch:file <batch.json> | --fills:file <table> --proposal <stem>
$R measure "$B" <strategy> [--agent <name>] [--held-out] [--repeat <run id>] [--reason "<text>"]
$R check "$B" [<strategy> | <run id> | <date>] [--live | --brief | --propose <date> [--force]]
$R check --schema [record|run|strategy|pad|proposal]
PYTHONPATH="$B" $U python "$B/tools/<verb>-<object>.py" [args]
$U pytest "$B/tests"
```

| Command | Takes | Returns, refuses |
| --- | --- | --- |
| `start` | New path; `--cap` default 10000000; `--universe:file` CSV `symbol`, optional `sector`; `--held-out` path outside book | Book id, held-out path and count, `claude_md`, `git` (`init`, `inside`, `absent`), baseline hypothesis id under `new`; seeds `delegates/{bet,author,critique}.md`; commits nothing. Refuses path holding `limits.json`, held-out path inside book |
| `load` | Built-in source or `lib/sources/<name>.py`; `--since` default day after source's last; `--config:file` required for `csv` | Files with rows and sha256, `data_snapshot`; exit 1 and `integrity` incident when stored file changed or vanished |
| `record` | One batch; or pasted fills table with `--proposal <stem>`, built into `fills` batch, same gate | `accepted` per kind, `new` ids; rejection names every problem by field path, writes nothing |
| `measure` | Registered strategy; `--agent` writes `ledger/runs/<agent>.jsonl`; `--held-out` one run per promotion gate; `--repeat` reruns a line, writes nothing; `--reason` passes policy gates | `run_id`, `asset_cap`, `trial`, scorecard, `reasons` for null fields, `refused`, `imports`; exit 1 on broken cost or holding bound, line still written |
| `check` | Nothing, strategy, run id, or proposal date; `--live`; `--brief`; `--propose <date>`; `--schema` needs no book | Continue view, standing, proposal, live report, brief, or new proposal file; every output has advisory `next` |

Output: one JSON document on stdout; `signal:` lines on stderr advisory.
Exit 0 done, 1 fix input, 2 upstream failed. Content slots: `--batch:file`,
`--batch:stdin`, or pipe.

## Record batch

Write batch to file; one `record` per step. Shapes: `check --schema record`.
Kinds, in acceptance order:

```json
{
  "hypotheses": [{"kw": ["two", "words"], "strategy": "<name>", "family_id": "<key of limits.families>", "falsifier": "...", "falsifier_by": "YYYY-MM-DD", "counterparty": "...", "min_holding_days": 21, "odds": {"p_win": 0.55, "payoff": 1.5, "horizon_days": 63, "kelly_implied": 0.25}, "mechanism": "...", "sector": "...", "priced": 0.0, "implied": 0.0, "capacity": "..."}],
  "critiques":  [{"kw": ["two", "words"], "run_id": "<run id>", "blockers": ["..."], "concerns": ["..."], "by": "<agent>"}],
  "decisions":  [{"kw": ["two", "words"], "subject": "<strategy|run id|hypothesis id|proposal stem|book id>", "action": "promote|reject|override|retire|approve|close", "reason": "..."}],
  "fills":      [{"symbol": "...", "side": "buy|sell", "quantity": 10, "price": 12.5, "date": "YYYY-MM-DD", "strategy": "<name>|opening", "proposal": "<stem>|null"}]
}
```

- Copy full ids from `new`. Correct with new line holding
  `"supersedes": "<full id>"`; moving `falsifier_by` later spends a trial.
- `odds` required: `record` refuses `kelly_implied` at or below 0, or over
  0.01 from `p_win - (1 - p_win) / payoff`. `mechanism` only when ex-ante:
  it lowers t threshold. New `family_id` only on operator's word.
- `close`: hypothesis id, `realized` decimal return, `against_odds`
  `win|loss`. `approve`: proposal stem, reply verbatim. Cap change:
  `override` on book id, new cap in `reason`.
- Fill needs `approve` on its `proposal` dated on or before fill `date`;
  holdings import as `opening` fills, `proposal` null.

## Strategy

Register hypothesis before any code for it; `measure` refuses strategy no
hypothesis names. Author writes `strategies/<name>/` to contract
`check --schema strategy` prints. Status words: `research` (absent file),
`live`, `retired`; write `status` only on operator's yes, recording
`promote` or `retire` naming strategy in same step. Never measure again to
shop for better number: changed claim is new hypothesis; code fix keeping
claim is new run, spends trial. Cite run only after `measure --repeat`
reproduces it.

## Loop

One lead session per book holds conversation, runs every `record`. Operator
message preempts loop: answer, then resume from bare `check`.

1. `load` every configured source.
2. Bare `check`; act on `next`; re-measure each `stale_cap` entry.
3. Research within family budgets through delegates (below).
4. Rebalance day (`preferences.json` `cadence`): Propose.
5. Weekly: `check --live` (Live). At promotion gate: `measure --held-out`,
   read its scorecard only.
6. Record `close` for each bet resolved (`overdue`, `unscored` warnings).
7. Post `check --brief` `lines` verbatim, adding nothing.

Heartbeat: end every turn by scheduling next wake at most 45 minutes out
(harness's scheduled-task tool, else cron), then stop. Each wake: bare
`check`, one loop step, `heartbeat` pad line (`item`, `outcome`,
`next_wake`), schedule, stop. Lead's context holds conversation, last
`check`, receipts; never filing text, logs, or data.

Delegate every unit with intermediate steps. Brief is book file
`delegates/<unit>.md` (Task, Reads, Writes, Rules, Output, Limit, Lessons);
write one before first dispatch of a new unit. Spawn message, whole:

```text
Book <path>. Read AGENTS.md, then delegates/<unit>.md. Unit: <values>. Agent <name>. Siblings: <none | bounds>.
```

| Unit | Values | Output |
| --- | --- | --- |
| `bet` | question; optional held name | `research/bets/<agent>.json` `hypotheses` batch, or no-bet in receipt |
| `author` | hypothesis id; runs it may measure: family `trials` minus `trials_used` | `strategies/<name>/`, run line via `measure --agent` |
| `critique` | run id; absolute path of `critique` | `research/critiques/<run id>.json` |

Agent name `<unit>-<n>` is its `--agent` and critique `by`; critique never
goes to run's author. Examine every receipt under summon's `examine`
(`wrote` inside Writes, `ids` exist), append it as `receipt` pad line, then,
before `record`:

- Clean receipt: nothing.
- Partial, stopped, out of scope, or wrong in way brief could have
  prevented: edit brief in same commit as receipt's pad line, one Lessons
  line naming receipt's `ts` plus rule change; commit message names receipt.
- Same lesson twice: rewrite that section, say so in Lessons.
- Critique flags same defect across authors: lesson goes to `author.md`.

Lessons stay append-only; never paste brief text into a message. Brief with
no lesson in thirty dispatches: `question` proposing it upstream.

Under `/summon` "Called from a skill":

| Field | Finance's value |
| --- | --- |
| task | brief's Task, one unit |
| evidence | spawn line's values; brief's Reads |
| rules | four invariants, brief's Rules; never `record`, held-out list |
| contract | brief's Output: one receipt JSON |
| limit | brief's Limit; author's run count |
| join | `examine`, then `record` of batch files named, then bare `check` |

## Gate

`check <strategy>` derives standing of newest research run: `promotable`,
`blocked`, or `discard` (PBO at or above `pbo_discard`). Blockers name value
and limit: `no run`, `dsr`, `pbo`, `t_alpha`, `factor`, `capacity`,
`cost_share`, `min_holding_days_realized`, `trials`, `no critique`,
`critique: <text>`, `status`, `odds` (only when nothing else blocks). Show
operator every blocker, never summary omitting one.

- `measure` refuses before running when `holding_days` is under
  `min_holding_days`, or trial-spending run lines dated today reach
  `trials_per_day`. `--reason "<why>"` runs past, stamped `override_reason`.
- Every run line but `trial: false` spends family trial, refused and
  held-out too. Budget spent: `question` quoting `trials_used`.
- Cap change: bare `check` lists each live strategy measured at other cap
  under `stale_cap`. Re-measure it: same `code_hash` at new cap writes
  `trial: false`, spends no trial.
- Bare `check` `calibration` scores closed bets per family and overall:
  `closed`, `mean_p_win`, `win_rate`, `brier`.

## Propose

Sleeve is strategy whose `status` reads `live`. On rebalance day, after
close:

1. `check "$B" --propose <date>` writes `proposals/<date>.json` once
   (`--force`: `<date>.<n>.json`); exit 1 when no live strategy has run
   line. Weight: `kelly_fraction.<tier>` x `edge_scale` (DSR) x Sharpe /
   vol, `entry_weight` before first fill, ruin-bounded (`book`).
2. `check "$B" <date>`. Put to operator in order: every `blockers` entry
   verbatim, `baseline` beside each sleeve, `tier`, `edge_scale`, `weight`,
   `stale`, `ruin` against bound (or `reasons`), `diff`, `cuts`,
   `unmanaged`, `summary`.
3. On reply, record `decision` on proposal stem, reply verbatim as `reason`:
   `approve`, `reject`, or `override`.
4. Operator trades, then pastes table, screenshot, or sentence. Transcribe,
   show parsed fills back; on yes run
   `record "$B" --fills:file <table> --proposal <stem>`.

`unmanaged` lists held names outside research set, never sold; never reason
from it about held-out membership.

## Live

`check "$B" --live` sets each live sleeve's real fills against `measure`'s
model path; `drawdown`, `slippage`, `tracking`, `stale` breach appends
incident, once per strategy and kind per 7 days. Show `report` whole.
Drawdown inside bound: propose no change.

## Extensions

Core (data, `Market` scope, hashing, trials, gate, scorecard) stays; book
extends it. Signatures: `book`.

| Hook | Path | Core use |
| --- | --- | --- |
| `sources` | `lib/sources/<name>.py` `fetch` | `load <name>`; built-in name wins |
| `market` | `lib/market/<name>.py` `extend` | accessors on `Market`; core name refused |
| `metrics` | `lib/metrics/<name>.py` `metric` | `scorecard.extra.<name>`, never gate |
| `sizing` | `lib/sizing.py` `weights` | replaces Kelly step of `check --propose` |
| `costs` | `lib/costs.py` `cost` | replaces default cost in `measure` |
| `brief` | `lib/brief.py` `lines` | appended to `check --brief` within 12 lines |
| critique item | `research/critique/<name>.md` | critique delegate reads it beside six core items |

- Hit limitation: write hook in same unit, with test; go on. Log `friction`
  only when core is wrong.
- Hook used by three runs with clean critiques: `question` proposing it
  upstream.
- Delete hook bare `check` `extensions` shows `idle`.

## Continue

With no `$B`, first ask operator which directory is the book; treat answer
as `$B`. Book there: continue. Empty: `start`. Neither: say what is there,
ask again.

At session start or after compaction: read `$B/AGENTS.md`, bare `check`,
`check --brief`; read `lines` verbatim; resume from `next`. API keys live in
environment only (`TIINGO_API_KEY`). Answer from ledger first.

## Gotchas

- `measure --repeat` compares AST digests of code and recorded hooks:
  comment or reformat reproduces; code or docstring change refuses.
- `approve` recorded after fill date: fill refused. Record it on reply.
- No `_factors`: `factor` null, blocks. `load french` before first
  `measure`.
- Older book reads `paper`, `probe` as `live`, `scored` as `close` (`book`).

## Completion checks

- Every `record` exited 0, or rejection corrected and resent.
- Every hypothesis carried odds and kill date before its code.
- Every multi-step unit went out by spawn line; every receipt examined,
  logged; defective one patched its brief.
- No critique came from run's author.
- Operator saw every blocker; every fill followed `approve`.
- Every resolved bet has `close`; `warnings` reported, not repaired.
- Nothing under skill edited; brief `lines` read verbatim.
