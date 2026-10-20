"""Proposal arithmetic, pure: positions replayed from fills, sleeves sized by
volatility target under a fractional Kelly cap, divided by correlation and
capped by risk share, per-name caps, whole-share orders diffed against held
positions, ADV cuts, carried orders, summary.

Sizing and the diff are O(S N + S^2 T log T) for S sleeves, N names, T
periods; replay is O(F) for F fills. Paper and live books never net.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from btm_corekit import Model
from btm_finance.ledger import Row
from btm_finance.models import Price, Side, Sizing, Status
from btm_finance.regimes import RegimeRef
from btm_finance.streams import (
    Series,
    divisors,
    effective_streams,
    pairs_of,
    risk_capped,
)

TOP = 10  # names in the concentration figure
BPS = 1e-4


class Account(StrEnum):
    """The position book a sleeve diffs against: its own dry-run fills, or
    the real fills (opening holdings included) every live sleeve shares."""

    PAPER = "paper"
    LIVE = "live"

    @property
    def dry_run(self) -> bool:
        match self:
            case Account.PAPER:
                return True
            case Account.LIVE:
                return False


def account_of(status: Status | None) -> Account | None:
    """Paper and live strategies are sleeves; research and retired are not."""
    match status:
        case Status.PAPER:
            return Account.PAPER
        case Status.LIVE:
            return Account.LIVE
        case Status.RESEARCH | Status.RETIRED | None:
            return None


class Order(Model):
    """One order as `approvals/<date>.json` lists it and `bin/send` reads it;
    `limit` null is market-on-open."""

    symbol: str
    side: Side
    quantity: Annotated[int, Field(gt=0)]
    price: Price
    adv_participation: float
    strategy: str
    limit: Price | None = None


class Proposed(Order):
    """An order with the positions it moves between."""

    account: Account
    held: float
    target: int
    carried_from: str | None = None


class Sleeve(Model):
    """One sleeve's sizing: `weight` is min(`vol_weight`, `kelly_cap`) over
    `divisor`, risk-share capped, the sum over sleeves scaled to at most 1."""

    strategy: str
    account: Account
    run_id: str
    sharpe_net: float | None
    vol_net: float | None
    max_drawdown: float | None
    vol_weight: float
    kelly_cap: float
    divisor: float
    weight: float
    code_changed: bool
    unknown: int
    signal: dict[str, float]


class Target(Model):
    """One name's capped weight of the cap, per sleeve, and whole shares."""

    weight: float
    sleeves: dict[str, float]
    quantity: dict[str, int]
    price: float
    sector: str


class CutKind(StrEnum):
    ADV = "adv"
    RISK_SHARE = "risk_share"


class AdvCut(Model):
    """An order cut to the ADV bound: `wanted` and `kept` in shares."""

    kind: Literal[CutKind.ADV] = CutKind.ADV
    symbol: str
    strategy: str
    wanted: int
    kept: int
    adv_participation: float
    bound: float


class RiskCut(Model):
    """A sleeve cut to the risk-share cap: `wanted` and `kept` are sleeve
    weights, `share` its risk share before the cap."""

    kind: Literal[CutKind.RISK_SHARE] = CutKind.RISK_SHARE
    strategy: str
    wanted: float
    kept: float
    share: float
    bound: float


Cut = Annotated[AdvCut | RiskCut, Field(discriminator="kind")]


class Holding(Model):
    """A position outside the names the sleeves see: shown, never sold."""

    symbol: str
    quantity: float
    account: Account
    strategy: str


class Carried(Model):
    """An unfilled order of the previous proposal; `merged` when this
    proposal's order for the same symbol, sleeve, and side carries it."""

    symbol: str
    strategy: str
    side: Side
    quantity: int
    carried_from: str
    merged: bool


class Skipped(Model):
    strategy: str
    reason: str


class Summary(Model):
    """Weights are of the cap; `cost` in currency; `turnover` one-way."""

    gross: float
    net: float
    cash: float
    sectors: dict[str, float]
    top10: float
    cost: float
    turnover: float
    orders: int


class Proposal(Model):
    """`proposals/<date>.json`, written once by `recommend`."""

    date: str
    as_of: str
    cap: int
    sleeves: dict[str, Sleeve]
    skipped: tuple[Skipped, ...]
    targets: dict[str, Target]
    orders: tuple[Proposed, ...]
    summary: Summary
    unmanaged: tuple[Holding, ...]
    carried: tuple[Carried, ...]
    cuts: tuple[Cut, ...]
    regime: RegimeRef | None
    effective_streams: float | None


class Approval(Model):
    """The operator's `approvals/<date>.json`; `proposal` names the file."""

    date: str
    proposal: str
    orders: tuple[Order, ...]


def approval_of(proposal: Proposal, stem: str) -> Approval:
    """Every proposed order in approval shape, dated as the proposal."""
    fields = set(Order.model_fields)
    return Approval(
        date=proposal.date,
        proposal=stem,
        orders=tuple(
            Order.model_validate(order.model_dump(include=fields))
            for order in proposal.orders
        ),
    )


@dataclass(frozen=True, slots=True)
class Candidate:
    """One sleeve as measured, and its target weights on the as-of day as
    `measure` would set them."""

    strategy: str
    account: Account
    run_id: str
    sharpe_net: float | None
    vol_net: float | None
    max_drawdown: float | None
    half_spread: float
    code_changed: bool
    unknown: int
    signal: Mapping[str, float]
    weights: Mapping[str, float]
    series: Series | None = None


@dataclass(frozen=True, slots=True)
class Quote:
    """Last close on or before the date, 21-day dollar ADV (NaN unknown)."""

    price: float
    adv: float
    sector: str


@dataclass(frozen=True, slots=True)
class Previous:
    """The newest earlier proposal, by file stem, and whether a `reject`
    decision names it."""

    stem: str
    proposal: Proposal
    rejected: bool


@dataclass(frozen=True, slots=True)
class Inputs:
    date: str
    as_of: str
    cap: int
    sizing: Sizing
    bound: float
    commission_bps: float
    candidates: tuple[Candidate, ...]
    skipped: tuple[Skipped, ...]
    quotes: Mapping[str, Quote]
    fills: Sequence[Row]
    previous: Previous | None
    risk_share: float = 1.0
    regime: RegimeRef | None = None


def sleeve_size(
    sharpe: float | None, vol: float | None, sizing: Sizing
) -> tuple[float, float]:
    """(vol_target / vol, kelly_fraction * sharpe / vol), annual units; zero
    when either input is missing or vol is not positive."""
    if sharpe is None or vol is None or not vol > 0.0:
        return 0.0, 0.0
    return sizing.vol_target / vol, max(sizing.kelly_fraction * sharpe / vol, 0.0)


@dataclass(frozen=True, slots=True)
class SleeveSizes:
    weights: dict[str, float]
    cuts: tuple[RiskCut, ...]


def sleeve_weights(
    candidates: Sequence[Candidate],
    sizing: Sizing,
    divisor: Mapping[str, float] | None = None,
    share: float = 1.0,
) -> SleeveSizes:
    """min(vol weight, Kelly cap) over `divisor`, risk-share capped, then
    scaled so the sum is at most 1. O(S log S)."""
    raw = {
        c.strategy: min(sleeve_size(c.sharpe_net, c.vol_net, sizing))
        / (divisor or {}).get(c.strategy, 1.0)
        for c in candidates
    }
    vols = {c.strategy: c.vol_net or 0.0 for c in candidates}
    capped = risk_capped(raw, vols, share)
    total_risk = sum(w * vols[name] for name, w in raw.items())
    total = sum(capped.values())
    scale = 1.0 / total if total > 1.0 else 1.0
    cuts = tuple(
        RiskCut(
            strategy=name,
            wanted=raw[name] * scale,
            kept=capped[name] * scale,
            share=raw[name] * vols[name] / total_risk,
            bound=share,
        )
        for name in raw
        if capped[name] < raw[name]
    )
    return SleeveSizes({name: w * scale for name, w in capped.items()}, cuts)


def combined(
    candidates: Sequence[Candidate], weights: Mapping[str, float], max_weight: float
) -> dict[str, dict[str, float]]:
    """Name to sleeve to fraction of the cap; a name whose net across sleeves
    passes `max_weight` is scaled down in every sleeve alike. O(S N)."""
    by_name: dict[str, dict[str, float]] = defaultdict(dict)
    for candidate in candidates:
        weight = weights[candidate.strategy]
        for name, share in candidate.weights.items():
            if weight * share != 0.0:
                by_name[name][candidate.strategy] = weight * share
    for parts in by_name.values():
        net = abs(sum(parts.values()))
        if net > max_weight:
            for strategy in parts:
                parts[strategy] *= max_weight / net
    return dict(by_name)


def whole(fraction: float, cap: int, price: float) -> int:
    """Whole shares worth `fraction` of the cap, toward zero."""
    return int(fraction * cap / price)


Shares = dict[str, float]


def replay(fills: Iterable[Row]) -> dict[tuple[Account, str], Shares]:
    """Signed positions per (account, strategy) from the live fill rows: a
    dry-run fill lands in the paper book, every other in the live one. O(F)."""
    books: dict[tuple[Account, str], Shares] = defaultdict(lambda: defaultdict(float))
    for row in fills:
        quantity = row.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, int | float):
            continue
        sign = 1.0 if row.get("side") == Side.BUY.value else -1.0
        account = Account.PAPER if row.get("dry_run") is True else Account.LIVE
        books[account, str(row.get("strategy"))][str(row.get("symbol"))] += (
            sign * quantity
        )
    return {key: dict(book) for key, book in books.items()}


def live_held(
    sleeves: Sequence[str],
    books: Mapping[tuple[Account, str], Shares],
    targets: Mapping[str, Mapping[str, int]],
) -> dict[str, Shares]:
    """Each live sleeve's share of the one real book. Real shares no live
    sleeve filled (opening holdings, retired sleeves) form a pool that fills
    sleeves' buys in name order; what is left lands on the last sleeve, so
    its diff sells it. O(S N)."""
    held = {s: dict(books.get((Account.LIVE, s), {})) for s in sleeves}
    pool: Shares = defaultdict(float)
    for (account, strategy), book in books.items():
        if account is Account.LIVE and strategy not in held:
            for symbol, quantity in book.items():
                pool[symbol] += quantity
    for symbol, quantity in pool.items():
        left = quantity
        for strategy in sleeves:
            own = held[strategy].get(symbol, 0.0)
            want = targets.get(strategy, {}).get(symbol, 0)
            take = min(max(want - own, 0.0), max(left, 0.0))
            held[strategy][symbol] = own + take
            left -= take
        held[sleeves[-1]][symbol] = held[sleeves[-1]].get(symbol, 0.0) + left
    return held


def participation(quantity: int, quote: Quote) -> float:
    if not quote.adv > 0.0:
        return math.inf
    return quantity * quote.price / quote.adv


def capped(quantity: int, quote: Quote, bound: float) -> int:
    """Largest whole quantity at or under `bound` of ADV; 0 when ADV unknown."""
    if not quote.adv > 0.0:
        return 0
    return min(quantity, int(bound * quote.adv / quote.price))


@dataclass(frozen=True, slots=True)
class Diffed:
    orders: tuple[Proposed, ...]
    cuts: tuple[AdvCut, ...]
    unmanaged: tuple[Holding, ...]


def diff(  # noqa: PLR0913 - one sleeve's whole diff
    strategy: str,
    account: Account,
    held: Shares,
    target: Mapping[str, int],
    *,
    quotes: Mapping[str, Quote],
    bound: float,
) -> Diffed:
    """Orders moving `held` to `target`, each cut to `bound` of ADV; held
    names without a quote are unmanaged. O(N)."""
    orders: list[Proposed] = []
    cuts: list[AdvCut] = []
    unmanaged: list[Holding] = []
    for symbol in sorted(set(held) | set(target)):
        now = held.get(symbol, 0.0)
        quote = quotes.get(symbol)
        if quote is None:
            if now:
                unmanaged.append(
                    Holding(
                        symbol=symbol, quantity=now, account=account, strategy=strategy
                    )
                )
            continue
        goal = target.get(symbol, 0)
        wanted = int(abs(goal - now))
        if wanted == 0:
            continue
        kept = capped(wanted, quote, bound)
        if kept < wanted:
            cuts.append(
                AdvCut(
                    symbol=symbol,
                    strategy=strategy,
                    wanted=wanted,
                    kept=kept,
                    adv_participation=participation(wanted, quote),
                    bound=bound,
                )
            )
        if kept == 0:
            continue
        orders.append(
            Proposed(
                symbol=symbol,
                side=Side.BUY if goal > now else Side.SELL,
                quantity=kept,
                price=quote.price,
                adv_participation=participation(kept, quote),
                strategy=strategy,
                account=account,
                held=now,
                target=goal,
            )
        )
    return Diffed(tuple(orders), tuple(cuts), tuple(unmanaged))


def filled(order: Order, account: Account, since: str, fills: Iterable[Row]) -> bool:
    """A fill of the same symbol, sleeve, side, and book dated on or after
    `since`."""
    return any(
        row.get("symbol") == order.symbol
        and row.get("strategy") == order.strategy
        and row.get("side") == order.side.value
        and (row.get("dry_run") is True) == account.dry_run
        and str(row.get("date", "")) >= since
        for row in fills
    )


def carry(
    previous: Previous | None, orders: Sequence[Proposed], fills: Sequence[Row]
) -> tuple[tuple[Proposed, ...], tuple[Carried, ...]]:
    """Mark this proposal's order that carries each unfilled earlier order;
    a rejected proposal carries nothing. O(P (N + F)) for P earlier orders."""
    if previous is None or previous.rejected:
        return tuple(orders), ()
    keyed = {(o.symbol, o.strategy, o.side): i for i, o in enumerate(orders)}
    marked = list(orders)
    carried: list[Carried] = []
    since = previous.proposal.date
    for old in previous.proposal.orders:
        if filled(old, old.account, since, fills):
            continue
        index = keyed.get((old.symbol, old.strategy, old.side))
        if index is not None:
            marked[index] = marked[index].with_(carried_from=previous.stem)
        carried.append(
            Carried(
                symbol=old.symbol,
                strategy=old.strategy,
                side=old.side,
                quantity=old.quantity,
                carried_from=previous.stem,
                merged=index is not None,
            )
        )
    return tuple(marked), tuple(carried)


def summary_of(
    targets: Mapping[str, Target],
    orders: Sequence[Proposed],
    spreads: Mapping[str, float],
    cap: int,
    commission_bps: float,
) -> Summary:
    """Gross, net, cash, sector and top-10 weights of the whole-share
    targets; cost at each sleeve's measured half-spread plus commission."""
    weights = {
        name: sum(target.quantity.values()) * target.price / cap
        for name, target in targets.items()
    }
    gross = sum(abs(w) for w in weights.values())
    net = sum(weights.values())
    sectors: dict[str, float] = defaultdict(float)
    for name, weight in weights.items():
        sectors[targets[name].sector] += weight
    top = sorted((abs(w) for w in weights.values()), reverse=True)[:TOP]
    notional = [order.quantity * order.price for order in orders]
    cost = sum(
        value * (spreads.get(order.strategy, 0.0) + commission_bps * BPS)
        for value, order in zip(notional, orders, strict=True)
    )
    return Summary(
        gross=gross,
        net=net,
        cash=1.0 - net,
        sectors=dict(sorted(sectors.items())),
        top10=sum(top) / gross if gross else 0.0,
        cost=cost,
        turnover=0.5 * sum(notional) / cap,
        orders=len(orders),
    )


def targets_of(
    shares: Mapping[str, Mapping[str, float]],
    quotes: Mapping[str, Quote],
    cap: int,
) -> dict[str, Target]:
    """Whole shares per name and sleeve at the reference price. O(S N)."""
    found: dict[str, Target] = {}
    for name in sorted(shares):
        quote = quotes[name]
        parts = shares[name]
        found[name] = Target(
            weight=sum(parts.values()),
            sleeves=dict(sorted(parts.items())),
            quantity={s: whole(w, cap, quote.price) for s, w in sorted(parts.items())},
            price=quote.price,
            sector=quote.sector,
        )
    return found


def by_sleeve(targets: Mapping[str, Target]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = defaultdict(dict)
    for name, target in targets.items():
        for strategy, quantity in target.quantity.items():
            out[strategy][name] = quantity
    return dict(out)


def held_of(
    candidates: Sequence[Candidate],
    books: Mapping[tuple[Account, str], Shares],
    wanted: Mapping[str, Mapping[str, int]],
) -> dict[str, Shares]:
    """Paper sleeves hold their own dry-run fills; live sleeves share the
    real book through `live_held`."""
    live = sorted(c.strategy for c in candidates if c.account is Account.LIVE)
    shares = live_held(live, books, wanted) if live else {}
    return {
        c.strategy: shares[c.strategy]
        if c.account is Account.LIVE
        else dict(books.get((Account.PAPER, c.strategy), {}))
        for c in candidates
    }


def unmanaged_real(
    books: Mapping[tuple[Account, str], Shares], quotes: Mapping[str, Quote]
) -> list[Holding]:
    """Real positions outside the sleeves' names, when no live sleeve diffs
    the real book."""
    return [
        Holding(symbol=symbol, quantity=quantity, account=account, strategy=strategy)
        for (account, strategy), book in sorted(books.items())
        if account is Account.LIVE
        for symbol, quantity in sorted(book.items())
        if quantity and symbol not in quotes
    ]


def propose(inputs: Inputs) -> Proposal:
    """The whole proposal from its inputs; deterministic given them."""
    sizing, cap = inputs.sizing, inputs.cap
    candidates = inputs.candidates
    names = [c.strategy for c in candidates]
    pairs = pairs_of({c.strategy: c.series for c in candidates})
    divisor = divisors(names, pairs)
    sized = sleeve_weights(candidates, sizing, divisor, inputs.risk_share)
    weights = sized.weights
    shares = combined(candidates, weights, sizing.max_weight)
    targets = targets_of(shares, inputs.quotes, cap)
    wanted = by_sleeve(targets)
    books = replay(inputs.fills)
    held = held_of(candidates, books, wanted)
    orders: list[Proposed] = []
    cuts: list[AdvCut | RiskCut] = list(sized.cuts)
    unmanaged: list[Holding] = []
    for candidate in candidates:
        done = diff(
            candidate.strategy,
            candidate.account,
            held[candidate.strategy],
            wanted.get(candidate.strategy, {}),
            quotes=inputs.quotes,
            bound=inputs.bound,
        )
        orders += done.orders
        cuts += done.cuts
        unmanaged += done.unmanaged
    if not any(c.account is Account.LIVE for c in candidates):
        unmanaged += unmanaged_real(books, inputs.quotes)
    marked, carried = carry(inputs.previous, orders, inputs.fills)
    spreads = {c.strategy: c.half_spread for c in candidates}
    sizes = {
        c.strategy: sleeve_size(c.sharpe_net, c.vol_net, sizing) for c in candidates
    }
    sleeves = {
        c.strategy: Sleeve(
            strategy=c.strategy,
            account=c.account,
            run_id=c.run_id,
            sharpe_net=c.sharpe_net,
            vol_net=c.vol_net,
            max_drawdown=c.max_drawdown,
            vol_weight=sizes[c.strategy][0],
            kelly_cap=sizes[c.strategy][1],
            divisor=divisor[c.strategy],
            weight=weights[c.strategy],
            code_changed=c.code_changed,
            unknown=c.unknown,
            signal=dict(sorted(c.signal.items())),
        )
        for c in candidates
    }
    # ext/ plug-ins (jurisdiction annotations) are deferred; they would run here.
    return Proposal(
        date=inputs.date,
        as_of=inputs.as_of,
        cap=cap,
        sleeves=sleeves,
        skipped=inputs.skipped,
        targets=targets,
        orders=marked,
        summary=summary_of(targets, marked, spreads, cap, inputs.commission_bps),
        unmanaged=tuple(unmanaged),
        carried=carried,
        cuts=tuple(cuts),
        regime=inputs.regime,
        effective_streams=effective_streams(
            [c.strategy for c in candidates if c.series is not None], pairs
        ),
    )
