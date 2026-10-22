# Families

Load before registering a hypothesis or proposing a new family to operator.
Families below are favoured for capital at or under the asset cap in
`limits.json`, listed in capacity order: families institutions cannot use
first, crowded large-cap families last.

## Using this list

* Family enters `limits.families` only on operator's yes: propose
  `family_id` and its suggested entry below; on yes, add it and record
  `decision` quoting reply, `applied` naming `limits.json`.
* Entry with `event: true` marks event family: its hypotheses carry `chain`,
  `expectation_source`, `discounted`, `confidence` (load `macro`); `record`
  accepts hypothesis without them, critique item `event-fields` flags each
  one absent; critique adds five `macro` items.
* Treat `capacity_class` as prior. Scorecard `capacity` tests it: `in_band`
  means ceiling between asset cap and scorecard's top point, `under_cap`
  below asset cap, `crowded` above top point.
* Read origin paper as search key only. Retrieve it with `/lit-review`
  before relying on any figure, sign, or sample from it. This file holds no
  return figure and no claim of what works now.
* Load data through `load` routes named per family; `sources` owns route
  ladder.

## forced-selling

* Mechanism: holder forced to sell on rule, not price (index deletion, fund
  outflow, mandate breach) pushes price below value; price recovers as
  forced flow ends.
* Counterparty: index funds and mandate-bound managers; rule fixes timing
  and size, so they sell regardless of price.
* `capacity_class`: `in_band`.
* Data: `csv` index membership history with announce and effective dates;
  bars; `csv` delistings.
* Falsifier: deleted names show no reversal relative to matched non-deleted
  names over `min_holding_days` after effective date.
* Trap: membership file built from current constituents erases deletions
  that later delisted; announce date versus effective date mixed up gives
  look-ahead.
* `limits.families` entry: `"forced-selling": {"trials": 8, "event": true}`.
* Origin: Harris and Gurel 1986, Journal of Finance; Coval and Stafford
  2007, Journal of Financial Economics.

## spin-offs

* Mechanism: parent holders receive shares outside their mandate (size,
  index, sector) and sell them; post-reorganization equity issued to
  creditors meets same selling.
* Counterparty: parent's institutional holders and former creditors, who
  hold shares they never chose and must exit.
* `capacity_class`: `in_band`.
* Data: `edgar` filings (Form 10, 8-K, reorganization plans) for event
  dates; bars; `csv` delistings.
* Falsifier: spun-off or reorganized names show no drift relative to size
  and sector peers after first trading day.
* Trap: survivorship (failed spin-offs and re-bankruptcies delist);
  delisting return convention is material here; first-day price often
  missing in bars.
* `limits.families` entry: `"spin-offs": {"trials": 6, "event": true}`.
* Origin: Cusatis, Miles and Woolridge 1993, Journal of Financial Economics;
  Eberhart, Altman and Aggarwal 1999, Journal of Finance.

## closed-end-discount

* Mechanism: fund trades at discount to net asset value driven by retail
  sentiment; discount narrows on activism, tender, or conversion.
* Counterparty: retail holders selling on sentiment; fund manager resisting
  actions that close discount.
* `capacity_class`: `in_band`.
* Data: `csv` daily net asset value and price per fund; bars.
* Falsifier: widest-discount decile shows no discount narrowing relative to
  narrowest decile over holding period.
* Trap: net asset value stale or published with lag (look-ahead if used same
  day); dead funds missing. Family stays blocked from promotion until a data
  route with at least ten years of daily discounts is evidenced.
* `trials`: 4.
* Origin: Lee, Shleifer and Thaler 1991, Journal of Finance; Pontiff 1995,
  Journal of Financial Economics.

## small-micro-anomaly

* Mechanism: anomaly signals (value, accruals, issuance) price slowly where
  analyst coverage and institutional ownership are thin.
* Counterparty: retail traders and small funds; large funds cannot hold
  enough shares to matter, so they leave mispricing.
* `capacity_class`: `in_band`.
* Data: `edgar` fundamentals; bars; `csv` delistings.
* Falsifier: signal's residual alpha in smallest size quintile is no larger
  than in largest.
* Trap: universe filter (`price_floor`, ADV multiple) applied with later
  price is look-ahead; micro caps delist often, so delisting return
  convention is material; tiny names dominate equal weight.
* `trials`: 10.
* Origin: Banz 1981, Journal of Financial Economics; Fama and French 2008,
  Journal of Finance; Hou, Xue and Zhang 2020, Review of Financial Studies.

## illiquid-mispricing

* Mechanism: names with few trades carry stale prices and an illiquidity
  premium that patient holder collects.
* Counterparty: holders needing liquidity now, who pay spread and impact to
  exit.
* `capacity_class`: `under_cap`; capacity curve may still show `in_band`.
* Data: bars with volume; spread estimators in scorecard `spread_model`.
* Falsifier: return premium of least liquid quintile disappears after
  scorecard costs.
* Trap: stale close prices fake mean reversion; spread underestimated
  (Corwin-Schultz reads low on thin names); delisting return material.
* `trials`: 6.
* Origin: Amihud 2002, Journal of Financial Markets; Pastor and Stambaugh
  2003, Journal of Political Economy.

## event-drift

* Mechanism: price under-reacts to earnings surprise or to changes in filing
  text, then drifts in surprise direction.
* Counterparty: investors anchored on prior estimate, slow to update.
* `capacity_class`: `in_band` when universe restricted to small and mid
  caps; `crowded` in large caps.
* Data: `edgar` fundamentals and filing text with release dates; bars.
* Falsifier: top surprise decile shows no drift over bottom decile after
  filing knowledge time.
* Trap: restated figures used at original date; surprise measured against
  value known only after filing; event time read instead of knowledge time.
* `limits.families` entry: `"event-drift": {"trials": 8, "event": true}`.
* Origin: Bernard and Thomas 1989, Journal of Accounting Research; Cohen,
  Malloy and Nguyen 2020, Journal of Finance.

## large-cap-factor

* Mechanism: published factor premia (value, momentum, quality, low risk) in
  liquid names.
* Counterparty: unclear; largest funds trade same signals.
* `capacity_class`: `crowded`. Promotion needs explicit reason.
* Data: bars; `edgar` fundamentals; `french` factor returns.
* Falsifier: residual alpha on factor model not above `t_empirical`.
* Trap: known factor in disguise; scorecard `factor` regression usually
  absorbs it.
* `trials`: 3.
* Origin: Fama and French 1993, Journal of Financial Economics; Jegadeesh
  and Titman 1993, Journal of Finance; Frazzini and Pedersen 2014, Journal
  of Financial Economics.

## Combinations

Every combination tried is trial, written down or not. Combination of
signals from families above follows four rules:

* Combination is hypothesis: name two or three components, mechanism for why
  they add, and expected orthogonality (correlation of component signals
  under stated bound on training folds).
* Search over combinations only inside training folds of registered strategy
  whose `config.params` declares search space; `measure` counts it as one
  trial, purged test folds and PBO judge it.
* Prefer few, slow, economically distinct components (flow signal plus
  fundamental signal plus liquidity screen) over many correlated ones.
  Report `effective_streams` on every combination.
* Record every combination considered and rejected in `research/backlog/`
  with reason, so critique item `multiplicity` sees it.

## Registering a hypothesis

1. Pick `capacity_class` first: prefer families above `large-cap-factor`.
2. Pick `sector` from `focus_sectors` in `preferences.json`.
3. Write falsifier before any code exists under `strategies/<name>/`.
4. Event family (`forced-selling` below): add four `macro` fields.

```json
{"hypotheses": [{"kw": ["index", "deletion"], "strategy": "index-deletion", "family_id": "forced-selling", "capacity_class": "in_band", "falsifier": "Deleted names show no excess return over matched non-deleted names across 21 trading days after effective date.", "counterparty": "Index funds that must sell deleted names at effective date regardless of price.", "min_holding_days": 21, "mechanism": "Rule-forced selling pushes price below value; price recovers once forced flow ends.", "sector": "Industrials", "chain": "deletion-under-stress", "expectation_source": "Index provider announcement before effective date.", "discounted": "Price discounts announced deletion; hypothesis disagrees that forced flow is fully absorbed by effective date.", "confidence": 0.4}]}
```
