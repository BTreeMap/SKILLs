"""Regime records as views, pure: the regime record, its staleness, the run
stamp, and the falsifier join. Derived on every call, never stored."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np

from btm_corekit import Model
from btm_finance.data.tables import Days, day_of
from btm_finance.ledger import Row

NONE = "none"  # the regime_days key for window days before the first record


class RegimeRef(Model):
    """The regime record as `check` and proposals show it."""

    id: str
    as_of: str
    stale: bool


@dataclass(frozen=True, slots=True)
class Dated:
    """One live regime row: its id, `as_of`, and `falsified` chain ids."""

    id: str
    as_of: date
    falsified: tuple[str, ...]


def dated(rows: Sequence[Row]) -> list[Dated]:
    """Live regime rows with a readable `as_of`, ordered by `as_of`, ledger
    order breaking ties. O(R log R)."""
    found: list[Dated] = []
    for row in rows:
        try:
            when = date.fromisoformat(str(row.get("as_of")))
        except ValueError:
            continue
        chains = row.get("falsified")
        found.append(
            Dated(
                id=str(row.get("id")),
                as_of=when,
                falsified=tuple(str(c) for c in chains)
                if isinstance(chains, list)
                else (),
            )
        )
    return sorted(found, key=lambda one: one.as_of)


def regime_record(
    records: Sequence[Dated], today: date, stale_days: int
) -> RegimeRef | None:
    """The newest record by `as_of`; stale when `as_of` is more than
    `stale_days` before `today`. O(1) on sorted records."""
    if not records:
        return None
    newest = records[-1]
    return RegimeRef(
        id=newest.id,
        as_of=newest.as_of.isoformat(),
        stale=(today - newest.as_of).days > stale_days,
    )


def regime_stamp(
    dates: Days, records: Sequence[Dated]
) -> tuple[tuple[str, ...], dict[str, int]]:
    """Record i holds from its `as_of` to record i + 1's; per id, the window
    days it holds, `none` before the first. O(R log W) on sorted inputs."""
    starts = np.asarray([day_of(r.as_of) for r in records], dtype=dates.dtype)
    cuts = np.searchsorted(dates, starts, side="left").tolist()
    bounds = [*cuts, len(dates)]
    days: dict[str, int] = {}
    if bounds[0] > 0:
        days[NONE] = int(bounds[0])
    for index, record in enumerate(records):
        held = int(bounds[index + 1] - bounds[index])
        if held > 0:
            days[record.id] = days.get(record.id, 0) + held
    return tuple(key for key in days if key != NONE), days


def concentration(regime_days: object) -> dict[str, float]:
    """Share of evidence days per regime id; empty for an unstamped run."""
    if not isinstance(regime_days, dict):
        return {}
    counts = {str(k): v for k, v in regime_days.items() if isinstance(v, int)}
    total = sum(counts.values())
    return {key: value / total for key, value in counts.items()} if total else {}


def falsified_warnings(
    records: Sequence[Dated], hypotheses: Sequence[Row], closed: Collection[object]
) -> list[dict[str, str]]:
    """One warning per hypothesis not closed by a decision whose `chain` a
    regime record lists under `falsified`. O(R C + H)."""
    fired: dict[str, str] = {}
    for record in records:
        for chain in record.falsified:
            fired[chain] = record.id
    return [
        {
            "hypothesis": str(h.get("id")),
            "strategy": str(h.get("strategy")),
            "chain": str(h.get("chain")),
            "regime": fired[str(h.get("chain"))],
            "problem": "chain falsifier fired; write one objection pad entry",
        }
        for h in hypotheses
        if str(h.get("chain")) in fired and h.get("id") not in closed
    ]
