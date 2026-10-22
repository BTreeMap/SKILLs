# Onboard through start

Load only for book without `AGENTS.md`, or empty directory (Continue).
`start --answers:file` writes book-root instructions: `README.md` for
humans, `AGENTS.md` for agents, `CLAUDE.md` pointing at `AGENTS.md`.

## Questions

Send these in one message, after directory question. Accept partial answers;
bracketed default applies to any answer operator leaves out or says default
to.

```text
1. Jurisdiction and base currency. [your locale]
2. Broker and accounts: names, types (taxable, sheltered), which account
   sleeves trade in, whether broker has an API. [no API: check prints
   orders for hand entry]
3. Capital: asset cap now, and expected in six months. [10000000]
4. Risk in two numbers: largest one-year loss of book you accept
   (ruin_bound), and Kelly fraction for backtest-only edges. [0.35; 0.25]
5. Horizon and cadence: holding period, rebalance cadence (monthly or
   quarterly), hour of daily brief (0 to 23), every day or weekdays only.
   [weeks to years; monthly; 7; weekdays]
6. Universe: index or list, exchanges, market-cap ceiling, exclusions by
   sector, symbol, country; focus sectors. [universe CSV given at start]
7. Data sources: tiingo, EDGAR (contact name and email), French factors.
   Keys stay in your environment, never in book. [free sources only:
   csv, edgar, french]
8. Training cutoff of agent's model, for hindsight check. [agent's stated
   cutoff]
9. Held-out list path, outside book. [under XDG_STATE_HOME]
10. Other agents or people working in this book, and whether each may
    propose. [you only]
```

For question 8 default, state own training cutoff; write it only after
operator confirms.

## Answers file

1. Write `answers.json` outside book in shape `check --schema answers`
   prints; omit every key operator left to default. `sources` records which
   sources book uses and EDGAR contact string only; no key, token, or
   password: unknown keys refuse.
2. Empty directory: `$R start "$B" --answers:file answers.json` plus
   `--universe:file` when operator gave one. `start` fills `limits.json` and
   `preferences.json` (`schedule` from `brief_hour` and `schedule`) from
   answers, commits scaffold as `start: <id>`, records `onboard` decision
   naming blob id of every governed file it wrote.
3. Existing book: `$R start "$B" --answers:file answers.json`. It writes
   three files, and `limits.json` when any answer differs, commits them as
   `onboard: <id>`, under `onboard` decision. Tell operator every `limits`
   entry (dotted path to value) written. Read `preferences` batch to
   operator; on confirmation, `record` it.
4. Create scheduled task with harness's scheduler (`/schedule` in Claude
   Code; `cron` elsewhere) running Daily loop at `schedule.hour` on
   `schedule.days` from `preferences.json`.
5. Run bare `check "$B"`; no `README.md`, `AGENTS.md`, `CLAUDE.md`, or
   governed-file warning remains.

On existing book, `start` refuses when any of three files exists; `--force`
rewrites all three, only on operator's word.

## Editing the files

- Lead may edit prose in `README.md` and `AGENTS.md`. `README.md` is for
  operator, who never reads skill: plain sentences, no verb, command, flag,
  or path but `ledger/`.
- Keep `AGENTS.md` `## Invariants` section verbatim: bare `check` warns when
  it differs from template.
- Keep `CLAUDE.md` relative symlink to `AGENTS.md`, or where symlinks fail,
  one line `Read AGENTS.md.`.
- New answers later: rerun `start --answers:file --force` with full
  `answers.json`; hand-written prose in three files is lost.
