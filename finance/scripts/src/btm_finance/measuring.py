"""The `measure` core, pure given panel, events, rules, strategy, and params: target
weights at each period's last trading day, trades at the next open, holdings
drift close to close, every trade costed, then the scorecard.

Panel and events must already hold only the names being measured. One run is
O(T N + R N L) for T days, N names, R rebalances, L the strategy's lookback.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import reduce
from numbers import Real
from typing import Any

import numpy as np

from btm_corekit import CommandError, signal
from btm_finance.api import FACTORS, Market, carried_forward, on_dates
from btm_finance.data.panel import Delisting, DelistKind, Events, Exchange, Panel
from btm_finance.data.tables import Days, Floats, date_of, day_of
from btm_finance.engine import (
    Spread,
    abdi_ranaldo_window,
    capacity_curve,
    corwin_schultz,
    cost_share,
    cscv,
    deflated_sharpe,
    factor_regression,
    max_drawdown,
    net_returns,
    purged_folds,
    rolling_mean,
    sharpe,
    sr_moments,
    year_sharpe,
)
from btm_finance.engine.metrics import PERIODS_PER_YEAR
from btm_finance.models import (
    Commission,
    Limits,
    Preferences,
    Rebalance,
    StrategyConfig,
    commission_at,
)
from btm_finance.scorecard import (
    FactorCard,
    Scorecard,
    WalkForward,
    finite,
)

WINDOW = 21  # trading days behind ADV, volatility, and spread estimates
LEVELS = (("0.1x", 0.1), ("1x", 1.0))
SHIFTS = (("-20%", 0.8), ("+20%", 1.2))
BLOCKS = 16  # CSCV blocks; PBO needs 2 * BLOCKS common periods
CORE = ("mkt_rf", "smb", "hml", "rmw", "cma", "mom")
EXTRA = (("quality", "qmj"), ("low_risk", "bab"))
Ints = np.ndarray[Any, np.dtype[np.intp]]
Strategy = Callable[[Market, Mapping[str, float]], Any]


@dataclass(frozen=True, slots=True)
class Trade:
    """One name traded at one rebalance, as `lib/costs.py` `cost` sees it:
    `day` the decision day (days since 1970-01-01), `weight` the one-way
    fraction of capital traded, `notional` that in currency at the capital
    being priced, `adv` 21-day dollar ADV, `daily_vol` 21-day volatility,
    `half_spread` the default estimator's, `commission_bps` the limit's."""

    symbol: str
    day: int
    weight: float
    notional: float
    adv: float
    daily_vol: float
    half_spread: float
    commission_bps: float


CostModel = Callable[[Trade, Market], Any]
"""`lib/costs.py` `cost(trade, market)`: proportional cost of one trade."""


@dataclass(frozen=True, slots=True, eq=False)
class Positions:
    """Target weights held each period of a run: rows `dates`, columns
    `names`, as `lib/metrics/<name>.py` `metric` sees them."""

    names: tuple[str, ...]
    dates: Days
    weights: Floats


Metric = Callable[[Floats, Positions, Market], Any]
"""`lib/metrics/<name>.py` `metric(returns, positions, market)`."""


@dataclass(frozen=True, slots=True)
class Rules:
    """Everything besides data one run obeys: the strategy's config, the
    bounds in `limits.json`, the exclusions in `preferences.json`."""

    rebalance: Rebalance
    holding_days: int
    long_only: bool
    asset_cap: float
    max_weight: float
    price_floor: float
    adv_multiple: float
    max_adv_participation: float
    commission_bps: Commission
    impact_coefficient: float
    delisting: Mapping[str, float]
    excluded_symbols: frozenset[str]
    excluded_sectors: frozenset[str]
    folds: int
    touches: tuple[str, ...]
    cutoff: int | None = None
    """`limits.model_cutoff` as days since the epoch."""
    top: tuple[str, float] = ("20x", 20.0)
    """The capacity curve's top point: label, multiple of `asset_cap`."""


def rules_of(limits: Limits, preferences: Preferences, config: StrategyConfig) -> Rules:
    family = limits.families.get(config.family_id)
    return Rules(
        rebalance=config.rebalance,
        holding_days=config.holding_days,
        long_only=config.long_only,
        asset_cap=float(limits.asset_cap),
        max_weight=limits.sizing.max_weight,
        price_floor=limits.price_floor,
        adv_multiple=limits.adv_multiple,
        max_adv_participation=limits.max_adv_participation,
        commission_bps=limits.commission_bps,
        impact_coefficient=limits.impact_coefficient,
        delisting=dict(limits.delisting),
        excluded_symbols=frozenset(preferences.exclusions.symbols),
        excluded_sectors=frozenset(preferences.exclusions.sectors),
        folds=limits.thresholds.folds,
        touches=family.touches if family is not None else (),
        cutoff=None if limits.model_cutoff is None else day_of(limits.model_cutoff),
    )


def per_row(values: Floats) -> tuple[Floats, Floats]:
    """Row sums and counts of the finite cells."""
    present = np.isfinite(values)
    return np.where(present, values, 0.0).sum(axis=1), present.sum(axis=1)


def rolling_std(values: Floats, window: int) -> Floats:
    """Trailing population std over `window` rows, NaN skipped. O(T N)."""
    mean = rolling_mean(values, window)
    square = rolling_mean(values**2, window)
    return np.sqrt(np.maximum(square - mean**2, 0.0))


def terminal(
    record: Delisting, exchange: Exchange, table: Mapping[str, float]
) -> float:
    """The delisting return: merger by its key; performance by exchange, else
    the worst performance return the table holds."""
    match record.kind:
        case DelistKind.MERGER:
            return table.get("merger", 0.0)
        case DelistKind.PERFORMANCE:
            worst = min((v for k, v in table.items() if k != "merger"), default=0.0)
            return table.get(exchange.value, worst)


@dataclass(frozen=True, slots=True, eq=False)
class Prepared:
    """Per-day arrays one panel needs, T by N unless named per name or per day.
    Returns are 0 where unknown; a delisted name returns its terminal return on
    its delisting row and nothing after. A NaN close between a name's first
    and last bar is a day its exchange held no session: price carried, return
    0, no observation for volatility, spread, or ADV; the next bar returns the
    whole move since the last close. Estimates at row t use days up to t."""

    close_cc: Floats
    overnight: Floats
    intraday: Floats
    dead: Ints
    adv: Floats
    vol: Floats
    half_ar: Floats
    half_cs: Floats
    rf: Floats

    @classmethod
    def of(
        cls, panel: Panel, events: Events, delisting: Mapping[str, float]
    ) -> Prepared:
        """O(T N)."""
        days, width = panel.close.shape
        with np.errstate(invalid="ignore", divide="ignore"):
            price = panel.close * panel.adj
            carried = carried_forward(price)
            before = np.vstack((np.full((1, width), np.nan), carried[:-1]))
            close_cc = price / before - 1.0
            overnight = panel.open * panel.adj / before - 1.0
            intraday = panel.close / panel.open - 1.0
        no_open = ~np.isfinite(overnight) | ~np.isfinite(intraday)
        overnight = np.where(no_open, close_cc, overnight)
        intraday = np.where(no_open, 0.0, intraday)
        vol = rolling_std(close_cc, WINDOW)
        close_cc, overnight, intraday = (
            np.nan_to_num(grid, nan=0.0) for grid in (close_cc, overnight, intraday)
        )
        dead = np.full(width, days, dtype=np.intp)
        for column in range(width):
            record = panel.delisting(column)
            if record is None:
                continue
            row = int(np.searchsorted(panel.dates, record.day, side="left"))
            if row >= days:
                continue
            dead[column] = row
            final = terminal(record, panel.exchange[column], delisting)
            for grid in (close_cc, overnight, intraday):
                grid[row:, column] = 0.0
            close_cc[row, column] = overnight[row, column] = final
        with np.errstate(invalid="ignore"):
            adv = rolling_mean(panel.close * panel.volume, WINDOW)
        cs = Spread(rolling_mean(corwin_schultz(panel.high, panel.low).full, WINDOW))
        ar = abdi_ranaldo_window(panel.high, panel.low, panel.close, window=WINDOW)
        return cls(
            close_cc=close_cc,
            overnight=overnight,
            intraday=intraday,
            dead=dead,
            adv=adv,
            vol=vol,
            half_ar=ar.half,
            half_cs=cs.half,
            rf=np.nan_to_num(on_dates(events, FACTORS, "rf", panel.dates), nan=0.0),
        )


def rebalance_rows(dates: Days, cadence: Rebalance) -> Ints:
    """The last row of each month, quarter, or year, except the panel's last
    row, which has no next open to trade at. O(T)."""
    months = dates.astype("datetime64[D]").astype("datetime64[M]").astype(np.int64)
    match cadence:
        case Rebalance.MONTHLY:
            key = months
        case Rebalance.QUARTERLY:
            key = months // 3
        case Rebalance.ANNUAL:
            key = months // 12
    ends: Ints = np.flatnonzero(key[1:] != key[:-1])
    return ends


def number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def commission_of(commission: Commission, panel: Panel) -> Floats:
    """Basis points per name by its exchange; an exchange the map prices
    neither directly nor through `other` pays 0, said once by `signal:`."""
    found = {ex: commission_at(commission, ex.value) for ex in set(panel.exchange)}
    for ex in sorted(ex for ex, bps in found.items() if bps is None):
        signal(f"limits.commission_bps names neither {ex.value} nor other; 0 charged")
    return np.array([found[ex] or 0.0 for ex in panel.exchange], dtype=np.float64)


@dataclass(frozen=True, slots=True, eq=False)
class Setting:
    """One measure's fixed inputs: the scoped data, its arrays, the rules,
    commission per name in basis points, and `lib/costs.py` when the book
    has one, priced in place of the default cost model."""

    panel: Panel
    events: Events
    prep: Prepared
    rules: Rules
    commission: Floats
    cost: CostModel | None = None

    @classmethod
    def of(
        cls, panel: Panel, events: Events, rules: Rules, cost: CostModel | None = None
    ) -> Setting:
        prep = Prepared.of(panel, events, rules.delisting)
        return cls(
            panel,
            events,
            prep,
            rules,
            commission_of(rules.commission_bps, panel),
            cost,
        )


@dataclass(frozen=True, slots=True, eq=False)
class Target:
    """One rebalance's weights; `unknown` names the signal returned but the
    day did not serve; `clipped` names cut to the ADV bound, `intended` gross
    before that cut, `clipped_weight` the gross it removed, left as cash."""

    weights: Floats
    unknown: int
    clipped: int = 0
    intended: float = 0.0
    clipped_weight: float = 0.0


def target_weights(
    raw: object, market: Market, setting: Setting, index: Mapping[str, int], row: int
) -> Target:
    """Signal output to weights: unknown names dropped and counted, negatives
    clipped when long-only, exclusions, price floor, ADV floor, gross 1, cap,
    then each name clipped so its quantity at asset cap stays within
    `max_adv_participation` of 21-day dollar ADV; no renormalizing."""
    panel, prep, rules = setting.panel, setting.prep, setting.rules
    when = date_of(int(panel.dates[row])).isoformat()
    if not isinstance(raw, Mapping):
        raise CommandError(
            f"signal returned {type(raw).__name__} on {when}, not a mapping"
        )
    served = set(market.names)
    weights = np.zeros(len(panel.names))
    unknown = 0
    for name, value in raw.items():
        weight = number(value)
        if not isinstance(name, str) or weight is None:
            raise CommandError(
                f"signal returned {name!r}: {value!r} on {when}; return finite "
                "numbers keyed by name"
            )
        if name not in served:
            unknown += 1
            continue
        weights[index[name]] = weight
    if rules.long_only:
        weights = np.maximum(weights, 0.0)
    for column, name in enumerate(panel.names):
        if (
            name in rules.excluded_symbols
            or panel.sector[column] in rules.excluded_sectors
        ):
            weights[column] = 0.0
    with np.errstate(invalid="ignore"):
        weights[~(panel.close[row] >= rules.price_floor)] = 0.0
    gross = float(np.abs(weights).sum())
    if gross == 0.0:
        return Target(weights, unknown)
    largest = min(rules.max_weight, float(np.abs(weights).max()) / gross)
    floor = rules.adv_multiple * largest * rules.asset_cap
    with np.errstate(invalid="ignore"):
        weights[~(prep.adv[row] >= floor)] = 0.0
    gross = float(np.abs(weights).sum())
    if gross == 0.0:
        return Target(weights, unknown)
    weights = np.clip(weights / gross, -rules.max_weight, rules.max_weight)
    bound = np.nan_to_num(
        rules.max_adv_participation * prep.adv[row] / rules.asset_cap, nan=0.0
    )
    kept = np.clip(weights, -bound, bound)
    intended = float(np.abs(weights).sum())
    return Target(
        kept,
        unknown,
        clipped=int((np.abs(kept) < np.abs(weights)).sum()),
        intended=intended,
        clipped_weight=intended - float(np.abs(kept).sum()),
    )


@dataclass(frozen=True, slots=True, eq=False)
class Track:
    """One simulated run from its first trade: per-period gross return, the
    one-way weight traded per name, the target weights held, the mean gross
    exposure targeted, and the (period, name) cells and gross the ADV bound
    clipped."""

    first: int
    gross: Floats
    trades: Floats
    positions: Floats
    exposure: float
    unknown: int
    clipped: int
    clipped_share: float


def simulate(
    setting: Setting, strategy: Strategy, params: Mapping[str, float]
) -> Track | None:
    """Holdings drift between rebalances, cash earns `rf`; None when the
    strategy never holds a weight. O(T N + R N L)."""
    panel, events, prep = setting.panel, setting.events, setting.prep
    days, width = panel.close.shape
    rows = rebalance_rows(panel.dates, setting.rules.rebalance)
    index = {name: column for column, name in enumerate(panel.names)}
    factor = np.ones(days)
    trades = np.zeros((days, width))
    positions = np.zeros((days, width))
    held = np.zeros(width)
    first: int | None = None
    exposures: list[float] = []
    unknown = clipped = 0
    intended = removed = 0.0
    for k, row in enumerate(rows.tolist()):
        market = Market.at(panel, events, int(panel.dates[row]))
        try:
            raw = strategy(market, params)
        except Exception as err:  # the strategy's failure, named for its author
            when = date_of(int(panel.dates[row])).isoformat()
            raise CommandError(f"signal raised on {when}: {err!r}") from err
        chosen = target_weights(raw, market, setting, index, row)
        unknown += chosen.unknown
        start = row + 1
        target = chosen.weights
        target[prep.dead <= start] = 0.0
        if first is None:
            if not target.any():
                continue
            first = start
        clipped += chosen.clipped
        intended += chosen.intended
        removed += chosen.clipped_weight
        exposures.append(float(np.abs(target).sum()))
        end = int(rows[k + 1]) + 1 if k + 1 < len(rows) else days
        stop = min(end, days - 1)
        trades[start], positions[start : stop + 1] = np.abs(target - held), target
        steps = 1.0 + prep.close_cc[start : stop + 1]
        steps[0] = 1.0 + prep.intraday[start]
        if end < days:
            steps[-1] = 1.0 + prep.overnight[end]
        growth = np.cumprod(steps, axis=0)
        interest = 1.0 + prep.rf[start : stop + 1]
        if end < days:
            interest[-1] = 1.0  # that row's rate accrues to the next holding
        cash = (1.0 - target.sum()) * np.cumprod(interest)
        value = cash + growth @ target
        factor[start : stop + 1] *= value / np.concatenate(([1.0], value[:-1]))
        if end < days:
            held = target * growth[-1] / value[-1]
            held[prep.dead <= end] = 0.0
    if first is None:
        return None
    return Track(
        first=first,
        gross=factor[first:] - 1.0,
        trades=trades[first:],
        positions=positions[first:],
        exposure=float(np.mean(exposures)),
        unknown=unknown,
        clipped=clipped,
        clipped_share=removed / intended if intended else 0.0,
    )


def filled(values: Floats, fallback: float) -> Floats:
    """NaN cells take their row's median of finite cells, else `fallback`."""
    sums_ok = np.isfinite(values)
    out = values.copy()
    for row in np.flatnonzero(~sums_ok.all(axis=1)).tolist():
        known = values[row][sums_ok[row]]
        out[row][~sums_ok[row]] = float(np.median(known)) if known.size else fallback
    return out


@dataclass(frozen=True, slots=True, eq=False)
class Costed:
    """A track's costs at the 1x capital level and the inputs the capacity
    curve reuses; all periods by names."""

    net: Floats
    half_spread: Floats
    adv: Floats
    vol: Floats
    participation_max: float
    half_spread_mean: float | None
    """Half-spread charged, trade-weighted; None when nothing traded."""


def priced(  # noqa: PLR0913 - one track's cost inputs, read once each
    setting: Setting,
    model: CostModel,
    track: Track,
    capital: float,
    *,
    half: Floats,
    adv: Floats,
    vol: Floats,
) -> Floats:
    """Per-period cost of the track under the book's cost model, one call per
    traded cell, at `capital`. O(P N) plus one `Market` per rebalance."""
    panel = setting.panel
    cost = np.zeros(len(track.gross))
    markets: dict[int, Market] = {}
    rows, columns = np.nonzero(track.trades)
    for row, column in zip(rows.tolist(), columns.tolist(), strict=True):
        decision = track.first - 1 + row
        day = int(panel.dates[decision])
        market = markets.get(decision) or Market.at(panel, setting.events, day)
        markets[decision] = market
        weight = float(track.trades[row, column])
        trade = Trade(
            symbol=panel.names[column],
            day=day,
            weight=weight,
            notional=weight * capital,
            adv=float(adv[row, column]),
            daily_vol=float(vol[row, column]),
            half_spread=float(half[row, column]),
            commission_bps=float(setting.commission[column]),
        )
        try:
            rate = number(model(trade, market))
        except Exception as err:  # the book's cost model failed, named for it
            raise CommandError(f"lib/costs.py cost raised: {err!r}") from err
        if rate is None:
            raise CommandError("lib/costs.py cost returned no finite number")
        cost[row] += weight * rate
    return cost


def costed(track: Track, setting: Setting) -> Costed:
    """Half-spread by the estimator primary for the name's ADV against the
    universe median, commission per name, square-root impact; or, with
    `lib/costs.py`, its cost per trade in place of all three. Zero ADV (a
    name quoted with no volume) reads as unknown, like NaN: the day's median
    fills it, so selling it costs a number, not 0 vol times infinite
    participation. O(P N)."""
    prep, rules, commission = setting.prep, setting.rules, setting.commission
    decision = track.first - 1 + np.arange(len(track.gross))
    traded = track.trades != 0.0
    adv_raw = prep.adv[decision]
    with np.errstate(invalid="ignore"):
        adv = filled(np.where(adv_raw > 0.0, adv_raw, np.nan), math.inf)
    vol = filled(prep.vol[decision], 0.0)
    ar, cs = prep.half_ar[decision], prep.half_cs[decision]
    _, counts = per_row(adv_raw)
    with np.errstate(invalid="ignore"):
        median = np.array(
            [
                float(np.median(line[np.isfinite(line)])) if n else math.nan
                for line, n in zip(adv_raw, counts.tolist(), strict=True)
            ]
        )
        below = ~(adv_raw >= median[:, None])
    primary = np.where(below, ar, cs)
    half = np.where(np.isfinite(primary), primary, np.where(below, cs, ar))
    half = filled(np.where(traded, half, np.nan), 0.0)
    half = np.where(traded, half, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        participation = np.where(traded, rules.asset_cap * track.trades / adv, 0.0)
    impact = rules.impact_coefficient * vol * np.sqrt(participation)
    net = (
        net_returns(
            track.gross,
            track.trades,
            half_spread=half,
            commission_bps=commission,
            impact=impact,
        )
        if setting.cost is None
        else track.gross
        - priced(
            setting, setting.cost, track, rules.asset_cap, half=half, adv=adv, vol=vol
        )
    )
    weight = float(track.trades.sum())
    return Costed(
        net=net,
        half_spread=half,
        adv=adv,
        vol=vol,
        participation_max=float(participation.max(initial=0.0)),
        half_spread_mean=finite(float((half * track.trades).sum()) / weight)
        if weight
        else None,
    )


@dataclass(frozen=True, slots=True)
class Peers:
    """The family's earlier run lines: how many, and of the peers (`ids`,
    research runs with a stored series) their per-period net Sharpe where
    recorded and their net series by date."""

    trials: int
    sharpes: tuple[float, ...]
    series: tuple[tuple[Days, Floats], ...]
    ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class Outcome:
    scorecard: Scorecard
    reasons: dict[str, str]
    dates: Days
    gross: Floats
    net: Floats
    unknown: int


@dataclass(frozen=True, slots=True, eq=False)
class Variant:
    dates: Days
    track: Track
    cost: Costed


def run_variant(
    setting: Setting, strategy: Strategy, params: Mapping[str, float]
) -> Variant | None:
    track = simulate(setting, strategy, params)
    if track is None:
        return None
    dates = setting.panel.dates[track.first :]
    return Variant(dates, track, costed(track, setting))


def common_matrix(columns: Sequence[tuple[Days, Floats]]) -> Floats:
    """Columns on the dates every one of them covers. O(C D log D)."""
    shared = reduce(np.intersect1d, [dates for dates, _ in columns])
    return np.column_stack(
        [values[np.searchsorted(dates, shared)] for dates, values in columns]
    )


def pbo_of(columns: Sequence[tuple[Days, Floats]]) -> tuple[float | None, str | None]:
    """CSCV over the trial matrix, O(T N + C B N) with C = comb(16, 8)."""
    if len(columns) < 2:  # noqa: PLR2004 - CSCV ranks at least two trials
        return None, "fewer than 2 trials: no numeric params and no family runs"
    matrix = common_matrix(columns)
    if matrix.shape[0] < 2 * BLOCKS:
        return None, f"{matrix.shape[0]} common periods, under {2 * BLOCKS}"
    return finite(cscv(matrix, blocks=BLOCKS).pbo), None


def post_cutoff(
    dates: Days, excess: Floats, tests: Sequence[Ints], cutoff: int | None
) -> tuple[float | None, str | None]:
    """Net Sharpe over the test folds whose first date is after `cutoff`,
    concatenated; null with its reason. O(T)."""
    if cutoff is None:
        return None, "limits.model_cutoff is null"
    after = [test for test in tests if int(dates[test[0]]) > cutoff]
    if not after:
        return None, f"no test fold starts after {date_of(cutoff).isoformat()}"
    value = finite(sharpe(excess[np.concatenate(after)]))
    return value, None if value is not None else "post-cutoff folds hold no Sharpe"


def walk_forward(
    dates: Days, excess: Floats, rules: Rules
) -> tuple[WalkForward | None, dict[str, str]]:
    folds, embargo = rules.folds, rules.holding_days
    if len(excess) < 2 * folds:
        return None, {
            "walk_forward": f"{len(excess)} periods, under 2 per fold for {folds} folds"
        }
    tests = [
        test for _, test in purged_folds(len(excess), folds=folds, embargo=embargo)
    ]
    sharpes = [finite(sharpe(excess[test])) for test in tests]
    known = [value for value in sharpes if value is not None]
    late, why = post_cutoff(dates, excess, tests, rules.cutoff)
    return WalkForward(
        folds=folds,
        embargo=embargo,
        sharpe=tuple(sharpes),
        mean=finite(float(np.mean(known))) if known else None,
        positive=sum(value > 0 for value in known) / len(sharpes),
        post_cutoff=late,
    ), {} if why is None else {"post_cutoff": why}


def factor_fit(
    events: Events, dates: Days, excess: Floats, touches: Sequence[str]
) -> tuple[FactorCard | None, str | None]:
    """Residual alpha on ff5+mom, plus QMJ or BAB when the family touches
    quality or low risk and the field is loaded."""
    series = {field: on_dates(events, FACTORS, field, dates) for field in CORE}
    absent = [field for field, values in series.items() if np.isnan(values).all()]
    if len(absent) == len(CORE):
        return None, f"no {FACTORS} events; run load french"
    if absent:
        return None, f"{FACTORS} lacks {', '.join(absent)}"
    for touch, field in EXTRA:
        values = on_dates(events, FACTORS, field, dates)
        if touch in touches and not np.isnan(values).all():
            series[field] = values
    names = tuple(series)
    matrix = np.column_stack([series[name] for name in names])
    keep = np.isfinite(matrix).all(axis=1)
    if keep.sum() <= len(names) + 2:
        return None, f"{int(keep.sum())} periods carry every factor"
    fit = factor_regression(excess[keep], matrix[keep], names)
    return FactorCard(
        alpha_annual=finite(fit.alpha_annual),
        t_alpha=finite(fit.t_alpha),
        loadings={name: finite(value) for name, value in fit.loadings.items()},
        model=fit.model,
        r2=finite(fit.r2),
        n=fit.n,
    ), None


def by_year_of(dates: Days, excess: Floats) -> dict[str, float | None]:
    years = (
        dates.astype("datetime64[D]").astype("datetime64[Y]").astype(np.int64) + 1970
    )
    return {key: finite(value) for key, value in year_sharpe(excess, years).items()}


def dsr_of(excess: Floats, peers: Peers) -> float | None:
    sr, skew, kurt = sr_moments(excess)
    if not math.isfinite(sr):
        return None
    trials = peers.trials + 1
    sample = [*peers.sharpes, sr]
    spread = float(np.var(sample, ddof=1)) if len(sample) > 1 and trials > 1 else None
    return finite(
        deflated_sharpe(
            sr, trials=trials, periods=len(excess), skew=skew, kurt=kurt, sr_var=spread
        )
    )


def capacity_of(
    setting: Setting, base: Variant, gross_excess: Floats, levels: Sequence[float]
) -> tuple[float, ...]:
    """Net Sharpe at each capital level: the default cost model's curve, or
    the book's cost model priced at each level."""
    track, cost = base.track, base.cost
    if setting.cost is None:
        return capacity_curve(
            gross_excess,
            track.trades,
            cost.adv,
            capital_levels=tuple(levels),
            daily_vol=cost.vol,
            half_spread=cost.half_spread,
            commission_bps=setting.commission,
            impact_coefficient=setting.rules.impact_coefficient,
        )
    return tuple(
        sharpe(
            gross_excess
            - priced(
                setting,
                setting.cost,
                track,
                capital,
                half=cost.half_spread,
                adv=cost.adv,
                vol=cost.vol,
            )
        )
        for capital in levels
    )


def extra_of(
    metrics: Mapping[str, Metric], setting: Setting, base: Variant
) -> dict[str, float | None]:
    """Each book metric on the run's net series and positions, with the
    `Market` of the last bar; a metric that fails or returns a non-number
    is the book's error, named by file."""
    if not metrics:
        return {}
    panel = setting.panel
    market = Market.at(panel, setting.events, int(panel.dates[-1]))
    positions = Positions(panel.names, base.dates, base.track.positions)
    found: dict[str, float | None] = {}
    for name, metric in sorted(metrics.items()):
        try:
            value = metric(base.cost.net, positions, market)
        except Exception as err:  # the book's metric failed, named for it
            raise CommandError(f"lib/metrics/{name}.py metric raised: {err!r}") from err
        numeric = isinstance(value, Real) and not isinstance(value, bool)
        if value is not None and not numeric:
            raise CommandError(
                f"lib/metrics/{name}.py metric returned {value!r}, not a number"
            )
        found[name] = number(value)
    return found


def evaluate(
    setting: Setting,
    strategy: Strategy,
    params: Mapping[str, float],
    peers: Peers,
    metrics: Mapping[str, Metric] | None = None,
) -> Outcome:
    """The base run, its 2k + 1 perturbation variants, and the scorecard.
    O((2k + 1)(T N + R N L)) plus one CSCV."""
    events, prep, rules = setting.events, setting.prep, setting.rules
    levels = (*LEVELS, rules.top)
    base = run_variant(setting, strategy, params)
    if base is None:
        raise CommandError(
            "signal held no weight on any rebalance day; nothing to measure"
        )
    if len(base.dates) < 2:  # noqa: PLR2004 - a Sharpe needs two periods
        raise CommandError("the first trade falls on the last day; load more history")
    rf = prep.rf[base.track.first :]
    gross_excess, excess = base.track.gross - rf, base.cost.net - rf
    perturbation: dict[str, dict[str, float | None]] = {}
    columns: list[tuple[Days, Floats]] = [(base.dates, base.cost.net)]
    for key in sorted(params):
        perturbation[key] = {}
        for label, scale in SHIFTS:
            moved = {**params, key: params[key] * scale}
            variant = run_variant(setting, strategy, moved)
            if variant is None:
                perturbation[key][label] = None
                continue
            shifted = variant.cost.net - prep.rf[variant.track.first :]
            perturbation[key][label] = finite(sharpe(shifted))
            columns.append((variant.dates, variant.cost.net))
    reasons: dict[str, str] = {}
    pbo, why = pbo_of([*columns, *peers.series])
    if why:
        reasons["pbo"] = why
    folds, why_folds = walk_forward(base.dates, excess, rules)
    reasons |= why_folds
    factor, why = factor_fit(events, base.dates, excess, rules.touches)
    if why:
        reasons["factor"] = why
    track, cost = base.track, base.cost
    periods = len(track.gross)
    one_way = 0.5 * float(track.trades.sum())
    capacity = capacity_of(
        setting, base, gross_excess, [scale * rules.asset_cap for _, scale in levels]
    )
    scorecard = Scorecard(
        sharpe_gross=finite(sharpe(gross_excess)),
        sharpe_net=finite(sharpe(excess)),
        dsr=dsr_of(excess, peers),
        trials=peers.trials + 1,
        pbo=pbo,
        walk_forward=folds,
        by_year=by_year_of(base.dates, excess),
        perturbation=perturbation,
        factor=factor,
        turnover_annual=one_way / (periods / PERIODS_PER_YEAR),
        cost_share=cost_share(gross_excess, excess),
        adv_participation_max=cost.participation_max,
        adv_clipped=track.clipped,
        adv_clipped_share=track.clipped_share,
        min_holding_days_realized=periods * track.exposure / one_way
        if one_way
        else float(periods),
        capacity={
            label: finite(value)
            for (label, _), value in zip(levels, capacity, strict=True)
        },
        half_spread_mean=cost.half_spread_mean,
        max_drawdown=max_drawdown(cost.net),
        extra=extra_of(metrics or {}, setting, base),
    )
    return Outcome(
        scorecard=scorecard,
        reasons=reasons,
        dates=base.dates,
        gross=track.gross,
        net=cost.net,
        unknown=track.unknown,
    )


def bounds(scorecard: Scorecard, limits: Limits) -> list[str]:
    """G3 bounds a finished run breaks, each `<field>: <value> vs <limit>`.
    ADV participation is no bound here: `target_weights` clips to it."""
    broken: list[str] = []
    if scorecard.cost_share > limits.max_cost_share:
        broken.append(
            f"cost_share: {scorecard.cost_share:.4g} vs {limits.max_cost_share}"
        )
    if scorecard.min_holding_days_realized < limits.min_holding_days:
        broken.append(
            f"min_holding_days_realized: {scorecard.min_holding_days_realized:.4g} "
            f"vs {limits.min_holding_days}"
        )
    return broken
