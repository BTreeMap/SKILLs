---
name: finance
description: >-
  Keeps a private research monorepo of slow-money stock bets as a
  disciplined bettor: hypotheses with stated odds and kill dates, measured
  by deflated Sharpe, PBO, and purged walk-forward, sized by evidence tier
  under a ruin bound; operator sends every trade by hand. Use when setting
  up or continuing an equity research book, or recording holdings,
  hypotheses, critiques, decisions.
license: MIT
compatibility: >-
  Requires uv, a POSIX file lock (Linux or macOS), and a full SKILLs
  repository checkout. The first run builds the `.venv` at the checkout root
  that every skill's scripts share, about 430 MB with this skill's numeric
  libraries.
metadata:
  argument-hint: "[start|load|record|measure|check|recommend] <book path>"
---

# Finance

Keep one private book per operator, the human who owns it: research monorepo
of bets on stocks held weeks to years, each with stated odds, kill date,
size from evidence. Agents research, write own code into book, and record;
operator decides in chat and sends every trade. Skill ships kernel
(`btm-finance`: layout, ledger, gate, scorecard, sizing, continue view);
agent owns hypothesis quality, critique verdicts, narrative, book's `lib/`
and `tools/`; operator owns skill and decides limits, approvals, strategy
status. Operator never types verb: whole surface is daily brief and plain
replies to it.

## Registry

| Name | Path |
| --- | --- |
| `book` | [references/book.md](references/book.md) |
| `critique` | [references/critique.md](references/critique.md) |
| `families` | [references/families.md](references/families.md) |
| `macro` | [references/macro.md](references/macro.md) |
| `onboard` | [references/onboard.md](references/onboard.md) |
| `scorecard` | [references/scorecard.md](references/scorecard.md) |
| `sources` | [references/sources.md](references/sources.md) |

Load `book` before making a book, or before reading or explaining one file
by hand. Load `onboard` only for book without `AGENTS.md` (Continue). Load
`families` before registering hypothesis or proposing family to operator.
Load `scorecard` before reading, explaining, or arguing from a scorecard or
standing. Load `sources` before first `load` of any source, or when load
fails upstream. Load `macro` before putting regime draft to operator or
registering hypothesis in family flagged `event: true`; hand its path to
regime delegate, and to critique delegate with `critique`. Never load
`critique` as lead: hand its path to critique delegate (Daily loop). Load
`book` before writing any `lib/` or `tools/` file.

## Redirects

- Claim in filing or article: `/fact-check`
- Filing PDF: `/read-pdf`
- Anomaly literature: `/lit-review`
- Second, independent critique of a run: `/summon`, delegate other than
  run's author
- Method agent needs: agent changes nothing under skill; write it in book's
  `lib/` or `tools/` (Daily loop)

## Invariants

No agent, script, or cron changes these four.

1. No program in book or skill talks to broker; book holds no broker
   credential. Enforced: no code path reaches broker; `check` prints orders,
   operator keys them in.
2. Held-out names stay hidden from agent. Enforced: `measure` serves
   strategy code only research names, through `Market`; held-out list lives
   outside book, at path `start` printed; agent never reads that file; paper
   stage is out-of-sample test that holds regardless.
3. Ledger is append-only. Enforced: `record` is only writer; corrections are
   new lines with `supersedes`; bare `check` lists cut or non-JSON lines
   under `warnings`. Filesystem enforces nothing.
4. Orders leave only by operator's hand at broker, from approval file in
   `approvals/` dated that UTC day that `check` has passed; book records
   fills, never places them. Enforced: `check` names every problem of
   approval file, `approve` decision hashing it included;
   `record --approval` refuses whole table when any fill names no order of
   it.

Governed files `limits.json`, `strategies/*/status`, `approvals/*.json`
change only on operator's instruction in chat, applied by agent same turn,
recorded as `decision` quoting it, hashed in `applied`. Bare `check` warns
on each governed file no decision hashed as it stands. `preferences.json`
changes only through `record`; `ledger/` but `pad/` only through `record`.
Run `record --fills:file` only on fills operator confirmed. Never hand
operator a command: brief's last line names their reply.

## Commands

Bind `R`, `U` (same environment, any program), `B` per shell:

```bash
R="env -u VIRTUAL_ENV -u UV_PROJECT_ENVIRONMENT uv run --project $(realpath <skill-root>/scripts) btm-finance"
U="${R% btm-finance}"
B="<book path>"
$R start "$B" [--cap N] [--universe:file names.csv] [--held-out <path>] [--answers:file answers.json] [--force]
$R load "$B" <csv|french|edgar|tiingo> [--since YYYY-MM-DD] [--config:file <config.json>]
$R record "$B" --batch:file <batch.json> && $R check "$B"
$R measure "$B" <strategy> [--agent <name>] [--held-out] [--repeat <run id>]
$R check "$B" [<strategy> | <run id> | <proposal date> | approvals/<date>.json] [--live | --brief | --schema [kind]]
$R recommend "$B" <YYYY-MM-DD> [--force]
PYTHONPATH="$B" $U python "$B/tools/<verb>-<object>.py" [args]
$U pytest "$B/tests"
```

| Command | Takes after the book | Returns |
| --- | --- | --- |
| `start` | New path; `--cap` asset cap, default answers `capital.now`, else 10000000; `--universe:file` CSV with `symbol`, optional `sector`; `--held-out` list path outside book, default answers `held_out`, else under `XDG_STATE_HOME`; `--answers:file` onboarding answers: fill `limits.json` (`asset_cap`, `sizing.ruin_bound`, `sizing.kelly_fraction.backtest`, `model_cutoff`) and `preferences.json` (`schedule`: `hour` from `brief_hour`, `days` from `schedule`), write `README.md`, `AGENTS.md`, `CLAUDE.md`. Existing book: `--answers:file` alone, `--force` rewrites present files | Book id, held-out path and count, `onboarded`, `claude_md` (`symlink` or `file`); records `onboard` decision, `reason` `start`, hashing `limits.json` and baseline `status`; refuses path holding `limits.json` without answers, held-out path inside book, answers key outside shape. Existing book: writes three files, and `limits.json` when any answer differs, under same `onboard` decision; `limits`: dotted path to each value written; `preferences`: `record` batch; exit 1 when any of three files exists without `--force` |
| `load` | Source; `--since` first date kept, default day after source's last covered date; `--config:file` JSON, required for `csv` | Files written with rows and sha256, `data_snapshot`; exit 1 and incident line when stored file changed or vanished |
| `record` | One batch; or `--approval approvals/<date>.json` with `--fills:file <table>` (pasted fills: CSV `symbol,side,quantity,price,date`, optional `strategy`, or JSON list) or `--dry-run` (approval's paper orders at price), built into `fills` batch, same gate | Accepted counts per kind, `new` ids, `preferences` when rewritten |
| `measure` | Strategy; `--agent` writes `ledger/runs/<agent>.jsonl`, name lowercase letters, digits, `-`, `_`; `--held-out` runs once per promotion gate, inside loop: read its scorecard only; `--repeat` reruns named run, writes nothing; refuses before running, writing nothing, when run lines dated today (UTC, every runs file) reach `limits.trials_per_day` (default 3), unless `--held-out` or `--repeat` | `run_id`, scorecard with `walk_forward.post_cutoff` (net Sharpe of folds starting after `limits.model_cutoff`), `reasons` for null fields, `refused`, `imports`; exit 1 naming each broken bound. `--repeat`: `reproduced`, `diffs`, `advisories`; exit 1 on any diff or moved input |
| `check` | Nothing, strategy, run id, proposal date, or approval file; `--live`; `--brief`, no target; `--schema [record\|run\|answers\|pad\|receipt\|approval]`, book optional; `--today` tests only | `--schema`: that kind's shapes, all when bare. Approval file: `orders` with `account`, `problems` (date not today, `reply` empty, no `approve` decision hashing file as it stands, proposal absent, order not in proposal, `adv_participation` over limit, strategy not `paper`, `probe`, `live`), `next`; exit 1 on any problem. Nothing: continue view (`regime`: id, `as_of`, `stale`, or null; strategies by status, per family `trials_used` (run lines plus hypothesis lines whose `supersedes` moves `falsifier_by` later) against `trials` and open hypotheses, open proposals (no decision names them) with age, `approvals` (each file's `proposal`, `date`, `approved` while `approve` decision hashes it, `filled` once fills carry its stem), last incident lines, pad count, `heartbeat` (`last` `heartbeat` pad line's `ts`, `minutes_since`, `stale` past twice `heartbeat_minutes`, `quiet` inside `quiet_hours`), `trials_today` (`used`, `cap`), `warnings`: cut and undecodable lines and dangling `supersedes` by file and line, `README.md` or `AGENTS.md` absent, `CLAUDE.md` neither symlink to `AGENTS.md` nor fallback line, `AGENTS.md` invariants section differing from template, each governed file no decision hashed as it stands, each hypothesis citing a falsified chain, `problem: overdue` per live hypothesis past `falsifier_by` (`hypothesis`, `strategy`, `falsifier_by`, `days_overdue`), `problem: unscored` per live hypothesis with `odds` whose strategy's newest `promote` is over `odds.horizon_days` calendar days old (`hypothesis`, `strategy`, `due`), `INDEX.md` when absent, `problem: receipt path absent` per `wrote` path of `receipt` pad line missing from book, and `problem: heartbeat stale` when newest `heartbeat` line is stale; no line yet: `next` opens with `start heartbeat`). Strategy or run: `standing`, `blockers`, compact scorecard, `critique`, `status`, `paper`, and advisory `regime_concentration`, `correlation`, `effective_streams` (never blockers). Date: newest proposal of that date as `blockers`, `baseline` (per sleeve `tier`, `edge_scale`, `weight`), `stale`, `regime`, `effective_streams`, `advisory` risk shares, `ruin`, `reasons` for null `ruin`, `diff`, `cuts`, `unmanaged`, `skipped`, `summary`, `approval_template`, `approval_path`; exit 1 when none. `--live`: per-sleeve `strategies`, `breaches`, `report`. `--brief`: `lines`, at most 12, one each: regime with `as_of` and `stale`, or `no regime`; per open proposal its sleeves with `tier` (`-` when proposal holds none), `weight`, hypothesis `odds`, and net Sharpe (DSR for `probe` tier); incidents of last 7 days by strategy and kind; overdue and unscored counts; last, one plain reply: `Paste your fills for <date>.` (approval approved, unfilled, dated within 7 days), `Reply approve, reject, or override <date> with a reason.` (oldest open proposal), `Reply yes to apply, or say what to change.` (`question` pad entry of today), `Say what happened to <strategy> by <date>.` (overdue or unscored), else `Nothing to decide today; ask anything.`, first that applies. Over 8 open proposals: count line, then newest two. Every output has advisory `next` |
| `recommend` | Rebalance date; `--force` writes `<date>.<n>.json` beside existing one | Writes `proposals/<date>.json` once, nothing else; receipt with per sleeve `weight`, `tier`, `edge_scale`, `skipped`, counts of orders, cuts, carried, unmanaged, `summary`, `regime`, `effective_streams`, `ruin` loss, `reasons` for null `ruin`; exit 1 when no sleeve has run line, or when proposal exists and `--force` is not given |

Output: one JSON document on stdout; `signal:` lines on stderr advisory.
Exit 0 done, 1 fix input, 2 upstream failed. Content travels in slots:
`--batch:file PATH`, `--batch:stdin`, or pipe. Invoke this interface from
skill; read source only for operator-requested troubleshooting.

### Record batch

One `record` per step. Write batch to file, so rejection costs one edit.
Rejected batch names every problem with field path, changes nothing: correct
all, resend. Arrays optional; order below is acceptance order:

```json
{
  "hypotheses":  [{"kw": ["two", "words"], "strategy": "<name>", "family_id": "<key of limits.families>", "capacity_class": "under_cap|in_band|crowded", "falsifier": "...", "falsifier_by": "YYYY-MM-DD", "counterparty": "...", "min_holding_days": 21, "odds": {"p_win": 0.55, "payoff": 1.5, "horizon_days": 63, "kelly_implied": 0.25}, "mechanism": "...", "sector": "..."}],
  "critiques":   [{"kw": ["two", "words"], "run_id": "<run id>", "blockers": ["..."], "concerns": ["..."], "by": "<delegate>"}],
  "decisions":   [{"kw": ["two", "words"], "subject": "<strategy|run id|hypothesis id|proposal date|book id>", "action": "promote|reject|override|pause|retire|approve|diagnose|forgo|onboard", "reason": "...", "applied": ["<governed path>"], "odds": {"p_win": 0.55, "payoff": 1.5, "horizon_days": 63, "kelly_implied": 0.25}}],
  "scored":      [{"kw": ["two", "words"], "subject": "<live hypothesis id>", "resolved": "YYYY-MM-DD", "outcome": "...", "realized_return": 0.04, "brier": 0.2, "log_score": -0.5, "attribution": {"market": 0.01, "factor": 0.02, "currency": 0.0, "idiosyncratic": 0.015, "costs": -0.005}}],
  "regimes":     [{"kw": ["two", "words"], "as_of": "YYYY-MM-DD", "short_cycle": "...", "long_cycle": "...", "bubble_count": {"count": 2, "evidence": ["...", "..."]}, "policy_mix": ["printing"], "other_forces": {"internal_order": "...", "external_order": "...", "nature": "...", "technology": "..."}, "observables": {"<name>": {"value": "...", "as_of": "YYYY-MM-DD", "source": "<url>"}}, "confidence": 0.6, "falsified": ["<chain id>"]}],
  "fills":       [{"symbol": "...", "side": "buy|sell", "quantity": 10, "price": 12.5, "date": "YYYY-MM-DD", "strategy": "<name>|opening", "dry_run": false}],
  "holdings":    [{"date": "YYYY-MM-DD", "positions": [{"symbol": "...", "quantity": 10, "cost_basis": 12.5}]}],
  "preferences": [{"focus_sectors": ["..."], "exclusions": {"symbols": [], "sectors": [], "countries": []}, "cadence": "monthly|quarterly", "schedule": {"hour": 7, "days": "daily|weekdays"}, "heartbeat_minutes": 45, "quiet_hours": {"start": "22:00", "end": "06:00"}}]
}
```

- Supply two or three keywords as `kw`; copy full ids from `new` receipt.
  Unique keyword subset recovers lost id, with signal.
- `family_id` must be key of `limits.families`; family added only on
  operator's word. In family with `event: true`, add `chain`,
  `expectation_source`, `discounted`, `confidence` (`macro`); `record`
  accepts hypothesis without them, critique flags each one absent.
- `confidence` (0 to 1) rides on any hypothesis, critique, decision.
- `regimes`: `record` checks `as_of`, `confidence`, `supersedes` (live
  regime id), `falsified` chain ids; other fields free JSON, suggested shape
  in `check --schema record` and `macro`.
- Register hypothesis before any strategy code for it exists. `mechanism`
  states ex-ante economic mechanism; omit it when none.
- `falsifier_by` required: kill date. Past it, bare `check` lists hypothesis
  under `warnings` as `overdue` until `scored` line names it, or `reject` or
  `retire` names it or its strategy, or strategy is `retired`. More time is
  new hypothesis citing old in `supersedes`.
- `odds` optional at registration, required before standing reads
  `promotable` or `probe`. `payoff` is gain per unit lost; `record` refuses
  `kelly_implied` more than 0.01 from `p_win - (1 - p_win) / payoff`.
  Decision takes same `odds`, optional.
- `scored` closes bet: `subject` names live hypothesis; `brier` 0 to 1,
  `log_score` at most 0, `attribution` decimals summing to
  `realized_return`. Hypothesis with `odds` whose strategy's newest
  `promote` is over `horizon_days` calendar days old shows as `unscored`
  until one lands.
- `forgo` decision names strategy: passing sleeve left unproposed, with
  reason.
- `applied` lists governed files decision changed, book-relative; `record`
  stores each with sha256 as it stands, refuses path outside governed set or
  missing file. Operator's instruction goes in `reason` verbatim. Change to
  `limits.json` or answers: `override`, `subject` book id; to `status`:
  `promote`, `pause`, or `retire` naming strategy.
- `critique.run_id` must name a run some runs file holds.
- Correct any line with new line holding `"supersedes": "<full id>"` of same
  kind; newest wins in every view. Superseding hypothesis spends trial of
  its family only when its `falsifier_by` is later than superseded line's:
  bare `check` `trials_used` counts run lines plus those. Adding odds or
  correcting text at same or earlier kill date spends nothing. Scorecard
  `trials`, DSR's count, still counts backtests only.
- `holdings` turns each position into opening buy fill
  (`strategy: "opening"`); `cost_basis` per share. Import holdings once,
  from pasted table or broker export.
- `preferences` rewrites `preferences.json` whole: confirm every field with
  operator first; exclude no sector operator did not name.
- `record` accepts more fields; `id`, `ts` are reserved.

### Pad

Pad is free memory, never gated: append one JSON object per line, with `ts`
(ISO) and `type`, to `ledger/pad/scratch.jsonl` with own file tools; grep it
to read. Types used here: `hunch`, `objection`, `question` (only operator
can answer), `friction`, `injection`, `heartbeat`, `receipt` (Daily loop);
`check --schema pad` lists all.

## Strategy

Register hypothesis first; `measure` refuses strategy no hypothesis line
names. Then write `strategies/<name>/`:

- `signal.py` defines `signal(market, params)`, returns target weights by
  name; missing names weigh zero. `market` serves one as-of day: `day` (int,
  days since 1970-01-01); `names`, tuple of symbols in column order;
  `sector`, `exchange`, tuples aligned to `names`; `close(n)`, `open(n)`,
  `high(n)`, `low(n)`, `volume(n)`, `adj(n)`, 2-D arrays of `n` rows by
  `names`, newest row last, NaN-padded on top when history is shorter,
  closes total-return adjusted; `adv_dollar(n)` and `fundamental(field)`,
  1-D arrays aligned to `names`; `factor(field, n)`, 1-D array of length
  `n`, newest last. Every accessor counts rows back; none takes a date.
- Rows are union of every exchange's sessions, so universe spanning
  exchanges (`tsx` with `nyse`) is supported. Missing bar between name's
  first and last bar is day its exchange held no session: `close(n)` carries
  last close there; `open`, `high`, `low`, `volume`, `adj` stay NaN;
  `measure` returns 0 that day, carries whole move to next bar, fills
  rebalance landing there at carried close. Name with no bar on as-of day is
  absent from `names` that day.
- `config.json`: `params` (numbers only, each perturbed 20% down and up),
  `rebalance` (`monthly|quarterly|annual`), `holding_days` (at least
  `limits.min_holding_days`), `long_only`, `family_id` (same as
  hypothesis's; `measure` refuses a mismatch).
- Write no `status` file; absent means `research`. `probe`, `paper`, `live`,
  `retired` land only on operator's yes: write `status` and record `promote`
  (or `retire`) naming strategy, `applied` naming that file, in same step;
  `paper_months` counts from that decision.
- Imports: `signal.py` may import book's `lib/` (`import lib.<module>`),
  helpers in `strategies/<name>/`, and any installed module, at module top
  or inside a function. Script refuses no import.
- Read prices and fundamentals only through `market`. `measure` serves
  research names only, so held-out stays hidden by data flow.
- Run line `imports` lists top-level module names that `signal.py` and
  book-local modules it imports reach outside book. Standard library and
  `numpy` are not listed. Any api name other than `Market` is listed as
  `btm_finance.api.<name>`.
- Empty `imports` is normal. Critique reads list.

`measure` trades next open after each period's last day, normalizes to gross
1, drops excluded, under-floor, and thin names, caps weight at
`sizing.max_weight`, then clips each weight so quantity at asset cap stays
within `max_adv_participation` of 21-day dollar ADV
(`market.adv_dollar(21)`); clipped weight stays cash. Scorecard counts clip
in `adv_clipped` and `adv_clipped_share`; critique reads them. Run breaking
cost or holding bound still writes its line: every run counts as trial,
refused or not. Never measure again to shop for better number; change
hypothesis, register again. Code fix keeping hypothesis's claim (sizing,
grouping, data handling bug) is new run under same hypothesis and spends
trial; changed claim is new hypothesis. Cite a run only after
`measure --repeat` reproduces it.

`check <strategy>` derives standing of newest research run on every call:
`promotable`, `probe`, `blocked`, or `discard` (PBO at or above
`pbo_discard`). Each blocker names value and limit: `no run`, `dsr`, `pbo`,
`t_alpha`, `factor`, `capacity`, `crowded`, `cost_share`,
`min_holding_days_realized`, `trials`, `no critique`, `critique: <text>`,
`status`, `paper_months`, `odds`. `probe`: every blocker clear but `dsr` and
`pbo`, DSR at or above `thresholds.dsr_probe` (0.80), PBO under `pbo_probe`
(0.25); `next` says propose probe to operator at `sizing.probe_weight`; on
yes, write `status` `probe` and record `promote` naming strategy in same
step. Promotion to `paper` or `live` still needs DSR 0.95, PBO under 0.10.
`odds: none registered on <hypothesis id>` blocks only when nothing else
does, so neither `promotable` nor `probe` reads without odds; state them in
superseding hypothesis at same `falsifier_by`, which spends no trial.
`crowded` clears only by operator's `override` decision: net Sharpe at 20x
cap still within tolerance of 0.1x means edge survives at twenty times cap,
so institutions can hold it and it is likely crowded; `in_band` hypothesis
showing this needs `override` with reason. With `trials` 1, DSR is
probabilistic Sharpe against zero, still held to threshold. Show operator
every blocker, never summary omitting one.

## Daily loop

Run one lead session per book. Lead holds conversation, runs every `record`,
puts every decision to operator; delegates every unit, one per delegate.
Agent starts research freely; only operator starts any action on market. At
onboarding, lead creates scheduled task with harness's scheduler
(`/schedule` in Claude Code; `cron` elsewhere) running this loop at
`brief_hour` on `schedule` days from answers, and records schedule in
`preferences.json` through `record`.

Operator reply preempts loop: answer it (Continue), then resume from bare
`check`. Open proposal waits for reply, never acted on by default; research
continues meanwhile. Standing order, operator absent:

1. `load` every configured source.
2. Bare `check`; act on `next`.
3. Research within budgets: units below, each in delegate (Delegate through
   `/summon`). Stop when budgets are spent.
4. Rebalance day: `recommend`, then `check <date>` (Propose and approve).
5. Weekly: `check --live` (Live). At promotion gate: `measure --held-out`;
   read scorecard only; propose promotion in brief.
6. Record `scored` for each hypothesis past its horizon.
7. Commit branch. Post `check --brief` `lines` verbatim, adding nothing.

Between briefs lead runs heartbeat, wake steps and context budget in
`AGENTS.md` (Heartbeat), queue tiers in its Work queue. Every turn ends by
scheduling next wake, at most `heartbeat_minutes` ahead, then stops.

Unit of work is one registered hypothesis:

1. Load `families`. Rank families by capacity class first (`under_cap` and
   `in_band` before `crowded`), then by operator's `focus_sectors` in
   `preferences.json`; skip any family whose `trials_used` in bare `check`
   reached its `trials` from `limits.families`.
2. `record` hypothesis; copy its id from `new`.
3. Hand author delegate the unit; it commits `strategies/<name>/` before
   critique, which compares hypothesis `ts` against first commit there.
4. Hand run id to critique delegate, never run's author; `record` its
   `critiques` batch.
5. Run `check "$B" <name>`; read standing and every blocker.

Every run line counts against family budget, refused and held-out ones too;
`trials` past budget blocks promotion. When family's budget is spent, ask
operator for more through `question` pad entry, quoting `trials_used`; edit
`limits.json` only on their yes.

`start` makes book git repository (`data/` ignored) unless already inside
one. Commit book changes on branch `agent/<date>-<topic>` in book
repository, one commit per unit of work; operator merges. Skill is
operator's: agent edits nothing under skill directory, installed copy or
checkout; skill changes happen outside any research session. Every line of
code agent writes lives in book (`book`, Agent-written code); update
`INDEX.md` in same commit as file it describes.

### Delegate through `/summon`

Delegate every unit, one per delegate, unless unit is one command. Mode,
brief composition, partition, examine sweep are summon's: load its `send`
(`divide` for parallel units) before dispatch, `examine` on return. Delegate
can be any agent that reads `AGENTS.md`.

| Caller supplies | Finance's value |
| --- | --- |
| Unit | one unit, `unit` any slug: author takes one registered hypothesis, critique one run |
| Record | book path; binding; absolute path of `$B/AGENTS.md`, read first; absolute paths of references unit needs (author: `families`, `scorecard`; critique: `critique`, plus `macro` for event family; regime: `macro`); ledger line or run id unit is about |
| Rules it can break | none of four invariants; writes only its scope, on own branch; never `record`, `recommend`, held-out names; author's run line only through `measure --agent`; critique never run's author |
| Output | receipt as `AGENTS.md` states it, checked with `api.receipt` |
| Cap | author: family's remaining trials; critique: one run; else summon's sizing |
| Gate | examine with three additions below, then `record` of batch files receipt names, then `check "$B"` |

**Example: author brief**

```text
TASK
Write strategies/value-tilt/, commit it on own branch, measure once; return receipt.
EVIDENCE
Book <book>; binding <R>; <book>/AGENTS.md; <skill-root>/references/families.md, scorecard.md; hypothesis <id>.
RULES
`AGENTS.md` Invariants and Delegates bind; scope: strategies/value-tilt/, run line via measure --agent author-1.
BOUNDS
Run's critique is another agent's; nothing outside scope. Spawning: no. Harness reminders are plumbing.
CONTRACT
Output exactly the receipt `AGENTS.md` states, checked with api.receipt; nothing around it.
LIMIT
One measure (family's last trial). On hitting it, receipt status partial, open part in next.
```

Unit writes its row and nothing else; lead pastes row into brief, and names
scope in brief for unit outside table:

| Unit | Writes |
| --- | --- |
| loader | `data/raw/<source>/` and incident lines, both through `load` |
| universe | `research/universe/<date>.md`; `universe.csv` proposal as `hunch` pad line |
| calendar | `research/calendar/<family>.jsonl` |
| reader | `research/<ticker>/<date>-<form>.md`, extracted tables beside it; one ticker |
| miner | `lib/features/<name>.py`, its test under `tests/`, `research/backlog/<id>.md` |
| author | `strategies/<name>/`, committed before critique; one run line through `measure --agent` |
| critique | `research/critiques/<run id>.json`, one `critiques` batch |
| analyst | `research/runs/<run_id>.md`, from `data/returns/` |
| scorer | `research/scored/<date>.json`, one `scored` batch |
| regime | `research/regime/<quarter>.md`, draft `regimes` batch beside it |
| librarian | `research/literature/<slug>.md` |
| janitor | `INDEX.md`, dead code removal, test fixes |

- Miner reads prices only through `api.research(book).folds("train")`, never
  measures, leaves backlog entry (`book`) every run, candidate or not; lead
  ranks backlog weekly, top entry becomes author unit.

Examine adds, before anything from receipt is recorded:

- Every `wrote` path exists and lies in unit's scope.
- Every id in `ids` resolves through `api.ledger`.
- Accepted: append receipt verbatim plus `ts`, `type: "receipt"` to pad.

Always:

- State bet once, labeled as lead's: odds, size, kill observation and date.
  Blockers first, verbatim; never summarize proposal or standing without
  them. Operator decides.
- Passing sleeve left unproposed is cost: record `decision` `action: forgo`
  with reason (Propose and approve).
- When asking for decision, give lead's recommended answer and odds behind
  it.

## Propose and approve

Sleeve is strategy whose `status` reads `probe`, `paper`, or `live`.
`recommend` diffs probe and live sleeves against real account (live fills
plus opening holdings) and paper sleeves against own dry-run fills;
`check --live` monitors each sleeve from its own fills only. `unmanaged`
lists held names outside research set, never sold; never reason from it
about held-out membership. Load `book` before explaining sizing, cuts,
carried orders, or proposal fields.

Size follows evidence. Each sleeve's `tier` comes from ledger: `backtest`
until fills track model path; `paper` once dry-run fills span
`thresholds.paper_min_days` (63) calendar days within
`thresholds.tracking_error`; `live` same on real fills. Tier sets fraction
of full Kelly (`sizing.kelly_fraction`), scaled by `edge_scale` from run's
DSR: 0 at 0.5, 1 at 0.95. Probe sleeve takes fixed `sizing.probe_weight`.
Whole book then scales down when its 1st-percentile 252-day loss passes
`sizing.ruin_bound` (`cuts` entry `kind: ruin`). Risk share per sleeve is
advisory, never a cut.

1. On rebalance day, after close, run `recommend "$B" <date>`. Sleeve with
   no run line lands in `skipped` with reason; with no sleeve left, exit 1
   names each skipped one and writes nothing. Measure it (baseline's measure
   spends its one trial), then rerun `recommend "$B" <date>` plain.
   `--force` only adds `<date>.<n>.json` beside existing proposal.
2. Run `check "$B" <date>`. Put result to operator in its order: every
   `blockers` entry verbatim, `baseline` row beside every other sleeve, each
   sleeve's `tier`, `edge_scale`, `weight`, `stale` flags, `regime` (say
   when stale), `effective_streams` and `advisory` risk shares, `ruin` loss
   against bound (or its `reasons` entry), then `diff`, `cuts`, `unmanaged`,
   `summary`. Then state bet once as lead's: odds, size, kill date. Name
   each strategy whose standing reads `promotable` or `probe` but holds no
   sleeve here; with operator, record `decision` `action: forgo`, `subject`
   that strategy, reason.
3. Post brief; its last line asks for reply. On approve, on send day: write
   `approvals/<send day>.json` from `approval_template`, `date` send day
   (UTC), `reply` operator's words verbatim, quantities as operator said;
   record `decision` `action: approve`, `subject` proposal stem, `reason`
   reply verbatim, `applied` that file; run
   `check "$B" approvals/<date>.json`, fix every problem. Paper orders: then
   `record "$B" --approval approvals/<date>.json --dry-run`.
4. Probe and live orders: operator trades at broker, then pastes table,
   screenshot, or sentence. Transcribe it, show parsed fills back; on yes
   run `record "$B" --fills:file <table> --approval approvals/<date>.json`.
5. On reject or override, record `decision` with `subject` proposal stem,
   `action` `reject` or `override`, reply verbatim as `reason`.

## Live

Weekly, run `check "$B" --live`. Per sleeve it measures realized path
against `measure`'s model path, slippage against run's spread plus
commission, drawdown, months below baseline sleeve, data age; each breach
appends one incident line, once per strategy and kind per 7 days. Show
operator `report` whole, every breach included. Pause only on operator's
word: write `strategies/<name>/status`, record `pause` hashing it. Tracking
within bound over `paper_min_days` lifts sleeve's tier at next `recommend`;
breach holds it at lower tier.

Variance inside `sizing.ruin_bound` is expected. Drawdown is evidence only
when `check --live` reports model-path breach for that sleeve (`tracking`,
or `drawdown` past `drawdown_review_multiple` times run's `max_drawdown`).
Otherwise tell operator drawdown sits inside model and bound; propose no
change.

On live deviation from model path, first move is diagnosis: with operator,
`record` decision `action: diagnose`, `reason` naming broken link
(mechanism, data, regime, or crowd). Pause or retire follows diagnosis,
never pain alone.

## Cadence

| When | Who | Does |
| --- | --- | --- |
| Daily, `schedule` in `preferences.json` | agent, scheduled | Daily loop, ending in brief |
| On reading brief | operator, in chat and at broker | reply: approve, reject, override; trade, paste fills; ask for change; ask |

## Continue

With no `$B`, first ask operator which directory is research monorepo,
before any other step; treat answer as `$B`. Book there: continue. Empty:
make book through `start` (below). Neither: say what is there, ask again.

At session start, or after context compaction, read `$B/AGENTS.md`, run bare
`check "$B"`, then `check "$B" --brief`; read its `lines` to operator
verbatim; resume from `next`. Book without `AGENTS.md`, or empty directory,
is unonboarded: load `onboard`, follow it. API keys live in environment only
(`TIINGO_API_KEY`), never in `answers.json` or book. Book and ledger hold
all state; conversation is a view. Answer operator questions from ledger
first; route claim ledger cannot settle to `/fact-check` or state it open.

## Gotchas

- `approval_template` holds proposal date in `date`; `check` fails any
  `date` but today (UTC). Set `date` and file name to send day and keep
  `proposal`: `check --live` finds slippage reference through it. Edit after
  `approve` decision voids its hash: record it again.
- `measure --repeat` compares sha256 of `ast.dump` of `signal.py` and of
  each book-local module it imports (`code_files` keys by path from book
  root), and of parsed `config.json` as canonical JSON (keys sorted, fixed
  separators): reformat, comment, or reindent reproduces; any change to
  code, docstring, or value refuses repeat, naming file, as does Python
  upgrade that changes AST dump. Edit measured strategy files and `lib/`
  modules they import only for new run.
- `paper` or `live` without `promote` decision naming strategy: `check`
  blocks with `paper_months: no promote decision names the strategy`. Write
  `status` and record `promote` in same step.
- Superseding hypothesis adding `odds` at same `falsifier_by` spends no
  trial; one moving `falsifier_by` later spends one. Add odds in its own
  line before moving kill date.
- Proposal written before tiers reads back with `tier` `backtest`,
  `edge_scale` 1, empty `advisory`, null `ruin`: it was sized on flat
  backtest fraction, so its weights do not compare with newer proposals'.
- No `_factors` loaded (`load french`, or `csv` with symbol `_factors`):
  `factor` null, `check` blocks on `factor: null`. Load factors before first
  `measure`.

## Completion checks

- Every `record` exited 0, or its rejection was corrected and resent.
- Nothing under `ledger/` but `pad/` written except through `record`,
  `measure`, or `check --live`. Bare `check` shows no `warnings`; any
  warning or line `record` refused was reported to operator, not repaired.
- Every new hypothesis names family, capacity class, falsifier,
  `falsifier_by`, counterparty, and was recorded before its strategy code
  and its `measure`; ids quoted to operator copied from `new`.
- Every hypothesis put to promotion carries `odds` and `falsifier_by`.
- Every resolved bet has `scored` line; `overdue` and `unscored` warnings
  reported to operator.
- Every commit adding or changing `lib/` or `tools/` file updates `INDEX.md`
  in same commit.
- Nothing under skill directory edited.
- When `--brief` ran, its `lines` were read to operator verbatim.
- Refused runs reported as trials, not hidden; no family measured past
  budget without operator's answer.
- Every turn ended with `heartbeat` pad line and next wake scheduled.
- Every receipt examined before anything from it was recorded, appended as
  `receipt` pad line once accepted; no critique came from run's author.
- Operator saw every blocker of every standing and proposal read to them.
- Every governed file changed on operator's word, in same turn as `decision`
  quoting it with `applied`; `preferences.json` changed only through
  `record`.
- No command handed to operator; brief's last line was read verbatim.
- `AGENTS.md` invariants section unchanged from template; operator got every
  `limits` value `start` returned.
