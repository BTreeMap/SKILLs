# Macro

Load when regime delegate drafts regime record, when lead puts draft to
operator, when lead registers hypothesis in family flagged `event: true` in
`limits.families`, and in critique delegate beside `critique`. Three rules
keep macro out of signals:

* No strategy conditions on macro variable unless its hypothesis registers
  that variable as mechanism and scorecard regime split tests it.
* Regime position is human-confirmed record, never number script derives.
* Carry no chain lacking observable and falsifier.

## Pricing identity

Every asset is lump sum today traded for cash flows later. Four determinants
move price: expected growth (cash flows), expected inflation (their
purchasing power), risk premium (excess over cash investors demand),
discount rate (what cash earns). Total return is yield plus price change.
10-year yield splits into real yield (discount leg) and breakeven inflation
(inflation leg), both read from market.

* Name which determinant moved before accepting any story about a price.

## Three motions

Productivity trend: output per person rises over decades as people learn and
invent; cycles oscillate around it. Over one to ten years cycles dominate;
past ten years trend dominates. Multi-year holds carry more trend exposure,
which is why baseline strategy exists.

Short-term debt cycle (illustration: about six years, give or take three):
ease, credit cheap, spending and asset prices rise, incomes then inflation
follow with lags, tighten, reverse; example below chain grammar writes it
out. Observables: policy rate against inflation, credit growth against
income growth, yield curve, breakeven inflation. Read surprise as deviation
from chain, not from headline.

Long-term debt cycle (illustration: about eighty years, give or take
twenty-five): each short cycle ends with more debt to income than last,
since easing ends each recession. Phases in order: (1) early, debt finances
income growth, burdens flat; (2) bubble, debt outgrows income for years
(checklist below); (3) top, tightening meets leveraged system, debt service
outruns income; (4) depression, falling prices cut collateral, lenders pull
back, forced selling feeds itself, rates at zero remove usual fix; (5)
deleveraging; (6) normalization, usually years later. Deleveraging levers,
reached for in this order (each less painful to someone than last):
austerity; defaults and restructurings; transfers from haves to have-nots;
money printing and asset purchases. Outcome is benign when mix pushes
nominal growth above nominal rates with tolerable inflation. Where easing
stops working (rates at zero, purchases no longer reach real economy),
direct fiscal and monetary coordination follows.

Variant: debt in own currency gives deflationary deleveraging; much debt in
foreign currency plus stopped capital inflows gives inflationary one, where
currency, not asset prices alone, takes adjustment.

Bubble checklist, counted as set (0 to 7 items present, evidence per item;
no single item decides): (1) prices high against traditional measures; (2)
prices discounting further rapid gains; (3) broad bullish sentiment; (4)
purchases financed by leverage; (5) buyers extended forward (inventory,
forward contracts); (6) new entrants not in market before; (7) easy policy
inflating it, tightening the likely pin.

Other four forces, context lines on regime record only, never walked as
chains (observables slow and contested): internal order (wealth and values
gaps); external order (great-power competition); acts of nature;
technological invention.

## Chain grammar

```text
node      <state variable>  observable: <flow or ratio>, source, as_of
edge      <cause> -> <effect>  sign: +/-, lag: <order of magnitude>, condition: <when it holds>
loop      [<edge>, <edge>, ...]  reversal: <what flips the sign>
constraint <limit>  binds_when: <condition>  branch: <next phase if it binds / if not>
actor     <who>  wants: <objective>  tools: <levers>  sequence: <order they reach for them>
price     <asset> discounts: <expectation>  moves_on: <surprise>
```

* Use flow or ratio as observable, never raw level; count observation as
  evidence only inside its edge's lag window.
* Treat policy maker with reaction function as `actor` node, not shock.

**Example: short-term debt cycle**

```text
node      policy_rate, credit_growth, spending, income, inflation
edge      ease -> credit_growth  sign: +, lag: months
edge      credit_growth -> spending  sign: +, lag: quarters
edge      spending -> income  sign: +, lag: quarters
edge      income -> inflation  sign: +, lag: a year or more
actor     central_bank  wants: growth without inflation  tools: policy_rate  sequence: ease, then tighten on inflation
loop      [credit -> spending, spending -> collateral, collateral -> credit]  reversal: debt service outruns income
constraint zero_floor  binds_when: prior cycle left rates near zero  branch: long-cycle depression phase / normal easing
price     yield_curve discounts: path of policy_rate  moves_on: surprise to that path
```

## Chain table

Cite chain by id. Mark "inference, test before relying on it" is unverified.

| Chain | Trigger | Mechanism | Observable and falsifier | Second-order effect | Implication for favoured families |
| --- | --- | --- | --- | --- | --- |
| `tightening-into-leverage` | Policy rate rising while private debt service to income is high | Debt service on floating and refinanced debt outruns incomes; weakest borrowers cut first | Debt service ratio, refinancing wall, credit spreads; falsified if spreads stay tight two quarters after rate peak | Forced sellers appear in most levered, least liquid names; fund redemptions follow | `forced-selling` and `spin-offs` (post-reorganization) get more candidates; register tightening as counterparty's constraint |
| `easing-into-bubble` | Real rates negative for years, debt growth outrunning income growth | Cheap money bids up long-duration cash flows and assets with no cash flows; new entrants and leverage arrive | Bubble checklist count; falsified if count stays low while prices rise | Small and micro cap anomalies compress as everything rises; crowding risk at momentum peaks (inference, test before relying on it) | Critique flags momentum or quality strategy whose evidence window sits inside high-count period as regime-concentrated |
| `deleveraging-printing` | Policy rate at floor, asset purchases begin | Nominal growth pushed above nominal rates; financial assets reprice before incomes | Real yield, breakeven inflation, central bank balance sheet; falsified if nominal growth stays below rates; for fund-discount claim, discount series must narrow within stated window | Closed-end fund discounts and illiquid spreads close fast, then stay closed (inference, test before relying on it) | `closed-end-discount`: entry in depression phase, exit in early reflation; chain gives holding period |
| `deletion-under-stress` | Rebalance or index review during drawdown | Mechanical sellers sell on date regardless of price; buy side thin in small names | Announcement date, effective date, ADV of deleted names; falsified if price impact absorbed by effective date | Deleted names drift as forced flow ends and fundamentals reassert | `forced-selling`: opportunity scales with stress, so regime record is budget input, not filter |
| `currency-inflation` | Capital inflows stop in country with foreign-currency debt | Currency falls, import prices rise, central bank cannot print its way out | Current account, reserves, external debt share; falsified if currency stabilizes without rate defence | Exporters gain margin, importers lose; cross-listed names misprice against home market | Only if universe holds such markets; otherwise critique item for names with foreign-currency revenue, not family |
| `expectation-vs-outcome` | Any scheduled release or policy decision | Price moves on outcome minus what was discounted, not on level | Priced expectation before event, outcome, move; falsified if move tracks level rather than surprise | Headline confirming discounted path moves nothing; small miss against crowded expectation moves a lot | Event families register `expectation_source`; surprise is signal, level is noise |
| `spin-off-supply` | Parent distributes subsidiary, or company exits restructuring | Holders get shares they did not choose; mandates force sales; coverage and index membership lag | Form 10 filings, days since distribution, holder turnover; falsified if spin trades at parent-like valuation from day one | Supply overhang clears over weeks to months; chain gives entry window | `spin-offs`: holding period and exit rule come from chain, not parameter sweep |

* Walk chain forward only from observed trigger, never from forecast of one.
* If chain's falsifier fires, list its id under regime `falsified` (bare
  `check` warns each hypothesis citing it); write one `objection` pad entry
  per such open hypothesis: chain id, falsifier, observable with source.

## Regime record

Regime delegate drafts from observables and chains, writing
`research/regime/<quarter>.md` and draft batch beside it; lead puts draft to
human, who confirms, edits, or rejects, states `confidence` (0 to 1, never
set by agent). Draft at most quarterly and when falsifier fires; correct by
new line with `supersedes`.

```json
{
  "kw": ["two", "words"],
  "as_of": "<date>",
  "short_cycle": "easing | mid-expansion | late-expansion | tightening | contraction",
  "long_cycle": "early | bubble | top | depression | deleveraging | normalization",
  "bubble_count": {"count": 2, "evidence": ["<one line per item present>", "..."]},
  "policy_mix": ["austerity | defaults | transfers | printing"],
  "other_forces": {"internal_order": "...", "external_order": "...", "nature": "...", "technology": "..."},
  "observables": {"<name>": {"value": "<as reported>", "as_of": "<date>", "source": "<url>"}},
  "confidence": 0.6,
  "falsified": ["<chain id whose falsifier fired>"],
  "supersedes": "<previous regime id>"
}
```

| Consumer | Use | Not allowed |
| --- | --- | --- |
| Hypothesis generation | Weights which families get delegate slots; supplies counterparty constraint registration must name | Hypothesis whose signal is regime itself |
| `measure` | Stamps every run line with regime ids its evidence window spans | Conditioning returns on regime unless hypothesis declared it and scorecard regime split tests it |
| Critique | Checks evidence concentration in one regime, mechanism survival in next phase, holding period crossing likely phase change | Rejecting strategy because critic forecasts regime change |
| `check <proposal>` | Shows regime record id, `as_of`, `stale`, and effective streams beside diff | Changing any weight in proposal |
| Human | Confirms, edits, rejects draft; states confidence | Nothing |

* If newest regime record is older than `limits.regime_stale_days`, `check`
  shows it stale on every proposal; tell operator, dispatch regime delegate
  for renewal.

## Registering event-family hypothesis

If family carries `event: true`, add to hypothesis fields `families` lists.
`record` accepts hypothesis without them; critique item `event-fields` names
each one absent as concern.

* `chain`: chain id from table, or `none`.
* `expectation_source`: where priced expectation is read before event.
* `discounted`: what price already discounts, and where hypothesis
  disagrees.
* `confidence`: number 0 to 1, registrant's stated confidence, apart from
  conclusion.

```json
{"hypotheses": [{"kw": ["earnings", "surprise"], "strategy": "filing-surprise-drift", "family_id": "event-drift", "capacity_class": "in_band", "falsifier": "Top surprise decile shows no drift over bottom decile across 63 trading days after filing knowledge time.", "counterparty": "Investors anchored on prior consensus estimate, slow to update.", "min_holding_days": 21, "mechanism": "Price under-reacts to surprise against discounted estimate, then drifts in surprise direction.", "sector": "Industrials", "chain": "expectation-vs-outcome", "expectation_source": "Consensus estimate as of day before filing knowledge time.", "discounted": "Price discounts consensus estimate; hypothesis disagrees on speed of adjustment after surprise, not on level.", "confidence": 0.4}]}
```

## Portfolio and decision principles

* Uncorrelated streams: treat new strategy highly correlated with live
  sleeve as added trial, not added stream. Read correlation with live
  sleeves and effective streams from `check <strategy>`; both advisory.
* Price is what is discounted: if hypothesis cannot state where it disagrees
  with price, treat it as factor exposure, not hypothesis.
* Size for being wrong: `recommend` scales whole book to `sizing.ruin_bound`
  and reports each sleeve's risk share against
  `limits.max_strategy_risk_share` under `advisory`, never cut; sleeve past
  it is concentration to name to operator.
* Drawdown tolerance: human sets review threshold before strategy goes live;
  use regime record to tell drawdown chain predicts from one it does not.
  Drawdown inside `sizing.ruin_bound` with no `check --live` model-path
  breach is variance, not evidence.
* Believability: discount claim whose source cannot state mechanism. Show
  family track record (critique survival, held-out, paper) as counts; never
  weight budgets by it.
* Confidence: state confidence apart from conclusion on every registration,
  critique, and regime record; show it beside recommendation.
* Third order: ask what happens to strategy when everyone seeing same
  first-order effect acts on it.
* Diagnose before act: if live strategy deviates from measured path, record
  decision with action `diagnose` and reason naming broken link (mechanism,
  data, regime, or crowd). Pause or retire on diagnosis, never on pain
  alone.

## Critique items for macro

Critic applies these beside twelve items and `event-fields` in `critique`,
same verdict rule, and adds each item name to `verdicts`. "None" under
Blocker means concern at most; never block on critic's regime forecast.

| Item | Inspect | Settles | Blocker | Concern |
| --- | --- | --- | --- | --- |
| `chain` | Hypothesis `chain`, `mechanism`; chain table row; regime record observables at hypothesis `ts` | Mechanism relies on named chain; trigger observed at registration, not forecast | Cited trigger forecast, not observed (absent `chain`: `event-fields` concern) | `chain` is `none` where table row fits |
| `regime-band` | Run line regime ids; regime records' `bubble_count` over evidence window; `signal.py` reads of macro variables | Evidence spans more than one regime and bubble-count band, or hypothesis names regime as mechanism | Signal conditions on macro variable hypothesis did not register | Evidence inside one regime or one band |
| `next-phase` | Chain table row; `holding_days` in `config.json`; current regime record | Mechanism holds in next phase of its chain, or holding period ends before likely phase change | None | Mechanism fails in next phase and holding period crosses it |
| `third-order` | Hypothesis `counterparty`, `mechanism`; scorecard `capacity` | Hypothesis states what happens when everyone seeing same first-order effect acts on it | None | Crowding answer absent or contradicted by `capacity` |
| `discounted` | Hypothesis `discounted`, `expectation_source`; `signal.py` surprise construction | Hypothesis names what price discounts and where it disagrees; surprise measured against expectation known before event | Event family signal uses outcome level, not surprise, or reads expectation not known at decision date | Disagreement with price unstated (factor exposure in disguise) |
