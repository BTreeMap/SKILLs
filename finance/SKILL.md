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
  Requires uv, git, a POSIX file lock (Linux or macOS), and a full SKILLs
  repository checkout; `start` runs `git init` outside a repository. The
  first run builds the `.venv` at the checkout root that every skill's
  scripts share, about 430 MB with this skill's numeric libraries.
metadata:
  argument-hint: "[start|load|record|measure|check|recommend] <book path>"
---

# Finance

Keep one private book per operator, the human who owns it: research monorepo
of bets on stocks held weeks to years, each with stated odds, kill date,
size from evidence. Agents research, write own code into book, and record;
operator decides in chat and sends every trade. Agent owns hypothesis
quality, critique verdicts, narrative, book's `lib/` and `tools/`; operator
owns skill and decides limits, approvals, strategy status. Operator never
types verb: whole surface is daily brief and plain replies to it.

## Registry

| Name | Path |
| --- | --- |
| `book` | [references/book.md](references/book.md) |
| `critique` | [references/critique.md](references/critique.md) |
| `scorecard` | [references/scorecard.md](references/scorecard.md) |
| `sources` | [references/sources.md](references/sources.md) |

Load `book` before making a book, reading or explaining one file by hand, or
writing any `lib/` or `tools/` file. Load `scorecard` before reading,
explaining, or arguing from a scorecard or standing. Load `sources` before
first `load` of any source, or when load fails upstream. Never load
`critique` as lead: hand its path to critique delegate.

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
   credential.
2. Held-out names stay hidden from agent: `measure` serves strategy code
   only research names, through `Market`; held-out list lives outside book,
   at path `start` printed; agent never reads that file.
3. Ledger is append-only: `record` is only writer; corrections are new lines
   with `supersedes`.
4. No order without a `decision` naming the proposal, recorded before any
   fill of it. `record --fills:file` refuses whole table when any fill names
   no order of the proposal.

`limits.json`, `strategies/*/status`, `preferences.json` change only on
operator's instruction in chat, applied by agent same turn, recorded as
`decision` quoting it. `ledger/` but `pad/` changes only through `record`.
Run `record --fills:file` only on fills operator confirmed. Never hand
operator a command: brief's last line names their reply.

## Commands

Bind `R`, `U` (same environment, any program), `B` per shell:

```bash
R="env -u VIRTUAL_ENV -u UV_PROJECT_ENVIRONMENT uv run --project $(realpath <skill-root>/scripts) btm-finance"
U="${R% btm-finance}"
B="<book path>"
$R start "$B" [--cap N] [--universe:file names.csv] [--held-out <path>]
$R load "$B" <csv|french|edgar|tiingo> [--since YYYY-MM-DD] [--config:file <config.json>]
$R record "$B" --batch:file <batch.json> && $R check "$B"
$R record "$B" --fills:file <table> --proposal <stem>
$R measure "$B" <strategy> [--agent <name>] [--held-out] [--repeat <run id>] [--reason "<text>"]
$R check "$B" [<strategy> | <run id> | <proposal date>] [--live | --brief | --schema [kind]]
$R recommend "$B" <YYYY-MM-DD> [--force]
PYTHONPATH="$B" $U python "$B/tools/<verb>-<object>.py" [args]
$U pytest "$B/tests"
```

| Command | Takes after the book | Returns |
| --- | --- | --- |
| `start` | New path; `--cap` asset cap, default 10000000; `--universe:file` CSV with `symbol`, optional `sector`; `--held-out` list path outside book, default under `XDG_STATE_HOME` | Book id, held-out path and count, `claude_md` (`symlink` or `file`), `git` (`init` on `main`, `inside` existing repository, or `absent`); commits nothing; refuses path holding `limits.json`, held-out path inside book |
| `load` | Source; `--since` first date kept, default day after source's last covered date; `--config:file` JSON, required for `csv` | Files written with rows and sha256, `data_snapshot`; exit 1 and incident line when stored file changed or vanished |
| `record` | One batch; or `--fills:file <table>` (pasted fills: CSV `symbol,side,quantity,price,date`, optional `strategy`, or JSON list) with `--proposal <stem>`, built into `fills` batch, same gate | Accepted counts per kind, `new` ids |
| `measure` | Strategy; `--agent` writes `ledger/runs/<agent>.jsonl`, name lowercase letters, digits, `-`, `_`; `--held-out` runs once per promotion gate, inside loop: read its scorecard only; `--repeat` reruns named run, writes nothing; refuses before running, writing nothing, on a policy gate: `holding_days` under `limits.min_holding_days`, or run lines dated today (UTC, every runs file) at `limits.trials_per_day` (default 3), unless `--held-out` or `--repeat`. `--reason` runs past policy gates, stamped as `override_reason` | `run_id`, scorecard with `walk_forward.post_cutoff` (net Sharpe of folds starting after `limits.model_cutoff`), `reasons` for null fields, `refused`, `imports`; run line stores `code_hash` (sha256 over AST dump of `signal.py` and each reached book-local module, canonical `config.json`), `code_files` (path to own digest), `engine` (package version), `universe` (`membership` or `static`), `override_reason`; exit 1 naming each broken bound. `--repeat`: `reproduced`, `diffs`, `advisories` (moved engine version); exit 1 on any diff or moved input |
| `check` | Nothing, strategy, run id, or proposal date; `--live`; `--brief`, no target; `--schema [record\|run\|pad\|strategy]`, book optional; `--today` tests only | `--schema`: that kind's shapes, all when bare. Nothing: continue view (strategies by status, per family `trials_used` against `trials` and open hypotheses, open proposals (no decision names them) with age, last incident lines, pad count, `trials_today` (`used`, `cap`), `warnings`: cut and undecodable lines and dangling `supersedes` by file and line, `problem: overdue` (`hypothesis`, `strategy`, `falsifier_by`, `days_overdue`), `problem: unscored` (`hypothesis`, `strategy`, `due`)). Strategy or run: `standing`, `blockers`, compact scorecard with `override_reason`, `critique`, `status`. Date: newest proposal of that date as `blockers`, `baseline` (per sleeve `tier`, `edge_scale`, `weight`), `stale`, `ruin`, `reasons` for null `ruin`, `diff`, `cuts`, `unmanaged`, `skipped`, `summary`; exit 1 when none. `--live`: per-sleeve `strategies`, `breaches`, `report`. `--brief`: `lines`, at most 12, one each: per open proposal its sleeves with `tier` (`-` when proposal holds none), `weight`, hypothesis `odds`, and net Sharpe; incidents of last 7 days by strategy and kind; overdue and unscored counts; last, one plain reply: `Paste your fills for <date>.` (proposal approved within 7 days, no fill names it), `Reply approve, reject, or override <date> with a reason.` (oldest open proposal), `Reply yes to apply, or say what to change.` (`question` pad entry of today no `answer` names), `Say what happened to <strategy> by <date>.` (overdue or unscored), else `Nothing to decide today; ask anything.`, first that applies. Over 9 open proposals: count line, then newest two. Every output has advisory `next` |
| `recommend` | Rebalance date; `--force` writes `<date>.<n>.json` beside existing one | Writes `proposals/<date>.json` once, nothing else; receipt with per sleeve `weight`, `tier`, `edge_scale`, `skipped`, counts of orders, cuts, carried, unmanaged, `summary`, `ruin` loss, `reasons` for null `ruin`; exit 1 when no sleeve has run line, or when proposal exists and `--force` is not given |

Output: one JSON document on stdout; `signal:` lines on stderr advisory.
Exit 0 done, 1 fix input, 2 upstream failed. Content travels in slots:
`--batch:file PATH`, `--batch:stdin`, or pipe. Read kernel source only for
operator-requested troubleshooting.

### Record batch

One `record` per step. Write batch to file, so rejection costs one edit.
Rejected batch names every problem with field path, changes nothing: correct
all, resend. Arrays optional; order below is acceptance order:

```json
{
  "hypotheses":  [{"kw": ["two", "words"], "strategy": "<name>", "family_id": "<key of limits.families>", "falsifier": "...", "falsifier_by": "YYYY-MM-DD", "counterparty": "...", "min_holding_days": 21, "odds": {"p_win": 0.55, "payoff": 1.5, "horizon_days": 63, "kelly_implied": 0.25}, "mechanism": "...", "sector": "..."}],
  "critiques":   [{"kw": ["two", "words"], "run_id": "<run id>", "blockers": ["..."], "concerns": ["..."], "by": "<delegate>"}],
  "decisions":   [{"kw": ["two", "words"], "subject": "<strategy|run id|hypothesis id|proposal date|book id>", "action": "promote|reject|override|retire|approve|close", "reason": "...", "odds": {"p_win": 0.55, "payoff": 1.5, "horizon_days": 63, "kelly_implied": 0.25}}],
  "fills":       [{"symbol": "...", "side": "buy|sell", "quantity": 10, "price": 12.5, "date": "YYYY-MM-DD", "strategy": "<name>|opening", "proposal": "<proposal stem>|null"}]
}
```

- Supply two or three keywords as `kw`; copy full ids from `new` receipt.
  Unique keyword subset recovers lost id, with signal.
- `family_id` must be key of `limits.families`; family added only on
  operator's word.
- `confidence` (0 to 1) rides on any hypothesis, critique, decision.
- `mechanism` states ex-ante economic mechanism; omit it when none.
- `falsifier_by` required: kill date. Past it, bare `check` lists hypothesis
  under `warnings` as `overdue` until `close` decision names it, or `reject`
  or `retire` names it or its strategy, or strategy is `retired`. More time
  is new hypothesis citing old in `supersedes`. Never-promoted bet past kill
  date: record `decision` `action: reject`, `subject` hypothesis id.
- `odds` optional at registration, required before standing reads
  `promotable`. `payoff` is gain per unit lost; `record` refuses
  `kelly_implied` more than 0.01 from `p_win - (1 - p_win) / payoff`.
  Decision takes same `odds`, optional.
- `close` decision ends bet: `subject` hypothesis id. Hypothesis with `odds`
  whose strategy's newest `promote` is over `horizon_days` calendar days old
  shows as `unscored` until one lands.
- Operator's instruction goes in `reason` verbatim. Change to `limits.json`:
  `override`, `subject` book id; to `status`: `promote` or `retire` naming
  strategy.
- `critique.run_id` must name a run some runs file holds.
- Correct any line with new line holding `"supersedes": "<full id>"` of same
  kind; newest wins in every view. Superseding hypothesis spends trial of
  its family only when its `falsifier_by` is later than superseded line's
  (line without one compares equal): bare `check` `trials_used` counts run
  lines plus those. Add odds in own line before moving kill date. Scorecard
  `trials`, DSR's count, still counts backtests only.
- Holdings import once as `fills` with `strategy: "opening"`, `proposal`
  null, from pasted table or broker export.
- `record` accepts more fields; `id`, `ts` are reserved.

### Pad

Pad is free memory, never gated: append one JSON object per line, with `ts`
(ISO) and `type`, to `ledger/pad/scratch.jsonl` with own file tools; grep it
to read. Types used here: `hunch`, `objection`, `question` (only operator
can answer), `answer` (`question`: answered line's `ts`; `text`: operator's
words), `friction`, `injection`, `heartbeat`; `check --schema pad` lists
all. Append `answer` when operator replies to `question`.

## Strategy

Register hypothesis before any strategy code for it exists; `measure`
refuses strategy no hypothesis line names. Author writes
`strategies/<name>/` (`signal.py`, `config.json`) to contract
`check --schema strategy` prints.

Write no `status` file; absent means `research`. `live`, `retired` land only
on operator's yes: write `status`, record `promote` (or `retire`) naming
strategy, in same step.

`measure` trades next open after each period's last day, normalizes to gross
1, drops excluded, under-floor, and thin names, caps weight at
`sizing.max_weight`, then clips each weight so quantity at asset cap stays
within `max_adv_participation` of 21-day dollar ADV
(`market.adv_dollar(21)`); clipped weight stays cash. Run breaking cost or
holding bound still writes its line. Never measure again to shop for better
number; change hypothesis, register again. Code fix keeping hypothesis's
claim (sizing, grouping, data handling bug) is new run under same hypothesis
and spends trial; changed claim is new hypothesis. Cite a run only after
`measure --repeat` reproduces it.

`check <strategy>` derives standing of newest research run on every call:
`promotable`, `blocked`, or `discard` (PBO at or above `pbo_discard`). Each
blocker names value and limit: `no run`, `dsr`, `pbo`, `t_alpha`, `factor`,
`capacity`, `cost_share`, `min_holding_days_realized`, `trials`,
`no critique`, `critique: <text>`, `status`, `odds`. Promotion needs DSR
0.95, PBO under 0.10. `odds: none registered on <hypothesis id>` blocks only
when nothing else does. Show operator every blocker, never summary omitting
one.

## Daily loop

Run one lead session per book. Lead holds conversation, runs every `record`,
puts every decision to operator. Agent starts research freely; only operator
starts any action on market.

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
6. Record `close` for each hypothesis past its horizon.
7. Post `check --brief` `lines` verbatim, adding nothing.

Unit of work is one registered hypothesis:

1. Rank families by operator's `focus_sectors` in `preferences.json`; skip
   any family whose `trials_used` in bare `check` reached its `trials` from
   `limits.families`. Bet fitting no family there goes to operator as
   `question` pad entry proposing one.
2. `record` hypothesis; copy its id from `new`.
3. Hand author delegate the unit; it writes `strategies/<name>/`, then its
   `ledger/runs/<agent>.jsonl`, before critique.
4. Hand run id to critique delegate, never run's author; `record` its
   `critiques` batch.
5. Run `check "$B" <name>`; read standing and every blocker.

Every run line counts against family budget, refused and held-out ones too;
`trials` past budget blocks promotion. When family's budget is spent, ask
operator for more through `question` pad entry, quoting `trials_used`; edit
`limits.json` only on their yes.

Agent edits nothing under skill directory, installed copy or checkout. Every
line of code agent writes lives in book (`book`, Agent-written code).

### Delegate through `/summon`

Delegate every unit, one per delegate, unless unit is one command. Mode,
partition, examine sweep are summon's: load its `send` (`divide` for
parallel units) before dispatch, `examine` on return. Delegate can be any
agent that reads `AGENTS.md`. Critique brief never names author nor carries
author's receipt beyond run id.

| Caller supplies | Finance's value |
| --- | --- |
| Unit | one unit, `unit` any slug: author takes one registered hypothesis, critique one run |
| Record | book path; absolute path of `AGENTS.md`, read first; agent name `<unit>-<n>` (`author-1`, `critique-1`), its `--agent` and critique `by`; unit's values (ledger line or run id, dates, names); sibling bounds when parallel |
| Rules it can break | none of four invariants; writes only its scope; never `record`, `recommend`, held-out names; author's run line only through `measure --agent`; critique never run's author |
| Cap | author: "runs you may measure: <trials minus trials_used>"; critique: one run; else summon's sizing |
| Gate | examine, then `record` of batch files delegate names, then `check "$B"` |

| Unit | Writes |
| --- | --- |
| loader | `data/raw/<source>/` and incident lines, both through `load` |
| universe | `research/universe/<date>.md`; `universe.csv` proposal as `hunch` pad line |
| calendar | `research/calendar/<family>.jsonl` |
| reader | `research/<ticker>/<date>-<form>.md`, extracted tables beside it; one ticker |
| author | `strategies/<name>/`, then `ledger/runs/<agent>.jsonl`; one run line through `measure --agent` |
| critique | `research/critiques/<run id>.json`, one `critiques` batch |
| analyst | `research/runs/<run_id>.md`, from `data/returns/` |
| librarian | `research/literature/<slug>.md` |

Always:

- State bet once, labeled as lead's: odds, size, kill observation and date.
  Blockers first, verbatim; never summarize proposal or standing without
  them. Operator decides.
- When asking for decision, give lead's recommended answer and odds behind
  it.

## Propose and approve

Sleeve is strategy whose `status` reads `live`. `recommend` diffs sleeves
against real account (real fills plus opening holdings); `check --live`
monitors each sleeve from its own fills only. `unmanaged` lists held names
outside research set, never sold; never reason from it about held-out
membership. Load `book` before explaining sizing, cuts, carried orders, or
proposal fields.

Size follows evidence. Each sleeve's `tier` comes from ledger: `backtest`
until real fills span `thresholds.tracked_days` (63) calendar days within
`thresholds.tracking_error`, then `tracked`. Tier sets fraction of full
Kelly (`sizing.kelly_fraction`), scaled by `edge_scale` from run's DSR: 0 at
0.5, 1 at 0.95, capped at `sizing.max_weight`. Sleeve with no real fill yet
takes `sizing.entry_weight`. Whole book then scales down when its
1st-percentile 252-day loss passes `sizing.ruin_bound` (`cuts` entry
`kind: ruin`).

1. On rebalance day, after close, run `recommend "$B" <date>`. Sleeve with
   no run line lands in `skipped` with reason; with no sleeve left, exit 1
   names each skipped one and writes nothing. Measure it (baseline's measure
   spends its one trial), then rerun `recommend "$B" <date>` plain.
   `--force` only adds `<date>.<n>.json` beside existing proposal.
2. Run `check "$B" <date>`. Put result to operator in its order: every
   `blockers` entry verbatim, `baseline` row beside every other sleeve, each
   sleeve's `tier`, `edge_scale`, `weight`, `stale` flags, `ruin` loss
   against bound (or its `reasons` entry), then `diff`, `cuts`, `unmanaged`,
   `summary`.
3. Post brief; its last line asks for reply. On approve, record `decision`
   `action: approve`, `subject` proposal stem, `reason` reply verbatim.
4. Operator trades at broker, then pastes table, screenshot, or sentence.
   Transcribe it, show parsed fills back; on yes run
   `record "$B" --fills:file <table> --proposal <stem>`.
5. On reject or override, record `decision` with `subject` proposal stem,
   `action` `reject` or `override`, reply verbatim as `reason`.

## Live

Weekly, run `check "$B" --live`. Per sleeve it measures realized path
against `measure`'s model path, slippage against run's spread plus
commission, drawdown, data age; each breach appends one incident line, once
per strategy and kind per 7 days. Show operator `report` whole, every breach
included. Retire only on operator's word: write `strategies/<name>/status`,
record `retire` naming it. Tracking within bound over `tracked_days` lifts
sleeve's tier at next `recommend`; breach holds it at lower tier.

Drawdown is evidence only when `check --live` reports model-path breach for
that sleeve (`tracking`, or `drawdown` past `drawdown_review_multiple` times
run's `max_drawdown`). Otherwise tell operator drawdown sits inside model
and bound; propose no change.

## Continue

With no `$B`, first ask operator which directory is research monorepo,
before any other step; treat answer as `$B`. Book there: continue. Empty:
make book through `start`. Neither: say what is there, ask again.

At session start, or after context compaction, read `$B/AGENTS.md`, run bare
`check "$B"`, then `check "$B" --brief`; read its `lines` to operator
verbatim; resume from `next`. API keys live in environment only
(`TIINGO_API_KEY`), never in book. Answer operator questions from ledger
first; route claim ledger cannot settle to `/fact-check` or state it open.

## Gotchas

- `measure --repeat` compares each `code_files` digest of `ast.dump`, and
  parsed `config.json`, with working tree: reformat, comment, or reindent
  reproduces; any change to code, docstring, value, or reached module set
  refuses repeat, naming path, as does Python upgrade that changes AST dump.
  Run line without `code_hash` refuses repeat. Moved engine version is
  advisory. Edit measured strategy files and `lib/` modules they import only
  for new run.
- Older book: `paper` or `probe` status reads `live` with signal; `scored`
  lines read as `close` decisions; fill carrying `approval` reads its stem
  as `proposal`; dry-run fills count toward no position.
- No `_factors` loaded (`load french`, or `csv` with symbol `_factors`):
  `factor` null, `check` blocks on `factor: null`. Load factors before first
  `measure`.

## Completion checks

- Every `record` exited 0, or its rejection was corrected and resent.
- Nothing under `ledger/` but `pad/` written except through `record`,
  `measure`, or `check --live`. Bare `check` shows no `warnings`; any
  warning or line `record` refused was reported to operator, not repaired.
- Every new hypothesis names family, falsifier, `falsifier_by`,
  counterparty, and was recorded before its strategy code and its `measure`;
  ids quoted to operator copied from `new`.
- Every resolved bet has `close` decision; `overdue` and `unscored` warnings
  reported to operator.
- Nothing under skill directory edited.
- When `--brief` ran, its `lines` were read to operator verbatim.
- Refused runs reported as trials, not hidden; no family measured past
  budget without operator's answer.
- No critique came from run's author.
- Operator saw every blocker of every standing and proposal read to them.
- Every approve decision recorded before any fill of its proposal.
- No command handed to operator; brief's last line was read verbatim.
